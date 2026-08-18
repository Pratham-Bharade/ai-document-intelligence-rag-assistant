"""
File: backend/app/core/logging.py
Purpose: Centralized logging configuration
Why it exists: Every production application needs structured logs.
               Without proper logging you cannot:
               - Debug issues in production
               - Track what the system is doing
               - Monitor errors and performance
               - Understand failure patterns
Dependencies: Python standard library `logging`
Main responsibilities:
  - Set up log format (timestamp, level, module, message)
  - Configure log level based on environment
  - Provide a function to get a named logger for any module
"""

import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """
    Configure the application logging system.
    
    Log levels (from least to most severe):
      DEBUG    → Detailed diagnostic info (only in development)
      INFO     → General operational messages ("User logged in", "Document processed")
      WARNING  → Something unexpected but non-critical
      ERROR    → A failure occurred but the app is still running
      CRITICAL → Severe failure, app may not be able to continue
    
    In development: Show DEBUG and above
    In production: Show INFO and above (DEBUG is too noisy)
    """

    # Determine log level based on environment
    log_level = logging.DEBUG if settings.is_development else logging.INFO

    # Log format: time | level | module:line | message
    # Example: 2026-08-18 14:30:00,123 | INFO     | app.rag.pipeline:87 | RAG pipeline complete
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # StreamHandler: writes logs to stdout (terminal)
            # In production, a separate tool (Datadog, CloudWatch) collects stdout
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence overly verbose third-party loggers
    # These libraries log too much detail that clutters our logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log that logging has been initialized
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized | environment={settings.environment} | level={logging.getLevelName(log_level)}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger for a specific module.
    
    Usage in any module:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processing document: %s", doc_id)
        logger.error("Failed to load PDF: %s", error)
    
    Using __name__ automatically names the logger after the module,
    so you can see exactly which file generated each log message.
    """
    return logging.getLogger(name)
