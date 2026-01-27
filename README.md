# 🧠 Aware AI

### A Production-Grade Self-Aware RAG System with Intelligent Memory Management

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat-square&logo=openai)](https://openai.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.3-06B6D4?style=flat-square&logo=tailwindcss)](https://tailwindcss.com/)
[![Supabase](https://img.shields.io/badge/Supabase-2.0-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com/)

---

**Aware AI** is an intelligent conversational system that combines **Retrieval-Augmented Generation (RAG)** with **persistent memory management** to deliver context-aware, personalized AI interactions. Built with a modern tech stack optimized for production deployment.

🌐 **Live Demo:** [aware-ai-rag.vercel.app](https://aware-ai-rag.vercel.app)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Real-time Streaming** | Server-Sent Events (SSE) for instant, token-by-token response delivery |
| 🧠 **Intelligent Memory** | Mem0-powered memory that learns and remembers across conversations |
| 📄 **Document RAG** | Upload PDFs, DOCX, Markdown—AI understands and retrieves from your documents |
| 💬 **Multi-turn Conversations** | Full conversation history with thread management and persistence |
| 🔍 **Semantic Search** | Vector-based search across conversation history and documents |
| 🌙 **Dark Mode** | Beautiful UI with system-aware dark/light theme toggle |
| ⌨️ **Keyboard Shortcuts** | Power-user shortcuts (Ctrl+K, Ctrl+/) for efficient navigation |
| 📤 **Export Conversations** | Download chats as JSON or Markdown |
| 📱 **Mobile Responsive** | Fully responsive design with collapsible sidebar |

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async Python web framework |
| **OpenAI GPT-4** | Large Language Model for intelligent responses |
| **Mem0** | Persistent, searchable memory layer |
| **ChromaDB** | Vector database for semantic search |
| **LangChain** | LLM orchestration and chaining |
| **Supabase** | PostgreSQL database for conversation persistence |
| **SSE-Starlette** | Server-Sent Events for real-time streaming |
| **WebSockets** | Bi-directional real-time communication |
| **PyPDF2 / python-docx** | Document processing pipeline |
| **tiktoken** | Token counting and context management |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Next.js 14** | React framework with App Router |
| **React 18** | UI component library |
| **TypeScript** | Type-safe JavaScript |
| **Tailwind CSS** | Utility-first CSS framework |
| **react-markdown** | Markdown rendering for AI responses |
| **react-syntax-highlighter** | Code syntax highlighting with themes |
| **react-hot-toast** | Toast notifications |
| **Lucide React** | Beautiful icon library |
| **Recharts** | Data visualization components |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Vercel** | Frontend deployment with edge functions |
| **AWS App Runner** | Containerized backend deployment |
| **Docker** | Container orchestration |
| **Supabase Cloud** | Managed PostgreSQL database |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Next.js 14 (Vercel)                    │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │   React 18  │ │  Tailwind   │ │  react-markdown     │  │  │
│  │  │  TypeScript │ │    CSS      │ │  syntax-highlighter │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS / SSE
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │               FastAPI (AWS App Runner)                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │   LLM    │ │   RAG    │ │  Memory  │ │   Document   │  │  │
│  │  │ Service  │ │ Service  │ │ Service  │ │  Processor   │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────────────┘  │  │
│  └───────┼────────────┼────────────┼────────────────────────┘  │
└──────────┼────────────┼────────────┼────────────────────────────┘
           │            │            │
           ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ OpenAI   │  │ ChromaDB │  │   Mem0   │  │   Supabase   │
    │ GPT-4    │  │ Vectors  │  │  Memory  │  │  PostgreSQL  │
    └──────────┘  └──────────┘  └──────────┘  └──────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/aware-AI.git
cd aware-AI

# Copy environment template
cp .env.example .env
```

Configure your `.env` file:
```env
# Required
OPENAI_API_KEY=sk-...

# Optional - Supabase for persistence
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Optional - Mem0 for cloud memory
MEM0_API_KEY=your-mem0-key
```

### Backend

```bash
cd packages/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd packages/frontend
npm install
npm run dev
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
aware-AI/
├── packages/
│   ├── backend/                 # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/             # REST & WebSocket routes
│   │   │   ├── core/            # Config & logging
│   │   │   ├── models/          # Pydantic schemas
│   │   │   ├── services/        # Business logic
│   │   │   │   ├── llm_service.py
│   │   │   │   ├── rag_service.py
│   │   │   │   ├── memory_service.py
│   │   │   │   ├── embedding_service.py
│   │   │   │   ├── document_processor.py
│   │   │   │   ├── memory_compression.py
│   │   │   │   ├── conversation_service.py
│   │   │   │   └── fine_tuning_service.py
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── frontend/                # Next.js Frontend
│       ├── src/
│       │   ├── app/             # App Router pages
│       │   ├── components/      # React components
│       │   │   ├── ChatInterface.tsx
│       │   │   ├── MessageBubble.tsx
│       │   │   ├── ThreadSidebar.tsx
│       │   │   ├── DocumentUpload.tsx
│       │   │   └── ThemeProvider.tsx
│       │   └── lib/             # API client
│       ├── Dockerfile
│       └── package.json
│
├── docs/
│   └── ARCHITECTURE.md          # Detailed architecture
├── docker-compose.yml
└── .env.example
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send message with SSE streaming response |
| `POST` | `/api/upload` | Upload and process documents (PDF, DOCX, MD) |
| `GET` | `/api/threads` | List all conversation threads |
| `GET` | `/api/threads/{id}` | Get thread with full message history |
| `DELETE` | `/api/threads/{id}` | Delete a conversation thread |
| `GET` | `/api/stats` | Get session and lifetime statistics |
| `POST` | `/api/memory/compress` | Trigger memory compression |
| `GET` | `/api/memory/search` | Semantic search across memories |
| `WS` | `/ws/chat` | WebSocket endpoint for real-time chat |

**API Documentation:** `http://localhost:8000/docs` (Swagger UI)

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Start new chat |
| `Ctrl + /` | Focus message input |
| `Escape` | Close mobile sidebar |

---

## 🎨 UI Features

- **Dark/Light Mode** - System-aware theme with manual toggle
- **Code Highlighting** - Syntax-highlighted code blocks with copy button
- **Markdown Rendering** - Full markdown support in AI responses
- **Toast Notifications** - Feedback for uploads, errors, and actions
- **Responsive Design** - Optimized for desktop, tablet, and mobile
- **Export Options** - Download conversations as JSON or Markdown

---

## 📈 Performance

- **Streaming Responses** - Token-by-token delivery via SSE
- **Optimized Bundle** - Next.js automatic code splitting
- **Edge Deployment** - Vercel edge network for low latency
- **Connection Pooling** - Efficient database connections via Supabase
- **Vector Indexing** - Fast semantic search with ChromaDB

---

## 🔒 Security

- Environment-based configuration (no hardcoded secrets)
- CORS protection with configurable origins
- Input validation via Pydantic schemas
- Secure file upload with type validation

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.

---

<p align="center">
  Built with ❤️ using modern AI technologies
</p>
