"""
File: backend/tests/test_database.py
Purpose: Unit tests for SQLAlchemy 2.0 ORM Models, Relationships, and Cascade Deletion.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
from app.models import User, Document, DocumentChunk, Conversation, Message


@pytest.fixture
def db_session():
    """Creates a temporary in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session: Session = TestingSession()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_crud_and_unique_constraint(db_session: Session):
    """Test User creation, querying, and unique email constraint enforcement."""
    user1 = User(
        email="dev@example.com",
        hashed_password="fake_hashed_pw",
        full_name="Developer One"
    )
    db_session.add(user1)
    db_session.commit()
    db_session.refresh(user1)

    assert user1.id is not None
    assert user1.email == "dev@example.com"
    assert user1.is_active is True
    assert user1.created_at is not None

    # Duplicate email should trigger IntegrityError
    user2 = User(
        email="dev@example.com",
        hashed_password="another_pw"
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_and_chunk_cascade_delete(db_session: Session):
    """Test that deleting a Document automatically cascades and deletes all its chunks."""
    user = User(email="owner@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    doc = Document(
        user_id=user.id,
        title="Handbook 2026",
        filename="handbook.pdf",
        file_path="/uploads/handbook.pdf",
        file_size=102400,
        total_pages=2,
        status="processed"
    )
    db_session.add(doc)
    db_session.commit()

    # Add 2 chunks
    chunk1 = DocumentChunk(document_id=doc.id, chunk_index=0, page_number=1, text="Chunk 1 text")
    chunk2 = DocumentChunk(document_id=doc.id, chunk_index=1, page_number=2, text="Chunk 2 text")
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    assert len(doc.chunks) == 2
    assert db_session.query(DocumentChunk).count() == 2

    # Delete Document -> Chunks must be deleted automatically
    db_session.delete(doc)
    db_session.commit()

    assert db_session.query(Document).count() == 0
    assert db_session.query(DocumentChunk).count() == 0


def test_conversation_and_messages_relationship(db_session: Session):
    """Test Conversation creation, Message appending, and cascade deletion."""
    user = User(email="chat_user@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="Project Architecture Chat")
    db_session.add(conv)
    db_session.commit()

    msg1 = Message(conversation_id=conv.id, role="user", content="How does RAG work?")
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="RAG combines retrieval with LLM generation.",
        sources_json=[{"page": 1, "doc": "handbook"}]
    )
    db_session.add_all([msg1, msg2])
    db_session.commit()

    assert len(conv.messages) == 2
    assert conv.messages[0].role == "user"
    assert conv.messages[1].role == "assistant"
    assert conv.messages[1].sources_json[0]["page"] == 1

    # Delete Conversation -> Messages must be deleted
    db_session.delete(conv)
    db_session.commit()

    assert db_session.query(Conversation).count() == 0
    assert db_session.query(Message).count() == 0


def test_session_rollback_on_error(db_session: Session):
    """Test that session.rollback() reverts uncommitted changes cleanly."""
    user = User(email="rollback_user@example.com", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    # Rollback before commit
    db_session.rollback()
    assert db_session.query(User).filter_by(email="rollback_user@example.com").first() is None
