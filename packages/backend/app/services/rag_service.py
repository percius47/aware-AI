import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from typing import List, Dict, Any, Optional
import uuid

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to vector store"""
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        if not metadatas:
            metadatas = [{} for _ in texts]
        
        # Get embeddings
        embeddings = await self.embedding_service.get_embeddings(texts)
        
        # Add to Chroma
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        return ids
    
    async def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        # Get query embedding
        query_embedding = await self.embedding_service.get_embeddings(query)
        
        # Search
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None,
                    "id": results['ids'][0][i] if results['ids'] else None
                })
        
        return formatted_results
    
    async def add_conversation_to_rag(
        self,
        conversation_id: str,
        messages: List[Dict[str, str]]
    ):
        """Add conversation history to RAG for semantic search"""
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        await self.add_documents(
            texts=[conversation_text],
            metadatas=[{
                "type": "conversation",
                "conversation_id": conversation_id,
                "timestamp": str(messages[-1].get("timestamp", ""))
            }]
        )
    
    def get_total_embeddings_count(self) -> int:
        """Get total number of embeddings in ChromaDB (lifetime stat)."""
        try:
            return self.collection.count()
        except Exception:
            return 0
    
    def get_documents_stats(self) -> Dict[str, Any]:
        """
        Get document upload statistics from ChromaDB metadata.
        Returns unique document count and filenames (excludes conversations).
        """
        try:
            # Get all entries that are NOT conversations (i.e., uploaded documents)
            # ChromaDB doesn't support $ne operator well, so we get all and filter
            results = self.collection.get(include=["metadatas"])
            
            filenames = set()
            doc_chunks = 0
            
            for meta in results.get("metadatas", []):
                if meta:
                    doc_type = meta.get("type", "")
                    # Count only actual documents (pdf, docx, text), not conversations
                    if doc_type in ["pdf", "docx", "text"]:
                        doc_chunks += 1
                        filename = meta.get("filename")
                        if filename:
                            filenames.add(filename)
            
            return {
                "total_chunks": doc_chunks,
                "unique_documents": len(filenames),
                "filenames": list(filenames)
            }
        except Exception as e:
            return {
                "total_chunks": 0,
                "unique_documents": 0,
                "filenames": [],
                "error": str(e)
            }