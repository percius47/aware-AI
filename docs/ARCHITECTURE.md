# 🏗️ Aware AI - System Architecture

## Overview

Aware AI is a production-grade conversational AI system that combines **Retrieval-Augmented Generation (RAG)** with **intelligent memory management**. The system is designed as a modern monorepo with clear separation of concerns between the frontend, backend, and external services.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        Next.js 14 (App Router)                         │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │  │
│  │  │   React    │  │  Tailwind  │  │    SSE     │  │    Theme       │   │  │
│  │  │ Components │  │    CSS     │  │   Client   │  │   Provider     │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘   │  │
│  │                                                                        │  │
│  │  Components: ChatInterface │ MessageBubble │ ThreadSidebar │ Upload   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                              Deployed on: Vercel                              │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                          HTTPS / Server-Sent Events
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Application                               │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      API Routes                                  │  │  │
│  │  │  POST /api/chat ──────► SSE Streaming Response                  │  │  │
│  │  │  POST /api/upload ────► Document Processing                     │  │  │
│  │  │  GET  /api/threads ───► Thread Listing                          │  │  │
│  │  │  GET  /api/stats ─────► Session Statistics                      │  │  │
│  │  │  WS   /ws/chat ───────► WebSocket Real-time                     │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  Middleware: CORS │ Request Logging │ Error Handling                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                            Deployed on: AWS App Runner                        │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                      │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  LLM Service │  │  RAG Service │  │   Memory     │  │   Conversation   │  │
│  │              │  │              │  │   Service    │  │     Service      │  │
│  │  • OpenAI    │  │  • ChromaDB  │  │              │  │                  │  │
│  │  • Streaming │  │  • Embedding │  │  • Mem0      │  │  • Supabase      │  │
│  │  • Context   │  │  • Search    │  │  • Search    │  │  • Persistence   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                 │                    │            │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐  ┌────────┴─────────┐  │
│  │  Embedding   │  │   Document   │  │    Memory    │  │   Fine-tuning    │  │
│  │   Service    │  │  Processor   │  │ Compression  │  │     Service      │  │
│  │              │  │              │  │              │  │                  │  │
│  │  • OpenAI    │  │  • PDF       │  │  • LLM       │  │  • Data Prep     │  │
│  │  • Custom    │  │  • DOCX      │  │  • Threshold │  │  • Job Mgmt      │  │
│  │  • Vectors   │  │  • Markdown  │  │  • Summary   │  │  • Monitoring    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                                               │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                    │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   OpenAI     │  │   ChromaDB   │  │     Mem0     │  │    Supabase      │  │
│  │              │  │              │  │              │  │                  │  │
│  │  GPT-4       │  │  Vector DB   │  │   Memory     │  │   PostgreSQL     │  │
│  │  Embeddings  │  │  Similarity  │  │   Storage    │  │   Threads DB     │  │
│  │  Fine-tune   │  │  Search      │  │   Search     │  │   Real-time      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### Frontend Components

#### 1. ChatInterface (`ChatInterface.tsx`)
The main chat component handling user interactions.

**Responsibilities:**
- Message state management with React hooks
- SSE connection for streaming responses
- Input handling with keyboard shortcuts
- Document upload integration
- Loading states and typing indicators

**Key Features:**
```typescript
- Real-time streaming via EventSource API
- Optimistic UI updates
- Auto-scroll to latest messages
- File attachment handling
- Focus management (Ctrl+/ shortcut)
```

#### 2. MessageBubble (`MessageBubble.tsx`)
Renders individual chat messages with rich formatting.

**Features:**
- Markdown rendering via `react-markdown`
- Code syntax highlighting with `react-syntax-highlighter` (One Dark theme)
- Copy code button on code blocks
- Copy full response button
- Relative timestamps (hover to see)
- Typing indicator animation
- Dark mode support

#### 3. ThreadSidebar (`ThreadSidebar.tsx`)
Manages conversation thread navigation.

**Features:**
- Thread grouping by date (Today, Yesterday, Previous 7 Days, Older)
- Mobile-responsive with slide-out animation
- Thread deletion with confirmation
- Keyboard shortcut hint (⌘+K)
- Persistence status indicator

#### 4. ThemeProvider (`ThemeProvider.tsx`)
React Context for theme management.

**Implementation:**
```typescript
- localStorage persistence
- System preference detection
- SSR-safe with fallback values
- Applies 'dark' class to <html>
```

---

### Backend Services

#### 1. LLM Service (`llm_service.py`)
Handles all OpenAI API interactions.

