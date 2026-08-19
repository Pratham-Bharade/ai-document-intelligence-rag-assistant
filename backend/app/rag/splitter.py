"""
File: backend/app/rag/splitter.py
Purpose: Split preprocessed documents into overlapping chunks.
Why it exists: LLMs and Embedding models have strict context limits (e.g., 8k tokens).
               You cannot embed a 500-page book in one go. You must break it into
               paragraphs. If you just slice text arbitrarily (e.g., every 500 chars),
               you will slice a word in half. We use Recursive splitting to split at
               logical boundaries (paragraphs -> sentences -> words -> chars).
Dependencies: langchain-text-splitters
Main responsibilities:
  - Take cleaned page text and break it into chunks.
  - Apply overlap so context isn't lost at the chunk boundaries.
  - Attach page numbers and metadata to every chunk.
"""

from typing import Any, Dict, List
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_document(
    cleaned_data: Dict[str, Any], 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Takes a preprocessed document and splits it into overlapping chunks.
    
    Why chunk_size=1000 and overlap=200?
    - 1000 characters is roughly 250 tokens. This captures about 1-2 paragraphs,
      which is generally a single cohesive thought.
    - 200 characters overlap ensures that if a sentence is split between two chunks,
      the end of chunk A overlaps with the beginning of chunk B, giving the LLM
      the full context.
      
    Returns a list of chunk dictionaries, ready for embedding.
    """
    
    # The RecursiveCharacterTextSplitter tries to split on double newlines (paragraphs) first.
    # If the paragraph is still bigger than chunk_size, it tries single newlines (lines),
    # then spaces (words), and finally characters as a last resort.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = []
    chunk_index = 0
    
    # We iterate page by page. 
    # PRO: This makes tracking the exact page number for citations trivially easy.
    # CON: If a paragraph starts at the bottom of Page 1 and ends on Page 2, 
    #      it gets hard-split. For most enterprise use-cases, this trade-off is 
    #      worth it for 100% accurate page citations.
    for page in cleaned_data.get("pages", []):
        page_text = page["text"]
        page_number = page["page_number"]
        
        # Split this specific page
        text_chunks = splitter.split_text(page_text)
        
        for text_chunk in text_chunks:
            chunks.append({
                "chunk_index": chunk_index,
                "text": text_chunk,
                "page_number": page_number,
                "metadata": cleaned_data.get("metadata", {})
            })
            chunk_index += 1
            
    return chunks
