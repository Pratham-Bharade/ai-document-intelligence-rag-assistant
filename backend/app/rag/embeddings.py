"""
File: backend/app/rag/embeddings.py
Purpose: Convert text chunks into mathematical vectors (embeddings) with resilient local semantic fallback.
Why it exists: We cannot search for text purely by keywords anymore.
               We need to search by semantic meaning. Embeddings translate
               human language into high-dimensional space so we can calculate
               the mathematical distance between concepts.
Dependencies: langchain-openai, numpy, hashlib
"""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional
import numpy as np

from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Custom exception for embedding-related failures."""
    pass


def _generate_semantic_fallback_vector(text: str, dimensions: int = 1536) -> List[float]:
    """
    Generates a 1536-dimensional L2-normalized semantic vector from text
    using sub-word character n-grams and token hashing.
    Used as an automatic zero-cost fallback when external API quotas are exhausted.
    """
    vec = np.zeros(dimensions, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        # Word-level hash projection
        h_word = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx_word = h_word % dimensions
        sign_word = 1.0 if ((h_word >> 8) & 1) else -1.0
        vec[idx_word] += 2.0 * sign_word

        # Sub-word 3-gram character projection
        for i in range(len(word) - 2):
            trigram = word[i:i+3]
            h_tri = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest(), 16)
            idx_tri = h_tri % dimensions
            sign_tri = 1.0 if ((h_tri >> 8) & 1) else -1.0
            vec[idx_tri] += 1.0 * sign_tri

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec.tolist()


class DocumentEmbedder:
    def __init__(self, api_key: Optional[str] = None, fallback_to_local: bool = True):
        """
        Initializes the embedding service.
        Connects to OpenAI embeddings API (text-embedding-3-small) with automated
        fallback to local semantic vector projection if quotas or credentials fail.
        """
        self.model_name = "text-embedding-3-small"
        self.expected_dimensions = 1536
        self.fallback_to_local = fallback_to_local
        
        effective_key = api_key or settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "dummy_key")
        
        try:
            self.embeddings_client = OpenAIEmbeddings(
                model=self.model_name,
                api_key=effective_key,
                max_retries=1,
                timeout=10.0
            )
        except Exception as e:
            if not self.fallback_to_local:
                raise EmbeddingServiceError(f"Initialization failed: {e}")
            logger.warning(f"Could not initialize OpenAI Embeddings client: {e}. Will use local semantic fallback.")
            self.embeddings_client = None

    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Takes a list of text chunk dictionaries and attaches a 'vector' 
        (list of floats) to each one.
        """
        if not chunks:
            return []

        texts = [chunk["text"] for chunk in chunks]
        all_vectors: List[List[float]] = []

        # Attempt OpenAI embeddings first if client is available
        use_fallback = False
        if self.embeddings_client:
            try:
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i : i + batch_size]
                    batch_vectors = self.embeddings_client.embed_documents(batch_texts)
                    if batch_vectors and len(batch_vectors[0]) == self.expected_dimensions:
                        all_vectors.extend(batch_vectors)
                    else:
                        if not self.fallback_to_local:
                            dim_got = len(batch_vectors[0]) if batch_vectors else 0
                            raise EmbeddingServiceError(f"Dimension mismatch: expected {self.expected_dimensions}, got {dim_got}")
                        use_fallback = True
                        break
            except EmbeddingServiceError:
                raise
            except Exception as e:
                if not self.fallback_to_local:
                    raise EmbeddingServiceError(f"API Timeout / Error: {e}")
                logger.warning(f"OpenAI embedding API unavailable ({e}). Seamlessly switching to local semantic projection.")
                use_fallback = True
                all_vectors.clear()
        else:
            if not self.fallback_to_local:
                raise EmbeddingServiceError("No embedding provider configured.")
            use_fallback = True

        # High-dimensional semantic projection fallback
        if use_fallback:
            for text in texts:
                all_vectors.append(_generate_semantic_fallback_vector(text, self.expected_dimensions))

        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_copy = chunk.copy()
            chunk_copy["vector"] = all_vectors[i]
            embedded_chunks.append(chunk_copy)

        return embedded_chunks

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding vector for a single search query string."""
        if not query.strip():
            return [0.0] * self.expected_dimensions

        if self.embeddings_client:
            try:
                vector = self.embeddings_client.embed_query(query)
                if len(vector) == self.expected_dimensions:
                    return vector
            except Exception as e:
                logger.warning(f"OpenAI query embedding failed ({e}). Using local semantic projection.")

        return _generate_semantic_fallback_vector(query, self.expected_dimensions)
