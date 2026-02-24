"""
Intent Detection Service - Analyzes user queries to determine intent and required tools.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from app.core.logging_config import get_logger
from app.services.llm_service import LLMService
from app.services.tools import list_tools, get_tools_for_llm

logger = get_logger("intent")


class IntentCategory(str, Enum):
    """Categories of user intent."""
    DOCUMENT_SUMMARY = "document_summary"
    DOCUMENT_SEARCH = "document_search"
    DOCUMENT_SPECIFIC = "document_specific"
    DOCUMENT_LIST = "document_list"
    MEMORY_RECALL = "memory_recall"
    GENERAL_CHAT = "general_chat"
    VAGUE_QUERY = "vague_query"


@dataclass
class DetectedIntent:
    """Result of intent detection."""
    category: IntentCategory
    confidence: float
    tools_to_use: List[str]
    is_vague: bool = False
    clarification_message: Optional[str] = None
    clarification_options: Optional[List[str]] = None
    extracted_entities: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "confidence": self.confidence,
            "tools_to_use": self.tools_to_use,
            "is_vague": self.is_vague,
            "clarification_message": self.clarification_message,
            "clarification_options": self.clarification_options,
            "extracted_entities": self.extracted_entities
        }


class IntentService:
    """Service for detecting user intent and determining required tools."""
    
    # Keywords for intent detection
    INTENT_KEYWORDS = {
        IntentCategory.DOCUMENT_SUMMARY: [
            "summarize", "summary", "key points", "main points", "overview",
            "what does it say", "tell me about", "explain the paper",
            "highlights", "tldr", "brief", "recap"
        ],
        IntentCategory.DOCUMENT_SEARCH: [
            "find", "search", "look for", "where does it say", "locate",
            "which part", "mentions", "refers to", "contains"
        ],
        IntentCategory.DOCUMENT_SPECIFIC: [
            "@", ".pdf", ".docx", ".txt", "the document", "the file",
            "that paper", "this paper", "uploaded file", "my document"
        ],
        IntentCategory.DOCUMENT_LIST: [
            "what documents", "list files", "my uploads", "what did i upload",
            "show documents", "available files", "uploaded documents"
        ],
        IntentCategory.MEMORY_RECALL: [
            "remember", "recall", "we discussed", "earlier", "last time",
            "previously", "you said", "i told you", "our conversation"
        ]
    }
    
    # Vague patterns that need clarification
    VAGUE_PATTERNS = [
        (r'\b(this|that|it|the document|the paper|the file)\b(?!\s+\w+\.(pdf|docx|txt))', 
         "Which document are you referring to?"),
        (r'^(summarize|explain|tell me about)\s*$',
         "What would you like me to summarize?"),
        (r'\b(something|stuff|things)\b',
         "Could you be more specific about what you're looking for?"),
    ]
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service
    
    def detect_intent_fast(
        self,
        query: str,
        available_documents: List[str] = None
    ) -> DetectedIntent:
        """
        Fast keyword-based intent detection (no LLM call).
        
        Args:
            query: User's query
            available_documents: List of user's document names
        
        Returns:
            DetectedIntent with category and tools
        """
        query_lower = query.lower().strip()
        
        # Check for @ syntax (explicit document reference)
        at_match = re.search(r'@(\S+)', query)
        if at_match:
            filename = at_match.group(1)
            return DetectedIntent(
                category=IntentCategory.DOCUMENT_SPECIFIC,
                confidence=0.95,
                tools_to_use=["get_document_by_name"],
                extracted_entities={"filename": filename}
            )
        
        # Check for explicit document names in query
        if available_documents:
            for doc in available_documents:
                if doc.lower() in query_lower:
                    return DetectedIntent(
                        category=IntentCategory.DOCUMENT_SPECIFIC,
                        confidence=0.9,
                        tools_to_use=["get_document_by_name"],
                        extracted_entities={"filename": doc}
                    )
        
        # Score each intent category
        scores: Dict[IntentCategory, float] = {}
        for category, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1
            scores[category] = score
        
        # Determine best matching intent
        best_category = max(scores, key=scores.get) if scores else IntentCategory.GENERAL_CHAT
        best_score = scores.get(best_category, 0)
        
        # Calculate confidence
        max_possible = len(self.INTENT_KEYWORDS.get(best_category, [])) or 1
        confidence = min(best_score / max_possible + 0.3, 0.95) if best_score > 0 else 0.5
        
        # Check for vagueness
        is_vague, clarification = self._check_vagueness(query_lower, available_documents)
        
        # If query is about documents but vague about which one
        if is_vague and best_category in [
            IntentCategory.DOCUMENT_SUMMARY,
            IntentCategory.DOCUMENT_SEARCH,
            IntentCategory.DOCUMENT_SPECIFIC
        ]:
            return DetectedIntent(
                category=IntentCategory.VAGUE_QUERY,
                confidence=0.8,
                tools_to_use=[],
                is_vague=True,
                clarification_message=clarification,
                clarification_options=available_documents or []
            )
        
        # Map intent to tools
        tools = self._get_tools_for_intent(best_category)
        
        return DetectedIntent(
            category=best_category,
            confidence=confidence,
            tools_to_use=tools
        )
    
    async def detect_intent_with_llm(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        available_documents: List[str] = None
    ) -> DetectedIntent:
        """
        Advanced intent detection using LLM (more accurate but slower).
        
        Args:
            query: User's query
            conversation_history: Recent conversation context
            available_documents: List of user's document names
        
        Returns:
            DetectedIntent with category and tools
        """
        if not self.llm_service:
            return self.detect_intent_fast(query, available_documents)
        
        # First do fast detection
        fast_result = self.detect_intent_fast(query, available_documents)
        
        # If fast detection is confident enough, use it
        if fast_result.confidence > 0.85 and not fast_result.is_vague:
            return fast_result
        
        # Use LLM for ambiguous cases
        tools_desc = get_tools_for_llm()
        docs_list = ", ".join(available_documents) if available_documents else "None uploaded"
        
        prompt = f"""Analyze this user query and determine the intent.

