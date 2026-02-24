"""
Memory Service - Handles conversation memory storage using Supabase pgvector.
"""
from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import get_logger, truncate_text
from typing import List, Dict, Any, Optional
import time
import uuid
import numpy as np

logger = get_logger("memory")

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not available for memory service")


class MemoryService:
    """
    Memory Service using Supabase pgvector for persistent memory storage.
    Falls back to in-memory storage if Supabase is not configured.
    """
    
    def __init__(self):
        self._fallback_memories: List[Dict[str, Any]] = []
        self._memories_created_count = 0
        self.client: Optional[Any] = None
        self._using_fallback = True
        self.embedding_service = EmbeddingService()
        
        if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_KEY:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                self._using_fallback = False
                logger.info("Memory Service: Supabase client initialized")
            except Exception as e:
                logger.warning(f"Memory Service: Failed to initialize Supabase: {e}")
                self.client = None
                self._using_fallback = True
        else:
            logger.info("Memory Service: Using in-memory fallback")
    
    @property
    def memories_created_count(self) -> int:
        return self._memories_created_count
    
    async def add_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Add conversation to memory with embeddings."""
        start_time = time.perf_counter()
        logger.info("[MEMORY] Storing new memory...")
        logger.info(f"  └─ User ID: {user_id[:8]}...")
        logger.info(f"  └─ Messages: {len(messages)} message(s)")
        
        # Create memory content from messages
        memory_content = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        try:
            if self.client:
                # Get embedding for the memory
                embeddings = await self.embedding_service.get_embeddings(memory_content)
                embedding = embeddings[0] if embeddings else None
                
                memory_id = str(uuid.uuid4())
                memory_data = {
                    "id": memory_id,
                    "user_id": user_id,
                    "content": memory_content,
                    "embedding": embedding,
                    "metadata": metadata or {}
                }
                
                response = self.client.table("memories").insert(memory_data).execute()
                
                if response.data:
                    self._memories_created_count += 1
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.info(f"  └─ Memory stored in Supabase ({elapsed:.0f}ms)")
                    return response.data
                else:
                    logger.error("  └─ Failed to store memory in Supabase")
                    return []
            else:
                # Fallback: simple in-memory storage
                logger.info("  └─ Mode: FALLBACK (in-memory)")
                memory_item = {
                    "id": str(uuid.uuid4()),
                    "content": memory_content,
                    "metadata": metadata or {},
                    "user_id": user_id
                }
                self._fallback_memories.append(memory_item)
                self._memories_created_count += 1
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(f"  └─ Memory stored in fallback ({elapsed:.0f}ms)")
                return [memory_item]
                
        except Exception as e:
            logger.error(f"  └─ Memory add error: {e}")
            return []
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search relevant memories using semantic similarity."""
        start_time = time.perf_counter()
        logger.info("[MEMORY] Searching memories...")
        logger.info(f"  └─ Query: \"{truncate_text(query, 50)}\"")
        logger.info(f"  └─ User ID: {user_id[:8]}...")
        
        try:
            if self.client:
                # Get query embedding
                query_embeddings = await self.embedding_service.get_embeddings(query)
                query_embedding = query_embeddings[0] if query_embeddings else None
                
                if not query_embedding:
                    logger.warning("  └─ Failed to get query embedding")
                    return []
                
                # Try RPC function first
                try:
                    response = self.client.rpc(
                        "match_memories",
                        {
                            "query_embedding": query_embedding,
                            "match_user_id": user_id,
                            "match_count": limit
                        }
                    ).execute()
                    
                    if response.data:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        logger.info(f"  └─ Found {len(response.data)} memories via RPC ({elapsed:.0f}ms)")
                        return [{"memory": m["content"], "metadata": m.get("metadata", {}), "id": m["id"]} for m in response.data]
                except Exception as rpc_error:
                    logger.warning(f"  └─ RPC failed, using client-side search: {rpc_error}")
                
                # Fallback to client-side search
                response = self.client.table("memories") \
                    .select("id, content, metadata, embedding") \
                    .eq("user_id", user_id) \
                    .execute()
                
                if response.data:
                    results = self._client_side_search(query_embedding, response.data, limit)
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.info(f"  └─ Found {len(results)} memories via client-side ({elapsed:.0f}ms)")
                    return results
                return []
            else:
                # Fallback: simple text search
                logger.info("  └─ Mode: FALLBACK (text search)")
                results = []
                query_lower = query.lower()
                for mem in self._fallback_memories:
                    if mem.get("user_id") == user_id and query_lower in mem.get("content", "").lower():
                        results.append({"memory": mem["content"], "metadata": mem.get("metadata", {}), "id": mem.get("id")})
                results = results[:limit]
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(f"  └─ Found {len(results)} memories ({elapsed:.0f}ms)")
                return results
                
        except Exception as e:
            logger.error(f"  └─ Memory search error: {e}")
            return []
    
    def _client_side_search(
        self,
        query_embedding: List[float],
        memories: List[Dict],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Client-side vector search when RPC is not available."""
        if not memories:
            return []
        
        query_vec = np.array(query_embedding)
        results = []
        
        for mem in memories:
            embedding = mem.get("embedding")
            if embedding:
                doc_vec = np.array(embedding)
                similarity = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-10)
                results.append({
                    "memory": mem["content"],
                    "metadata": mem.get("metadata", {}),
                    "id": mem["id"],
                    "similarity": float(similarity)
                })
        
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:limit]
    
    async def get_all_memories(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all memories for user."""
        logger.info(f"[MEMORY] Getting all memories for user: {user_id[:8]}...")
        
        try:
            if self.client:
                response = self.client.table("memories") \
                    .select("id, content, metadata") \
                    .eq("user_id", user_id) \
                    .execute()
                
                memories = response.data or []
                logger.info(f"  └─ Found {len(memories)} memories (Supabase)")
                return [{"id": m["id"], "memory": m["content"], "metadata": m.get("metadata", {})} for m in memories]
            else:
                results = [m for m in self._fallback_memories if m.get("user_id") == user_id]
                logger.info(f"  └─ Found {len(results)} memories (fallback)")
                return results
        except Exception as e:
            logger.error(f"  └─ Memory get_all error: {e}")
            return []
    
    async def delete_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> bool:
        """Delete a memory."""
        logger.info(f"[MEMORY] Deleting memory: {memory_id[:8]}...")
        
        try:
            if self.client:
                self.client.table("memories") \
                    .delete() \
                    .eq("id", memory_id) \
                    .eq("user_id", user_id) \
                    .execute()
                logger.info("  └─ Memory deleted (Supabase)")
                return True
            else:
                self._fallback_memories = [m for m in self._fallback_memories if m.get("id") != memory_id]
                logger.info("  └─ Memory deleted (fallback)")
                return True
        except Exception as e:
            logger.error(f"  └─ Memory delete error: {e}")
            return False
    
    async def clear_user_memories(self, user_id: str) -> bool:
        """Clear all memories for a user."""
        logger.info(f"[MEMORY] Clearing all memories for user: {user_id[:8]}...")
        
        try:
            if self.client:
                self.client.table("memories") \
                    .delete() \
                    .eq("user_id", user_id) \
                    .execute()
                logger.info("  └─ All memories cleared (Supabase)")
                return True
            else:
                self._fallback_memories = [m for m in self._fallback_memories if m.get("user_id") != user_id]
                logger.info("  └─ All memories cleared (fallback)")
                return True
        except Exception as e:
            logger.error(f"  └─ Clear memories error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "using_fallback": self._using_fallback,
            "memories_created_session": self._memories_created_count,
            "fallback_memories_count": len(self._fallback_memories) if self._using_fallback else 0
        }
