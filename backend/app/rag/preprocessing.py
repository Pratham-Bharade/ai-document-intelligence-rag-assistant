"""
File: backend/app/rag/preprocessing.py
Purpose: Clean and normalize extracted text before chunking.
Why it exists: PDFs often contain messy text: weird whitespace, broken ligatures
               (like 'fi' converted to a single special character), zero-width
               characters, and redundant blank pages. If we don't clean this,
               the LLM gets confused and tokenization becomes inefficient.
Dependencies: Python standard libraries (re, unicodedata)
Main responsibilities:
  - Normalize unicode characters (smart quotes to straight quotes, expand ligatures).
  - Fix weird spacing (collapse multiple spaces, cap newlines at 2).
  - Remove invisible/zero-width characters that break embedding models.
  - Drop pages that have no actual content after cleaning.
"""

import re
import unicodedata
from typing import Any, Dict

def normalize_text(text: str) -> str:
    """
    Cleans text by normalizing unicode and fixing whitespace issues.
    
    WARNING: We avoid aggressive cleaning (like removing all punctuation,
    lowercasing everything, or stripping out numbers) because modern LLMs
    need punctuation, casing, and formatting to understand context perfectly.
    """
    if not text:
        return ""

    # 1. Normalize Unicode
    # NFKC normalizes things like the 'fi' ligature into two separate characters 'f' and 'i'.
    # It also normalizes smart quotes (“ ”) to standard quotes (" "), which tokenizers prefer.
    text = unicodedata.normalize("NFKC", text)
    
    # 2. Fix whitespace
    # PDFs often have strings of 10+ newlines. We cap consecutive newlines at exactly 2.
    # This preserves paragraph breaks but removes massive vertical gaps.
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces/tabs (but not newlines) with a single space.
    text = re.sub(r'[^\S\n]+', ' ', text)
    
    # 3. Remove completely null/zero-width characters
    # These characters are invisible to humans but look like tokens to an LLM.
    text = text.replace('\u200b', '') # Zero-width space
    text = text.replace('\x00', '')   # Null byte
    
    return text.strip()


def preprocess_document(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes the output of extract_text_from_pdf and cleans the text of every page.
    
    Returns a dictionary in the same format, but with cleaned text and 
    empty pages removed.
    """
    cleaned_pages = []
    
    for page in extracted_data["pages"]:
        cleaned_text = normalize_text(page["text"])
        
        # We only keep pages that actually have text after cleaning.
        # This automatically drops blank pages or pages that were just whitespace.
        if cleaned_text:
            cleaned_pages.append({
                "page_number": page["page_number"],
                "text": cleaned_text,
                "is_scanned": page.get("is_scanned", False)
            })
            
    return {
        "metadata": extracted_data.get("metadata", {}),
        "total_pages": extracted_data.get("total_pages", 0),
        "pages": cleaned_pages
    }