User query: "{query}"

Available documents: {docs_list}

Available tools:
{tools_desc}

Recent conversation context (last 3 messages):
{self._format_history(conversation_history[-3:])}

Respond in this exact format:
INTENT: <one of: document_summary, document_search, document_specific, document_list, memory_recall, general_chat, vague_query>
CONFIDENCE: <0.0 to 1.0>
TOOLS: <comma-separated tool names to use, or "none">
IS_VAGUE: <true or false>
CLARIFICATION: <if vague, what to ask the user, otherwise "none">
ENTITIES: <extracted entities like filename=X, otherwise "none">
"""
        
        try:
            response = await self.llm_service.generate_non_streaming(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            return self._parse_llm_response(response, available_documents)
            
        except Exception as e:
            logger.warning(f"LLM intent detection failed: {e}, using fast detection")
            return fast_result
    
    def _check_vagueness(
        self,
        query: str,
        available_documents: List[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if query is too vague and needs clarification."""
        
        # Check vague patterns
        for pattern, clarification in self.VAGUE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                # If user has multiple documents and refers to "the document" vaguely
                if available_documents and len(available_documents) > 1:
                    if "document" in clarification.lower() or "paper" in clarification.lower():
                        return True, f"You have {len(available_documents)} documents. Which one would you like me to use?"
                return True, clarification
        
        # Check for document references when multiple documents exist
        doc_refs = ["this paper", "the paper", "this document", "the document", 
                    "uploaded file", "my file", "the file"]
        if available_documents and len(available_documents) > 1:
            for ref in doc_refs:
                if ref in query.lower():
                    # Check if a specific document name is also mentioned
                    has_specific = any(doc.lower() in query.lower() for doc in available_documents)
                    if not has_specific:
                        return True, f"You have {len(available_documents)} documents: {', '.join(available_documents)}. Which one would you like me to use?"
        
        return False, None
    
    def _get_tools_for_intent(self, category: IntentCategory) -> List[str]:
        """Map intent category to required tools."""
        mapping = {
            IntentCategory.DOCUMENT_SUMMARY: ["get_all_user_documents"],
            IntentCategory.DOCUMENT_SEARCH: ["search_documents"],
            IntentCategory.DOCUMENT_SPECIFIC: ["get_document_by_name"],
            IntentCategory.DOCUMENT_LIST: ["list_documents"],
            IntentCategory.MEMORY_RECALL: ["search_memories", "get_recent_memories"],
            IntentCategory.GENERAL_CHAT: [],
            IntentCategory.VAGUE_QUERY: [],
        }
        return mapping.get(category, [])
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for prompt."""
        if not history:
            return "No recent conversation"
        
        formatted = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # Truncate
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _parse_llm_response(
        self,
        response: str,
        available_documents: List[str] = None
    ) -> DetectedIntent:
        """Parse LLM response into DetectedIntent."""
        lines = response.strip().split("\n")
        parsed = {}
        
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip().upper()] = value.strip()
        
        # Extract values with defaults
        intent_str = parsed.get("INTENT", "general_chat").lower().replace(" ", "_")
        try:
            category = IntentCategory(intent_str)
        except ValueError:
            category = IntentCategory.GENERAL_CHAT
        
        confidence = float(parsed.get("CONFIDENCE", "0.7"))
        tools_str = parsed.get("TOOLS", "none")
        tools = [t.strip() for t in tools_str.split(",") if t.strip() and t.strip() != "none"]
        
        is_vague = parsed.get("IS_VAGUE", "false").lower() == "true"
        clarification = parsed.get("CLARIFICATION")
        if clarification and clarification.lower() == "none":
            clarification = None
        
        # Parse entities
        entities = {}
        entities_str = parsed.get("ENTITIES", "none")
        if entities_str and entities_str.lower() != "none":
            for pair in entities_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    entities[k.strip()] = v.strip()
        
        return DetectedIntent(
            category=category,
            confidence=confidence,
            tools_to_use=tools or self._get_tools_for_intent(category),
            is_vague=is_vague,
            clarification_message=clarification,
            clarification_options=available_documents if is_vague else None,
            extracted_entities=entities
        )
