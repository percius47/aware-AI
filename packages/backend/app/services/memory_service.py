from mem0 import Memory
from app.core.config import settings
from app.core.logging_config import get_logger, Timer, truncate_text
from typing import List, Dict, Any, Optional
import os
import time

# Set OPENAI_API_KEY environment variable at module level (before any Mem0 initialization)
if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

logger = get_logger("mem0")

class MemoryService:
    def __init__(self):
        self._fallback_memories = []
        self._memories_created_count = 0  # Track memories created this session
        
        # Check if OpenAI API key is available
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
            logger.warning("OPENAI_API_KEY not set. Mem0 requires OpenAI for embeddings. Using fallback mode.")
            self.memory = None
            self._using_fallback = True
            return
        
        try:
            # Configure Mem0 with explicit LLM and embedder settings
            config = {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": settings.OPENAI_MODEL,
                        "api_key": settings.OPENAI_API_KEY
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": settings.OPENAI_EMBEDDING_MODEL,
                        "api_key": settings.OPENAI_API_KEY
                    }
                },
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "memories",
                        "path": settings.CHROMA_PERSIST_DIR
                    }
                }
            }
            
            self.memory = Memory.from_config(config)
            self._using_fallback = False
            logger.info("Mem0 initialized successfully")
            logger.info(f"  └─ Vector store: ChromaDB at {settings.CHROMA_PERSIST_DIR}")
            logger.info(f"  └─ Embedder: OpenAI {settings.OPENAI_EMBEDDING_MODEL}")
        except Exception as e:
            logger.warning(f"Mem0 initialization failed: {e}. Using fallback mode.")
            self.memory = None
            self._using_fallback = True
    
    @property
    def memories_created_count(self) -> int:
        """Get count of memories created this session."""
        return self._memories_created_count
    
    async def add_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Add conversation to memory"""
        start_time = time.perf_counter()
        logger.info("[MEM0] Storing new memory...")
        logger.info(f"  └─ User ID: {user_id}")
        logger.info(f"  └─ Messages: {len(messages)} message(s)")
        
        try:
            if self.memory is None:
                # Fallback: simple storage
                logger.info("  └─ Mode: FALLBACK (in-memory)")
                memory_item = {
                    "memory": "\n".join([f"{m['role']}: {m['content']}" for m in messages]),
                    "metadata": metadata or {},
                    "user_id": user_id
                }
                self._fallback_memories.append(memory_item)
                self._memories_created_count += 1
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(f"  └─ Memory stored successfully ({elapsed:.0f}ms)")
                return [memory_item]
            
            # Extract key information from conversation
            logger.info("  └─ Mode: MEM0 (persistent)")
            conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            logger.info(f"  └─ Content preview: \"{truncate_text(conversation_text, 60)}\"")
            
            memories = self.memory.add(
                messages=[{"role": "user", "content": conversation_text}],
                user_id=user_id,
                metadata=metadata or {}
            )
            self._memories_created_count += 1
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"  └─ Memory stored successfully ({elapsed:.0f}ms)")
            logger.info(f"  └─ Total memories created this session: {self._memories_created_count}")
            return memories
        except Exception as e:
            logger.error(f"  └─ Memory add error: {e}")
            return []
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search relevant memories"""
        start_time = time.perf_counter()
        logger.info("[MEM0] Searching memories from past conversations...")
        logger.info(f"  └─ Query: \"{truncate_text(query, 50)}\"")
        logger.info(f"  └─ User ID: {user_id}")
        logger.info(f"  └─ Limit: {limit}")
        
        try:
            if self.memory is None:
                # Fallback: simple text search
                logger.info("  └─ Mode: FALLBACK (in-memory search)")
                results = []
                query_lower = query.lower()
                for mem in self._fallback_memories:
                    if mem.get("user_id") == user_id and query_lower in mem.get("memory", "").lower():
                        results.append(mem)
                results = results[:limit]
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(f"  └─ Found {len(results)} memories ({elapsed:.0f}ms)")
                return results
            
            logger.info("  └─ Mode: MEM0 (semantic search via embeddings)")
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"  └─ Found {len(results) if results else 0} relevant memories ({elapsed:.0f}ms)")
            
            # Log memory details
            if results:
                for i, mem in enumerate(results[:3]):  # Show first 3
                    if isinstance(mem, dict):
                        content = mem.get("memory", mem.get("content", ""))
                        score = mem.get("score", mem.get("relevance", "N/A"))
                        logger.info(f"  └─ Memory {i+1}: \"{truncate_text(str(content), 40)}\" (score: {score})")
                    else:
                        logger.info(f"  └─ Memory {i+1}: {truncate_text(str(mem), 40)}")
            else:
                logger.info("  └─ No relevant memories found for this query")
            
            return results if results else []
        except Exception as e:
            logger.error(f"  └─ Memory search error: {e}")
            return []
    
    async def get_all_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all memories for user"""
        logger.info(f"[MEM0] Getting all memories for user: {user_id}")
        try:
            if self.memory is None:
                results = [m for m in self._fallback_memories if m.get("user_id") == user_id]
                logger.info(f"  └─ Found {len(results)} memories (fallback mode)")
                return results
            
            memories = self.memory.get_all(user_id=user_id)
            logger.info(f"  └─ Found {len(memories) if memories else 0} memories")
            return memories if memories else []
        except Exception as e:
            logger.error(f"  └─ Memory get_all error: {e}")
            return []
    
    async def delete_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> bool:
        """Delete a memory"""
        logger.info(f"[MEM0] Deleting memory: {memory_id}")
        try:
            if self.memory is None:
                self._fallback_memories = [m for m in self._fallback_memories if m.get("id") != memory_id]
                logger.info("  └─ Memory deleted (fallback mode)")
                return True
            
            self.memory.delete(memory_ids=[memory_id], user_id=user_id)
            logger.info("  └─ Memory deleted successfully")
            return True
        except Exception as e:
            logger.error(f"  └─ Memory delete error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "using_fallback": self._using_fallback,
            "memories_created_session": self._memories_created_count,
            "fallback_memories_count": len(self._fallback_memories) if self._using_fallback else 0
        }
