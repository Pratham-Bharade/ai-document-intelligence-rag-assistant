"""
File: backend/app/rag/pipeline.py
Purpose: Complete End-to-End RAG Orchestration Pipeline.
Why it exists: Connects all modular components built across Phases 3 through 9 into a
               cohesive, production-ready document ingestion and Q&A engine.
Dependencies: loader, preprocessing, splitter, embeddings, vector_store, retriever, llm
Main responsibilities:
  - Coordinate the entire ingestion lifecycle:
      PDF -> Validate -> Extract -> Clean -> Chunk -> Embed -> Store
  - Coordinate the entire query lifecycle:
      Question -> Retrieve -> Rank -> Prompt -> LLM -> Grounded Answer + Citations
  - Support both non-streaming and streaming generation with source attribution.
"""

import logging
import time
import uuid
from typing import Any, Dict, Generator, List, Optional

from app.core.cache import cache_manager
from app.core.telemetry import (
    FAITHFULNESS_SCORES,
    RAG_QUERIES_TOTAL,
    RAG_QUERY_LATENCY,
    SECURITY_ATTACKS_BLOCKED_TOTAL
)
from app.rag.embeddings import DocumentEmbedder
from app.rag.guardrails import SecurityGuardrails
from app.rag.llm import LLMService
from app.rag.loader import (
    extract_text_from_document,
    extract_text_from_pdf,
    validate_document,
    validate_pdf
)
from app.rag.preprocessing import preprocess_document
from app.rag.prompts import PromptMode, build_rag_messages
from app.rag.retriever import AdvancedRetriever
from app.rag.splitter import chunk_document
from app.rag.vector_store import InMemoryVectorStore

logger = logging.getLogger(__name__)


class RAGPipelineError(Exception):
    """Custom exception for all RAG pipeline execution errors."""
    pass


