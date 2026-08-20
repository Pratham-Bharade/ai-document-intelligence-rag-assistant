"""
File: backend/app/schemas/document.py
Purpose: Pydantic schemas for Document and Chunk operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    page_number: int
    text: str
    metadata_json: Optional[Dict[str, Any]] = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    filename: str
    file_size: int
    mime_type: str
    total_pages: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentDetailRead(DocumentRead):
    chunks: List[DocumentChunkRead] = []
