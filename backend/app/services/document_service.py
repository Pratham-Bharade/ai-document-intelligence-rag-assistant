"""
File: backend/app/services/document_service.py
Purpose: Document Management Service for uploading, storing, ingesting, and deleting documents.
"""

import os
import shutil
import uuid
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.telemetry import DOCUMENT_PAGES_TOTAL, DOCUMENTS_INGESTED_TOTAL
from app.models.document import Document, DocumentChunk
from app.rag.pipeline import RAGPipeline


class DocumentServiceError(Exception):
    """Custom exception for document operations."""
    pass


def save_upload_file(upload_file: UploadFile, destination_path: str) -> int:
    """Streams uploaded file chunks directly to disk to prevent high RAM usage."""
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return os.path.getsize(destination_path)


def create_document_record(
    db: Session,
    user_id: str,
    title: str,
    filename: str,
    file_path: str,
    file_size: int,
    mime_type: str
) -> Document:
    """Creates a new Document database row with status 'pending'."""
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def process_document_ingestion(
    db: Session,
    pipeline: RAGPipeline,
    document_id: str
) -> Document:
    """
    Runs the RAG Pipeline on the document file and persists chunks in DB.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise DocumentServiceError(f"Document {document_id} not found.")

    try:
        # Ingest into RAG pipeline
        report = pipeline.ingest_pdf(
            file_path=doc.file_path,
            document_id=doc.id,
            custom_metadata={"title": doc.title, "filename": doc.filename}
        )

        doc.total_pages = report.get("total_pages", 0)
        doc.status = "processed"
        DOCUMENTS_INGESTED_TOTAL.labels(status="success").inc()
        DOCUMENT_PAGES_TOTAL.inc(doc.total_pages)

        # Also mirror chunk records into DB
        for c in pipeline.vector_store.chunks:
            if c.get("metadata", {}).get("document_id") == doc.id:
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=c.get("chunk_index", 0),
                    page_number=c.get("page_number", 1),
                    text=c.get("text", ""),
                    metadata_json=c.get("metadata")
                )
                db.add(db_chunk)

        db.commit()
        db.refresh(doc)
        return doc

    except Exception as e:
        doc.status = "failed"
        DOCUMENTS_INGESTED_TOTAL.labels(status="failed").inc()
        db.commit()
        raise DocumentServiceError(f"Document processing failed: {e}")


def get_user_documents(db: Session, user_id: str) -> List[Document]:
    """Lists all documents owned by a user."""
    return db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()


def get_document_by_id(db: Session, user_id: str, document_id: str) -> Optional[Document]:
    """Fetches a specific document owned by user."""
    return db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()


def delete_document(db: Session, user_id: str, document_id: str) -> bool:
    """Deletes document record, chunks, and disk file."""
    doc = get_document_by_id(db, user_id, document_id)
    if not doc:
        return False

    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    db.delete(doc)
    db.commit()
    return True
