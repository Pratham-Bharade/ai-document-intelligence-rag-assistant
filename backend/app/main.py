"""
File: backend/app/main.py
Purpose: FastAPI Application Entry Point, Security & Telemetry Middleware, and Prometheus /metrics.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, conversations, documents, rag
from app.core.config import settings
from app.core.middleware import (
    AuditLoggingMiddleware,
    RateLimiterMiddleware,
    SecurityHeadersMiddleware
)
from app.core.telemetry import RequestIdMiddleware, get_prometheus_metrics_response
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan context."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Application shutdown.")


app = FastAPI(
    title="AI Document Intelligence & RAG Assistant",
    description=(
        "Production-oriented Retrieval-Augmented Generation system. "
        "Upload documents, ask questions, get grounded AI answers with citations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 1. Register Custom Security, Correlation Tracing & Audit Middleware (outer to inner)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware, max_requests=120, window_seconds=60)

# 2. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Include API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/metrics", tags=["Observability & Telemetry"])
def prometheus_metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    return get_prometheus_metrics_response()


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "message": "AI Document Intelligence & RAG Assistant is running",
    }


@app.get("/", tags=["System"])
async def root() -> dict:
    """Root endpoint providing API discovery links."""
    return {
        "name": "AI Document Intelligence & RAG Assistant",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "api_prefix": "/api"
    }
