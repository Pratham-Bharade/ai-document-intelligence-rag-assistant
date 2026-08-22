"""
File: backend/app/api/routes/rag.py
Purpose: RAG Query & Streaming API Endpoints with Document Metadata Context Injection.
"""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_rag_pipeline
from app.models.document import Document
from app.models.user import User
from app.rag.pipeline import RAGPipeline, RAGPipelineError
from app.rag.prompts import PromptMode

router = APIRouter(prefix="/rag", tags=["RAG Intelligence"])


class RAGQueryRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    top_k: int = 4
    mode: PromptMode = PromptMode.QA
    few_shot: bool = False
    hybrid: bool = False
    custom_instructions: Optional[str] = None


class RAGSourceResponse(BaseModel):
    page_number: Optional[int]
    document_id: Optional[str]
    score: Optional[float]
    snippet: str


class RAGQueryResponse(BaseModel):
    answer: str
    provider: Optional[str]
    model: Optional[str]
    sources: List[RAGSourceResponse]
    total_sources: int
    mode: str
    guardrails: Optional[Dict[str, Any]] = None


def _get_document_metadata_context(db: Session, document_id: Optional[str], user_id: str) -> Optional[str]:
    """Extracts structural metadata (total pages, title, file name) for RAG context."""
    if document_id:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            return (
                f"Document Title: {doc.title or doc.filename}\n"
                f"Total Pages: {doc.total_pages}\n"
                f"Document ID: {doc.id}\n"
                f"File Size: {doc.file_size} bytes"
            )
    else:
        user_docs = db.query(Document).filter(Document.user_id == user_id).all()
        if user_docs:
            doc_lines = [f"- {d.title or d.filename}: {d.total_pages} pages (ID: {d.id})" for d in user_docs]
            return "Available Knowledge Base Documents:\n" + "\n".join(doc_lines)
    return None


@router.post("/query", response_model=RAGQueryResponse)
def query_documents(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Any:
    """
    Executes an end-to-end RAG query against uploaded documents.
    """
    metadata_filter = {}
    if payload.document_id:
        metadata_filter["document_id"] = payload.document_id

    doc_metadata_str = _get_document_metadata_context(db, payload.document_id, current_user.id)

    try:
        response = pipeline.query(
            question=payload.question,
            top_k=payload.top_k,
            metadata_filter=metadata_filter if metadata_filter else None,
            hybrid=payload.hybrid,
            mode=payload.mode,
            few_shot=payload.few_shot,
            custom_instructions=payload.custom_instructions,
            document_metadata=doc_metadata_str
        )
        return response
    except RAGPipelineError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query execution failed: {str(e)}"
        )


@router.post("/query/stream")
def stream_query_documents(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Streams RAG response tokens via Server-Sent Events (SSE) with structural metadata awareness.
    """
    metadata_filter = {}
    if payload.document_id:
        metadata_filter["document_id"] = payload.document_id

    doc_metadata_str = _get_document_metadata_context(db, payload.document_id, current_user.id)

    def event_generator():
        try:
            for event in pipeline.stream_query(
                question=payload.question,
                top_k=payload.top_k,
                metadata_filter=metadata_filter if metadata_filter else None,
                hybrid=payload.hybrid,
                mode=payload.mode,
                few_shot=payload.few_shot,
                custom_instructions=payload.custom_instructions,
                document_metadata=doc_metadata_str
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_packet = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_packet)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
