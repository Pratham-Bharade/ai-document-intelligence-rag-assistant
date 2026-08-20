"""
File: backend/tests/test_pipeline.py
Purpose: End-to-end integration tests for the complete RAG Pipeline.
"""

import pytest
import fitz
from unittest.mock import MagicMock

from app.rag.pipeline import RAGPipeline, RAGPipelineError
from app.rag.embeddings import DocumentEmbedder
from app.rag.vector_store import InMemoryVectorStore
from app.rag.llm import LLMService


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Creates a realistic 2-page PDF document for end-to-end testing."""
    pdf_path = tmp_path / "company_handbook.pdf"
    doc = fitz.open()
    
    # Page 1: Working Hours & Remote Work
    page1 = doc.new_page()
    page1.insert_text(
        (50, 50),
        "Company Handbook - Section 1\n\n"
        "Working Hours Policy:\n"
        "Standard working hours are from 9:00 AM to 5:00 PM EST, Monday through Friday.\n"
        "Employees are eligible for remote work on Mondays and Fridays with manager approval."
    )
    
    # Page 2: Leave & Health Benefits
    page2 = doc.new_page()
    page2.insert_text(
        (50, 50),
        "Company Handbook - Section 2\n\n"
        "Paid Time Off (PTO) Policy:\n"
        "All full-time engineers receive 25 days of paid annual leave per calendar year.\n"
        "Health insurance coverage begins on the first day of employment."
    )
    
    doc.save(pdf_path)
    doc.close()
    return str(pdf_path)


@pytest.fixture
def mock_rag_pipeline():
    """Initializes a RAGPipeline with mocked Embedder and LLMService."""
    # 4-dimensional vector space for fast deterministic testing
    store = InMemoryVectorStore(expected_dim=4)
    
    # Mock Embedder: generates deterministic unit vectors
    mock_embedder = MagicMock(spec=DocumentEmbedder)
    mock_embedder.expected_dimensions = 4
    
    def fake_embed(chunks, batch_size=100):
        results = []
        for i, c in enumerate(chunks):
            chunk_copy = c.copy()
            # If chunk mentions "remote" or "hours", point in direction 0
            # If chunk mentions "leave" or "PTO", point in direction 1
            text = c.get("text", "").lower()
            if "remote" in text or "hours" in text or "monday" in text:
                chunk_copy["vector"] = [1.0, 0.0, 0.0, 0.0]
            elif "leave" in text or "pto" in text or "vacation" in text:
                chunk_copy["vector"] = [0.0, 1.0, 0.0, 0.0]
            else:
                chunk_copy["vector"] = [0.5, 0.5, 0.0, 0.0]
            results.append(chunk_copy)
        return results

    mock_embedder.embed_chunks.side_effect = fake_embed

    # Mock LLMService
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {
        "content": "According to the handbook, employees can work remotely on Mondays and Fridays [Page 1].",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "finish_reason": "stop"
    }
    
    def fake_stream(messages, max_tokens=1024):
        yield "Employees can work remotely "
        yield "on Mondays and Fridays "
        yield "[Page 1]."
    mock_llm.stream_generate.side_effect = fake_stream

    pipeline = RAGPipeline(
        embedder=mock_embedder,
        vector_store=store,
        llm_service=mock_llm
    )
    return pipeline


def test_pipeline_end_to_end_ingest_and_query(mock_rag_pipeline, sample_pdf_path):
    """Test full workflow: Ingest PDF -> Vectorize -> Query -> Verified Answer + Sources."""
    # 1. Ingest PDF
    ingest_res = mock_rag_pipeline.ingest_pdf(
        file_path=sample_pdf_path,
        document_id="handbook_2026"
    )
    assert ingest_res["status"] == "success"
    assert ingest_res["total_pages"] == 2
    assert ingest_res["total_chunks"] >= 2
    assert mock_rag_pipeline.vector_store.count() >= 2

    # 2. Query
    query_res = mock_rag_pipeline.query(
        question="What days can I work from home?",
        top_k=2
    )

    # 3. Verify Output
    assert "Mondays and Fridays" in query_res["answer"]
    assert query_res["provider"] == "groq"
    assert query_res["total_sources"] > 0
    
    # Check that sources cite Page 1 and handbook_2026
    top_source = query_res["sources"][0]
    assert top_source["page_number"] == 1
    assert top_source["document_id"] == "handbook_2026"
    assert "Remote work" in top_source["snippet"] or "working hours" in top_source["snippet"]


def test_pipeline_stream_query(mock_rag_pipeline, sample_pdf_path):
    """Test streaming end-to-end generator yielding sources first, then tokens."""
    mock_rag_pipeline.ingest_pdf(file_path=sample_pdf_path, document_id="handbook_2026")

    events = list(mock_rag_pipeline.stream_query(question="What are the working hours?"))

    assert len(events) >= 3
    # Event 1: Sources packet
    assert events[0]["type"] == "sources"
    assert len(events[0]["sources"]) > 0
    assert events[0]["sources"][0]["page_number"] == 1

    # Middle events: Token packets
    token_contents = [e["content"] for e in events if e["type"] == "token"]
    full_streamed_text = "".join(token_contents)
    assert "Mondays and Fridays" in full_streamed_text

    # Final event: Done packet
    assert events[-1]["type"] == "done"


def test_pipeline_empty_question(mock_rag_pipeline):
    """Test that empty queries raise a clear RAGPipelineError."""
    with pytest.raises(RAGPipelineError, match="Question cannot be empty"):
        mock_rag_pipeline.query(question="   ")
