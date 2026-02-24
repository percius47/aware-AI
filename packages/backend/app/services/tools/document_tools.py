"""
Document Tools - Tools for interacting with uploaded documents and RAG.
"""
from typing import List, Dict, Any, Optional
from app.services.tools import register_tool, ToolResult
from app.services.rag_service import RAGService
from app.core.logging_config import get_logger

logger = get_logger("document_tools")

# Shared RAG service instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


@register_tool(
    name="search_documents",
    description="Search uploaded documents using semantic similarity. Use when user asks to find specific information in their documents.",
    parameters={"query": "string", "limit": "integer"}
)
async def search_documents(
    query: str,
    limit: int = 10,
    user_id: str = None
) -> ToolResult:
    """
    Semantic search through user's uploaded documents.
    
    Args:
        query: Search query
        limit: Maximum number of results
        user_id: User ID for filtering
    
    Returns:
        ToolResult with matching document chunks
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    rag = get_rag_service()
    results = await rag.search(query=query, user_id=user_id, n_results=limit)
    
    if not results:
        return ToolResult(
            data=[],
            summary="No matching documents found"
        )
    
    # Format results for context
    formatted = []
    for r in results:
        formatted.append({
            "content": r.get("content", ""),
            "metadata": r.get("metadata", {}),
            "relevance": 1 - r.get("distance", 0)
        })
    
    # Get unique filenames
    filenames = set()
    for r in results:
        fname = r.get("metadata", {}).get("filename")
        if fname:
            filenames.add(fname)
    
    summary = f"Found {len(results)} relevant chunks from {len(filenames)} document(s)"
    if filenames:
        summary += f": {', '.join(list(filenames)[:3])}"
    
    return ToolResult(
        data=formatted,
        summary=summary
    )


@register_tool(
    name="get_all_user_documents",
    description="Retrieve ALL content from user's uploaded documents. Use when user asks to summarize, review, or discuss all their documents without a specific search query.",
    parameters={"max_chunks": "integer"}
)
async def get_all_user_documents(
    max_chunks: int = 50,
    user_id: str = None
) -> ToolResult:
    """
    Fetch all document content for a user.
    
    Args:
        max_chunks: Maximum chunks to return
        user_id: User ID for filtering
    
    Returns:
        ToolResult with all document content
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    rag = get_rag_service()
    
    # Use Supabase client directly if available
    if rag.client:
        try:
            response = rag.client.table("documents") \
                .select("id, content, metadata") \
                .eq("user_id", user_id) \
                .limit(max_chunks) \
                .execute()
            
            documents = response.data or []
            
            # Group by filename
            by_filename: Dict[str, List[str]] = {}
            for doc in documents:
                metadata = doc.get("metadata", {})
                filename = metadata.get("filename", "unknown")
                content = doc.get("content", "")
                
                if filename not in by_filename:
                    by_filename[filename] = []
                by_filename[filename].append(content)
            
            # Format for context
            formatted = []
            for filename, chunks in by_filename.items():
                formatted.append({
                    "filename": filename,
                    "content": "\n\n".join(chunks),
                    "chunk_count": len(chunks)
                })
            
            summary = f"Retrieved {len(documents)} chunks from {len(by_filename)} document(s)"
            if by_filename:
                summary += f": {', '.join(list(by_filename.keys())[:5])}"
            
            return ToolResult(
                data=formatted,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error fetching all documents: {e}")
            return ToolResult(
                data=[],
                summary=f"Error fetching documents: {str(e)}",
                success=False,
                error=str(e)
            )
    else:
        # Fallback: use in-memory documents
        user_docs = [d for d in rag._fallback_documents if d.get("user_id") == user_id][:max_chunks]
        
        by_filename: Dict[str, List[str]] = {}
        for doc in user_docs:
            filename = doc.get("metadata", {}).get("filename", "unknown")
            content = doc.get("content", "")
            if filename not in by_filename:
                by_filename[filename] = []
            by_filename[filename].append(content)
        
        formatted = [{"filename": fn, "content": "\n\n".join(chunks), "chunk_count": len(chunks)} 
                     for fn, chunks in by_filename.items()]
        
        return ToolResult(
            data=formatted,
            summary=f"Retrieved {len(user_docs)} chunks from {len(by_filename)} document(s) (fallback)"
        )


@register_tool(
    name="get_document_by_name",
    description="Retrieve content from a specific document by filename. Use when user mentions a specific document name or uses @filename syntax.",
    parameters={"filename": "string", "max_chunks": "integer"}
)
async def get_document_by_name(
    filename: str,
    max_chunks: int = 30,
    user_id: str = None
) -> ToolResult:
    """
    Fetch a specific document by filename.
    
    Args:
        filename: Document filename to fetch
        max_chunks: Maximum chunks to return
        user_id: User ID for filtering
    
    Returns:
        ToolResult with document content
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    rag = get_rag_service()
    
    if rag.client:
        try:
            response = rag.client.table("documents") \
                .select("id, content, metadata") \
                .eq("user_id", user_id) \
                .eq("metadata->>filename", filename) \
                .limit(max_chunks) \
                .execute()
            
            documents = response.data or []
            
            if not documents:
                return ToolResult(
                    data=[],
                    summary=f"Document '{filename}' not found"
                )
            
            # Combine all chunks
            content_parts = [doc.get("content", "") for doc in documents]
            combined_content = "\n\n".join(content_parts)
            
            return ToolResult(
                data={
                    "filename": filename,
                    "content": combined_content,
                    "chunk_count": len(documents)
                },
                summary=f"Retrieved {len(documents)} chunks from '{filename}'"
            )
            
        except Exception as e:
            logger.error(f"Error fetching document by name: {e}")
            return ToolResult(
                data=[],
                summary=f"Error fetching document: {str(e)}",
                success=False,
                error=str(e)
            )
    else:
        # Fallback
        user_docs = [
            d for d in rag._fallback_documents 
            if d.get("user_id") == user_id and d.get("metadata", {}).get("filename") == filename
        ][:max_chunks]
        
        if not user_docs:
            return ToolResult(
                data=[],
                summary=f"Document '{filename}' not found (fallback)"
            )
        
        content_parts = [d.get("content", "") for d in user_docs]
        
        return ToolResult(
            data={
                "filename": filename,
                "content": "\n\n".join(content_parts),
                "chunk_count": len(user_docs)
            },
            summary=f"Retrieved {len(user_docs)} chunks from '{filename}' (fallback)"
        )


@register_tool(
    name="list_documents",
    description="List all document names the user has uploaded. Use to show available documents or when user asks what files they have.",
    parameters={}
)
async def list_documents(user_id: str = None) -> ToolResult:
    """
    List all document filenames for a user.
    
    Args:
        user_id: User ID for filtering
    
    Returns:
        ToolResult with list of document names
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    rag = get_rag_service()
    stats = rag.get_documents_stats(user_id=user_id)
    
    filenames = stats.get("filenames", [])
    
    if not filenames:
        return ToolResult(
            data=[],
            summary="No documents uploaded"
        )
    
    return ToolResult(
        data=filenames,
        summary=f"Found {len(filenames)} document(s): {', '.join(filenames)}"
    )
