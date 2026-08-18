"""
File: backend/app/api/dependencies.py
Purpose: Shared FastAPI dependency functions
Why it exists: FastAPI's dependency injection system lets you define reusable
               components (like "get current user" or "get database session")
               that get automatically injected into route handlers.
               This avoids copy-pasting the same code in every endpoint.
Dependencies: Will grow as we add authentication and database layers.
Main responsibilities:
  - Provide database session dependency
  - Provide current authenticated user dependency
  - Provide pagination parameters

Note: This file will be built out in Phase 15 (FastAPI) and Phase 16 (Auth).
      It is created now to establish the correct project structure.
"""

# This file will be populated in Phase 15 and Phase 16.
# For now it exists to make the api package complete.
