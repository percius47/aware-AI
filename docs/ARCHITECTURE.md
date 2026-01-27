# Aware AI Architecture

## System Overview

Aware AI is a self-aware RAG (Retrieval-Augmented Generation) system with intelligent memory management. The system is built as a monorepo with a FastAPI backend and Next.js frontend.

## Architecture Diagram

```
┌─────────────┐
│   Browser   │
│  (Next.js)  │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend              │
│  ┌───────────────────────────────┐  │
│  │      API Routes               │  │
│  │  - /api/chat                  │  │
│  │  - /api/upload                │  │
│  │  - /api/memory/*              │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │      Services Layer           │  │
│  │  - LLM Service                │  │
│  │  - RAG Service                │  │
│  │  - Memory Service             │  │
│  │  - Embedding Service          │  │
│  │  - Document Processor         │  │
│  └───────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       ├──► OpenAI API (LLM)
       ├──► Mem0 (Memory)
       ├──► ChromaDB (Vector Store)
       └──► File System (Documents)
```

## Components

### Backend (FastAPI)

#### Core Services

1. **LLM Service** (`app/services/llm_service.py`)
   - OpenAI API integration
   - Streaming and non-streaming response generation
   - Temperature and parameter configuration

2. **RAG Service** (`app/services/rag_service.py`)
   - ChromaDB vector store management
   - Document embedding and storage
   - Semantic search functionality
   - Conversation history indexing

3. **Memory Service** (`app/services/memory_service.py`)
   - Mem0 integration for persistent memory
   - Memory search and retrieval
   - Memory management operations
   - Fallback to local storage if Mem0 unavailable

4. **Embedding Service** (`app/services/embedding_service.py`)
   - OpenAI embeddings
   - Custom embedding models (sentence-transformers)
   - Toggle between providers via configuration

5. **Document Processor** (`app/services/document_processor.py`)
   - PDF processing (PyPDF2)
   - DOCX processing (python-docx)
   - Plain text processing
   - Chunking and metadata extraction

6. **Memory Compression Service** (`app/services/memory_compression.py`)
   - Automatic memory summarization
   - Threshold-based compression
   - LLM-powered summarization

7. **Fine-tuning Service** (`app/services/fine_tuning_service.py`)
   - Training data preparation (JSONL format)
   - OpenAI fine-tuning job creation
   - Job status monitoring

#### API Layer

- **REST API** (`app/api/routes.py`)
  - Chat endpoint with SSE streaming
  - Document upload
  - Memory operations
  - Conversation management

- **WebSocket** (`app/api/websocket.py`)
  - Real-time chat communication
  - Streaming responses

### Frontend (Next.js)

#### Components

1. **ChatInterface** (`src/components/ChatInterface.tsx`)
   - Message state management
   - Streaming response handling
   - Input handling and submission

2. **MessageBubble** (`src/components/MessageBubble.tsx`)
   - Message display
   - Markdown rendering
   - Streaming indicator

3. **DocumentUpload** (`src/components/DocumentUpload.tsx`)
   - File upload UI
   - Progress indication
   - Success/error feedback

#### API Client

- **API Client** (`src/lib/api.ts`)
  - Axios configuration
  - Chat API methods
  - Document upload
  - Memory operations

## Data Flow

### Chat Flow

1. User sends message via frontend
2. Frontend calls `/api/chat` endpoint
3. Backend retrieves relevant memories from Mem0
4. Backend searches knowledge base via RAG (ChromaDB)
5. Context is built from memories + RAG results
6. OpenAI LLM generates response with context
7. Response is streamed back to frontend (SSE)
8. Conversation is saved to memory and RAG

### Document Processing Flow

1. User uploads document via frontend
2. Frontend sends file to `/api/upload`
3. Backend processes document (PDF/DOCX/text)
4. Document is chunked and embedded
5. Chunks are stored in ChromaDB vector store
6. Success response returned to frontend

### Memory Compression Flow

1. Memory count reaches threshold
2. Compression service is triggered
3. Recent memories are summarized using LLM
4. Summary is stored as new memory
5. Old memories can be optionally deleted

## Data Storage

### Vector Database (ChromaDB)
- Stores document embeddings
- Stores conversation embeddings for semantic search
- Metadata includes: filename, page numbers, conversation IDs

### Memory Storage (Mem0)
- Persistent user memories
- Semantic searchable
- Metadata includes: conversation IDs, timestamps

### File System
- Fine-tuning data (JSONL files)
- ChromaDB persistence directory
- Uploaded documents (optional)

## Configuration

### Environment Variables

- **OpenAI**: API key, model selection, embedding model
- **Mem0**: API key, project ID (optional)
- **Vector DB**: Type (chroma/pinecone), configuration
- **Memory**: Compression thresholds, summary intervals
- **Fine-tuning**: Enabled flag, data directory

## Security Considerations

- API keys stored in environment variables
- CORS configuration for frontend
- Input validation on all endpoints
- File type validation for uploads
- Error handling to prevent information leakage

## Scalability

### Current Limitations
- In-memory conversation storage (should use database)
- Single ChromaDB instance (can scale to distributed)
- No load balancing (single backend instance)

### Future Improvements
- Database for conversation persistence
- Redis for caching
- Distributed vector database
- Load balancing and horizontal scaling
- Rate limiting and request queuing

## Deployment

### Docker Compose
- Backend and frontend services
- Shared network for communication
- Volume mounts for data persistence
- Environment variable injection

### Production Considerations
- Use production-grade database
- Implement proper authentication
- Add rate limiting
- Set up monitoring and logging
- Configure backup strategies
- Use managed services for vector DB and memory

## Development Workflow

1. Backend development: FastAPI with hot reload
2. Frontend development: Next.js with hot reload
3. Docker: Full stack orchestration
4. Testing: Unit tests for services, integration tests for API

## Monitoring

- Health check endpoint: `/health`
- API documentation: `/docs`
- Logging: Structured logging (to be implemented)
- Metrics: Request/response metrics (to be implemented)
