"""
File: backend/app/main.py
Purpose: FastAPI application entry point
Why it exists: Every FastAPI app needs a single entry point where the app
               is created, middleware is registered, and routers are included.
               This is what Uvicorn runs: uvicorn app.main:app
Dependencies: fastapi, core.config, core.logging
Main responsibilities:
  - Create the FastAPI app instance
  - Register middleware (CORS, etc.)
  - Include API routers
  - Define lifecycle events (startup/shutdown)
  - Provide health check endpoint
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# We'll import these as we build each phase:
# from app.api.routes import auth, documents, chat
# from app.core.config import settings
# from app.db.session import engine

logger = logging.getLogger(__name__)

# =============================================================================
# CREATE THE FASTAPI APPLICATION
# =============================================================================
# The app object is the core of the entire backend.
# All routes, middleware, and configuration attach to this object.

app = FastAPI(
    title="AI Document Intelligence & RAG Assistant",
    description=(
        "Production-oriented Retrieval-Augmented Generation system. "
        "Upload documents, ask questions, get grounded AI answers with citations."
    ),
    version="0.1.0",
    # FastAPI automatically generates interactive API docs at /docs (Swagger UI)
    # and /redoc. These URLs control where those docs live.
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
# CORS = Cross-Origin Resource Sharing
# Without this, browsers BLOCK JavaScript from making API calls to a different
# domain/port. Our React app runs on port 5173, our FastAPI on port 8000.
# The browser sees them as "different origins" and blocks requests.
# Adding CORS middleware tells the browser: "these origins are allowed."
#
# ⚠️  In production, replace ["*"] with your actual frontend URL:
#     allow_origins=["https://yourdomain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,   # Allow cookies/auth headers
    allow_methods=["*"],      # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],      # Allow Authorization, Content-Type, etc.
)

# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================
# Every production API must have a health check endpoint.
# Load balancers and monitoring tools call this to verify the server is alive.
# Returns 200 OK when healthy, which means the server is running.

@app.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Returns server status. Used by load balancers and monitoring.",
)
async def health_check() -> dict:
    """
    Health check endpoint.
    Returns a simple status response when the server is running.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "message": "AI Document Intelligence & RAG Assistant is running",
    }


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/", tags=["System"])
async def root() -> dict:
    """Root endpoint — provides basic API info."""
    return {
        "name": "AI Document Intelligence & RAG Assistant",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# =============================================================================
# NOTE: As we build each phase, we will add:
# - app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# - app.include_router(documents.router, prefix="/documents", tags=["Documents"])
# - app.include_router(chat.router, prefix="/chat", tags=["Chat"])
# =============================================================================
