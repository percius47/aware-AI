import uuid
from datetime import datetime
from typing import Dict, Any, List

def generate_conversation_id() -> str:
    """Generate unique conversation ID"""
    return str(uuid.uuid4())

def format_timestamp() -> str:
    """Get current timestamp"""
    return datetime.now().isoformat()

def build_context_from_memories(memories: list) -> str:
    """Build context string from memories"""
    if not memories:
        return ""
    
    context_parts = []
    for mem in memories:
        # Handle different memory formats (dict, string, or Mem0 result object)
        if isinstance(mem, str):
            content = mem
        elif isinstance(mem, dict):
            content = mem.get("memory", "") or mem.get("content", "") or mem.get("text", "")
        elif hasattr(mem, 'memory'):
            # Mem0 result object
            content = getattr(mem, 'memory', '') or getattr(mem, 'content', '')
        else:
            content = str(mem) if mem else ""
        
        if content:
            context_parts.append(f"- {content}")
    
    return "\n".join(context_parts)

def build_context_from_rag_results(rag_results: list) -> str:
    """Build context string from RAG results"""
    if not rag_results:
        return ""
    
    context_parts = []
    for result in rag_results:
        # Handle different result formats
        if isinstance(result, str):
            content = result
            source = "Unknown"
        elif isinstance(result, dict):
            content = result.get("content", "") or result.get("text", "") or result.get("document", "")
            metadata = result.get("metadata", {}) if isinstance(result.get("metadata"), dict) else {}
            source = metadata.get("source", metadata.get("filename", "Unknown"))
        else:
            content = str(result) if result else ""
            source = "Unknown"
        
        if content:
            context_parts.append(f"[Source: {source}]\n{content}")
    
    return "\n\n".join(context_parts)
