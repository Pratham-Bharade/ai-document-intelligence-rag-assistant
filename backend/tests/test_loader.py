"""
File: backend/tests/test_loader.py
Purpose: Unit tests for the document loader module.
"""

import os
import pytest
import fitz  # PyMuPDF
from app.rag.loader import validate_pdf, extract_text_from_pdf, DocumentLoaderError

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_pdfs(tmp_path):
    """Creates temporary PDF files for testing."""
    files = {}
    
    # 1. Valid PDF with text
    valid_pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a test document.\nWith multiple lines.")
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Page 2 content.")
    doc.save(valid_pdf_path)
    doc.close()
    files["valid"] = str(valid_pdf_path)
    
    # 2. Empty file (0 bytes)
    empty_file_path = tmp_path / "empty.pdf"
    empty_file_path.write_text("")
    files["empty"] = str(empty_file_path)
    
    # 3. Not a PDF (text file pretending to be PDF)
    fake_pdf_path = tmp_path / "fake.pdf"
    fake_pdf_path.write_text("I am just a text file, not a real PDF.")
    files["fake"] = str(fake_pdf_path)
    
    return files

# =============================================================================
# TESTS FOR VALIDATION
# =============================================================================

def test_validate_valid_pdf(temp_pdfs):
    """Test that a valid PDF passes validation."""
    assert validate_pdf(temp_pdfs["valid"]) is True

def test_validate_nonexistent_file():
    """Test that missing files raise an error."""
    with pytest.raises(DocumentLoaderError, match="File not found"):
        validate_pdf("does_not_exist.pdf")

def test_validate_empty_file(temp_pdfs):
    """Test that 0-byte files are rejected."""
    with pytest.raises(DocumentLoaderError, match="File is empty"):
        validate_pdf(temp_pdfs["empty"])

def test_validate_fake_pdf(temp_pdfs):
    """Test that files with wrong MIME types are rejected."""
    with pytest.raises(DocumentLoaderError, match="Unsupported file type"):
        validate_pdf(temp_pdfs["fake"])

def test_validate_large_file(temp_pdfs):
    """Test that files exceeding max size are rejected."""
    # We pass max_size_mb = 0 to easily trigger the size limit
    with pytest.raises(DocumentLoaderError, match="File too large"):
        validate_pdf(temp_pdfs["valid"], max_size_mb=0)

# =============================================================================
# TESTS FOR EXTRACTION
# =============================================================================

def test_extract_text_valid(temp_pdfs):
    """Test that text is correctly extracted page by page."""
    result = extract_text_from_pdf(temp_pdfs["valid"])
    
    assert result["total_pages"] == 2
    
    # Check page 1
    page1 = result["pages"][0]
    assert page1["page_number"] == 1
    assert "This is a test document." in page1["text"]
    assert page1["is_scanned"] is False
    
    # Check page 2
    page2 = result["pages"][1]
    assert page2["page_number"] == 2
    assert "Page 2 content." in page2["text"]

def test_extract_corrupted_pdf(temp_pdfs):
    """Test that corrupted/fake PDFs raise a clear error during extraction."""
    with pytest.raises(DocumentLoaderError, match="File is corrupted or not a valid PDF"):
        extract_text_from_pdf(temp_pdfs["fake"])
