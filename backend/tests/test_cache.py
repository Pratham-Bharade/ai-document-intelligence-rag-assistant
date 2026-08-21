"""
File: backend/tests/test_cache.py
Purpose: Unit tests for Exact Hash Query Cache, Semantic Embedding Cache, and Document Invalidation.
"""

import pytest
from unittest.mock import MagicMock

from app.core.cache import RAGCacheManager
from app.rag.pipeline import RAGPipeline
from app.rag.embeddings import DocumentEmbedder
from app.rag.vector_store import InMemoryVectorStore
from app.rag.llm import LLMService


def test_exact_cache_hit_and_miss():
    """Verify exact query caching with SHA-256 keys."""
    cache = RAGCacheManager()
    query = "What is the return policy?"
    doc_id = "doc-101"
    response_payload = {"answer": "You can return within 30 days.", "sources": []}

    # Initial query is a cache miss
    assert cache.get_exact(query, document_id=doc_id, mode="qa") is None

    # Populate cache
    cache.set(
        query=query,
        query_vector=[1.0, 0.0, 0.0],
        document_id=doc_id,
        mode="qa",
        response=response_payload
    )

    # Second query is an exact cache hit
    hit = cache.get_exact(query, document_id=doc_id, mode="qa")
    assert hit is not None
    assert hit["cached"] is True
    assert hit["cache_type"] == "exact"
    assert hit["answer"] == "You can return within 30 days."


def test_semantic_cache_hit():
    """Verify semantic cache hits questions with > 0.95 vector cosine similarity."""
    cache = RAGCacheManager(semantic_threshold=0.90)
    cached_vector = [1.0, 0.0, 0.0]
    query_vector = [0.98, 0.05, 0.0]  # Very close vector (high cosine similarity)

    cache.set(
        query="What are company holidays?",
        query_vector=cached_vector,
        document_id="doc-202",
        mode="qa",
        response={"answer": "Employees receive 10 paid holidays."}
    )

    hit = cache.get_semantic(query_vector, document_id="doc-202", mode="qa")
    assert hit is not None
    assert hit["cached"] is True
    assert hit["cache_type"] == "semantic"
    assert hit["semantic_similarity"] >= 0.90
    assert hit["answer"] == "Employees receive 10 paid holidays."


def test_cache_invalidation_on_document_delete():
    """Verify document invalidation purges all associated query cache entries."""
    cache = RAGCacheManager()
    doc_id = "doc-to-delete"

    cache.set(
        query="Policy details",
        query_vector=[1.0, 0.0],
        document_id=doc_id,
        mode="qa",
        response={"answer": "Old policy."}
    )

    assert cache.get_exact("Policy details", document_id=doc_id) is not None

    # Invalidate document
    purged = cache.invalidate_document(doc_id)
    assert purged >= 1
    assert cache.get_exact("Policy details", document_id=doc_id) is None


def test_pipeline_integration_with_caching():
    """Verify pipeline.query() skips LLM execution on cache hits."""
    mock_embed = MagicMock(spec=DocumentEmbedder)
    mock_embed.expected_dimensions = 4
    mock_embed.embed_query.return_value = [1.0, 0.0, 0.0, 0.0]
    mock_embed.embed_chunks.side_effect = lambda chunks, batch_size=100: [
        {**c, "vector": [1.0, 0.0, 0.0, 0.0]} for c in chunks
    ]

    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {"content": "Generated from LLM.", "provider": "groq", "model": "llama-3.3-70b"}

    store = InMemoryVectorStore(expected_dim=4)
    pipeline = RAGPipeline(embedder=mock_embed, vector_store=store, llm_service=mock_llm)

    # First call: executes LLM
    res1 = pipeline.query("What is the protocol?", metadata_filter={"document_id": "doc-555"})
    assert mock_llm.generate.call_count == 1
    assert res1["answer"] == "Generated from LLM."

    # Second identical call: served from cache (LLM not called again)
    res2 = pipeline.query("What is the protocol?", metadata_filter={"document_id": "doc-555"})
    assert mock_llm.generate.call_count == 1  # Still 1!
    assert res2["cached"] is True
