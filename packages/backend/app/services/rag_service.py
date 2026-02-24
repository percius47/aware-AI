"""
RAG Service - Handles document storage and retrieval using Supabase pgvector.
"""
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.core.logging_config import get_logger
import uuid
import json

logger = get_logger("rag")

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not available for RAG service")


class RAGService:
    """
    RAG Service using Supabase pgvector for persistent vector storage.
    Falls back to in-memory storage if Supabase is not configured.
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.client: Optional[Any] = None
        self._fallback_documents: List[Dict[str, Any]] = []
        
        if SUPABASE_AVAILABLE and settings.SUPABASE_URL and settings.SUPABASE_KEY:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("RAG Service: Supabase client initialized")
            except Exception as e:
                logger.warning(f"RAG Service: Failed to initialize Supabase: {e}")
                self.client = None
        else:
            logger.info("RAG Service: Using in-memory fallback")
    
    @property
    def is_persistent(self) -> bool:
        return self.client is not None
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        user_id: str = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to vector store with user isolation."""
        if not user_id:
            logger.warning("add_documents called without user_id")
            return []
        
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        if not metadatas:
            metadatas = [{} for _ in texts]
        
        # Get embeddings
        embeddings = await self.embedding_service.get_embeddings(texts)
        
        if self.client:
            try:
                # Insert documents into Supabase
                documents_to_insert = []
                for i, (text, embedding, metadata, doc_id) in enumerate(zip(texts, embeddings, metadatas, ids)):
                    documents_to_insert.append({
                        "id": doc_id,
                        "user_id": user_id,
                        "content": text,
                        "embedding": embedding,
                        "metadata": metadata
                    })
                
                # Batch insert
                response = self.client.table("documents").insert(documents_to_insert).execute()
                
                if response.data:
                    logger.info(f"Added {len(response.data)} documents for user {user_id[:8]}...")
                    return ids
                else:
                    logger.error("Failed to insert documents into Supabase")
                    return []
                    
            except Exception as e:
                logger.error(f"Error adding documents to Supabase: {e}")
                return []
        else:
            # Fallback: in-memory storage
            for i, (text, embedding, metadata, doc_id) in enumerate(zip(texts, embeddings, metadatas, ids)):
                self._fallback_documents.append({
                    "id": doc_id,
                    "user_id": user_id,
                    "content": text,
                    "embedding": embedding,
                    "metadata": metadata
                })
            logger.info(f"Added {len(texts)} documents to fallback storage")
            return ids
    
    async def search(
        self,
        query: str,
        user_id: str = None,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents filtered by user_id."""
        if not user_id:
            logger.warning("search called without user_id")
            return []
        
        # Get query embedding
        query_embedding = await self.embedding_service.get_embeddings(query)
        query_embedding = query_embedding[0] if isinstance(query_embedding[0], list) else query_embedding
        
        if self.client:
            try:
                # Try RPC function first (faster, requires SQL function setup)
                try:
                    response = self.client.rpc(
                        "match_documents",
                        {
                            "query_embedding": query_embedding,
                            "match_user_id": user_id,
                            "match_count": n_results
                        }
                    ).execute()
                    
                    if response.data:
                        formatted_results = []
                        for doc in response.data:
                            formatted_results.append({
                                "content": doc.get("content", ""),
                                "metadata": doc.get("metadata", {}),
                                "distance": 1 - doc.get("similarity", 0),
                                "id": doc.get("id")
                            })
                        logger.info(f"Found {len(formatted_results)} documents via RPC for user {user_id[:8]}...")
                        return formatted_results
                except Exception as rpc_error:
                    logger.warning(f"RPC search failed, falling back to client-side: {rpc_error}")
                
                # Fallback: Fetch all user documents and search client-side
                response = self.client.table("documents") \
                    .select("id, content, metadata, embedding") \
                    .eq("user_id", user_id) \
                    .execute()
                
                if response.data:
                    return self._client_side_search(query_embedding, response.data, n_results)
                return []
                
            except Exception as e:
                logger.error(f"Error searching documents in Supabase: {e}")
                return self._fallback_search(query_embedding, user_id, n_results)
        else:
            return self._fallback_search(query_embedding, user_id, n_results)
    
    def _client_side_search(
        self,
        query_embedding: List[float],
        documents: List[Dict],
        n_results: int
    ) -> List[Dict[str, Any]]:
        """Client-side vector search when RPC is not available."""
        import numpy as np
        
        if not documents:
            return []
        
        query_vec = np.array(query_embedding)
        results = []
        
        for doc in documents:
            embedding = doc.get("embedding")
            if embedding:
                doc_vec = np.array(embedding)
                similarity = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-10)
                results.append({
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                    "distance": float(1 - similarity),
                    "id": doc["id"]
                })
        
        results.sort(key=lambda x: x["distance"])
        logger.info(f"Found {min(len(results), n_results)} documents via client-side search")
        return results[:n_results]
    
    def _fallback_search(
        self,
        query_embedding: List[float],
        user_id: str,
        n_results: int
    ) -> List[Dict[str, Any]]:
        """Fallback in-memory vector search."""
        import numpy as np
        
        user_docs = [d for d in self._fallback_documents if d.get("user_id") == user_id]
        
        if not user_docs:
            return []
        
        # Calculate cosine similarity
        query_vec = np.array(query_embedding)
        results = []
        
        for doc in user_docs:
            doc_vec = np.array(doc["embedding"])
            similarity = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
            results.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "distance": float(1 - similarity),
                "id": doc["id"]
            })
        
        # Sort by distance (lower is better)
        results.sort(key=lambda x: x["distance"])
        return results[:n_results]
    
    async def add_conversation_to_rag(
        self,
        conversation_id: str,
        messages: List[Dict[str, str]],
        user_id: str = None
    ):
        """Add conversation history to RAG for semantic search."""
        if not user_id:
            logger.warning("add_conversation_to_rag called without user_id")
            return
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        await self.add_documents(
            texts=[conversation_text],
            metadatas=[{
                "type": "conversation",
                "conversation_id": conversation_id,
                "timestamp": str(messages[-1].get("timestamp", ""))
            }],
            user_id=user_id
        )
    
    def get_total_embeddings_count(self, user_id: str = None) -> int:
        """Get total number of embeddings for a user."""
        if self.client and user_id:
            try:
                response = self.client.table("documents") \
                    .select("id", count="exact") \
                    .eq("user_id", user_id) \
                    .execute()
                return response.count or 0
            except Exception as e:
                logger.error(f"Error getting embeddings count: {e}")
                return 0
        else:
            if user_id:
                return len([d for d in self._fallback_documents if d.get("user_id") == user_id])
            return len(self._fallback_documents)
    
    def get_documents_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get document statistics for a user."""
        if self.client and user_id:
            try:
                response = self.client.table("documents") \
                    .select("id, metadata") \
                    .eq("user_id", user_id) \
                    .execute()
                
                filenames = set()
                doc_chunks = 0
                
                for doc in response.data or []:
                    metadata = doc.get("metadata", {})
                    doc_type = metadata.get("type", "")
                    if doc_type in ["pdf", "docx", "text"]:
                        doc_chunks += 1
                        filename = metadata.get("filename")
                        if filename:
                            filenames.add(filename)
                
                return {
                    "total_chunks": doc_chunks,
                    "unique_documents": len(filenames),
                    "filenames": list(filenames)
                }
            except Exception as e:
                logger.error(f"Error getting document stats: {e}")
                return {"total_chunks": 0, "unique_documents": 0, "filenames": [], "error": str(e)}
        else:
            # Fallback
            filenames = set()
            doc_chunks = 0
            
            user_docs = self._fallback_documents if not user_id else \
                [d for d in self._fallback_documents if d.get("user_id") == user_id]
            
            for doc in user_docs:
                metadata = doc.get("metadata", {})
                doc_type = metadata.get("type", "")
                if doc_type in ["pdf", "docx", "text"]:
                    doc_chunks += 1
                    filename = metadata.get("filename")
                    if filename:
                        filenames.add(filename)
            
            return {
                "total_chunks": doc_chunks,
                "unique_documents": len(filenames),
                "filenames": list(filenames)
            }
    
    def delete_document_by_filename(self, user_id: str, filename: str) -> bool:
        """Delete all chunks for a specific document by filename."""
        if not user_id or not filename:
            logger.warning("delete_document_by_filename called without user_id or filename")
            return False
        
        if self.client:
            try:
                # Delete documents where metadata->filename matches
                response = self.client.table("documents") \
                    .delete() \
                    .eq("user_id", user_id) \
                    .eq("metadata->>filename", filename) \
                    .execute()
                logger.info(f"Deleted document '{filename}' for user {user_id[:8]}...")
                return True
            except Exception as e:
                logger.error(f"Error deleting document by filename: {e}")
                return False
        else:
            # Fallback
            before_count = len(self._fallback_documents)
            self._fallback_documents = [
                d for d in self._fallback_documents 
                if not (d.get("user_id") == user_id and d.get("metadata", {}).get("filename") == filename)
            ]
            deleted = before_count - len(self._fallback_documents)
            logger.info(f"Deleted {deleted} chunks for '{filename}' (fallback)")
            return True
    
    def clear_user_documents(self, user_id: str) -> bool:
        """Clear all documents for a specific user."""
        if not user_id:
            logger.warning("clear_user_documents called without user_id")
            return False
        
        if self.client:
            try:
                self.client.table("documents") \
                    .delete() \
                    .eq("user_id", user_id) \
                    .execute()
                logger.info(f"Cleared all documents for user {user_id[:8]}...")
                return True
            except Exception as e:
                logger.error(f"Error clearing user documents: {e}")
                return False
        else:
            # Fallback
            self._fallback_documents = [
                d for d in self._fallback_documents if d.get("user_id") != user_id
            ]
            logger.info(f"Cleared fallback documents for user {user_id[:8]}...")
            return True
    
    def clear_all_documents(self) -> bool:
        """Clear ALL documents (admin function - use clear_user_documents for user-specific)."""
        if self.client:
            try:
                # This is dangerous - only for admin use
                # For safety, we'll just log a warning
                logger.warning("clear_all_documents called - this clears ALL users' data!")
                return False
            except Exception as e:
                logger.error(f"Error clearing all documents: {e}")
                return False
        else:
            self._fallback_documents = []
            return True
