"""
File: backend/app/api/routes/admin.py
Purpose: Admin-only RBAC Management Endpoints.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_superuser, get_db
from app.models import Conversation, Document, DocumentChunk, Message, User
from app.schemas.user import UserRead

router = APIRouter(prefix="/admin", tags=["Admin & System Management"])


@router.get("/users", response_model=List[UserRead])
def list_all_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
) -> Any:
    """Admin-only: List all registered users."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/stats", response_model=Dict[str, Any])
def get_system_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_active_superuser)
) -> Any:
    """Admin-only: Aggregate system statistics."""
    total_users = db.query(User).count()
    total_docs = db.query(Document).count()
    total_chunks = db.query(DocumentChunk).count()
    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()

    return {
        "total_users": total_users,
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_conversations": total_conversations,
        "total_messages": total_messages
    }
