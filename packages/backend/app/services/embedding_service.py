import openai
from app.core.config import settings
from typing import List, Union
import numpy as np
import os

class EmbeddingService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_model = settings.OPENAI_EMBEDDING_MODEL
        self.custom_model = None
        self.use_custom = settings.USE_CUSTOM_EMBEDDINGS
        
        if self.use_custom:
            try:
                from sentence_transformers import SentenceTransformer
                # Load custom embedding model
                self.custom_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                print("Warning: sentence-transformers not available, falling back to OpenAI")
                self.use_custom = False
    
    async def get_embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = None
    ) -> List[List[float]]:
        """Get embeddings for text(s)"""
        if isinstance(texts, str):
            texts = [texts]
        
        if self.use_custom and self.custom_model:
            # Use custom model
            embeddings = self.custom_model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Use OpenAI
            response = self.openai_client.embeddings.create(
                model=model or self.openai_model,
                input=texts
            )
            return [item.embedding for item in response.data]
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        if self.use_custom:
            return 384  # all-MiniLM-L6-v2 dimension
        return 1536  # OpenAI text-embedding-3-small
