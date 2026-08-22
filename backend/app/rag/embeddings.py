"""
File: backend/app/rag/embeddings.py
Purpose: Convert text chunks into mathematical vectors (embeddings).
Why it exists: We cannot search for text purely by keywords anymore.
               We need to search by *semantic meaning*. Embeddings translate
               human language into high-dimensional space so we can calculate
               the mathematical distance between concepts.
Dependencies: langchain-openai
Main responsibilities:
  - Connect to an Embedding API (OpenAI text-embedding-3-small).
  - Manage batch processing to respect API rate limits and payload sizes.
  - Implement retry logic (exponential backoff) for API instability.
  - Validate vector dimensions (prevent database crashes).
"""

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingServiceError(Exception):
    """Custom exception for embedding-related failures."""
    pass


class DocumentEmbedder:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the embedding service.
        We default to 'text-embedding-3-small' because it provides excellent
        semantic retrieval at a fraction of the cost of older models.
        """
        self.model_name = "text-embedding-3-small"
        self.expected_dimensions = 1536
        
        effective_key = api_key or settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "dummy_key")
        
        try:
            # LangChain's OpenAI wrapper automatically handles exponential backoff 
            # retries internally via the 'tenacity' library. We set max_retries=3.
            self.embeddings_client = OpenAIEmbeddings(
                model=self.model_name,
                api_key=effective_key,
                max_retries=3,
                timeout=30.0
            )
        except Exception as e:
            logger.error(f"Failed to initialize Embedding client: {e}")
            raise EmbeddingServiceError(f"Initialization failed: {e}")

    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Takes a list of text chunk dictionaries and attaches a 'vector' 
        (list of floats) to each one.
        
        Processes requests in batches to avoid HTTP 413 (Payload Too Large) errors.
        """
        if not chunks:
            return []
            
        # Extract just the raw text strings needed for the API
        texts = [chunk["text"] for chunk in chunks]
        all_vectors = []
        
        try:
            # Explicit batching
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                logger.info(f"Generating embeddings for batch {i//batch_size + 1}...")
                
                # Network call to OpenAI
                batch_vectors = self.embeddings_client.embed_documents(batch_texts)
                
                # Strict dimension validation
                if batch_vectors and len(batch_vectors[0]) != self.expected_dimensions:
                    raise EmbeddingServiceError(
                        f"Fatal: Dimension mismatch. Database expects {self.expected_dimensions}, "
                        f"but model returned {len(batch_vectors[0])}."
                    )
                    
                all_vectors.extend(batch_vectors)
                
        except Exception as e:
            logger.error(f"API Error during embedding generation: {e}")
            raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")
            
        # Attach the resulting vectors back to their original chunks
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            # We copy the dictionary to avoid mutating the original input
            chunk_copy = chunk.copy()
            chunk_copy["vector"] = all_vectors[i]
            embedded_chunks.append(chunk_copy)
            
        return embedded_chunks

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding vector for a single query string."""
        if not query.strip():
            return [0.0] * self.expected_dimensions
        try:
            vector = self.embeddings_client.embed_query(query)
            if len(vector) != self.expected_dimensions:
                raise EmbeddingServiceError(
                    f"Dimension mismatch: expected {self.expected_dimensions}, got {len(vector)}"
                )
            return vector
        except Exception as e:
            logger.error(f"API Error during query embedding: {e}")
            raise EmbeddingServiceError(f"Query embedding generation failed: {str(e)}")
