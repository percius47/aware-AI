from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService
from app.utils.helpers import generate_conversation_id, build_context_from_memories
from app.core.logging_config import get_logger, log_separator, truncate_text
import json
import time

websocket_router = APIRouter()
logger = get_logger("websocket")

llm_service = LLMService()
rag_service = RAGService()
memory_service = MemoryService()

@websocket_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    conversation_id = generate_conversation_id()
    conversation_history = []
    
    log_separator(logger)
    logger.info(f"[WS] Connection accepted")
    logger.info(f"  └─ Conversation ID: {conversation_id[:8]}...")
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            request_start = time.perf_counter()
            log_separator(logger)
            logger.info(f"[WS] Message received")
            logger.info(f"  └─ Message: \"{truncate_text(user_message, 50)}\"")
            
            # Add user message
            conversation_history.append({"role": "user", "content": user_message})
            
            # Get memories and RAG context
            user_id = "default_user"
            
            logger.info("[MEMORY] Retrieving relevant memories...")
            mem_start = time.perf_counter()
            memories = await memory_service.search_memories(user_id, user_message, limit=5)
            mem_elapsed = (time.perf_counter() - mem_start) * 1000
            logger.info(f"  └─ Found {len(memories)} memories ({mem_elapsed:.0f}ms)")
            
            logger.info("[RAG] Searching knowledge base...")
            rag_start = time.perf_counter()
            rag_results = await rag_service.search(user_message, n_results=3)
            rag_elapsed = (time.perf_counter() - rag_start) * 1000
            logger.info(f"  └─ Found {len(rag_results)} documents ({rag_elapsed:.0f}ms)")
            
            # Build context
            memory_context = build_context_from_memories(memories)
            
            logger.info("[CONTEXT] Building LLM context...")
            logger.info(f"  └─ Memory context: {len(memory_context)} chars")
            logger.info(f"  └─ Conversation history: {len(conversation_history)} messages")
            
            # Build messages
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."}
            ]
            if memory_context:
                messages.append({
                    "role": "system",
                    "content": f"User context: {memory_context}"
                })
            messages.extend(conversation_history[-10:])
            
            # Stream response
            logger.info("[LLM] Sending request to OpenAI (streaming)...")
            llm_start = time.perf_counter()
            full_response = ""
            chunk_count = 0
            async for chunk in llm_service.generate_response(messages, stream=True):
                full_response += chunk
                chunk_count += 1
                await websocket.send_text(json.dumps({"type": "chunk", "content": chunk}))
            
            llm_elapsed = (time.perf_counter() - llm_start) * 1000
            logger.info(f"  └─ Response received ({chunk_count} chunks, {llm_elapsed:.0f}ms)")
            logger.info(f"  └─ Response length: {len(full_response)} chars")
            
            conversation_history.append({"role": "assistant", "content": full_response})
            
            # Save to memory
            logger.info("[POST] Storing conversation to memory...")
            await memory_service.add_memory(
                user_id=user_id,
                messages=conversation_history[-2:],
                metadata={"conversation_id": conversation_id}
            )
            
            await websocket.send_text(json.dumps({"type": "done"}))
            
            total_elapsed = (time.perf_counter() - request_start) * 1000
            log_separator(logger)
            logger.info(f"[WS] Request completed ({total_elapsed:.0f}ms total)")
            
    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected (conversation: {conversation_id[:8]}...)")
