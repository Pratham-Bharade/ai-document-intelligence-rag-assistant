"""
File: backend/tests/test_security_auth.py
Purpose: Unit and Integration tests for RBAC, Security Headers, Rate Limiting, and Audit Logging.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_password_hash, create_access_token
from app.core.middleware import SlidingWindowRateLimiter


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_security_db():
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
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def normal_user_token(client):
    """Creates a regular non-superuser."""
    db = TestingSession()
    user = User(
        email="regular@example.com",
        hashed_password=get_password_hash("pass123"),
        is_superuser=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.id, "email": user.email})
    db.close()
    return token


@pytest.fixture
def superuser_token(client):
    """Creates an admin superuser."""
    db = TestingSession()
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        is_superuser=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(data={"sub": user.id, "email": user.email})
    db.close()
    return token


def test_rbac_standard_user_forbidden_on_admin_routes(client, normal_user_token):
    """A regular user must receive HTTP 403 Forbidden on admin endpoints."""
    res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {normal_user_token}"})
    assert res.status_code == 403
    assert "administrative privileges" in res.json()["detail"]


def test_rbac_superuser_allowed_on_admin_routes(client, superuser_token):
    """A superuser must receive HTTP 200 OK on admin endpoints."""
    res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {superuser_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_users" in data
    assert "total_documents" in data


def test_security_headers_present(client):
    """All responses must include OWASP security headers."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert "max-age=" in res.headers.get("strict-transport-security", "")
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_audit_logging_process_time_header(client):
    """Responses must include X-Process-Time header measured by audit middleware."""
    res = client.get("/health")
    assert "x-process-time" in res.headers
    assert "ms" in res.headers["x-process-time"]


def test_sliding_window_rate_limiter():
    """Test rate limiter logic blocking requests when limit is exceeded."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    ip = "192.168.1.100"

    assert limiter.is_allowed(ip) is True  # 1
    assert limiter.is_allowed(ip) is True  # 2
    assert limiter.is_allowed(ip) is True  # 3
    assert limiter.is_allowed(ip) is False # 4 (Exceeded)
