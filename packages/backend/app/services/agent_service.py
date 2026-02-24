"""
Agent Orchestrator Service - Main coordination layer for the agentic architecture.

This service orchestrates the flow:
1. Intent detection
2. Vagueness checking (clarification if needed)
3. Tool selection and execution
4. Response generation with tool results as context
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass
from app.core.logging_config import get_logger
from app.services.intent_service import IntentService, DetectedIntent, IntentCategory
from app.services.llm_service import LLMService
from app.services.tools import execute_tool, load_tools, list_tools, ToolResult
from app.services.tools.document_tools import get_rag_service

logger = get_logger("agent")


@dataclass
class AgentEvent:
    """Event emitted by the agent during processing."""
    type: str  # thinking, intent, tool_call, tool_result, clarification, chunk, done, error
    content: Optional[str] = None
    tool: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    message: Optional[str] = None
    options: Optional[List[str]] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    conversation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = {"type": self.type}
        if self.content is not None:
            result["content"] = self.content
        if self.tool is not None:
            result["tool"] = self.tool
        if self.params is not None:
            result["params"] = self.params
        if self.summary is not None:
            result["summary"] = self.summary
        if self.message is not None:
            result["message"] = self.message
        if self.options is not None:
            result["options"] = self.options
        if self.intent is not None:
            result["intent"] = self.intent
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.conversation_id is not None:
            result["conversation_id"] = self.conversation_id
        return result


class AgentOrchestrator:
    """
    Main agent orchestrator that coordinates intent detection, tool execution,
    and response generation.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        # Initialize services
        self.llm_service = llm_service or LLMService()
        self.intent_service = IntentService(llm_service=self.llm_service)
        
        # Load tools (registers them in the registry)
        try:
            load_tools()
        except Exception as e:
            logger.warning(f"Some tools failed to load: {e}")
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        conversation_id: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Main entry point for processing a user query.
        
        Yields AgentEvent objects as processing progresses.
        
        Args:
            query: User's query string
            user_id: User ID for data isolation
            conversation_id: Current conversation ID
            conversation_history: Recent messages for context
        
        Yields:
            AgentEvent objects for each step
        """
        conversation_history = conversation_history or []
        
        try:
            # Step 1: Get available documents for context
            yield AgentEvent(type="thinking", content="Checking your available documents...")
            available_docs = await self._get_user_documents(user_id)
            
            # Step 2: Detect intent
            yield AgentEvent(type="thinking", content="Analyzing your request...")
            
            intent = await self.intent_service.detect_intent_with_llm(
                query=query,
                conversation_history=conversation_history,
                available_documents=available_docs
            )
            
            yield AgentEvent(
                type="intent",
                intent=intent.category.value,
                confidence=intent.confidence
            )
            
            logger.info(f"Detected intent: {intent.category.value} (confidence: {intent.confidence:.2f})")
            
            # Step 3: Check for vagueness - request clarification if needed
            if intent.is_vague:
                yield AgentEvent(
                    type="clarification",
                    message=intent.clarification_message,
                    options=intent.clarification_options or available_docs
                )
                return  # Stop here, wait for user clarification
            
            # Step 4: Execute tools based on intent
            tool_results: List[ToolResult] = []
            
            if intent.tools_to_use:
                yield AgentEvent(type="thinking", content=f"Preparing to use {len(intent.tools_to_use)} tool(s)...")
                
                for tool_name in intent.tools_to_use:
                    # Build parameters for tool
                    params = self._build_tool_params(tool_name, query, intent)
                    
                    yield AgentEvent(
                        type="tool_call",
                        tool=tool_name,
                        params={k: v for k, v in params.items() if k != "user_id"}  # Don't expose user_id
                    )
                    
                    # Execute tool
                    result = await execute_tool(tool_name, params, user_id)
                    tool_results.append(result)
                    
                    yield AgentEvent(
                        type="tool_result",
                        tool=tool_name,
                        summary=result.summary
                    )
                    
                    if not result.success:
                        logger.warning(f"Tool {tool_name} failed: {result.error}")
            
            # Step 5: Generate response using LLM with tool results as context
            yield AgentEvent(type="thinking", content="Generating response...")
            
            async for chunk in self._generate_response(
                query=query,
                tool_results=tool_results,
                conversation_history=conversation_history,
                intent=intent
            ):
                yield AgentEvent(type="chunk", content=chunk)
            
            # Step 6: Done
            yield AgentEvent(type="done", conversation_id=conversation_id)
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            yield AgentEvent(
                type="error",
                content=f"An error occurred: {str(e)}"
            )
    
    async def _get_user_documents(self, user_id: str) -> List[str]:
        """Get list of user's document names."""
        try:
            rag = get_rag_service()
            stats = rag.get_documents_stats(user_id=user_id)
            return stats.get("filenames", [])
        except Exception as e:
            logger.warning(f"Failed to get document list: {e}")
            return []
    
    def _build_tool_params(
        self,
        tool_name: str,
        query: str,
        intent: DetectedIntent
    ) -> Dict[str, Any]:
        """Build parameters for a tool based on the query and intent."""
        params = {}
        
        if tool_name == "search_documents":
            params["query"] = query
            params["limit"] = 10
        
        elif tool_name == "get_all_user_documents":
            params["max_chunks"] = 50
        
        elif tool_name == "get_document_by_name":
            # Extract filename from intent entities or query
            filename = intent.extracted_entities.get("filename")
            if not filename:
                # Try to extract from @ syntax
                import re
                match = re.search(r'@(\S+)', query)
                if match:
                    filename = match.group(1)
            params["filename"] = filename or ""
            params["max_chunks"] = 30
        
        elif tool_name == "list_documents":
            pass  # No params needed
        
        elif tool_name == "search_memories":
            params["query"] = query
            params["limit"] = 5
        
        elif tool_name == "get_recent_memories":
            params["limit"] = 10
        
        return params
    
    async def _generate_response(
        self,
        query: str,
        tool_results: List[ToolResult],
        conversation_history: List[Dict[str, str]],
        intent: DetectedIntent
    ) -> AsyncGenerator[str, None]:
        """Generate the final response using LLM with tool results as context."""
        
        # Build context from tool results
        context_parts = []
        
        for result in tool_results:
            if result.success and result.data:
                context_parts.append(self._format_tool_result(result))
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        # Build system prompt based on intent
        system_prompt = self._build_system_prompt(intent, context)
        
        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10)
        messages.extend(conversation_history[-10:])
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Generate response
        async for chunk in self.llm_service.generate_response(messages, stream=True):
            yield chunk
    
    def _format_tool_result(self, result: ToolResult) -> str:
        """Format a tool result for inclusion in LLM context."""
        if not result.data:
            return ""
        
        data = result.data
        
        # Handle list of documents
        if isinstance(data, list):
            if all(isinstance(item, dict) and "content" in item for item in data):
                # Document chunks
                parts = []
                for i, item in enumerate(data[:20]):  # Limit chunks
                    filename = item.get("metadata", {}).get("filename") or item.get("filename", "")
                    content = item.get("content", "")[:2000]  # Truncate long content
                    if filename:
                        parts.append(f"[From {filename}]:\n{content}")
                    else:
                        parts.append(content)
                return "\n\n---\n\n".join(parts)
            elif all(isinstance(item, dict) and "filename" in item for item in data):
                # Grouped documents
                parts = []
                for item in data:
                    filename = item.get("filename", "unknown")
                    content = item.get("content", "")[:3000]  # Truncate
                    parts.append(f"=== Document: {filename} ===\n{content}")
                return "\n\n".join(parts)
            elif all(isinstance(item, str) for item in data):
                # List of filenames
                return f"Available documents: {', '.join(data)}"
        
        # Handle single document
        if isinstance(data, dict):
            filename = data.get("filename", "")
            content = data.get("content", "")
            if filename:
                return f"=== Document: {filename} ===\n{content}"
            return str(content)
        
        return str(data)
    
    def _build_system_prompt(self, intent: DetectedIntent, context: str) -> str:
        """Build appropriate system prompt based on intent and context."""
        
        base_prompt = """You are an AI assistant with access to the user's uploaded documents and conversation history.

CRITICAL INSTRUCTIONS:
1. Base your answers on the provided document content below.
2. If the answer is in the documents, cite it confidently (e.g., "According to your document...").
3. If no relevant information is found in the documents, clearly say so.
4. Be concise but thorough.

FORMATTING RULES:
- For numbered lists, keep the number and content on the SAME line (e.g., "1. **Title:** Content" not "1.\n**Title:**")
- Use markdown formatting for emphasis: **bold** for titles, *italic* for emphasis
- Keep list items compact and readable"""
        
        if intent.category == IntentCategory.DOCUMENT_SUMMARY:
            base_prompt += """

TASK: Summarize the key points from the user's documents.
- Provide a clear, structured summary
- Highlight the most important information
- Use bullet points or numbered lists when appropriate"""
        
        elif intent.category == IntentCategory.DOCUMENT_SEARCH:
            base_prompt += """

TASK: Find and present specific information from the documents.
- Quote relevant passages when possible
- Indicate which document the information comes from"""
        
        elif intent.category == IntentCategory.MEMORY_RECALL:
            base_prompt += """

TASK: Recall information from previous conversations.
- Reference relevant past discussions
- Provide context from earlier interactions"""
        
        elif intent.category == IntentCategory.DOCUMENT_LIST:
            base_prompt += """

TASK: Help the user understand their uploaded documents.
- List the available documents
- Briefly describe what each contains if information is available"""
        
        # Add context if available
        if context:
            base_prompt += f"""

=== DOCUMENT CONTENT ===
{context}
=== END DOCUMENT CONTENT ==="""
        else:
            base_prompt += """

Note: No relevant document content was found for this query."""
        
        return base_prompt
