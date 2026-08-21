"""
File: backend/app/core/telemetry.py
Purpose: Structured JSON Logging, Correlated Request-ID Tracing, and Prometheus Observability Metrics.
"""

import contextvars
import json
import logging
import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to correlate Request ID across async tasks and logs
request_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


# -----------------------------------------------------------------------------
# 1. STRUCTURED JSON LOG FORMATTER
# -----------------------------------------------------------------------------

class JSONLogFormatter(logging.Formatter):
    """
    Formats standard Python log records into structured JSON dictionaries
    ready for ingestion by Datadog, CloudWatch, Grafana Loki, or Elasticsearch.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_ctx_var.get() or "system",
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


# -----------------------------------------------------------------------------
# 2. REQUEST ID & CORRELATION TRACING MIDDLEWARE
# -----------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Intercepts incoming HTTP requests, extracts or generates a unique UUID `X-Request-ID`,
    attaches it to the async context, and returns it in the response headers.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx_var.set(req_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx_var.reset(token)


# -----------------------------------------------------------------------------
# 3. PROMETHEUS METRICS DEFINITIONS
# -----------------------------------------------------------------------------

# Total RAG queries partitioned by provider, mode, and execution status
RAG_QUERIES_TOTAL = Counter(
    "rag_queries_total",
    "Total RAG queries executed",
    ["provider", "mode", "status"]
)

# Latency histogram for end-to-end RAG query execution
RAG_QUERY_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "End-to-end latency of RAG queries in seconds",
    ["mode"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Total document uploads and ingestions
DOCUMENTS_INGESTED_TOTAL = Counter(
    "documents_ingested_total",
    "Total documents processed through ingestion pipeline",
    ["status"]
)

# Total PDF pages parsed and chunked
DOCUMENT_PAGES_TOTAL = Counter(
    "document_pages_total",
    "Total document pages parsed and chunked into vector embeddings"
)

# Security guardrail detections (Prompt injection, Jailbreak)
SECURITY_ATTACKS_BLOCKED_TOTAL = Counter(
    "security_attacks_blocked_total",
    "Total malicious prompt injection and jailbreak attacks intercepted",
    ["attack_type"]
)

# Distribution of RAG answer faithfulness scores (0.0 to 1.0)
FAITHFULNESS_SCORES = Histogram(
    "rag_faithfulness_scores",
    "Distribution of calculated RAG faithfulness evaluation scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


def get_prometheus_metrics_response() -> Response:
    """Returns all collected metrics in standard Prometheus text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
