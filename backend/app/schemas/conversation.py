"""
File: backend/app/schemas/conversation.py
Purpose: Pydantic schemas for Conversations and Messages.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    content: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    sources_json: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = []
