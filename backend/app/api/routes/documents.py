"""
File: backend/app/api/routes/documents.py
Purpose: Document Management API Endpoints (Upload, Ingest, List, Get, Delete).
"""

import os
import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_rag_pipeline
from app.core.config import settings
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

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Any:
    """
    Uploads a PDF document, streams it to disk, and runs RAG ingestion.
    """
    # 1. Validation check on filename / extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are currently supported."
        )

    doc_title = title or file.filename.rsplit(".", 1)[0]
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    dest_path = os.path.join(upload_dir, unique_filename)

    try:
        # 2. Save file stream to disk
        file_size = save_upload_file(file, dest_path)

        # 3. Create initial database record
        doc = create_document_record(
            db=db,
            user_id=current_user.id,
            title=doc_title,
            filename=file.filename,
            file_path=dest_path,
            file_size=file_size,
            mime_type=file.content_type or "application/pdf"
        )

        # 4. Run RAG ingestion (Chunking, Embedding, Vector indexing)
        doc = process_document_ingestion(db, pipeline, doc.id)
        return doc

    except DocumentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during ingestion: {str(e)}"
        )


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
