from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from typing import List, Dict, Any
from app.core.config import settings

class MemoryCompressionService:
    def __init__(self):
        self.llm_service = LLMService()
        self.memory_service = MemoryService()
    
    async def summarize_memories(
        self,
        user_id: str,
        memory_count_threshold: int = None
    ) -> Dict[str, Any]:
        """Summarize and compress memories"""
        threshold = memory_count_threshold or settings.MEMORY_COMPRESSION_THRESHOLD
        
        memories = await self.memory_service.get_all_memories(user_id)
        
        if len(memories) < threshold:
            return {"compressed": False, "reason": "Below threshold"}
        
        # Get recent memories
        recent_memories = memories[-threshold:]
        
        # Create summary prompt
        memory_texts = [mem.get("memory", "") or mem.get("content", "") for mem in recent_memories]
        combined_text = "\n\n".join(memory_texts)
        
        summary_prompt = f"""Summarize the following memories into key insights and facts. 
        Preserve important details about the user's preferences, context, and relationships.
        
        Memories:
        {combined_text}
        
        Provide a concise summary that captures the essential information."""
        
        messages = [
            {"role": "system", "content": "You are a memory compression assistant."},
            {"role": "user", "content": summary_prompt}
        ]
        
        summary = await self.llm_service.generate_non_streaming(messages)
        
        # Store summary as new memory
        await self.memory_service.add_memory(
            user_id=user_id,
            messages=[{"role": "user", "content": f"Summary: {summary}"}],
            metadata={"type": "compressed_summary", "original_count": len(recent_memories)}
        )
        
        # Optionally delete old memories (commented out for safety)
        # for mem in recent_memories:
        #     await self.memory_service.delete_memory(user_id, mem.get("id"))
        
        return {
            "compressed": True,
            "summary": summary,
            "original_count": len(recent_memories),
            "new_memory_id": "summary_memory_id"
        }