```python
class LLMService:
    - generate_response()      # Non-streaming completion
    - generate_stream()        # Streaming completion via SSE
    - build_context()          # Construct prompts with memory + RAG
```

**Configuration:**
- Model: GPT-4 Turbo (configurable)
- Temperature: 0.7 (configurable)
- Max tokens: Dynamic based on context

#### 2. RAG Service (`rag_service.py`)
Implements Retrieval-Augmented Generation.

```python
class RAGService:
    - add_document()           # Embed and store document chunks
    - search()                 # Semantic similarity search
    - index_conversation()     # Index chat history for retrieval
```

**Vector Storage:**
- ChromaDB for local development
- Pinecone support for production scale

#### 3. Memory Service (`memory_service.py`)
Manages persistent user memories via Mem0.

```python
class MemoryService:
    - add_memory()             # Store new memory
    - search_memories()        # Semantic memory search
    - get_all_memories()       # Retrieve user memories
    - delete_memory()          # Remove specific memory
```

**Fallback:**
- Graceful degradation to in-memory storage if Mem0 unavailable

#### 4. Conversation Service (`conversation_service.py`)
Handles conversation persistence with Supabase.

```python
class ConversationService:
    - create_thread()          # Create new conversation
    - add_message()            # Append message to thread
    - get_thread()             # Retrieve thread with messages
    - list_threads()           # Get all user threads
    - delete_thread()          # Remove conversation
    - generate_title()         # AI-generated thread titles
```

**Database Schema:**
```sql
-- threads table
id: UUID PRIMARY KEY
title: TEXT
created_at: TIMESTAMP
updated_at: TIMESTAMP

-- messages table
id: UUID PRIMARY KEY
thread_id: UUID REFERENCES threads
role: TEXT ('user' | 'assistant')
content: TEXT
created_at: TIMESTAMP
```

#### 5. Document Processor (`document_processor.py`)
Processes uploaded documents for RAG.

**Supported Formats:**
| Format | Library | Features |
|--------|---------|----------|
| PDF | PyPDF2 | Text extraction, page numbers |
| DOCX | python-docx | Paragraphs, formatting |
| Markdown | Native | Headers, code blocks |
| Plain Text | Native | Direct processing |

**Processing Pipeline:**
1. File type detection
2. Content extraction
3. Text chunking (500 tokens, 50 overlap)
4. Metadata attachment
5. Vector embedding
6. ChromaDB storage

#### 6. Memory Compression (`memory_compression.py`)
Manages memory optimization.

```python
class MemoryCompressionService:
    - should_compress()        # Check threshold
    - compress_memories()      # Summarize via LLM
    - cleanup_old_memories()   # Remove compressed originals
```

**Algorithm:**
1. Count total memories
2. If > threshold (default: 100)
3. Retrieve recent memories
4. Generate LLM summary
5. Store summary as new memory
6. Optionally delete originals

#### 7. Embedding Service (`embedding_service.py`)
Generates vector embeddings.

**Providers:**
- OpenAI `text-embedding-3-small` (default)
- Custom sentence-transformers models

```python
class EmbeddingService:
    - embed_text()             # Single text embedding
    - embed_batch()            # Batch embeddings
    - get_dimensions()         # Vector dimensions
```

---

## Data Flows

### Chat Message Flow

```
User Input
    │
    ▼
┌─────────────────┐
│  ChatInterface  │ ─── POST /api/chat ───►
└─────────────────┘
                                            ┌─────────────────────┐
                                            │   API Route Handler │
                                            │                     │
                                            │  1. Validate input  │
                                            │  2. Get/create      │
                                            │     conversation    │
                                            └──────────┬──────────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────┐
                    ▼                                  ▼                  ▼
            ┌──────────────┐                 ┌──────────────┐    ┌──────────────┐
            │ Memory Search│                 │  RAG Search  │    │  Build       │
            │ (Mem0)       │                 │  (ChromaDB)  │    │  Context     │
            └──────────────┘                 └──────────────┘    └──────────────┘
                    │                                  │                  │
                    └──────────────────────────────────┴──────────────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │   LLM Service       │
                                            │   (OpenAI GPT-4)    │
                                            │                     │
                                            │   Stream tokens     │
                                            └──────────┬──────────┘
                                                       │
                                              SSE Stream
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │   Save to Supabase  │
                                            │   Update memories   │
                                            │   Index in RAG      │
                                            └─────────────────────┘
                                                       │
                    ◄──────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│  MessageBubble  │ ─── Render streaming tokens
└─────────────────┘
```

### Document Upload Flow

