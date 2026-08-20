"""
File: backend/app/models/__init__.py
Purpose: Export all database models for clean imports and Alembic autogenerate discovery.
"""

from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.models.conversation import Conversation, Message

__all__ = [
    "User",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message"
]
