"""
File: backend/tests/test_vector_store.py
Purpose: Unit tests for vector math and InMemoryVectorStore.
"""

import pytest
import numpy as np
from app.rag.vector_store import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    InMemoryVectorStore,
    VectorStoreError
)


def test_cosine_similarity_identical_vectors():
    """Identical vectors should have a cosine similarity of 1.0."""
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([1.0, 2.0, 3.0])
    assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    """Orthogonal (perpendicular) vectors should have similarity of 0.0."""
    v1 = np.array([1.0, 0.0])
    v2 = np.array([0.0, 1.0])
    assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == 0.0


def test_cosine_similarity_opposite_vectors():
    """Opposite direction vectors should have similarity of -1.0."""
    v1 = np.array([1.0, 0.0])
    v2 = np.array([-1.0, 0.0])
    assert pytest.approx(cosine_similarity(v1, v2), 0.0001) == -1.0


def test_euclidean_distance():
    """Distance between (0,0) and (3,4) is 5.0 (Pythagorean theorem)."""
    v1 = np.array([0.0, 0.0])
    v2 = np.array([3.0, 4.0])
    assert pytest.approx(euclidean_distance(v1, v2), 0.0001) == 5.0


def test_in_memory_store_empty_search():
    """Searching an empty store should return empty list without error."""
    store = InMemoryVectorStore(expected_dim=3)
    results = store.search([1.0, 0.0, 0.0])
    assert results == []


def test_in_memory_store_search_and_ranking():
    """Test that search ranks the most similar vector first and includes score."""
    store = InMemoryVectorStore(expected_dim=3)
    
    chunks = [
        {"chunk_index": 0, "text": "Unrelated topic", "vector": [0.0, 1.0, 0.0]},
        {"chunk_index": 1, "text": "Highly relevant topic", "vector": [0.95, 0.05, 0.0]},
        {"chunk_index": 2, "text": "Somewhat relevant topic", "vector": [0.7, 0.3, 0.0]},
    ]
    store.add_chunks(chunks)
    
    # Query vector close to [1.0, 0.0, 0.0]
    query_vector = [1.0, 0.0, 0.0]
    results = store.search(query_vector, top_k=2)
    
    assert len(results) == 2
    # First result should be the most relevant
    assert results[0]["chunk_index"] == 1
    assert results[0]["score"] > results[1]["score"]
    assert "score" in results[0]


def test_in_memory_store_threshold_filtering():
    """Chunks below score_threshold should be filtered out."""
    store = InMemoryVectorStore(expected_dim=2)
    chunks = [
        {"chunk_index": 0, "text": "High match", "vector": [1.0, 0.0]},
        {"chunk_index": 1, "text": "Low match", "vector": [0.1, 0.9]},
    ]
    store.add_chunks(chunks)
    
    # Search with high threshold
    results = store.search(query_vector=[1.0, 0.0], score_threshold=0.8)
    assert len(results) == 1
    assert results[0]["chunk_index"] == 0


def test_in_memory_store_dimension_mismatch():
    """Adding or searching with wrong dimensions must raise VectorStoreError."""
    store = InMemoryVectorStore(expected_dim=1536)
    
    # Wrong chunk dimension (3 instead of 1536)
    with pytest.raises(VectorStoreError, match="Dimension mismatch"):
        store.add_chunks([{"text": "Bad dim", "vector": [1.0, 2.0, 3.0]}])
        
    # Wrong query dimension
    with pytest.raises(VectorStoreError, match="Query vector dimension mismatch"):
        store.search(query_vector=[1.0, 2.0])
