# Aware AI - Self-Aware RAG System with Memory Management

A production-ready AI system featuring:
- **RAG (Retrieval-Augmented Generation)** with multi-modal support
- **Mem0** for intelligent memory management
- **Real-time streaming** chat interface
- **Multi-turn conversations** with context awareness
- **Semantic search** over conversation history
- **Knowledge graph** visualization
- **Fine-tuning pipeline** for custom models
- **Custom embedding models** support
- **Document processing** (PDF, DOCX, Markdown, Images)
- **Automatic memory summarization** and compression

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js 14+ with Tailwind CSS
- **Vector DB**: ChromaDB (local) / Pinecone (cloud)
- **Memory**: Mem0
- **LLM**: OpenAI API
- **Embeddings**: OpenAI / Custom models (sentence-transformers)

## Project Structure

```
aware-AI/
├── packages/
│   ├── backend/          # FastAPI backend
│   │   ├── app/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/         # Next.js frontend
│       ├── src/
│       ├── package.json
│       └── Dockerfile
├── docs/                 # Documentation
├── docker-compose.yml    # Root-level orchestration
├── .env.example          # Environment template
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd aware-AI
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other configurations
```

3. **Backend Setup:**
```bash
cd packages/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Frontend Setup:**
```bash
cd packages/frontend
npm install
```

5. **Run Backend:**
```bash
cd packages/backend
uvicorn app.main:app --reload --port 8000
```

6. **Run Frontend:**
```bash
cd packages/frontend
npm run dev
```

### Docker Setup

```bash
# Build and run all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `OPENAI_MODEL` - Model to use (default: gpt-4-turbo-preview)
- `MEM0_API_KEY` - Mem0 API key (optional, falls back to local)
- `VECTOR_DB_TYPE` - Vector database type (chroma or pinecone)
- `USE_CUSTOM_EMBEDDINGS` - Use custom embedding models (true/false)

## Features

### Core AI Features
- ✅ Multi-modal RAG (text, PDFs, images, web scraping)
- ✅ Real-time streaming responses
- ✅ Multi-turn conversation management
- ✅ Semantic search over history
- ✅ Knowledge graph visualization

### Advanced Features
- ✅ Fine-tuning pipeline
- ✅ Custom embedding models
- ✅ Document processing pipeline
- ✅ Automatic memory summarization & compression

## API Documentation

Once the backend is running, visit:
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Frontend**: http://localhost:3000

### Key Endpoints

- `POST /api/chat` - Chat with streaming support
- `POST /api/upload` - Upload and process documents
- `POST /api/memory/compress` - Compress memories
- `GET /api/memory/search` - Search memories
- `GET /api/conversations/{id}` - Get conversation history
- `WS /ws/chat` - WebSocket chat endpoint

## Development

### Backend Development
```bash
cd packages/backend
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd packages/frontend
npm run dev
```

### Running Tests
```bash
# Backend tests (when implemented)
cd packages/backend
pytest

# Frontend tests (when implemented)
cd packages/frontend
npm test
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.
