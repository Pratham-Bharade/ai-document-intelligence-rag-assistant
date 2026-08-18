# System Architecture

This document describes the core architecture of the AI Document Intelligence & RAG Assistant.

## 1. High-Level Architecture

The system follows a classic client-server model augmented with AI services:

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│                 │       │                 │       │   PostgreSQL    │
│  React Frontend │◄─────►│ FastAPI Backend │◄─────►│   + pgvector    │
│  (Vite + TS)    │ REST  │ (Python 3.10+)  │ SQL   │ (App Data +     │
│                 │ JSON  │                 │       │  Vector Search) │
└─────────────────┘       └────────┬────────┘       └─────────────────┘
                                   │
                                   │ API Calls
                                   ▼
                          ┌─────────────────┐
                          │   AI Services   │
                          │ (Groq / OpenAI  │
                          │   Embeddings)   │
                          └─────────────────┘
```

## 2. Backend Layered Architecture (Separation of Concerns)

Our FastAPI backend uses a strict **layered architecture**. This ensures that different parts of the application have single, clear responsibilities.

```text
HTTP Request
     │
     ▼
[ API Layer ]         (app/api/)
     │  - Defines HTTP methods (GET, POST)
     │  - Validates incoming JSON (Pydantic schemas)
     │  - Handles HTTP status codes and responses
     ▼
[ Service Layer ]     (app/services/)
     │  - Core business logic (e.g., Auth, User Management)
     │  - Orchestrates calls between Database and RAG layers
     │  - Does not know about HTTP requests directly
     ▼
[ RAG Layer ]         (app/rag/)
     │  - Document Ingestion (Loader, Preprocessing, Chunking)
     │  - Vector Generation (Embeddings)
     │  - Search and Retrieval (Vector Store, Retriever)
     │  - Context Building and LLM Prompting
     ▼
[ Database Layer ]    (app/db/ and app/models/)
        - SQLAlchemy ORM models
        - Database sessions and connections
        - Direct database queries and vector similarity search
```

### Why Layers?
- **Maintainability:** If we switch from FastAPI to another web framework, only the API layer changes.
- **Testability:** We can unit test the Service and RAG layers without making HTTP requests.
- **Security:** The API layer validates all inputs before they reach the core logic.

## 3. RAG (Retrieval-Augmented Generation) Architecture

The system has two main RAG workflows:

### A. Document Ingestion Pipeline
When a user uploads a PDF:
1. **Validation & Extraction:** Verify the file and extract text.
2. **Preprocessing:** Clean whitespace and normalize formatting.
3. **Chunking:** Split text into overlapping segments (e.g., 1000 chars with 200 overlap).
4. **Embedding:** Convert each chunk into a vector (array of floats).
5. **Storage:** Save chunk text, metadata (page number), and vector in PostgreSQL.

### B. Query & Generation Pipeline
When a user asks a question:
1. **Question Embedding:** Convert the user's question into a vector using the *same model*.
2. **Vector Search:** Calculate cosine similarity between the question vector and all chunk vectors in the database.
3. **Retrieval:** Return the Top-K most similar chunks.
4. **Context Construction:** Combine the Top-K chunks into a structured prompt.
5. **LLM Generation:** Send the prompt to the LLM to generate an answer grounded *only* in the provided context.

## 4. Database Architecture (Unified Store)

We use **PostgreSQL with the pgvector extension** to handle *both* relational application data and vector storage.

- **Relational Data:** Users, uploaded documents metadata, conversation history.
- **Vector Data:** Document chunks and their high-dimensional embeddings.

By combining these, we avoid the operational complexity of managing a separate dedicated vector database (like Qdrant or Pinecone) while easily supporting relational queries (e.g., "Search only within chunks from Document A belonging to User B").
