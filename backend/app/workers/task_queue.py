"""
File: backend/app/workers/task_queue.py
Purpose: Asynchronous Task Queue, Status Tracking, and Background Job Dispatcher.
Why it exists: Large document ingestion (extracting 500 pages, running OCR, computing 2,000 vector embeddings)
               takes 10 to 60+ seconds. Running this synchronously inside an HTTP request causes gateway timeouts (504).
               The Task Queue offloads work to asynchronous workers and provides real-time progress tracking.
"""

import json
import logging
import threading
import uuid
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskQueueManager:
    """
    Manages task dispatching and state tracking using Redis with an in-memory fallback.
    """
    def __init__(self, redis_url: Optional[str] = None):
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None

        if redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info("Connected to Redis for Task Queue.")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}), using in-memory task store.")
                self._redis_client = None

    def create_task(self, task_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Initializes a new task in QUEUED state."""
        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.QUEUED.value,
            "progress": 0,
            "result": None,
            "error": None,
            "metadata": metadata or {}
        }
        self._save_task(task_id, task_data)
        return task_id

    def update_progress(self, task_id: str, progress: int, status: TaskStatus = TaskStatus.PROCESSING) -> None:
        """Updates the numeric progress percentage (0-100) and status."""
        task = self.get_task(task_id)
        if task:
            task["progress"] = max(0, min(100, progress))
            task["status"] = status.value
            self._save_task(task_id, task)

    def mark_completed(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Marks task as successfully completed."""
        task = self.get_task(task_id)
        if task:
            task["status"] = TaskStatus.COMPLETED.value
            task["progress"] = 100
            task["result"] = result
            self._save_task(task_id, task)

    def mark_failed(self, task_id: str, error_message: str) -> None:
        """Marks task as failed with error details."""
        task = self.get_task(task_id)
        if task:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = error_message
            self._save_task(task_id, task)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves task state."""
        if self._redis_client:
            try:
                raw = self._redis_client.get(f"task:{task_id}")
                return json.loads(raw) if raw else None
            except Exception:
                pass
        return self._memory_store.get(task_id)

    def _save_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        if self._redis_client:
            try:
                # Store with 24 hour expiration
                self._redis_client.setex(f"task:{task_id}", 86400, json.dumps(task_data))
            except Exception:
                pass
        self._memory_store[task_id] = task_data

    def dispatch_async(self, func: Callable, *args, **kwargs) -> str:
        """
        Dispatches a callable in a background worker thread.
        Returns the unique task ID immediately.
        """
        task_id = self.create_task(task_type=func.__name__)
        
        def runner():
            try:
                self.update_progress(task_id, 10, TaskStatus.PROCESSING)
                result = func(*args, task_id=task_id, **kwargs)
                self.mark_completed(task_id, result=result)
            except Exception as e:
                logger.exception(f"Background task {task_id} failed: {e}")
                self.mark_failed(task_id, error_message=str(e))

        worker_thread = threading.Thread(target=runner, daemon=True)
        worker_thread.start()
        return task_id


# Global singleton task queue
task_queue = TaskQueueManager()
