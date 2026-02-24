from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse, DocumentProcessResponse
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService
from app.services.document_processor import DocumentProcessor
from app.services.memory_compression import MemoryCompressionService
from app.services.conversation_service import ConversationService
from app.services.agent_service import AgentOrchestrator
from app.core.logging_config import get_logger, log_separator, truncate_text
from app.core.auth import get_current_user, CurrentUser
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
# Structure: {user_id: {conversation_id: [messages]}}
conversations: dict = {}
# Track session stats per user
session_stats: dict = {}

def get_user_conversations(user_id: str) -> dict:
    """Get or create conversations dict for a user."""
    if user_id not in conversations:
        conversations[user_id] = {}
    return conversations[user_id]

def get_user_stats(user_id: str) -> dict:
    """Get or create stats dict for a user."""
    if user_id not in session_stats:
        session_stats[user_id] = {
            "messages_sent": 0,
            "conversations_started": 0
        }
    return session_stats[user_id]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Chat endpoint with agentic tool-calling architecture"""
    request_start = time.perf_counter()
    
    try:
        log_separator(logger)
        logger.info("[CHAT] New chat request received (Agent Mode)")
        
        # Use authenticated user's ID for memory isolation
        user_id = current_user.id
        user_convs = get_user_conversations(user_id)
        user_stats = get_user_stats(user_id)
        
        conversation_id = request.conversation_id or generate_conversation_id()
        is_new_conversation = conversation_id not in user_convs
        
        logger.info(f"  └─ Conversation ID: {conversation_id[:8]}...")
        logger.info(f"  └─ Message: \"{truncate_text(request.message, 50)}\"")
        logger.info(f"  └─ Stream: {request.stream}")
        logger.info(f"  └─ New conversation (in memory): {is_new_conversation}")
        
        # If not in memory but conversation_id was provided, check persistent storage first
        if is_new_conversation and request.conversation_id:
            existing_thread = await conversation_service.get_thread(conversation_id)
            if existing_thread:
                user_convs[conversation_id] = [
                    {"role": m["role"], "content": m["content"]}
                    for m in existing_thread.get("messages", [])
                ]
                is_new_conversation = False
                logger.info(f"  └─ Loaded existing thread: {conversation_id[:8]}... ({len(user_convs[conversation_id])} messages)")
        
        if is_new_conversation:
            user_stats["conversations_started"] += 1
            title = conversation_service.generate_title_from_message(request.message)
            thread = await conversation_service.create_thread(user_id, title)
            if thread and thread.get("id"):
                conversation_id = thread["id"]
                logger.info(f"  └─ Created thread: {conversation_id[:8]}...")
            user_convs[conversation_id] = []
        
        # Add user message to cache
        user_convs[conversation_id].append({
            "role": "user",
            "content": request.message
        })
        user_stats["messages_sent"] += 1
        
        # Save user message to Supabase
        await conversation_service.add_message(conversation_id, "user", request.message)
        
        # Create agent orchestrator
        agent = AgentOrchestrator(llm_service=llm_service)
        
        if request.stream:
            async def generate():
                full_response = ""
                is_clarification = False
                
                async for event in agent.process_query(
                    query=request.message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_history=user_convs[conversation_id][:-1]  # Exclude current message
                ):
                    # Emit the event as SSE
                    yield f"data: {json.dumps(event.to_dict())}\n\n"
                    
                    # Track response chunks
                    if event.type == "chunk":
                        full_response += event.content or ""
                    elif event.type == "clarification":
                        is_clarification = True
                
                # Only store response if we got an actual response (not clarification)
                if full_response and not is_clarification:
                    # Store assistant response
                    user_convs[conversation_id].append({
                        "role": "assistant",
                        "content": full_response
                    })
                    
                    # Save to Supabase
                    await conversation_service.add_message(conversation_id, "assistant", full_response)
                    
                    # Add to memory
                    await memory_service.add_memory(
                        user_id=user_id,
                        messages=user_convs[conversation_id][-2:],
                        metadata={"conversation_id": conversation_id}
                    )
                
                total_elapsed = (time.perf_counter() - request_start) * 1000
                log_separator(logger)
                logger.info(f"[CHAT] Request completed ({total_elapsed:.0f}ms total)")
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            # Non-streaming mode - collect all events and return final response
            full_response = ""
            events = []
            
            async for event in agent.process_query(
                query=request.message,
                user_id=user_id,
                conversation_id=conversation_id,
                conversation_history=user_convs[conversation_id][:-1]
            ):
                events.append(event.to_dict())
                if event.type == "chunk":
                    full_response += event.content or ""
            
            if full_response:
                user_convs[conversation_id].append({
                    "role": "assistant",
                    "content": full_response
                })
                await conversation_service.add_message(conversation_id, "assistant", full_response)
                await memory_service.add_memory(
                    user_id=user_id,
                    messages=user_convs[conversation_id][-2:],
                    metadata={"conversation_id": conversation_id}
                )
            
            total_elapsed = (time.perf_counter() - request_start) * 1000
            log_separator(logger)
            logger.info(f"[CHAT] Request completed ({total_elapsed:.0f}ms total)")
            
            return ChatResponse(
                response=full_response,
                conversation_id=conversation_id,
                sources=[],
                memory_used=[]
            )
    except ValueError as e:
        logger.error(f"[CHAT] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@router.post("/upload", response_model=DocumentProcessResponse)
async def upload_document(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
    """Upload and process document"""
    try:
        content = await file.read()
        result = await doc_processor.process_file(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            user_id=current_user.id
        )
        
        return DocumentProcessResponse(
            document_id=str(uuid.uuid4()),
            chunks=result["chunks"],
            status="processed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/compress")
async def compress_memory(current_user: CurrentUser = Depends(get_current_user)):
    """Compress and summarize memories"""
    result = await compression_service.summarize_memories(current_user.id)
    return result

@router.get("/memory/search")
async def search_memory(query: str, limit: int = 5, current_user: CurrentUser = Depends(get_current_user)):
    """Search memories"""
    results = await memory_service.search_memories(current_user.id, query, limit)
    return {"results": results}

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get conversation history"""
    user_convs = get_user_conversations(current_user.id)
    if conversation_id not in user_convs:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": user_convs[conversation_id]}

