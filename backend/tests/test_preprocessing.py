"""
File: backend/tests/test_preprocessing.py
Purpose: Unit tests for text normalization and preprocessing.
"""

from app.rag.preprocessing import normalize_text, preprocess_document

def test_normalize_whitespace():
    """Test that excessive whitespace is reduced but paragraphs are preserved."""
    raw_text = "This   has \t\t way too   much \n\n\n\n whitespace."
    cleaned = normalize_text(raw_text)
    
    # Multiple spaces become one, multiple newlines cap at two.
    assert cleaned == "This has way too much \n\n whitespace."

def test_normalize_unicode():
    """Test that weird unicode (like ligatures) is expanded properly."""
    # \uFB01 is the 'fi' ligature (often happens when copying from PDFs)
    raw_text = "The \uFB01nal result."
    cleaned = normalize_text(raw_text)
    
    assert cleaned == "The final result."

def test_remove_invisible_chars():
    """Test that zero-width spaces and null bytes are deleted."""
    raw_text = "Hidden\u200bSpace\x00"
    cleaned = normalize_text(raw_text)
    
    assert cleaned == "HiddenSpace"

def test_preprocess_document():
    """Test that a full document object is cleaned and blank pages are dropped."""
    dummy_data = {
        "metadata": {"title": "Test Doc"},
        "total_pages": 3,
        "pages": [
            {"page_number": 1, "text": "Page 1   content\n\n\nwith spaces", "is_scanned": False},
            {"page_number": 2, "text": "   \n\t  ", "is_scanned": False}, # Blank after cleaning
            {"page_number": 3, "text": "Page 3 content", "is_scanned": True}
        ]
    }
    
    result = preprocess_document(dummy_data)
    
    # Page 2 should be completely removed
    assert len(result["pages"]) == 2
    
    # Check page 1
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][0]["text"] == "Page 1 content\n\nwith spaces"
    
    # Check page 3 (which is now at index 1 in the cleaned array)
    assert result["pages"][1]["page_number"] == 3
    assert result["pages"][1]["is_scanned"] is True
