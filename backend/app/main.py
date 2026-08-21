"""
File: backend/app/main.py
Purpose: FastAPI Application Entry Point and Router Registration.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents, rag, conversations
from app.core.config import settings
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
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")


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
        "api_prefix": "/api"
    }
