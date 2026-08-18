# AI Document Intelligence & RAG Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18+-blue?style=flat-square&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-16+-blue?style=flat-square&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Production-oriented AI-powered document question-answering system using Retrieval-Augmented Generation (RAG)**

</div>

---

## 🧠 What Is This?

This system allows users to upload documents (PDFs) and ask natural language questions about them. Instead of manually searching through pages, the AI retrieves the most relevant sections and generates a grounded, cited answer in seconds.

**Example:**
> Upload your company HR policy PDF, then ask:
> *"How many sick leave days can I carry forward to next year?"*
> 
> The system retrieves the exact relevant paragraph and answers with the page number.

---

## 🏗️ Architecture

```
User → React Frontend
     → FastAPI Backend
     → RAG Pipeline (chunk → embed → retrieve → generate)
     → PostgreSQL + pgvector (unified relational + vector store)
     → LLM API (Groq / OpenAI)
```

Full architecture documentation: [docs/architecture.md](docs/architecture.md)

---

## ✨ Features

- 📄 **Document Upload & Processing** — PDF upload, text extraction, OCR for scanned PDFs
- 🧩 **Intelligent Chunking** — Overlapping chunks for better retrieval context
- 🔢 **Vector Embeddings** — Semantic search (not just keyword matching)
- 🔍 **RAG Retrieval** — Top-K similarity search with pgvector
- 🤖 **LLM Answer Generation** — Grounded answers citing source pages
- 💬 **Conversation Memory** — Multi-turn conversations with history
- 🔐 **Authentication** — JWT-based user authentication
- 📚 **Multi-Document** — Ask questions across multiple uploaded documents
- 🛡️ **Hallucination Controls** — System prompt constraints and source citations

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, TanStack Query |
| Backend | Python 3.10+, FastAPI, Pydantic, SQLAlchemy |
| AI/RAG | sentence-transformers, Groq/OpenAI LLM API |
| Database | PostgreSQL 16 + pgvector |
| DevOps | Docker, Docker Compose, Git/GitHub |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 16 with pgvector extension
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-rag-assistant.git
cd ai-rag-assistant
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Database Setup

```bash
# Ensure PostgreSQL is running with pgvector extension
# Then run migrations:
alembic upgrade head
```

### 5. Start Backend

```bash
uvicorn app.main:app --reload
# API available at: http://localhost:8000
# Interactive API docs: http://localhost:8000/docs
```

### 6. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Frontend available at: http://localhost:5173
```

### 7. Docker (All-in-One)

```bash
docker-compose up --build
```

---

## 📁 Project Structure

```
ai-rag-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/                 # API routes and dependencies
│   │   ├── core/                # Configuration and logging
│   │   ├── rag/                 # Complete RAG pipeline
│   │   │   ├── loader.py        # PDF loading and text extraction
│   │   │   ├── preprocessing.py # Text cleaning and normalization
│   │   │   ├── splitter.py      # Document chunking
│   │   │   ├── embeddings.py    # Embedding generation
│   │   │   ├── vector_store.py  # pgvector storage
│   │   │   ├── retriever.py     # Similarity search
│   │   │   ├── context_builder.py
│   │   │   ├── prompts.py       # Prompt templates
│   │   │   └── pipeline.py      # End-to-end RAG orchestration
│   │   ├── services/            # Business logic layer
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   └── db/                  # Database connection and sessions
│   ├── tests/                   # Test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # React application
├── docs/                        # Architecture and documentation
├── scripts/                     # Utility scripts
├── .env.example                 # Environment variable template
├── docker-compose.yml
├── README.md
└── CHANGELOG.md
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System and RAG architecture |
| [Database](docs/database.md) | Schema, relationships, pgvector |
| [RAG Pipeline](docs/rag.md) | How the RAG pipeline works |
| [API Reference](docs/api.md) | All API endpoints |
| [Security](docs/security.md) | Security model |
| [Evaluation](docs/evaluation.md) | RAG quality evaluation |
| [Deployment](docs/deployment.md) | Docker and deployment guide |

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

---

## 📊 RAG Pipeline Flow

```
Document Upload         Question Asked
──────────────          ──────────────
PDF                     User Question
 ↓                           ↓
Validate               Embed Question
 ↓                           ↓
Extract Text         Vector Similarity
 ↓                        Search
Preprocess                   ↓
 ↓                      Top-K Chunks
Chunk                        ↓
 ↓                     Build Context
Embed Chunks                 ↓
 ↓                    Craft LLM Prompt
Store in pgvector            ↓
                        LLM Response
                             ↓
                     Answer + Citations
```

---

## 🌱 Development Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Project setup | ✅ Complete |
| 2 | Architecture | 🔄 In Progress |
| 3 | Document Ingestion | ⏳ Planned |
| 4 | Text Processing | ⏳ Planned |
| 5 | Chunking | ⏳ Planned |
| 6 | Embeddings | ⏳ Planned |
| 7 | Vector Search | ⏳ Planned |
| 8 | Retrieval | ⏳ Planned |
| 9 | LLM Integration | ⏳ Planned |
| 10 | RAG Pipeline | ⏳ Planned |

---

## 🤝 Contributing

This is a learning project. If you're reading this repository for reference:
1. Start with `docs/architecture.md` for system understanding.
2. Read `docs/rag.md` to understand the RAG pipeline.
3. Explore `backend/app/rag/` for the core AI implementation.

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

Built as a learning project to deeply understand Generative AI, RAG systems, and production AI application development.

> *"The goal is not just a working project, but the ability to understand, explain, debug, and defend every component."*
