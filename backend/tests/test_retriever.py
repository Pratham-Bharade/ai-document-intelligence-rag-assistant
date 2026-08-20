"""
File: backend/tests/test_retriever.py
Purpose: Unit tests for AdvancedRetriever, RRF, metadata filtering, and context budgeting.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.rag.retriever import (
    AdvancedRetriever,
    reciprocal_rank_fusion,
    lexical_keyword_search,
    RetrieverError
)
from app.rag.vector_store import InMemoryVectorStore
from app.rag.embeddings import DocumentEmbedder


def test_reciprocal_rank_fusion():
    """Test that RRF correctly fuses rankings from two different search algorithms."""
    # Algorithm 1 ranked: Chunk A (rank 1), Chunk B (rank 2)
    list1 = [
        {"chunk_index": "A", "text": "Doc A"},
        {"chunk_index": "B", "text": "Doc B"}
    ]
    # Algorithm 2 ranked: Chunk B (rank 1), Chunk C (rank 2)
    list2 = [
        {"chunk_index": "B", "text": "Doc B"},
        {"chunk_index": "C", "text": "Doc C"}
    ]

    fused = reciprocal_rank_fusion([list1, list2], k=60)
    
    # Chunk B appeared in both lists (rank 2 in list1, rank 1 in list2)
    # Score B = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ~= 0.016129 + 0.016393 = 0.032522
    # Score A = 1/(60+1) = 1/61 ~= 0.016393
    # Score C = 1/(60+2) = 1/62 ~= 0.016129
    
    # Chunk B must be ranked #1
    assert fused[0]["chunk_index"] == "B"
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]
    assert len(fused) == 3


def test_lexical_keyword_search():
    """Test that lexical search finds exact keyword occurrences."""
    chunks = [
        {"chunk_index": 0, "text": "The server error code is ERR-9021"},
        {"chunk_index": 1, "text": "The quick brown fox jumps over the dog"},
        {"chunk_index": 2, "text": "Another error code notice ERR-9021 in production"}
    ]
    results = lexical_keyword_search("ERR-9021", chunks, top_k=2)
    
    assert len(results) == 2
    assert "ERR-9021" in results[0]["text"]
    assert "ERR-9021" in results[1]["text"]


@pytest.fixture
def mock_retriever_setup():
    """Sets up a populated InMemoryVectorStore with a mocked Embedder."""
    store = InMemoryVectorStore(expected_dim=4)
    
    chunks = [
        {
            "chunk_index": 0,
            "page_number": 1,
            "metadata": {"document_id": "doc_A"},
            "text": "Remote work policy: Employees can work 2 days from home.",
            "vector": [1.0, 0.0, 0.0, 0.0]
        },
        {
            "chunk_index": 1,
            "page_number": 2,
            "metadata": {"document_id": "doc_A"},
            "text": "Vacation policy: Employees get 20 paid vacation days.",
            "vector": [0.0, 1.0, 0.0, 0.0]
        },
        {
            "chunk_index": 2,
            "page_number": 1,
            "metadata": {"document_id": "doc_B"},
            "text": "Engineering on-call rotation schedule.",
            "vector": [0.0, 0.0, 1.0, 0.0]
        }
    ]
    store.add_chunks(chunks)

    # Mock embedder that returns [1.0, 0.0, 0.0, 0.0] for "remote work"
    mock_embedder = MagicMock(spec=DocumentEmbedder)
    mock_embedder.embed_chunks.return_value = [{"text": "remote", "vector": [1.0, 0.0, 0.0, 0.0]}]

    retriever = AdvancedRetriever(vector_store=store, embedder=mock_embedder)
    return retriever, store


def test_retrieve_basic(mock_retriever_setup):
    """Test basic semantic retrieval."""
    retriever, _ = mock_retriever_setup
    results = retriever.retrieve("remote work policy", top_k=1)
    
    assert len(results) == 1
    assert results[0]["chunk_index"] == 0
    assert "Remote work" in results[0]["text"]


def test_retrieve_with_metadata_filter(mock_retriever_setup):
    """Test filtering by metadata like document_id or page_number."""
    retriever, _ = mock_retriever_setup
    
    # Filter for doc_B only (even though query matches chunk 0 best)
    results = retriever.retrieve(
        "remote work",
        top_k=2,
        metadata_filter={"document_id": "doc_B"}
    )
    
    assert len(results) == 1
    assert results[0]["metadata"]["document_id"] == "doc_B"
    assert results[0]["chunk_index"] == 2


def test_retrieve_context_budgeting(mock_retriever_setup):
    """Test that retriever trims chunks when max_context_chars is exceeded."""
    retriever, _ = mock_retriever_setup
    
    # Chunk 0 has 57 characters. Set budget to 60 characters -> only 1 chunk fits.
    results = retriever.retrieve(
        "remote work",
        top_k=3,
        max_context_chars=60
    )
    
    assert len(results) == 1
    assert results[0]["chunk_index"] == 0
