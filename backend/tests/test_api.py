"""
File: backend/tests/test_api.py
Purpose: Integration tests for FastAPI REST Endpoints (Auth, Documents, RAG, Conversations).
"""

import io
import pytest
import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import MagicMock

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.api.dependencies import get_rag_pipeline
from app.rag.pipeline import RAGPipeline
from app.rag.embeddings import DocumentEmbedder
from app.rag.vector_store import InMemoryVectorStore
from app.rag.llm import LLMService


from sqlalchemy.pool import StaticPool

# Use in-memory SQLite with StaticPool so all threads share the same database
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mock_pipeline():
    """Mock RAG pipeline for fast API testing."""
    store = InMemoryVectorStore(expected_dim=4)
    mock_embed = MagicMock(spec=DocumentEmbedder)
    mock_embed.expected_dimensions = 4
    mock_embed.embed_chunks.side_effect = lambda chunks, batch_size=100: [
        {**c, "vector": [1.0, 0.0, 0.0, 0.0]} for c in chunks
    ]
    
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {
        "content": "Standard hours are 9 AM to 5 PM [Page 1].",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "finish_reason": "stop"
    }
    def fake_stream(messages, max_tokens=1024):
        yield "Standard hours "
        yield "are 9 to 5."
    mock_llm.stream_generate.side_effect = fake_stream

    return RAGPipeline(embedder=mock_embed, vector_store=store, llm_service=mock_llm)


@pytest.fixture
def client(mock_pipeline):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    """Creates a user and returns their JWT token."""
    client.post(
        "/api/auth/register",
        json={"email": "api_user@example.com", "password": "securepassword123", "full_name": "API Tester"}
    )
    res = client.post(
        "/api/auth/login/json",
        json={"email": "api_user@example.com", "password": "securepassword123"}
    )
    return res.json()["access_token"]


def test_auth_me(client, auth_token):
    """Test /api/auth/me returns current user profile."""
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "api_user@example.com"


def test_document_upload_and_list(client, auth_token):
    """Test uploading a PDF and listing uploaded documents."""
    # Create in-memory PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Working Hours: 9:00 AM to 5:00 PM EST.")
    pdf_bytes = doc.tobytes()
    doc.close()

    # Upload
    files = {"file": ("policy.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res = client.post(
        "/api/documents/upload",
        files=files,
        data={"title": "Company Policy"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]
    assert res.json()["title"] == "Company Policy"
    assert res.json()["status"] == "processed"

    # List
    list_res = client.get("/api/documents", headers={"Authorization": f"Bearer {auth_token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_rag_query_endpoint(client, auth_token):
    """Test POST /api/rag/query."""
    res = client.post(
        "/api/rag/query",
        json={"question": "What are the working hours?", "top_k": 2},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "Standard hours" in data["answer"]
    assert "sources" in data
    assert "guardrails" in data


def test_rag_streaming_endpoint(client, auth_token):
    """Test POST /api/rag/query/stream Server-Sent Events."""
    res = client.post(
        "/api/rag/query/stream",
        json={"question": "What are the working hours?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    assert "data:" in res.text


def test_conversations_flow(client, auth_token):
    """Test creating conversation thread and sending messages."""
    # Create thread
    conv_res = client.post(
        "/api/conversations",
        json={"title": "Policy Chat"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # Send message
    msg_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Can I work remotely?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert msg_res.status_code == 201
    assert msg_res.json()["role"] == "assistant"
    assert "Standard hours" in msg_res.json()["content"]

    # Get conversation details
    get_conv = client.get(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert get_conv.status_code == 200
    assert len(get_conv.json()["messages"]) == 2  # 1 user + 1 assistant message


def test_unauthorized_access(client):
    """Endpoints requiring authentication must return 401 when no token is passed."""
    res = client.get("/api/documents")
    assert res.status_code == 401
