# Enterprise AI Document Intelligence & RAG Assistant
## Technical Architecture & Subsystem Specification (v1.0.0)

---

## 1. System Overview & Architecture Diagram

```text
                                  +---------------------------------------+
                                  |     React 18 + TypeScript SPA         |
                                  |   (Vite, Tailwind, SSE Streaming)     |
                                  +-------------------+-------------------+
                                                      |
                                                      | HTTP / SSE
                                                      v
                                  +---------------------------------------+
                                  |         Nginx Reverse Proxy           |
                                  |   (SSL, Rate Limit, SSE Buffer Off)   |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+--------------------------------------------------------------------------------------------------------------------+
|                                              FastAPI Application Layer                                              |
|                                                                                                                    |
|   [ Security Middleware ] ----> [ RequestIdMiddleware ] ----> [ AuditLoggingMiddleware ] ----> [ RateLimiter ]     |
|                                                                                                                    |
|   +-------------------+   +--------------------+   +--------------------+   +----------------------------------+   |
|   |  /api/auth Routes |   | /api/docs Routes   |   |  /api/rag Routes   |   | /api/conversations Routes        |   |
|   +---------+---------+   +---------+----------+   +---------+----------+   +----------------+-----------------+   |
|             |                       |                        |                               |                     |
+-------------|-----------------------|------------------------|-------------------------------|---------------------+
              |                       |                        |                               |
              v                       v                        v                               v
+-----------------------+   +--------------------+   +--------------------+   +----------------------------------+
| AuthService (JWT/Bcr) |   | DocumentService    |   | RAGPipeline        |   | ConversationMemoryManager        |
+-----------------------+   +---------+----------+   +---------+----------+   +----------------------------------+
                                      |                        |
                                      v                        |
                            +--------------------+             |
                            | TaskQueueManager   |             |
                            | (Redis / Async)    |             |
                            +---------+----------+             |
                                      |                        |
                                      v                        v
                            +--------------------+   +--------------------+
                            | Document Ingestion |   | Multi-Tier Cache   |
                            | & Tesseract OCR    |   | (Exact + Semantic) |
                            +---------+----------+   +---------+----------+
                                      |                        |
                                      v                        v
                            +--------------------+   +--------------------+
                            | Recursive Chunking |   | Hybrid Retriever   |
                            | & Preprocessing    |   | (Dense + Lexical)  |
                            +---------+----------+   +---------+----------+
                                      |                        |
                                      v                        v
                            +--------------------+   +--------------------+
                            | Embedder (OpenAI)  |   | LLM Gateway (Groq) |
                            | & Quantizer (SQ8)  |   | + OpenAI Fallback  |
                            +---------+----------+   +---------+----------+
                                      |                        |
                                      +------------+-----------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------------------------+
|                                              Persistence & Telemetry Tier                                          |
|                                                                                                                    |
|   [ PostgreSQL 16 + pgvector ]          [ Redis 7.0 Cache & Queue ]          [ Prometheus /metrics Scraper ]       |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 2. The 25 Core Modular Subsystems

| Phase | Subsystem | File Location | Responsibility |
| :--- | :--- | :--- | :--- |
| **01** | Project Setup & Environment | `backend/` | Virtualenv, pyproject, and dependencies |
| **02** | Layered Architecture | `backend/app/` | Domain-driven modular folder organization |
| **03** | Document Ingestion & PDF | `app/rag/loader.py` | PyMuPDF streaming, validation, OCR heuristics |
| **04** | Text Preprocessing | `app/rag/preprocessing.py` | Unicode NFC normalization, whitespace cleaning |
| **05** | Recursive Chunking | `app/rag/splitter.py` | Paragraph/sentence-aware token chunking with overlap |
| **06** | Vector Embeddings | `app/rag/embeddings.py` | OpenAI embeddings generation with batching & retries |
| **07** | Vector Similarity Store | `app/rag/vector_store.py` | Cosine similarity, thresholding & ranking |
| **08** | Hybrid Retrieval & RRF | `app/rag/retriever.py` | Dense vector + BM25 keyword Reciprocal Rank Fusion |
| **09** | Dual LLM Gateway | `app/rag/llm.py` | Groq LPU primary with automatic OpenAI fallback |
| **10** | End-to-End Orchestrator | `app/rag/pipeline.py` | Unified RAG query and ingestion pipeline |
| **11** | Prompt Engineering | `app/rag/prompts.py` | Few-shot grounded prompts, QA, Summary, Extraction |
| **12** | Security Guardrails | `app/rag/guardrails.py` | Prompt injection detection, PII redaction, faithfulness |
| **13** | RAG Triad Evaluation | `app/rag/evaluation.py` | Context relevance, faithfulness, answer relevance |
| **14** | Database & ORM | `app/models/`, `app/db/` | SQLAlchemy 2.0 models, PostgreSQL engine, UUIDs |
| **15** | REST API Endpoints | `app/api/routes/` | FastAPI REST routes, SSE streaming responses |
| **16** | Auth & Security Middleware | `app/core/security.py` | JWT, Bcrypt, RBAC, Rate Limiting, OWASP headers |
| **17** | Conversation Memory | `app/rag/memory.py` | Sliding window multi-turn compression & rephrasing |
| **18** | React + TypeScript SPA | `frontend/` | Vite, Tailwind CSS, Typewriter token streaming, Citations |
| **19** | Docker Containerization | `Dockerfile`, `compose` | Production multi-stage Docker builds & Compose |
| **20** | Observability & Telemetry | `app/core/telemetry.py` | Structured JSON logs, Request IDs, Prometheus `/metrics` |
| **21** | Background Workers | `app/workers/` | Redis task queues for async PDF ingestion & polling |
| **22** | Multi-Tier Query Caching | `app/core/cache.py` | Exact SHA-256 hash & Semantic cosine cache |
| **23** | CI/CD Pipelines | `.github/workflows/` | GitHub Actions for Pytest, Vite build, GHCR publishing |
| **24** | Performance & Quantization | `app/rag/quantization.py` | 8-bit Scalar Quantization (SQ8) & Stream Debouncer |
| **25** | Production Release | `README.md`, `v1.0.0` | Full documentation, E2E lifecycle test, release tag |

---

## 3. Database Schema

```text
+-------------------+       +-----------------------+       +------------------------+
|       users       |       |       documents       |       |    document_chunks     |
+-------------------+       +-----------------------+       +------------------------+
| id (UUID, PK)     |<---+  | id (UUID, PK)         |<---+  | id (UUID, PK)          |
| email (Unique)    |    +--| user_id (FK)          |    +--| document_id (FK)       |
| hashed_password   |       | title                 |       | chunk_index (Integer)  |
| full_name         |       | file_path             |       | page_number (Integer)  |
| is_active         |       | file_size             |       | text (Text)            |
| is_superuser      |       | total_pages           |       | metadata_json (JSONB)  |
| created_at        |       | status (processed/..) |       | created_at             |
| updated_at        |       | created_at            |       +------------------------+
+---------+---------+       +-----------------------+
          |
          |                 +-----------------------+       +------------------------+
          |                 |     conversations     |       |        messages        |
          |                 +-----------------------+       +------------------------+
          +---------------->| id (UUID, PK)         |<---+  | id (UUID, PK)          |
                            | user_id (FK)          |    +--| conversation_id (FK)   |
                            | title                 |       | role (user/assistant)  |
                            | created_at            |       | content (Text)         |
                            +-----------------------+       | prompt_mode            |
                                                            | sources_json (JSONB)   |
                                                            | created_at             |
                                                            +------------------------+
```
