"""
File: backend/tests/test_main.py
Purpose: Basic smoke tests for the FastAPI application
Why it exists: Tests confirm that the server starts and basic endpoints work.
               These run fast (< 1 second) and catch obvious breakage early.
Dependencies: pytest, fastapi.testclient or httpx
Main responsibilities:
  - Verify the health check endpoint returns 200
  - Verify the root endpoint returns expected data
  - Serve as a template for future test modules
"""

from fastapi.testclient import TestClient

from app.main import app

# TestClient is a synchronous HTTP client that runs the FastAPI app in-process.
# No real server is started — tests run entirely in memory.
# This makes tests extremely fast.
client = TestClient(app)


def test_health_check():
    """
    Test that the health check endpoint returns HTTP 200 with correct body.
    
    This is the most important smoke test. If this fails, the server is broken.
    """
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body


def test_root_endpoint():
    """Test the root endpoint returns API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "docs" in body


def test_docs_available():
    """Test that interactive API documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_nonexistent_endpoint_returns_404():
    """
    Test that an unknown URL returns 404, not 500.
    
    If this returns 500, something is wrong with error handling.
    404 is the expected and correct response for unknown routes.
    """
    response = client.get("/this-does-not-exist")
    assert response.status_code == 404
