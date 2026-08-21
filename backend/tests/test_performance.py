"""
File: backend/tests/test_performance.py
Purpose: Unit tests for Vector Quantization (SQ8), Stream Debouncer, and Performance Profiler.
"""

import pytest
import numpy as np

from app.rag.quantization import ScalarQuantizer8Bit, QuantizedChunk
from app.rag.stream_optimizer import debounce_token_stream
from app.rag.profiler import RAGPerformanceProfiler
from app.rag.vector_store import InMemoryVectorStore


def test_scalar_quantization_accuracy_and_compression():
    """Verify SQ8 achieves 4x byte reduction and retains > 0.99 cosine similarity."""
    dim = 128
    np.random.seed(42)
    original_vector = np.random.randn(dim).tolist()

    # Quantize
    q_bytes, scale, min_val = ScalarQuantizer8Bit.quantize(original_vector)
    
    # Check byte size (1 byte per dimension in int8)
    assert len(q_bytes) == dim

    # Dequantize
    reconstructed = ScalarQuantizer8Bit.dequantize(q_bytes, scale, min_val)
    assert len(reconstructed) == dim

    # Compute cosine similarity between original float32 and dequantized vector
    a = np.array(original_vector, dtype=np.float32)
    b = np.array(reconstructed, dtype=np.float32)
    cosine_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # SQ8 should preserve > 99% accuracy
    assert cosine_sim > 0.99


def test_quantized_chunk_memory_efficiency():
    """Verify QuantizedChunk stores compressed representation."""
    dim = 64
    vector = [0.5] * dim
    chunk = QuantizedChunk(
        chunk_id="c-1",
        text="Sample text content",
        page_number=1,
        vector=vector
    )

    assert len(chunk.q_bytes) == dim
    reconstructed = chunk.get_vector()
    assert len(reconstructed) == dim
    assert chunk.memory_bytes < (dim * 4 + len("Sample text content") + 50)


def test_stream_debouncer():
    """Verify debounce_token_stream coalesces single-character tokens into word chunks."""
    raw_tokens = ["T", "h", "e", " ", "q", "u", "i", "c", "k", " ", "b", "r", "o", "w", "n", " ", "f", "o", "x"]
    
    # Run debouncer with batch size of 8 chars
    debounced_chunks = list(debounce_token_stream(iter(raw_tokens), batch_chars=8, max_delay_ms=100.0))

    # Should have significantly fewer chunks than original 19 single tokens
    assert len(debounced_chunks) < len(raw_tokens)
    
    # Complete reconstructed text must be 100% identical
    assert "".join(debounced_chunks) == "".join(raw_tokens)


def test_profiler_memory_savings_calculation():
    """Verify RAGPerformanceProfiler computes 4x theoretical memory savings."""
    report = RAGPerformanceProfiler.calculate_memory_savings(num_vectors=10000, dimensions=1536)
    
    assert report["num_vectors"] == 10000
    assert report["float32_ram_mb"] > report["int8_quantized_ram_mb"]
    assert report["ram_savings_percent"] > 70.0  # Approx 75% savings


def test_profiler_search_latency():
    """Verify search latency profiling across in-memory vector store."""
    store = InMemoryVectorStore(expected_dim=4)
    # Add dummy chunks
    store.add_chunks([
        {"id": f"c-{i}", "text": f"Chunk {i}", "page_number": 1, "vector": [1.0, 0.0, 0.0, 0.0]}
        for i in range(10)
    ])

    report = RAGPerformanceProfiler.profile_search_latency(
        vector_store=store,
        sample_query_vector=[1.0, 0.0, 0.0, 0.0],
        num_queries=50
    )

    assert report["num_queries"] == 50
    assert report["avg_latency_ms"] >= 0.0
    assert report["qps"] > 0
