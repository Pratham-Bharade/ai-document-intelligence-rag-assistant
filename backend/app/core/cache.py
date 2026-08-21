"""
File: backend/app/core/cache.py
Purpose: Multi-Tier Caching Layer (Exact Query Cache & Semantic Embedding Cache) with Invalidation.
Why it exists: LLM inference takes 1,000–3,000ms and costs API tokens per query.
               Repeated or semantically identical questions can be served in < 15ms
               directly from cache with 0 LLM cost.
"""

import hashlib
import json
import logging
import numpy as np
from typing import Any, Dict, List, Optional
from prometheus_client import Counter

logger = logging.getLogger(__name__)

# Prometheus metrics for cache telemetry
RAG_CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Total RAG cache queries partitioned by cache type and hit/miss result",
    ["cache_type", "result"]
)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Computes cosine similarity between two 1D vector arrays."""
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class SemanticCacheEntry:
    """Represents a cached query with its embedding vector and cached answer."""
    def __init__(
        self,
        query: str,
        vector: List[float],
        document_id: Optional[str],
        mode: str,
        response: Dict[str, Any]
    ):
        self.query = query
        self.vector = vector
        self.document_id = document_id
        self.mode = mode
        self.response = response


from collections import defaultdict

class RAGCacheManager:
    """
    Two-Tier Cache Manager:
      Tier 1: Exact Hash Cache (O(1) SHA-256 lookup in < 1ms)
      Tier 2: Semantic Cache (Vector cosine similarity matching in < 10ms)
    """
    def __init__(self, semantic_threshold: float = 0.95):
        self.semantic_threshold = semantic_threshold
        self._exact_store: Dict[str, Dict[str, Any]] = {}
        self._doc_to_exact_keys: Dict[str, set] = defaultdict(set)
        self._semantic_store: List[SemanticCacheEntry] = []

    def _hash_key(self, query: str, document_id: Optional[str], mode: str) -> str:
        raw = f"{query.lower().strip()}|{document_id or 'all'}|{mode}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_exact(self, query: str, document_id: Optional[str] = None, mode: str = "qa") -> Optional[Dict[str, Any]]:
        """Tier 1: Exact string hash lookup."""
        key = self._hash_key(query, document_id, mode)
        if key in self._exact_store:
            RAG_CACHE_HITS.labels(cache_type="exact", result="hit").inc()
            logger.info(f"Exact cache HIT for query: '{query}'")
            cached = self._exact_store[key].copy()
            cached["cached"] = True
            cached["cache_type"] = "exact"
            return cached

        RAG_CACHE_HITS.labels(cache_type="exact", result="miss").inc()
        return None

    def get_semantic(
        self,
        query_vector: List[float],
        document_id: Optional[str] = None,
        mode: str = "qa"
    ) -> Optional[Dict[str, Any]]:
        """Tier 2: Semantic similarity search across previously cached query vectors."""
        best_score = -1.0
        best_entry: Optional[SemanticCacheEntry] = None

        for entry in self._semantic_store:
            if entry.document_id == document_id and entry.mode == mode:
                score = cosine_similarity(query_vector, entry.vector)
                if score > best_score:
                    best_score = score
                    best_entry = entry

        if best_entry and best_score >= self.semantic_threshold:
            RAG_CACHE_HITS.labels(cache_type="semantic", result="hit").inc()
            logger.info(f"Semantic cache HIT (score={best_score:.4f}) for query.")
            cached = best_entry.response.copy()
            cached["cached"] = True
            cached["cache_type"] = "semantic"
            cached["semantic_similarity"] = round(best_score, 4)
            return cached

        RAG_CACHE_HITS.labels(cache_type="semantic", result="miss").inc()
        return None

    def set(
        self,
        query: str,
        query_vector: Optional[List[float]],
        document_id: Optional[str],
        mode: str,
        response: Dict[str, Any]
    ) -> None:
        """Saves a response into both Exact and Semantic cache stores."""
        # 1. Exact Cache
        exact_key = self._hash_key(query, document_id, mode)
        self._exact_store[exact_key] = response
        if document_id:
            self._doc_to_exact_keys[document_id].add(exact_key)

        # 2. Semantic Cache
        if query_vector:
            self._semantic_store.append(
                SemanticCacheEntry(
                    query=query,
                    vector=query_vector,
                    document_id=document_id,
                    mode=mode,
                    response=response
                )
            )

    def invalidate_document(self, document_id: str) -> int:
        """
        Purges all cached entries associated with a specific document ID.
        """
        # Purge exact cache keys mapped to this doc
        exact_keys = self._doc_to_exact_keys.pop(document_id, set())
        for k in exact_keys:
            self._exact_store.pop(k, None)

        # Purge semantic cache entries
        prev_len = len(self._semantic_store)
        self._semantic_store = [e for e in self._semantic_store if e.document_id != document_id]
        purged_count = len(exact_keys) + (prev_len - len(self._semantic_store))

        logger.info(f"Invalidated {purged_count} cache entries for document {document_id}")
        return purged_count

    def clear_all(self) -> None:
        """Purges all caches."""
        self._exact_store.clear()
        self._doc_to_exact_keys.clear()
        self._semantic_store.clear()


# Global singleton cache manager
cache_manager = RAGCacheManager(semantic_threshold=0.95)