@router.get("/stats")
async def get_stats(current_user: CurrentUser = Depends(get_current_user)):
    """Get session and lifetime statistics for the dashboard"""
    memory_stats = memory_service.get_stats()
    doc_stats = rag_service.get_documents_stats(user_id=current_user.id)
    thread_count = await conversation_service.get_thread_count(current_user.id)
    user_stats = get_user_stats(current_user.id)
    user_convs = get_user_conversations(current_user.id)
    
    return {
        "session": {
            "messages_sent": user_stats["messages_sent"],
            "active_threads": len(user_convs)
        },
        "lifetime": {
            "total_embeddings": rag_service.get_total_embeddings_count(user_id=current_user.id),
            "documents_uploaded": doc_stats["unique_documents"],
            "document_chunks": doc_stats["total_chunks"],
            "document_filenames": doc_stats.get("filenames", []),
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
async def list_threads(limit: int = 50, current_user: CurrentUser = Depends(get_current_user)):
    """List all conversation threads for a user"""
    threads = await conversation_service.list_threads(current_user.id, limit)
    return {
        "threads": threads,
        "count": len(threads),
        "is_persistent": conversation_service.is_persistent
    }

@router.get("/threads/{conversation_id}")
async def get_thread(conversation_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific thread with all its messages"""
    thread = await conversation_service.get_thread(conversation_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@router.post("/threads")
async def create_thread(title: str = "New Chat", current_user: CurrentUser = Depends(get_current_user)):
    """Create a new conversation thread"""
    thread = await conversation_service.create_thread(current_user.id, title)
    if not thread:
        raise HTTPException(status_code=500, detail="Failed to create thread")
    return thread

@router.delete("/threads/{conversation_id}")
async def delete_thread(conversation_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete a conversation thread"""
    success = await conversation_service.delete_thread(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete thread")
    
    # Also remove from in-memory cache if exists
    user_convs = get_user_conversations(current_user.id)
    if conversation_id in user_convs:
        del user_convs[conversation_id]
    
    return {"status": "deleted", "conversation_id": conversation_id}

@router.delete("/documents/{filename:path}")
async def delete_document(filename: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete a specific uploaded document by filename"""
    logger.info(f"[DOCUMENTS] Deleting document '{filename}' for user {current_user.id[:8]}...")
    
    try:
        success = rag_service.delete_document_by_filename(current_user.id, filename)
        if success:
            return {"status": "deleted", "filename": filename}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
    except Exception as e:
        logger.error(f"[DOCUMENTS] Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.delete("/reset-all")
async def reset_all_data(current_user: CurrentUser = Depends(get_current_user)):
    """
    Reset ALL data for the current user: threads, messages, memories, and documents.
    WARNING: This action is irreversible!
    """
    logger.warning(f"[RESET] User {current_user.id} initiated full data reset")
    
    results = {
        "threads_deleted": 0,
        "memories_cleared": False,
        "documents_cleared": False,
        "local_cache_cleared": False
    }
    
    try:
        # 1. Delete all threads (which cascades to messages in Supabase)
        threads = await conversation_service.list_threads(current_user.id, limit=1000)
        for thread in threads:
            await conversation_service.delete_thread(thread["id"])
            results["threads_deleted"] += 1
        
        # 2. Clear all memories for the user
        try:
            await memory_service.clear_user_memories(current_user.id)
            results["memories_cleared"] = True
        except Exception as e:
            logger.warning(f"[RESET] Failed to clear memories: {e}")
        
        # 3. Clear RAG documents/embeddings for this user only
        try:
            rag_service.clear_user_documents(current_user.id)
            results["documents_cleared"] = True
        except Exception as e:
            logger.warning(f"[RESET] Failed to clear documents: {e}")
        
        # 4. Clear local in-memory cache for this user only
        user_convs = get_user_conversations(current_user.id)
        user_convs.clear()
        user_stats = get_user_stats(current_user.id)
        user_stats["messages_sent"] = 0
        user_stats["conversations_started"] = 0
        results["local_cache_cleared"] = True
        
        logger.info(f"[RESET] Complete. Results: {results}")
        return {
            "status": "success",
            "message": "All data has been reset",
            "details": results
        }
        
    except Exception as e:
        logger.error(f"[RESET] Error during reset: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")
