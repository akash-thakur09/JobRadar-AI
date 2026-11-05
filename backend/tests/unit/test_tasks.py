"""Unit tests for Celery worker tasks."""

import pytest

from app.workers.tasks import smoke_test_task


@pytest.mark.unit
def test_smoke_test_task() -> None:
    """Verify that the Celery smoke-test task executes and returns healthy status."""
    result = smoke_test_task.apply(kwargs={"message": "unit_test_run"}).get()
    assert result["status"] == "healthy"
    assert result["message"] == "unit_test_run"
    assert "task_id" in result
    assert "executed_at" in result