class RAGPipeline:
    """
    Unified RAG Orchestrator managing document ingestion, chunking,
    embedding, semantic search, hybrid retrieval, and LLM synthesis.
    """
    def __init__(
        self,
        embedder: Optional[DocumentEmbedder] = None,
        vector_store: Optional[InMemoryVectorStore] = None,
        retriever: Optional[AdvancedRetriever] = None,
        llm_service: Optional[LLMService] = None,
        guardrails: Optional[SecurityGuardrails] = None
    ):
        self.embedder = embedder or DocumentEmbedder()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.retriever = retriever or AdvancedRetriever(
            vector_store=self.vector_store,
            embedder=self.embedder
        )
        self.llm_service = llm_service or LLMService()
        self.guardrails = guardrails or SecurityGuardrails()

    def ingest_pdf(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the full ingestion pipeline on a single document file (PDF, Word, TXT, CSV, PPTX).
        
        Lifecycle:
          1. Validate file size & format
          2. Extract text and page numbers
          3. Preprocess and normalize text
          4. Split into recursive overlapping chunks
          5. Generate vector embeddings in batches
          6. Store chunks in vector database
          
        Returns:
          Ingestion report dict (document_id, total_pages, total_chunks)
        """
        doc_id = document_id or str(uuid.uuid4())
        meta = (custom_metadata or {}).copy()
        meta["document_id"] = doc_id
        meta["source_path"] = file_path

        logger.info(f"Starting ingestion for document {doc_id} from {file_path}...")

        # Step 1: Validation
        validate_document(file_path)

        # Step 2: Extraction
        extracted_data = extract_text_from_document(file_path)
        extracted_data["metadata"].update(meta)

        # Step 3: Preprocessing
        cleaned_data = preprocess_document(extracted_data)

        # Step 4: Chunking
        chunks = chunk_document(cleaned_data, chunk_size=1000, chunk_overlap=200)
        if not chunks:
            logger.warning(f"Document {doc_id} produced 0 text chunks.")
            return {
                "document_id": doc_id,
                "total_pages": cleaned_data.get("total_pages", 0),
                "total_chunks": 0,
                "status": "empty"
            }

        # Inject complete document metadata (title, filename, document_id) into each chunk
        for chunk in chunks:
            chunk["metadata"] = meta.copy()

        # Step 5: Embedding
        embedded_chunks = self.embedder.embed_chunks(chunks, batch_size=100)

        # Step 6: Vector Storage
        self.vector_store.add_chunks(embedded_chunks)

        logger.info(
            f"Successfully ingested document {doc_id}: "
            f"{cleaned_data.get('total_pages', 0)} pages, {len(chunks)} chunks."
        )

        return {
            "document_id": doc_id,
            "total_pages": cleaned_data.get("total_pages", 0),
            "total_chunks": len(chunks),
            "status": "success"
        }

    def query(
        self,
        question: str,
        top_k: int = 4,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        hybrid: bool = False,
        mode: PromptMode = PromptMode.QA,
        few_shot: bool = False,
        custom_instructions: Optional[str] = None,
        document_metadata: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full RAG query lifecycle:
          1. Retrieve Top-K relevant chunks (with metadata filter / hybrid search)
          2. Format grounded prompt with source citations and selected PromptMode
          3. Generate answer using LLM (Groq with OpenAI fallback)
          4. Format response with verified source citations
        """
        start_t = time.perf_counter()
        if not question.strip():
            RAG_QUERIES_TOTAL.labels(provider="none", mode=mode.value, status="error").inc()
            raise RAGPipelineError("Question cannot be empty.")

        # Step 0: Input Security & PII Redaction
        is_safe, sanitized_question, security_msg = self.guardrails.validate_input(question)
        if not is_safe:
            logger.warning(f"Query blocked by guardrails: {security_msg}")
            SECURITY_ATTACKS_BLOCKED_TOTAL.labels(attack_type="prompt_injection").inc()
            RAG_QUERIES_TOTAL.labels(provider="guardrails", mode=mode.value, status="blocked").inc()
            return {
                "answer": f"I cannot process this request: {security_msg}",
                "provider": "guardrails",
                "model": "security-filter",
                "sources": [],
                "total_sources": 0,
                "mode": mode.value,
                "guardrails": {"is_grounded": True, "faithfulness_score": 1.0, "blocked": True}
            }

        target_doc_id = (metadata_filter or {}).get("document_id")

        # Cache Check 1: Exact Query Cache
        cached_exact = cache_manager.get_exact(sanitized_question, target_doc_id, mode.value)
        if cached_exact:
            return cached_exact

        # Generate query embedding for retrieval & semantic cache check
        query_vector = self.embedder.embed_query(sanitized_question)

        # Cache Check 2: Semantic Similarity Query Cache
        cached_semantic = cache_manager.get_semantic(query_vector, target_doc_id, mode.value)
        if cached_semantic:
            return cached_semantic

        # Step 1: Retrieval
        retrieved_chunks = self.retriever.retrieve(
            query=sanitized_question,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
            hybrid=hybrid
        )

        # Step 2: Prompt Formatting with selected mode and few-shot grounding
        messages = build_rag_messages(
            query=sanitized_question,
            context_chunks=retrieved_chunks,
            mode=mode,
            few_shot=few_shot,
            custom_instructions=custom_instructions,
            document_metadata=document_metadata
        )

        # Step 3: LLM Generation
        llm_output = self.llm_service.generate(messages=messages)
        generated_answer = llm_output.get("content", "")

        # Step 4: Output Guardrails & Faithfulness Scoring
        guardrails_report = self.guardrails.verify_output(generated_answer, retrieved_chunks)
        faith_score = guardrails_report.get("faithfulness_score", 0.0)
        FAITHFULNESS_SCORES.observe(faith_score)

        # Step 5: Format Source Citations
        sources = []
        for chunk in retrieved_chunks:
            sources.append({
                "page_number": chunk.get("page_number"),
                "document_id": chunk.get("metadata", {}).get("document_id"),
                "score": chunk.get("score") or chunk.get("rrf_score"),
                "snippet": chunk.get("text", "")[:200] + ("..." if len(chunk.get("text", "")) > 200 else "")
            })

        duration = time.perf_counter() - start_t
        RAG_QUERY_LATENCY.labels(mode=mode.value).observe(duration)
        RAG_QUERIES_TOTAL.labels(
            provider=llm_output.get("provider", "unknown"),
            mode=mode.value,
            status="success"
        ).inc()

        result_payload = {
            "answer": generated_answer,
            "provider": llm_output.get("provider"),
            "model": llm_output.get("model"),
            "sources": sources,
            "total_sources": len(sources),
            "mode": mode.value,
            "guardrails": guardrails_report
        }

        # Store in cache for future hits
        cache_manager.set(
            query=sanitized_question,
            query_vector=query_vector,
            document_id=target_doc_id,
            mode=mode.value,
            response=result_payload
        )

        return result_payload

    def stream_query(
        self,
        question: str,
        top_k: int = 4,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        hybrid: bool = False,
        mode: PromptMode = PromptMode.QA,
        few_shot: bool = False,
        custom_instructions: Optional[str] = None,
        document_metadata: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams answers token-by-token with source attribution.
        
        Yields:
          1. Initial packet with sources: {"type": "sources", "sources": [...]}
          2. Token packets: {"type": "token", "content": "..."}
          3. Completion packet: {"type": "done"}
        """
        if not question.strip():
            raise RAGPipelineError("Question cannot be empty.")

        # Step 1: Retrieval
        retrieved_chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
            hybrid=hybrid
        )

        # Build and yield source citations first
        sources = []
        for chunk in retrieved_chunks:
            sources.append({
                "page_number": chunk.get("page_number"),
                "document_id": chunk.get("metadata", {}).get("document_id"),
                "score": chunk.get("score") or chunk.get("rrf_score"),
                "snippet": chunk.get("text", "")[:200] + ("..." if len(chunk.get("text", "")) > 200 else "")
            })
        yield {"type": "sources", "sources": sources}

        # Step 2: Prompt Formatting
        messages = build_rag_messages(
            query=question,
            context_chunks=retrieved_chunks,
            mode=mode,
            few_shot=few_shot,
            custom_instructions=custom_instructions,
            document_metadata=document_metadata
        )

        # Step 3: Stream tokens
        for token in self.llm_service.stream_generate(messages=messages):
            yield {"type": "token", "content": token}

        yield {"type": "done"}
