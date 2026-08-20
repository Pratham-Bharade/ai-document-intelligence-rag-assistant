"""
File: backend/tests/test_splitter.py
Purpose: Unit tests for document chunking logic.
"""

from app.rag.splitter import chunk_document

def test_chunk_short_text():
    """Test that text smaller than chunk_size is not split."""
    data = {
        "metadata": {"title": "Short Doc"},
        "pages": [
            {"page_number": 1, "text": "This is a very short text."}
        ]
    }
    
    chunks = chunk_document(data, chunk_size=100, chunk_overlap=10)
    
    assert len(chunks) == 1
    assert chunks[0]["text"] == "This is a very short text."
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0

def test_chunk_long_text():
    """Test that text larger than chunk_size is split with overlap."""
    long_text = "A" * 100 + " " + "B" * 100
    data = {
        "metadata": {},
        "pages": [
            {"page_number": 1, "text": long_text}
        ]
    }
    
    # Size 120, overlap 20
    chunks = chunk_document(data, chunk_size=120, chunk_overlap=20)
    
    assert len(chunks) > 1
    
    # Check that metadata and page numbers are preserved across all chunks
    for chunk in chunks:
        assert chunk["page_number"] == 1
        assert "metadata" in chunk
        assert "chunk_index" in chunk

def test_chunk_respects_paragraphs():
    """Test that recursive splitter splits at paragraphs (\n\n) before words."""
    para1 = "This is paragraph one." * 5  # Length ~110
    para2 = "This is paragraph two." * 5  # Length ~110
    
    text = f"{para1}\n\n{para2}"
    
    data = {"pages": [{"page_number": 1, "text": text}]}
    
    # Size is enough for one paragraph, but not both
    chunks = chunk_document(data, chunk_size=150, chunk_overlap=0)
    
    assert len(chunks) == 2
    assert para1 in chunks[0]["text"]
    assert para2 in chunks[1]["text"]

def test_chunk_multiple_pages():
    """Test that page numbers are correctly attached to chunks from different pages."""
    data = {
        "pages": [
            {"page_number": 1, "text": "Page 1 text."},
            {"page_number": 2, "text": "Page 2 text."}
        ]
    }
    
    chunks = chunk_document(data, chunk_size=50, chunk_overlap=0)
    
    assert len(chunks) == 2
    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2
