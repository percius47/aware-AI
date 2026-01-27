import openai
from app.core.config import settings
from typing import List, Dict, AsyncGenerator
import json

class LLMService:
    def __init__(self):
        self.model = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def _check_api_key(self):
        if not self.client:
            raise ValueError("OPENAI_API_KEY is not set. Please set it in your .env file.")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from OpenAI"""
        self._check_api_key()
        try:
            stream_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream,
                temperature=temperature
            )
            
            if stream:
                for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield stream_response.choices[0].message.content
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def generate_non_streaming(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """Generate non-streaming response"""
        self._check_api_key()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False,
            temperature=temperature
        )
        return response.choices[0].message.content
