"""
File: backend/app/api/routes/documents.py
Purpose: Document Management API Endpoints (Upload, Async Ingestion, Task Status, List, Get, Delete).
"""

import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_rag_pipeline
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.schemas.document import DocumentDetailRead, DocumentRead
from app.services.document_service import (
    DocumentServiceError,
    create_document_record,
    delete_document,
    get_document_by_id,
    get_user_documents,
    process_document_ingestion,
    save_upload_file
)
from app.workers.task_queue import task_queue
from app.workers.tasks import background_ingest_document

router = APIRouter(prefix="/documents", tags=["Documents"])


SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".pptx"}


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Any:
    """
    Synchronously uploads a document (PDF, Word, TXT, CSV, PPTX), streams to disk, and runs RAG ingestion.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTS))}"
        )

    doc_title = title or file.filename.rsplit(".", 1)[0]
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    dest_path = os.path.join(upload_dir, unique_filename)

    try:
        file_size = save_upload_file(file, dest_path)

        doc = create_document_record(
            db=db,
            user_id=current_user.id,
            title=doc_title,
            filename=file.filename,
            file_path=dest_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream"
        )

        doc = process_document_ingestion(db, pipeline, doc.id)
        return doc

    except DocumentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upload/async", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_async(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Dict[str, Any]:
    """
    Asynchronously uploads a document, saves to disk, and dispatches ingestion to background queue.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTS))}"
        )

    doc_title = title or file.filename.rsplit(".", 1)[0]
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    dest_path = os.path.join(upload_dir, unique_filename)

    file_size = save_upload_file(file, dest_path)

    doc = create_document_record(
        db=db,
        user_id=current_user.id,
        title=doc_title,
        filename=file.filename,
        file_path=dest_path,
        file_size=file_size,
        mime_type=file.content_type or "application/pdf"
    )

    # Dispatch to background task queue
    task_id = task_queue.dispatch_async(
        background_ingest_document,
        db_session_factory=SessionLocal,
        pipeline=pipeline,
        document_id=doc.id
    )

    return {
        "task_id": task_id,
        "document_id": doc.id,
        "status": "queued",
        "message": "Document accepted for asynchronous background processing."
    }


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Retrieve the real-time progress and status of a background ingestion task."""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found."
        )
    return task


@router.get("", response_model=List[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """List all documents uploaded by the current user."""
    return get_user_documents(db, current_user.id)


@router.get("/{document_id}", response_model=DocumentDetailRead)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get details of a specific document including its extracted chunks."""
    doc = get_document_by_id(db, current_user.id, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete a document, its database chunks, and its file on disk."""
    success = delete_document(db, current_user.id, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
