from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    stream: bool = True
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    memory_used: Optional[List[Dict[str, Any]]] = None

class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    size: int

class DocumentProcessResponse(BaseModel):
    document_id: str
    chunks: int
    status: str

class MemoryItem(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

class FineTuningRequest(BaseModel):
    training_data: List[Dict[str, str]]
    model_name: Optional[str] = None
    epochs: int = 3
