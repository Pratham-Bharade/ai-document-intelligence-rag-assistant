"""
File: backend/app/rag/profiler.py
Purpose: Benchmarking and Performance Profiler for Embeddings, Vector Search, and Quantization.
"""

import time
from typing import Any, Dict, List
import numpy as np

from app.rag.embeddings import DocumentEmbedder
from app.rag.quantization import ScalarQuantizer8Bit
from app.rag.vector_store import InMemoryVectorStore


class RAGPerformanceProfiler:
    """
    Diagnostic suite for measuring vector throughput, latency, and memory compression.
    """
    @staticmethod
    def calculate_memory_savings(num_vectors: int, dimensions: int = 1536) -> Dict[str, Any]:
        """
        Calculates theoretical RAM requirements for Float32 vs Quantized Int8.
        """
        float32_bytes_per_vector = dimensions * 4  # 4 bytes per float32
        int8_bytes_per_vector = dimensions * 1 + 16  # 1 byte per int8 + 16 bytes scale/offset
        
        total_float32_mb = (num_vectors * float32_bytes_per_vector) / (1024 * 1024)
        total_int8_mb = (num_vectors * int8_bytes_per_vector) / (1024 * 1024)
        savings_ratio = float32_bytes_per_vector / int8_bytes_per_vector

        return {
            "num_vectors": num_vectors,
            "dimensions": dimensions,
            "float32_ram_mb": round(total_float32_mb, 2),
            "int8_quantized_ram_mb": round(total_int8_mb, 2),
            "ram_savings_percent": round((1.0 - (total_int8_mb / total_float32_mb)) * 100, 1),
            "compression_ratio": round(savings_ratio, 2)
        }

    @staticmethod
    def profile_search_latency(
        vector_store: InMemoryVectorStore,
        sample_query_vector: List[float],
        num_queries: int = 100
    ) -> Dict[str, float]:
        """
        Executes N search queries and computes throughput (QPS) and latency percentiles.
        """
        latencies = []
        for _ in range(num_queries):
            start = time.perf_counter()
            vector_store.search(sample_query_vector, top_k=5)
            latencies.append((time.perf_counter() - start) * 1000.0)  # ms

        arr = np.array(latencies)
        return {
            "num_queries": num_queries,
            "avg_latency_ms": round(float(np.mean(arr)), 3),
            "p50_latency_ms": round(float(np.percentile(arr, 50)), 3),
            "p95_latency_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_latency_ms": round(float(np.percentile(arr, 99)), 3),
            "qps": round(float(num_queries / (np.sum(arr) / 1000.0)), 1)
        }
