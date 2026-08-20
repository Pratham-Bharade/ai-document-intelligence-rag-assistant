"""
File: backend/app/rag/vector_store.py
Purpose: In-memory vector similarity search and distance metric calculations.
Why it exists: Before storing vectors in PostgreSQL with pgvector, we need to
               understand and implement the core mathematical algorithms that power
               all vector databases (Cosine Similarity, Dot Product, Euclidean Distance).
               This in-memory store allows ultra-fast local testing and benchmarking.
Dependencies: numpy
Main responsibilities:
  - Calculate vector similarity metrics from first principles.
  - Store and index document chunks in memory.
  - Perform Top-K nearest neighbor search given a query vector.
  - Filter results by minimum similarity score thresholds.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Custom exception for vector store operations."""
    pass


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Computes cosine similarity between two 1D vectors:
        cos(theta) = (v1 . v2) / (||v1|| * ||v2||)
    
    Returns a score between -1.0 and 1.0 (where 1.0 = identical direction).
    """
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return float(np.dot(v1, v2) / (norm1 * norm2))


def euclidean_distance(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Computes Euclidean (L2) distance between two vectors:
        d = sqrt(sum((v1_i - v2_i)^2))
    
    Returns distance >= 0.0 (where 0.0 = exact same point).
    """
    return float(np.linalg.norm(v1 - v2))


def dot_product(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Computes the dot product between two vectors:
        dot = sum(v1_i * v2_i)
    
    If vectors are normalized (magnitude = 1), dot product == cosine similarity.
    """
    return float(np.dot(v1, v2))


class InMemoryVectorStore:
    """
    An in-memory Vector Store for document chunks and their high-dimensional embeddings.
    """
    def __init__(self, expected_dim: int = 1536):
        self.expected_dim = expected_dim
        self.chunks: List[Dict[str, Any]] = []
        self._vectors_matrix: Optional[np.ndarray] = None

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Adds embedded chunks to the store and updates the internal matrix.
        Each chunk must contain a 'vector' key with a list of floats.
        """
        if not chunks:
            return

        for chunk in chunks:
            if "vector" not in chunk:
                raise VectorStoreError("Chunk missing required 'vector' field.")
            
            vec = chunk["vector"]
            if len(vec) != self.expected_dim:
                raise VectorStoreError(
                    f"Dimension mismatch: expected {self.expected_dim}, got {len(vec)}"
                )
            
            self.chunks.append(chunk)

        # Rebuild contiguous numpy matrix for vectorized batch similarity computation
        vectors = [c["vector"] for c in self.chunks]
        self._vectors_matrix = np.array(vectors, dtype=np.float32)
        logger.info(f"Vector store now contains {len(self.chunks)} chunks.")

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Performs cosine similarity search against all stored vectors.
        
        Args:
            query_vector: 1536-dimensional float vector of the user's question.
            top_k: Maximum number of closest chunks to return.
            score_threshold: Minimum cosine similarity score (0.0 to 1.0).
            
        Returns:
            List of matching chunk dicts, each augmented with 'score'.
        """
        if len(query_vector) != self.expected_dim:
            raise VectorStoreError(
                f"Query vector dimension mismatch: expected {self.expected_dim}, got {len(query_vector)}"
            )

        if not self.chunks or self._vectors_matrix is None:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        
        if q_norm == 0:
            return []

        # Vectorized cosine similarity across all stored chunks simultaneously:
        # scores = (Matrix . q) / (Matrix_norms * q_norm)
        matrix_norms = np.linalg.norm(self._vectors_matrix, axis=1)
        # Avoid division by zero for zero vectors
        matrix_norms[matrix_norms == 0] = 1e-10
        
        dot_products = np.dot(self._vectors_matrix, q_vec)
        cosine_scores = dot_products / (matrix_norms * q_norm)

        # Pair each chunk with its score
        scored_results: List[Tuple[Dict[str, Any], float]] = []
        for idx, score in enumerate(cosine_scores):
            score_val = float(score)
            if score_val >= score_threshold:
                scored_results.append((self.chunks[idx], score_val))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Take Top-K and attach score to chunk copy
        results = []
        for chunk, score in scored_results[:top_k]:
            result_item = chunk.copy()
            result_item["score"] = round(score, 4)
            results.append(result_item)

        return results

    def clear(self) -> None:
        """Empties all stored chunks."""
        self.chunks.clear()
        self._vectors_matrix = None

    def count(self) -> int:
        """Returns total number of chunks currently stored."""
        return len(self.chunks)
