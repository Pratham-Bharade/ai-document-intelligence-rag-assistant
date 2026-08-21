"""
File: backend/app/services/chat_service.py
Purpose: Chat and Conversation Service for managing conversation threads and messages.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message


def create_conversation(db: Session, user_id: str, title: str = "New Chat") -> Conversation:
    """Creates a new conversation thread."""
    conv = Conversation(user_id=user_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_user_conversations(db: Session, user_id: str) -> List[Conversation]:
    """Retrieves all conversation threads for a user."""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).all()


def get_conversation_by_id(db: Session, user_id: str, conversation_id: str) -> Optional[Conversation]:
    """Fetches a specific conversation with all its messages."""
    return db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id
    ).first()


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources_json: Optional[List[Dict[str, Any]]] = None
) -> Message:
    """Appends a new message (user or assistant) to a conversation."""
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources_json=sources_json
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def delete_conversation(db: Session, user_id: str, conversation_id: str) -> bool:
    """Deletes a conversation thread and all its messages."""
    conv = get_conversation_by_id(db, user_id, conversation_id)
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True
