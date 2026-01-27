from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse, DocumentProcessResponse
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService
from app.services.document_processor import DocumentProcessor
from app.services.memory_compression import MemoryCompressionService
from app.services.conversation_service import ConversationService
from app.core.logging_config import get_logger, log_separator, truncate_text
from app.utils.helpers import (
    generate_conversation_id,
    build_context_from_memories,
    build_context_from_rag_results
)
import json
import uuid
import time
import sys

router = APIRouter()
logger = get_logger("chat")

llm_service = LLMService()
rag_service = RAGService()
memory_service = MemoryService()
doc_processor = DocumentProcessor()
compression_service = MemoryCompressionService()
conversation_service = ConversationService()

# Debug: Check the conversation_service state right after creation
print(f"[ROUTES INIT] conversation_service created, id={id(conversation_service)}", flush=True)
print(f"[ROUTES INIT] is_persistent={conversation_service.is_persistent}", flush=True)
print(f"[ROUTES INIT] client={conversation_service.client}", flush=True)

# Store conversations in memory (for session-based quick access)
conversations = {}
# Track session stats
session_stats = {
    "messages_sent": 0,
    "conversations_started": 0
}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with RAG and memory"""
    request_start = time.perf_counter()
    
    try:
        log_separator(logger)
        logger.info("[CHAT] New chat request received")
        
        conversation_id = request.conversation_id or generate_conversation_id()
        is_new_conversation = conversation_id not in conversations
        
        logger.info(f"  └─ Conversation ID: {conversation_id[:8]}...")
        logger.info(f"  └─ Message: \"{truncate_text(request.message, 50)}\"")
        logger.info(f"  └─ Stream: {request.stream}")
        logger.info(f"  └─ New conversation: {is_new_conversation}")
        
        # Initialize conversation if new
        user_id = "default_user"  # In production, get from auth
        if is_new_conversation:
            session_stats["conversations_started"] += 1
            
            # Create thread in persistent storage (Supabase or fallback)
            # IMPORTANT: Use the thread ID returned from create_thread, not the frontend-generated ID
            title = conversation_service.generate_title_from_message(request.message)
            thread = await conversation_service.create_thread(user_id, title)
            if thread and thread.get("id"):
                conversation_id = thread["id"]  # Use the actual thread ID
                logger.info(f"  └─ Created persistent thread: {conversation_id[:8]}... with title: \"{title[:30]}...\"")
            else:
                logger.warning(f"  └─ Failed to create persistent thread, using generated ID: {conversation_id[:8]}...")
            
            conversations[conversation_id] = []
        
        # Add user message
        conversations[conversation_id].append({
            "role": "user",
            "content": request.message
        })
        session_stats["messages_sent"] += 1
        
        # Save user message to Supabase
        await conversation_service.add_message(conversation_id, "user", request.message)
        
        # Get relevant memories
        logger.info("[MEMORY] Retrieving relevant memories...")
        mem_start = time.perf_counter()
        memories = await memory_service.search_memories(
            user_id=user_id,
            query=request.message,
            limit=5
        )
        mem_elapsed = (time.perf_counter() - mem_start) * 1000
        
        # Get relevant documents from RAG
        logger.info("[RAG] Searching knowledge base...")
        rag_start = time.perf_counter()
        rag_results = await rag_service.search(
            query=request.message,
            n_results=3
        )
        rag_elapsed = (time.perf_counter() - rag_start) * 1000
        logger.info(f"  └─ Found {len(rag_results)} documents ({rag_elapsed:.0f}ms)")
        
        # Build context
        memory_context = build_context_from_memories(memories)
        rag_context = build_context_from_rag_results(rag_results)
        
        logger.info("[CONTEXT] Building LLM context...")
        logger.info(f"  └─ Memory context: {len(memory_context)} chars")
        logger.info(f"  └─ RAG context: {len(rag_context)} chars")
        logger.info(f"  └─ Conversation history: {len(conversations[conversation_id])} messages")
        
        # Build messages for LLM
        system_message = """You are an AI assistant with access to the user's memory and knowledge base.
        Use the provided context to give personalized and informed responses.
        Be conversational and remember details from previous interactions."""
        
        messages = [{"role": "system", "content": system_message}]
        
        if memory_context:
            messages.append({
                "role": "system",
                "content": f"User's relevant memories:\n{memory_context}"
            })
        
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"Relevant knowledge:\n{rag_context}"
            })
        
        # Add conversation history (last 10 messages)
        messages.extend(conversations[conversation_id][-10:])
        
        # Generate response
        logger.info("[LLM] Sending request to OpenAI...")
        logger.info(f"  └─ Total messages: {len(messages)}")
        
        if request.stream:
            async def generate():
                llm_start = time.perf_counter()
                full_response = ""
                chunk_count = 0
                async for chunk in llm_service.generate_response(messages, stream=True):
                    full_response += chunk
                    chunk_count += 1
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                llm_elapsed = (time.perf_counter() - llm_start) * 1000
                logger.info(f"  └─ Response received ({chunk_count} chunks, {llm_elapsed:.0f}ms)")
                logger.info(f"  └─ Response length: {len(full_response)} chars")
                
                # Store assistant response
                conversations[conversation_id].append({
                    "role": "assistant",
                    "content": full_response
                })
                
                # Save assistant message to Supabase
                await conversation_service.add_message(conversation_id, "assistant", full_response)
                
                # Add to memory
                logger.info("[POST] Storing conversation to memory...")
                await memory_service.add_memory(
                    user_id=user_id,
                    messages=conversations[conversation_id][-2:],  # Last user + assistant
                    metadata={"conversation_id": conversation_id}
                )
                
                # Add conversation to RAG for semantic search
                await rag_service.add_conversation_to_rag(
                    conversation_id=conversation_id,
                    messages=conversations[conversation_id]
                )
                
                total_elapsed = (time.perf_counter() - request_start) * 1000
                log_separator(logger)
                logger.info(f"[CHAT] Request completed ({total_elapsed:.0f}ms total)")
                
                yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            llm_start = time.perf_counter()
            response = await llm_service.generate_non_streaming(messages)
            llm_elapsed = (time.perf_counter() - llm_start) * 1000
            logger.info(f"  └─ Response received ({llm_elapsed:.0f}ms)")
            logger.info(f"  └─ Response length: {len(response)} chars")
            
            # Store response
            conversations[conversation_id].append({
                "role": "assistant",
                "content": response
            })
            
            # Save assistant message to Supabase
            await conversation_service.add_message(conversation_id, "assistant", response)
            
            # Add to memory
            logger.info("[POST] Storing conversation to memory...")
            await memory_service.add_memory(
                user_id=user_id,
                messages=conversations[conversation_id][-2:],
                metadata={"conversation_id": conversation_id}
            )
            
            # Safely extract sources from rag_results
            sources = []
            for r in rag_results:
                if isinstance(r, dict):
                    sources.append(r.get("metadata", {}))
                else:
                    sources.append({})
            
            # Safely format memory_used
            memory_used = []
            for m in memories:
                if isinstance(m, dict):
                    memory_used.append(m)
                elif isinstance(m, str):
                    memory_used.append({"content": m})
                else:
                    memory_used.append({"content": str(m) if m else ""})
            
            total_elapsed = (time.perf_counter() - request_start) * 1000
            log_separator(logger)
            logger.info(f"[CHAT] Request completed ({total_elapsed:.0f}ms total)")
            
            return ChatResponse(
                response=response,
                conversation_id=conversation_id,
                sources=sources,
                memory_used=memory_used
            )
    except ValueError as e:
        logger.error(f"[CHAT] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@router.post("/upload", response_model=DocumentProcessResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document"""
    try:
        content = await file.read()
        result = await doc_processor.process_file(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        return DocumentProcessResponse(
            document_id=str(uuid.uuid4()),
            chunks=result["chunks"],
            status="processed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/compress")
async def compress_memory(user_id: str = "default_user"):
    """Compress and summarize memories"""
    result = await compression_service.summarize_memories(user_id)
    return result

@router.get("/memory/search")
async def search_memory(query: str, user_id: str = "default_user", limit: int = 5):
    """Search memories"""
    results = await memory_service.search_memories(user_id, query, limit)
    return {"results": results}

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversations[conversation_id]}

