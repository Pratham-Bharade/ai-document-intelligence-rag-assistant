# Enterprise AI Document Intelligence & RAG Assistant (v1.0.0)

[![Continuous Integration (CI)](https://github.com/Pratham-Bharade/ai-document-intelligence-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Pratham-Bharade/ai-document-intelligence-rag-assistant/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.3-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg)](https://www.docker.com/)

An enterprise-grade, high-throughput **Retrieval-Augmented Generation (RAG) and Document Intelligence Platform** designed for deep reasoning over complex PDFs, scanned documents, and multi-page technical manuals. 

Engineered from scratch across 25 modular phases with dual LLM fallback (Groq LPU + OpenAI), hybrid vector retrieval (RRF), multi-tier semantic caching, PII security guardrails, asynchronous Redis task queues, and real-time Server-Sent Events (SSE) typewriter streaming.

---

## Key Features & Highlights

- **Multi-Engine PDF Extraction & OCR:** Ingests native text, forms, and scanned image PDFs using PyMuPDF and Tesseract OCR heuristics.
- **Hybrid Dense & Lexical Retrieval (RRF):** Merges cosine semantic vectors with BM25 keyword matching via Reciprocal Rank Fusion.
- **Dual LLM Gateway with Automatic Fallback:** Ultra-low latency inference via Groq LPU (`llama-3.3-70b-versatile`) with automated fallback to OpenAI (`gpt-4o-mini`).
- **Real-Time Token Streaming:** Server-Sent Events (SSE) with typewriter animations and verified clickable source citation badges.
- **Enterprise Security Guardrails:** Automated prompt injection detection, PII regex redaction, and answer faithfulness verification.
- **Multi-Turn Conversation Memory:** Context window budgeting and standalone query re-writing.
- **Multi-Tier Query Caching:** Sub-1ms SHA-256 exact hash cache and sub-15ms semantic embedding cosine cache with automated document invalidation.
- **Asynchronous Redis Task Queue:** Non-blocking background document ingestion with real-time progress polling.
- **Full Observability & Telemetry:** Prometheus metrics (`/metrics`), structured JSON logging, and `X-Request-ID` correlation tracing.
- **Vector Scalar Quantization (SQ8):** 75% vector RAM compression with > 99% accuracy retention.
- **Modern React 18 + TypeScript SPA:** Dark-mode dashboard built with Tailwind CSS, Lucide icons, and Axios JWT interceptors.

---

## Quickstart with Docker Compose

Ensure [Docker](https://www.docker.com/) and Docker Compose are installed, then run:

```bash
# 1. Clone repository
git clone https://github.com/Pratham-Bharade/ai-document-intelligence-rag-assistant.git
cd ai-document-intelligence-rag-assistant

# 2. Configure environment keys
cp backend/.env.example backend/.env
# Add your GROQ_API_KEY and OPENAI_API_KEY in backend/.env

# 3. Launch all 4 multi-container services
docker compose up -d --build
```

Access the services:
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Telemetry Scrape:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **PostgreSQL Database:** `localhost:5432` (`raguser` / `ragpassword`)
- **Redis Cache & Queue:** `localhost:6379`

---

## Manual Local Development Setup

### 1. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt

# Run database migrations and launch server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (React + Vite)
```bash
cd frontend
npm install
npm run dev
# Vite runs at http://localhost:5173
```

---

## Running the Automated Test Suite

The test suite covers 109 automated unit, integration, security, and full-lifecycle tests:

```bash
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest -v
```

---

## REST API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user account |
| `POST` | `/api/auth/login/json` | Authenticate and obtain JWT access token |
| `POST` | `/api/documents/upload` | Synchronous PDF upload & RAG indexing |
| `POST` | `/api/documents/upload/async` | Asynchronous upload returning task ID (HTTP 202) |
| `GET` | `/api/documents/tasks/{task_id}` | Poll background ingestion progress (0-100%) |
| `GET` | `/api/documents` | List user uploaded documents |
| `DELETE` | `/api/documents/{id}` | Delete document and invalidate cached queries |
| `POST` | `/api/rag/query` | Grounded RAG query with source citations |
| `POST` | `/api/rag/query/stream` | Server-Sent Events (SSE) token stream |
| `POST` | `/api/conversations` | Create multi-turn conversation session |
| `POST` | `/api/conversations/{id}/messages`| Send message with context memory & query re-writing |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint |
| `GET` | `/health` | System health check |

---

## Architecture Specification

For a comprehensive deep-dive into all 25 modular subsystems, database schemas, and mathematical derivations, refer to [ARCHITECTURE.md](file:///D:/Ai%20Projects/AI%20Document%20Intelligence%20&%20RAG%20Assistant/ARCHITECTURE.md).

---

## License
Released under the [MIT License](LICENSE).
