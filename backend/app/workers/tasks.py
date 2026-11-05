"""Celery worker task definitions."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.smoke_test_task", bind=True)
def smoke_test_task(self: Any, message: str = "smoke_test") -> dict[str, Any]:
    """Minimal baseline smoke-test task verifying worker connectivity."""
    task_id = getattr(getattr(self, "request", None), "id", "local-exec")
    logger.info("Executing smoke test task: %s (task_id=%s)", message, task_id)
    return {
        "status": "healthy",
        "task_id": str(task_id),
        "message": message,
        "executed_at": datetime.now(UTC).isoformat(),
    }
