"""
File: backend/app/workers/tasks.py
Purpose: Background Task Implementations for Heavy Document Ingestion and Bulk Re-indexing.
"""

import logging
from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from app.rag.pipeline import RAGPipeline
from app.services.document_service import process_document_ingestion
from app.workers.task_queue import task_queue

logger = logging.getLogger(__name__)


def background_ingest_document(
    db_session_factory: Callable[[], Session],
    pipeline: RAGPipeline,
    document_id: str,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes PDF parsing, OCR, chunking, and embedding generation in a background worker thread.
    """
    db: Session = db_session_factory()
    try:
        if task_id:
            task_queue.update_progress(task_id, 25)

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found in database.")

        if task_id:
            task_queue.update_progress(task_id, 50)

        # Ingest and mirror chunks
        doc = process_document_ingestion(db, pipeline, document_id)

        if task_id:
            task_queue.update_progress(task_id, 90)

        return {
            "document_id": doc.id,
            "title": doc.title,
            "total_pages": doc.total_pages,
            "status": doc.status
        }
    finally:
        db.close()
