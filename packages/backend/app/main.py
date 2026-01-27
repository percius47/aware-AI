from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.api.routes import router
from app.api.websocket import websocket_router

# Initialize logging
setup_logging()
logger = get_logger("app")
logger.info("Starting Aware AI API...")

app = FastAPI(
    title="Aware AI API",
    description="Self-Aware RAG System with Memory Management",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")
app.include_router(websocket_router)

@app.get("/")
async def root():
    return {"message": "Aware AI API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
