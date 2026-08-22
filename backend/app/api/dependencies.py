"""
File: backend/app/api/dependencies.py
Purpose: FastAPI Dependencies for Database Sessions, Current User Auth, and RAG Pipeline.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.rag.pipeline import RAGPipeline

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


import logging
import os

logger = logging.getLogger(__name__)

# Global RAG Pipeline Singleton
_pipeline_instance: Optional[RAGPipeline] = None


def _rehydrate_pipeline_from_db(pipeline: RAGPipeline) -> None:
    """Restores all processed documents and vector embeddings from disk on server startup."""
    from app.db.session import SessionLocal
    from app.models.document import Document

    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.status == "processed").all()
        for doc in docs:
            if doc.file_path and os.path.exists(doc.file_path):
                # Verify not already loaded
                already_loaded = any(
                    c.get("metadata", {}).get("document_id") == doc.id
                    for c in pipeline.vector_store.chunks
                )
                if not already_loaded:
                    try:
                        logger.info(f"Rehydrating knowledge base document: {doc.title} ({doc.id})")
                        pipeline.ingest_pdf(
                            file_path=doc.file_path,
                            document_id=doc.id,
                            custom_metadata={"title": doc.title, "filename": doc.filename}
                        )
                    except Exception as e:
                        logger.warning(f"Could not rehydrate document {doc.id}: {e}")
    except Exception as e:
        logger.warning(f"Database rehydration failed: {e}")
    finally:
        db.close()


def get_rag_pipeline() -> RAGPipeline:
    """Provides a shared RAGPipeline instance, automatically rehydrating on startup."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
        _rehydrate_pipeline_from_db(_pipeline_instance)
    return _pipeline_instance


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Decodes the JWT Bearer token and returns the authenticated User instance.
    Raises HTTP 401 Unauthorized if the token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    RBAC dependency requiring the user to have superuser/admin privileges.
    Raises HTTP 403 Forbidden if user is not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have adequate administrative privileges."
        )
    return current_user
