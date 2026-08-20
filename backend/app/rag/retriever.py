"""
File: backend/app/rag/retriever.py
Purpose: Advanced context retrieval, metadata filtering, and hybrid search (RRF).
Why it exists: Pure vector search has blind spots. If a user queries an exact error code
               like "ERR-404-X9" or a specific product name "iPhone 15 Pro", semantic
               embeddings often retrieve generic matches instead of the exact string.
               Hybrid search fuses dense semantic search with lexical keyword search
               using Reciprocal Rank Fusion (RRF) for the highest retrieval accuracy.
Dependencies: re, typing, numpy
Main responsibilities:
  - Coordinate embedding generation for user queries.
  - Apply metadata pre-filtering (document_id, page_number).
  - Execute dense vector search and lexical keyword matching.
  - Fuse rankings via Reciprocal Rank Fusion (RRF).
  - Enforce token/character context budgeting to prevent LLM prompt overflow.
"""

import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.rag.embeddings import DocumentEmbedder
from app.rag.vector_store import InMemoryVectorStore

logger = logging.getLogger(__name__)


class RetrieverError(Exception):
    """Custom exception for retrieval failures."""
    pass


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60,
    id_key: str = "chunk_index"
) -> List[Dict[str, Any]]:
    """
    Combines multiple ranked lists of chunks using Reciprocal Rank Fusion (RRF):
        RRF_score(d) = sum( 1 / (k + rank_i(d)) )
    
    where k is a smoothing constant (typically 60) that prevents top ranks from dominating.
    
    Args:
        ranked_lists: List of ranked result lists (e.g. [dense_results, keyword_results]).
        k: Smoothing constant (default 60).
        id_key: The unique identifier key in each chunk dict.
        
    Returns:
        A single fused list of chunk dictionaries sorted by combined RRF score.
    """
    rrf_scores: Dict[Any, float] = defaultdict(float)
    chunk_lookup: Dict[Any, Dict[str, Any]] = {}

    for result_list in ranked_lists:
        for rank, chunk in enumerate(result_list, start=1):
            chunk_id = chunk[id_key]
            rrf_scores[chunk_id] += 1.0 / (k + rank)
            if chunk_id not in chunk_lookup:
                chunk_lookup[chunk_id] = chunk

    # Sort chunks by descending RRF score
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    fused_results = []
    for cid in sorted_chunk_ids:
        chunk_copy = chunk_lookup[cid].copy()
        chunk_copy["rrf_score"] = round(rrf_scores[cid], 6)
        fused_results.append(chunk_copy)

    return fused_results


def lexical_keyword_search(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Performs keyword/lexical matching on chunks based on term frequency overlap.
    Crucial for exact product codes, acronyms, and rare proper nouns.
    """
    if not query or not chunks:
        return []

    # Tokenize query into words (ignoring case)
    query_terms = set(re.findall(r'\w+', query.lower()))
    if not query_terms:
        return []

    scored_chunks: List[Tuple[Dict[str, Any], int]] = []

    for chunk in chunks:
        text = chunk.get("text", "").lower()
        # Count term matches
        match_count = sum(1 for term in query_terms if term in text)
        if match_count > 0:
            scored_chunks.append((chunk, match_count))

    # Sort by number of matched terms descending
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    results = []
    for chunk, match_count in scored_chunks[:top_k]:
        c = chunk.copy()
        c["keyword_matches"] = match_count
        results.append(c)

    return results


class AdvancedRetriever:
    """
    Enterprise-grade retriever supporting semantic search, metadata filtering,
    hybrid fusion, and context length budgeting.
    """
    def __init__(self, vector_store: InMemoryVectorStore, embedder: DocumentEmbedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        max_context_chars: int = 4000,
        hybrid: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant chunks for a given query.
        
        Args:
            query: The user's input prompt/question.
            top_k: Max chunks to retrieve.
            score_threshold: Minimum similarity threshold for vector search.
            metadata_filter: Dict of key-values to match (e.g. {"document_id": "doc_123"}).
            max_context_chars: Max total characters of combined chunks allowed in context.
            hybrid: If True, combines vector search and keyword search via RRF.
            
        Returns:
            Ranked, filtered, and budgeted list of chunk dicts.
        """
        if not query.strip():
            return []

        # 1. Generate query embedding using the embedder
        try:
            # We embed a single query text
            query_chunks = [{"text": query}]
            embedded_query = self.embedder.embed_chunks(query_chunks)
            query_vector = embedded_query[0]["vector"]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise RetrieverError(f"Query embedding generation failed: {e}")

        # 2. Vector Search (Fetch more candidates if filtering or hybrid search is active)
        fetch_limit = top_k * 3 if (metadata_filter or hybrid) else top_k
        dense_results = self.vector_store.search(
            query_vector=query_vector,
            top_k=fetch_limit,
            score_threshold=score_threshold
        )

        # 3. Apply Metadata Filtering (Pre/Post-filtering)
        if metadata_filter:
            filtered_dense = []
            for chunk in dense_results:
                chunk_meta = chunk.get("metadata", {})
                # Also check top-level keys like page_number
                matches_all = True
                for f_key, f_val in metadata_filter.items():
                    val_in_meta = chunk_meta.get(f_key)
                    val_in_top = chunk.get(f_key)
                    if val_in_meta != f_val and val_in_top != f_val:
                        matches_all = False
                        break
                if matches_all:
                    filtered_dense.append(chunk)
            dense_results = filtered_dense

        # 4. Optional Hybrid Search (Dense + Sparse/Keyword Fusion)
        if hybrid:
            available_chunks = self.vector_store.chunks
            if metadata_filter:
                # Filter chunk pool first
                available_chunks = [
                    c for c in available_chunks
                    if all(
                        c.get("metadata", {}).get(k) == v or c.get(k) == v
                        for k, v in metadata_filter.items()
                    )
                ]
            sparse_results = lexical_keyword_search(query, available_chunks, top_k=fetch_limit)
            final_candidates = reciprocal_rank_fusion([dense_results, sparse_results], k=60)
        else:
            final_candidates = dense_results

        # 5. Enforce Top-K
        final_candidates = final_candidates[:top_k]

        # 6. Context Window Budgeting
        # Trims context so we do not exceed token/character limits for the LLM
        budgeted_results = []
        accumulated_chars = 0

        for chunk in final_candidates:
            chunk_text = chunk.get("text", "")
            chunk_len = len(chunk_text)
            if accumulated_chars + chunk_len > max_context_chars:
                logger.warning(
                    f"Context budget reached ({accumulated_chars} chars). "
                    f"Trimming remaining {len(final_candidates) - len(budgeted_results)} chunks."
                )
                break
            budgeted_results.append(chunk)
            accumulated_chars += chunk_len

        return budgeted_results
