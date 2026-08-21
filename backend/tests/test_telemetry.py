"""
File: backend/tests/test_telemetry.py
Purpose: Unit and Integration tests for Structured JSON Logging, Request-ID tracing, and Prometheus Metrics.
"""

import json
import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.telemetry import (
    JSONLogFormatter,
    RAG_QUERIES_TOTAL,
    RAG_QUERY_LATENCY,
    request_id_ctx_var
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_json_log_formatter():
    """Verify JSONLogFormatter formats log record into valid JSON with expected keys."""
    formatter = JSONLogFormatter()
    logger = logging.getLogger("test_logger")
    record = logger.makeRecord(
        name="test_logger",
        level=logging.INFO,
        fn="test_telemetry.py",
        lno=25,
        msg="Test log message",
        args=(),
        exc_info=None
    )

    request_id_ctx_var.set("req-12345")
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test log message"
    assert parsed["request_id"] == "req-12345"


def test_request_id_header_injected(client):
    """Responses must include X-Request-ID header generated or echoed by RequestIdMiddleware."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert len(res.headers["x-request-id"]) > 10


def test_request_id_echoed_if_provided(client):
    """If client sends X-Request-ID, the server must preserve and echo the same ID."""
    custom_id = "custom-client-uuid-999"
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == custom_id


def test_prometheus_metrics_endpoint(client):
    """GET /metrics must return HTTP 200 with Prometheus text metrics."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    assert "rag_queries_total" in res.text
    assert "rag_query_latency_seconds" in res.text
    assert "documents_ingested_total" in res.text
