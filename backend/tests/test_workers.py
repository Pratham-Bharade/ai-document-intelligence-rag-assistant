"""
File: backend/tests/test_workers.py
Purpose: Unit and Integration tests for Background Task Queue, Redis/Memory workers, and Async Upload endpoints.
"""

import io
import time
import pytest
import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.api.dependencies import get_rag_pipeline
from app.rag.pipeline import RAGPipeline
from app.rag.embeddings import DocumentEmbedder
from app.rag.vector_store import InMemoryVectorStore
from app.rag.llm import LLMService
from app.workers.task_queue import TaskQueueManager, TaskStatus


# In-memory SQLite for worker tests
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_worker_db():
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
    store = InMemoryVectorStore(expected_dim=4)
    mock_embed = MagicMock(spec=DocumentEmbedder)
    mock_embed.expected_dimensions = 4
    mock_embed.embed_chunks.side_effect = lambda chunks, batch_size=100: [
        {**c, "vector": [1.0, 0.0, 0.0, 0.0]} for c in chunks
    ]
    return RAGPipeline(embedder=mock_embed, vector_store=store, llm_service=MagicMock(spec=LLMService))


@pytest.fixture
def client(mock_pipeline):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    client.post(
        "/api/auth/register",
        json={"email": "worker_user@example.com", "password": "securepassword123", "full_name": "Worker Tester"}
    )
    res = client.post(
        "/api/auth/login/json",
        json={"email": "worker_user@example.com", "password": "securepassword123"}
    )
    return res.json()["access_token"]


def test_task_queue_manager_lifecycle():
    """Test TaskQueueManager in-memory task state transitions."""
    manager = TaskQueueManager()
    task_id = manager.create_task(task_type="test_job", metadata={"file": "doc.pdf"})

    task = manager.get_task(task_id)
    assert task["status"] == TaskStatus.QUEUED.value
    assert task["progress"] == 0

    # Update progress
    manager.update_progress(task_id, 45)
    task = manager.get_task(task_id)
    assert task["status"] == TaskStatus.PROCESSING.value
    assert task["progress"] == 45

    # Complete
    manager.mark_completed(task_id, result={"pages": 10})
    task = manager.get_task(task_id)
    assert task["status"] == TaskStatus.COMPLETED.value
    assert task["progress"] == 100
    assert task["result"]["pages"] == 10


def test_task_queue_manager_failure():
    """Test TaskQueueManager recording failure states."""
    manager = TaskQueueManager()
    task_id = manager.create_task(task_type="failing_job")
    manager.mark_failed(task_id, error_message="Disk quota exceeded")

    task = manager.get_task(task_id)
    assert task["status"] == TaskStatus.FAILED.value
    assert task["error"] == "Disk quota exceeded"


def test_async_upload_endpoint_and_task_polling(client, auth_token):
    """Test POST /api/documents/upload/async returns 202 and task status polling."""
    # Create small test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Async Ingestion Document Body.")
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("async_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res = client.post(
        "/api/documents/upload/async",
        files=files,
        data={"title": "Async Document Test"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert res.status_code == 202
    data = res.json()
    assert "task_id" in data
    assert "document_id" in data
    assert data["status"] == "queued"

    task_id = data["task_id"]

    # Poll status endpoint
    poll_res = client.get(
        f"/api/documents/tasks/{task_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert poll_res.status_code == 200
    assert poll_res.json()["task_id"] == task_id
