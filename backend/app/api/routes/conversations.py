"""
File: backend/app/api/routes/conversations.py
Purpose: Conversation Threads & Persistent Multi-Turn Chat API Endpoints.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_rag_pipeline
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.schemas.conversation import ConversationCreate, ConversationRead, MessageCreate, MessageRead
from app.services.chat_service import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation_by_id,
    get_user_conversations
)

router = APIRouter(prefix="/conversations", tags=["Conversations & Chat"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_new_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new chat conversation thread."""
    conv = create_conversation(db, current_user.id, title=payload.title or "New Chat")
    return conv


@router.get("", response_model=List[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """List all chat conversation threads for the current user."""
    return get_user_conversations(db, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get a conversation thread and all its chronological messages."""
    conv = get_conversation_by_id(db, current_user.id, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    return conv


@router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Any:
    """
    Sends a user message to a conversation thread:
      1. Saves the User message to DB
      2. Executes RAG query across user's documents
      3. Saves the Assistant response with source citations to DB
      4. Returns the Assistant Message record
    """
    conv = get_conversation_by_id(db, current_user.id, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # 1. Save User Message
    add_message(
        db=db,
        conversation_id=conv.id,
        role="user",
        content=payload.content
    )

    # 2. Run RAG Pipeline
    rag_result = pipeline.query(question=payload.content)

    # 3. Save Assistant Message with sources
    assistant_msg = add_message(
        db=db,
        conversation_id=conv.id,
        role="assistant",
        content=rag_result.get("answer", ""),
        sources_json=rag_result.get("sources", [])
    )

    return assistant_msg


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete a conversation thread and all its messages."""
    success = delete_conversation(db, current_user.id, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