@router.get("/stats")
async def get_stats(user_id: str = "default_user"):
    """Get session and lifetime statistics for the dashboard"""
    memory_stats = memory_service.get_stats()
    doc_stats = rag_service.get_documents_stats()
    thread_count = await conversation_service.get_thread_count(user_id)
    
    return {
        "session": {
            "messages_sent": session_stats["messages_sent"],
            "active_threads": len(conversations)
        },
        "lifetime": {
            "total_embeddings": rag_service.get_total_embeddings_count(),
            "documents_uploaded": doc_stats["unique_documents"],
            "document_chunks": doc_stats["total_chunks"],
            "total_threads": thread_count
        },
        "memory": {
            "memories_created": memory_stats["memories_created_session"],
            "using_fallback": memory_stats["using_fallback"]
        }
    }

# ============================================================
# Thread Management Endpoints
# ============================================================

@router.get("/debug/supabase")
async def debug_supabase():
    """Debug endpoint to check Supabase status"""
    from app.services.conversation_service import SUPABASE_AVAILABLE
    from app.core.config import settings
    return {
        "supabase_available": SUPABASE_AVAILABLE,
        "supabase_url_set": bool(settings.SUPABASE_URL),
        "supabase_url": settings.SUPABASE_URL[:40] + "..." if settings.SUPABASE_URL else None,
        "supabase_key_set": bool(settings.SUPABASE_KEY),
        "client_exists": conversation_service.client is not None,
        "client_type": str(type(conversation_service.client)),
        "is_persistent": conversation_service.is_persistent,
        "fallback_threads_count": len(conversation_service._fallback_threads),
        "service_id": id(conversation_service)
    }

@router.get("/threads")
async def list_threads(user_id: str = "default_user", limit: int = 50):
    """List all conversation threads for a user"""
    threads = await conversation_service.list_threads(user_id, limit)
    return {
        "threads": threads,
        "count": len(threads),
        "is_persistent": conversation_service.is_persistent
    }

@router.get("/threads/{conversation_id}")
async def get_thread(conversation_id: str):
    """Get a specific thread with all its messages"""
    thread = await conversation_service.get_thread(conversation_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@router.post("/threads")
async def create_thread(user_id: str = "default_user", title: str = "New Chat"):
    """Create a new conversation thread"""
    thread = await conversation_service.create_thread(user_id, title)
    if not thread:
        raise HTTPException(status_code=500, detail="Failed to create thread")
    return thread

@router.delete("/threads/{conversation_id}")
async def delete_thread(conversation_id: str):
    """Delete a conversation thread"""
    success = await conversation_service.delete_thread(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete thread")
    
    # Also remove from in-memory cache if exists
    if conversation_id in conversations:
        del conversations[conversation_id]
    
    return {"status": "deleted", "conversation_id": conversation_id}
