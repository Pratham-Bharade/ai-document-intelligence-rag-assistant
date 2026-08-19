"""
File: backend/app/rag/loader.py
Purpose: Validate, load, and extract text from PDF documents.
Why it exists: The first step in any RAG system is getting text out of documents.
               PDFs are notoriously complex (images, layouts, corrupted files).
               This module abstracts away that complexity so the rest of the 
               system just gets clean text and metadata.
Dependencies: 
    - PyMuPDF (fitz) for fast, accurate text extraction.
    - python-magic for true MIME type validation (not just file extensions).
    - pytesseract for OCR on scanned PDFs.
Main responsibilities:
  - Validate file size, type, and integrity.
  - Extract text page-by-page.
  - Maintain page numbers (crucial for citations).
  - Detect scanned pages and apply OCR if necessary.
"""

import os
import logging
from typing import Any, Dict, List

import fitz  # PyMuPDF
import magic

logger = logging.getLogger(__name__)

class DocumentLoaderError(Exception):
    """Custom exception for all document loading errors."""
    pass


def validate_pdf(file_path: str, max_size_mb: int = 50) -> bool:
    """
    Validates that a file is a valid PDF and within size limits.
    
    Why not just check if it ends in '.pdf'?
    Because an attacker could rename 'malware.exe' to 'document.pdf'.
    We must check the actual file signature (MIME type).
    """
    if not os.path.exists(file_path):
        raise DocumentLoaderError(f"File not found: {file_path}")

    # Check file size
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > max_size_mb:
        raise DocumentLoaderError(f"File too large: {size_mb:.2f} MB. Max allowed is {max_size_mb} MB.")

    if size_bytes == 0:
        raise DocumentLoaderError("File is empty.")

    # Check MIME type using magic numbers (file signature)
    try:
        mime_type = magic.from_file(file_path, mime=True)
        if mime_type != 'application/pdf':
            raise DocumentLoaderError(f"Unsupported file type: {mime_type}. Only application/pdf is allowed.")
    except DocumentLoaderError:
        raise
    except Exception as e:
        logger.error(f"Error checking MIME type with magic: {e}")
        # Fallback to simple extension check if magic fails
        if not file_path.lower().endswith(".pdf"):
            raise DocumentLoaderError("File does not appear to be a PDF.")

    return True


def apply_ocr_to_page(page: fitz.Page) -> str:
    """
    Applies Optical Character Recognition to a scanned PDF page.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
        
        # Render the PDF page to a high-resolution image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Zoom 2x for better OCR
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        # Run OCR
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.warning(f"OCR failed or Tesseract is not installed: {e}")
        return ""


def extract_text_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extracts text and metadata from a PDF file.
    
    Returns a dictionary containing:
        - metadata: Document metadata (title, author, etc.)
        - total_pages: Number of pages
        - pages: List of dictionaries with page_number and text
    """
    try:
        # We use fitz (PyMuPDF) because it is significantly faster and 
        # more accurate than PyPDF2 or pdfplumber.
        doc = fitz.open(file_path)
    except fitz.FileDataError as e:
        raise DocumentLoaderError(f"File is corrupted or not a valid PDF: {e}")
    except Exception as e:
        raise DocumentLoaderError(f"Failed to open PDF: {e}")

    pages_data = []
    
    # Iterate through every page
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extract plain text
        text = page.get_text("text").strip()
        is_scanned = False
        
        # Heuristic: If a page has very few characters but isn't empty visually,
        # it might be a scanned image. (Using < 50 chars as a rough threshold).
        if len(text) < 50:
            # Check if the page actually contains images
            image_list = page.get_images(full=True)
            if image_list:
                is_scanned = True
                logger.info(f"Page {page_num + 1} appears to be scanned. Applying OCR...")
                ocr_text = apply_ocr_to_page(page)
                if ocr_text:
                    text = ocr_text

        pages_data.append({
            "page_number": page_num + 1,  # 1-indexed for humans
            "text": text,
            "is_scanned": is_scanned
        })
        
    metadata = doc.metadata
    
    # Clean up the fitz document object
    doc.close()
    
    return {
        "metadata": metadata,
        "total_pages": len(pages_data),
        "pages": pages_data
    }
