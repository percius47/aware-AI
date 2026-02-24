"""
Memory Tools - Tools for interacting with conversation memory.
"""
from typing import List, Dict, Any, Optional
from app.services.tools import register_tool, ToolResult
from app.services.memory_service import MemoryService
from app.core.logging_config import get_logger

logger = get_logger("memory_tools")

# Shared memory service instance
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get or create memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


@register_tool(
    name="search_memories",
    description="Search through past conversation memories. Use when user refers to previous discussions, asks 'remember when', or needs context from earlier conversations.",
    parameters={"query": "string", "limit": "integer"}
)
async def search_memories(
    query: str,
    limit: int = 5,
    user_id: str = None
) -> ToolResult:
    """
    Search conversation memories using semantic similarity.
    
    Args:
        query: Search query
        limit: Maximum number of memories to return
        user_id: User ID for filtering
    
    Returns:
        ToolResult with matching memories
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    memory = get_memory_service()
    memories = await memory.search_memories(
        user_id=user_id,
        query=query,
        limit=limit
    )
    
    if not memories:
        return ToolResult(
            data=[],
            summary="No matching memories found"
        )
    
    # Format memories for context
    formatted = []
    for m in memories:
        if isinstance(m, dict):
            formatted.append({
                "content": m.get("memory", m.get("content", "")),
                "metadata": m.get("metadata", {})
            })
        else:
            formatted.append({"content": str(m), "metadata": {}})
    
    return ToolResult(
        data=formatted,
        summary=f"Found {len(memories)} relevant memories"
    )


@register_tool(
    name="get_recent_memories",
    description="Get the most recent conversation memories. Use when user asks about recent discussions or when context from recent conversations would be helpful.",
    parameters={"limit": "integer"}
)
async def get_recent_memories(
    limit: int = 10,
    user_id: str = None
) -> ToolResult:
    """
    Get all memories for a user (most recent ones).
    
    Args:
        limit: Maximum number of memories to return
        user_id: User ID for filtering
    
    Returns:
        ToolResult with recent memories
    """
    if not user_id:
        return ToolResult(
            data=[],
            summary="No user ID provided",
            success=False,
            error="User ID required"
        )
    
    memory = get_memory_service()
    all_memories = await memory.get_all_memories(user_id=user_id)
    
    # Take the most recent ones
    recent = all_memories[-limit:] if len(all_memories) > limit else all_memories
    
    if not recent:
        return ToolResult(
            data=[],
            summary="No memories found"
        )
    
    # Format memories
    formatted = []
    for m in recent:
        if isinstance(m, dict):
            formatted.append({
                "content": m.get("memory", m.get("content", "")),
                "metadata": m.get("metadata", {})
            })
        else:
            formatted.append({"content": str(m), "metadata": {}})
    
    return ToolResult(
        data=formatted,
        summary=f"Retrieved {len(recent)} recent memories"
    )
