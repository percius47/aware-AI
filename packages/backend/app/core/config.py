from pydantic_settings import BaseSettings
from typing import List
import json
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (aware-AI folder, 5 levels up from this file)
# Path: packages/backend/app/core/config.py -> aware-AI/
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# Explicitly load .env file before pydantic-settings
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # Fallback: try loading from current working directory
    load_dotenv()

class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Mem0
    MEM0_API_KEY: str = ""
    MEM0_PROJECT_ID: str = ""
    
    # Vector DB
    VECTOR_DB_TYPE: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "aware-ai"
    
    # Server
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    # Store CORS origins as string to avoid pydantic-settings JSON parsing issues
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from string (supports both JSON array and comma-separated formats)"""
        value = self.CORS_ORIGINS
        if not value:
            return ["http://localhost:3000", "http://localhost:3001"]
        
        # Try JSON format first
        if value.strip().startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Fall back to comma-separated format
        return [origin.strip() for origin in value.split(',') if origin.strip()]
    
    # Memory
    MEMORY_COMPRESSION_THRESHOLD: int = 50
    MEMORY_SUMMARY_INTERVAL: int = 10
    MAX_CONTEXT_TOKENS: int = 8000
    
    # Fine-tuning
    FINE_TUNING_ENABLED: bool = True
    FINE_TUNING_DATA_DIR: str = "./fine_tuning_data"
    
    # Embeddings
    USE_CUSTOM_EMBEDDINGS: bool = False
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        case_sensitive = True
        populate_by_name = True  # Allow using both alias and field name

settings = Settings()
