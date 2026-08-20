"""
File: backend/tests/test_embeddings.py
Purpose: Unit tests for the DocumentEmbedder.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.rag.embeddings import DocumentEmbedder, EmbeddingServiceError

@pytest.fixture
def mock_embedder():
    """
    Fixture that creates an embedder but heavily mocks the underlying 
    OpenAI network calls so we don't spend money during unit tests.
    """
    # Patch the OpenAIEmbeddings class before initialization
    with patch("app.rag.embeddings.OpenAIEmbeddings") as MockOpenAI:
        # Create a mock instance
        mock_instance = MockOpenAI.return_value
        
        # When embed_documents is called, return fake 1536-dimensional vectors
        def fake_embed(texts):
            return [[0.1] * 1536 for _ in texts]
            
        mock_instance.embed_documents.side_effect = fake_embed
        
        # Initialize our wrapper class
        embedder = DocumentEmbedder(api_key="test_key")
        return embedder

def test_embed_empty_list(mock_embedder):
    """Test that an empty input returns an empty output safely."""
    result = mock_embedder.embed_chunks([])
    assert result == []

def test_embed_single_chunk(mock_embedder):
    """Test standard embedding of a single chunk."""
    chunks = [{"text": "Hello world", "chunk_index": 0}]
    result = mock_embedder.embed_chunks(chunks)
    
    assert len(result) == 1
    assert "vector" in result[0]
    assert len(result[0]["vector"]) == 1536
    assert result[0]["text"] == "Hello world"

def test_embed_batching(mock_embedder):
    """Test that batching processes all chunks without dropping any."""
    # Create 250 dummy chunks
    chunks = [{"text": f"Text {i}", "chunk_index": i} for i in range(250)]
    
    # Process with batch size 100
    result = mock_embedder.embed_chunks(chunks, batch_size=100)
    
    assert len(result) == 250
    # The underlying mock should have been called 3 times (100, 100, 50)
    assert mock_embedder.embeddings_client.embed_documents.call_count == 3

def test_embed_api_failure():
    """Test that API failures are caught and wrapped in our custom exception."""
    with patch("app.rag.embeddings.OpenAIEmbeddings") as MockOpenAI:
        mock_instance = MockOpenAI.return_value
        # Simulate a network timeout or authentication error
        mock_instance.embed_documents.side_effect = Exception("API Timeout")
        
        embedder = DocumentEmbedder(api_key="test_key")
        chunks = [{"text": "Hello world"}]
        
        with pytest.raises(EmbeddingServiceError, match="API Timeout"):
            embedder.embed_chunks(chunks)

def test_dimension_validation():
    """Test that if the model returns the wrong vector size, we crash safely."""
    with patch("app.rag.embeddings.OpenAIEmbeddings") as MockOpenAI:
        mock_instance = MockOpenAI.return_value
        # Simulate returning a 768-dimensional vector instead of 1536
        mock_instance.embed_documents.return_value = [[0.1] * 768]
        
        embedder = DocumentEmbedder(api_key="test_key")
        chunks = [{"text": "Wrong dimensions"}]
        
        with pytest.raises(EmbeddingServiceError, match="Dimension mismatch"):
            embedder.embed_chunks(chunks)
