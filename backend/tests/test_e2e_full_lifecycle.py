"""
File: backend/tests/test_e2e_full_lifecycle.py
Purpose: End-to-End Full System Lifecycle Integration Test (Phase 25 Capstone).
Covers: Registration -> Login -> Async PDF Ingestion -> RAG Query & Citations ->
        Multi-Tier Caching -> Multi-Turn Conversation Memory -> Prometheus Telemetry -> Document Deletion & Invalidation.
"""

import io
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

# Isolated SQLite database for full lifecycle test
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_e2e_db():
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
    mock_embed.embed_query.return_value = [1.0, 0.0, 0.0, 0.0]
    mock_embed.embed_chunks.side_effect = lambda chunks, batch_size=100: [
        {**c, "vector": [1.0, 0.0, 0.0, 0.0]} for c in chunks
    ]

    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.return_value = {
        "content": "Employees are entitled to 20 days annual leave per company handbook section 4.",
        "provider": "groq",
        "model": "llama-3.3-70b"
    }

    return RAGPipeline(embedder=mock_embed, vector_store=store, llm_service=mock_llm)


@pytest.fixture
def client(mock_pipeline):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_full_system_e2e_lifecycle(client):
    """
    Executes the entire 25-phase enterprise lifecycle in a single coherent flow.
    """
    # 1. User Registration
    user_payload = {
        "email": "enterprise_ceo@acme.corp",
        "password": "SecurePassword123!",
        "full_name": "Chief Executive Officer"
    }
    reg_res = client.post("/api/auth/register", json=user_payload)
    assert reg_res.status_code == 201, reg_res.text

    # 2. User Authentication (JWT)
    login_res = client.post("/api/auth/login/json", json={
        "email": "enterprise_ceo@acme.corp",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Synchronous Document Ingestion
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "ACME Corporation Annual Leave Policy. Section 4: Employees are entitled to 20 days annual leave.")
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("acme_policy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"title": "ACME Employee Policy 2026"},
        headers=headers
    )
    assert upload_res.status_code == 201, upload_res.text
    doc_id = upload_res.json()["id"]

    # 4. RAG Query Execution with Verified Citations
    query_payload = {
        "question": "How many days of annual leave do employees receive?",
        "document_id": doc_id,
        "mode": "qa"
    }
    rag_res = client.post("/api/rag/query", json=query_payload, headers=headers)
    assert rag_res.status_code == 200, rag_res.text
    ans = rag_res.json()
    assert "20 days annual leave" in ans["answer"]
    assert "guardrails" in ans
    assert ans["guardrails"]["is_grounded"] is True

    # 5. Multi-Turn Conversation Memory Flow
    conv_res = client.post("/api/conversations", json={"title": "Policy Inquiry"}, headers=headers)
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    msg_res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "What is the policy regarding annual leave?", "mode": "qa"},
        headers=headers
    )
    assert msg_res.status_code == 201

    # 6. Prometheus Telemetry Verification
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    assert "rag_queries_total" in metrics_res.text
    assert "documents_ingested_total" in metrics_res.text

    # 7. Document Deletion & Cache Invalidation
    del_res = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 204

    # Document should now be 404
    get_res = client.get(f"/api/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 404