```
File Selection
    │
    ▼
┌─────────────────┐
│ DocumentUpload  │ ─── POST /api/upload (multipart) ───►
└─────────────────┘
                                            ┌─────────────────────┐
                                            │  Document Processor │
                                            │                     │
                                            │  1. Detect format   │
                                            │  2. Extract text    │
                                            │  3. Chunk content   │
                                            └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │  Embedding Service  │
                                            │                     │
                                            │  Generate vectors   │
                                            │  for each chunk     │
                                            └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │      ChromaDB       │
                                            │                     │
                                            │  Store embeddings   │
                                            │  with metadata      │
                                            └─────────────────────┘
                                                       │
                    ◄──────────────────────────────────┘
    │
    ▼
┌─────────────────┐
│  Toast Success  │
└─────────────────┘
```

---

## Technology Choices & Rationale

### Why FastAPI?
- **Async-first**: Native async/await support for I/O-bound operations
- **Type Safety**: Pydantic integration for request/response validation
- **Auto-documentation**: Swagger UI generated from code
- **Performance**: One of the fastest Python frameworks

### Why Next.js 14?
- **App Router**: Modern React Server Components architecture
- **Edge Runtime**: Optimal for Vercel deployment
- **TypeScript**: First-class TypeScript support
- **Built-in Optimizations**: Image, font, and script optimization

### Why Supabase?
- **PostgreSQL**: Robust relational database
- **Real-time**: Built-in WebSocket subscriptions
- **Auth Ready**: Easy to add authentication later
- **Free Tier**: Generous free tier for development

### Why Mem0?
- **Semantic Memory**: More than key-value storage
- **Search**: Vector-based memory retrieval
- **Managed**: No infrastructure to maintain
- **Fallback**: Graceful local fallback

### Why ChromaDB?
- **Embedded**: No separate server needed
- **Python Native**: First-class Python support
- **Fast**: Optimized for similarity search
- **Portable**: Easy local development

---

## Deployment Architecture

```
                    ┌─────────────────────────────────────┐
                    │              Internet               │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │          Cloudflare / CDN           │
                    └─────────────────┬───────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         │                         ▼
┌───────────────────────┐             │             ┌───────────────────────┐
│       Vercel          │             │             │    AWS App Runner     │
│                       │             │             │                       │
│  ┌─────────────────┐  │             │             │  ┌─────────────────┐  │
│  │   Next.js 14    │  │◄────────────┘────────────►│  │    FastAPI      │  │
│  │   Static +      │  │        HTTPS/SSE          │  │    Container    │  │
│  │   Edge Runtime  │  │                           │  │                 │  │
│  └─────────────────┘  │                           │  └─────────────────┘  │
│                       │                           │                       │
│  Auto-deploy from     │                           │  Auto-deploy from     │
│  GitHub main branch   │                           │  GitHub main branch   │
└───────────────────────┘                           └───────────┬───────────┘
                                                                │
                    ┌───────────────────────────────────────────┤
                    │                   │                       │
                    ▼                   ▼                       ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
          │    Supabase     │ │     OpenAI      │ │        Mem0         │
          │                 │ │                 │ │                     │
          │  PostgreSQL     │ │  GPT-4 API      │ │  Memory Storage     │
          │  (Managed)      │ │  Embeddings     │ │  (Managed)          │
          └─────────────────┘ └─────────────────┘ └─────────────────────┘
```

---

## Security Considerations

| Area | Implementation |
|------|----------------|
| **Secrets** | Environment variables, never in code |
| **CORS** | Configured allowed origins |
| **Input Validation** | Pydantic schemas on all endpoints |
| **File Upload** | Type validation, size limits |
| **API Keys** | Server-side only, never exposed to client |

---

## Monitoring & Observability

| Metric | Source |
|--------|--------|
| **API Latency** | FastAPI middleware |
| **Error Rates** | Structured logging |
| **Token Usage** | OpenAI API tracking |
| **Memory Count** | Mem0 dashboard |
| **Database** | Supabase dashboard |

---

## Future Enhancements

- [ ] User authentication (Supabase Auth)
- [ ] Rate limiting middleware
- [ ] Redis caching layer
- [ ] Distributed vector database (Pinecone)
- [ ] Webhook integrations
- [ ] Multi-user support
- [ ] Analytics dashboard
- [ ] A/B testing for prompts

---

## Local Development

```bash
# Terminal 1 - Backend
cd packages/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd packages/frontend
npm run dev
```

**Environment Variables Required:**
```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js 14 App Router](https://nextjs.org/docs/app)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
