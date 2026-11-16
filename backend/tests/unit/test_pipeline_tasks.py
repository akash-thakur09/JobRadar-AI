"""Unit tests for Celery pipeline orchestration tasks and candidate scheduling."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.pipeline.enums import PipelineRunStatusEnum
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.tasks import (
    _async_execute_pipeline_run,
    _async_schedule_candidate_pipeline_runs,
)


@pytest.mark.unit
async def test_pipeline_task_invalid_uuid() -> None:
    """_async_execute_pipeline_run handles malformed UUID strings gracefully."""
    mock_task = MagicMock()
    result = await _async_execute_pipeline_run(mock_task, "not-a-valid-uuid")

    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_pipeline_run_uuid"


@pytest.mark.unit
async def test_pipeline_task_successful_execution() -> None:
    """_async_execute_pipeline_run drives orchestration through service."""
    run_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    completed_run = PipelineRun(
        id=run_id,
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.COMPLETED,
        jobs_discovered=10,
        matches_qualified=3,
        resumes_generated=3,
        notifications_sent=3,
    )

    mock_service = MagicMock()
    mock_service.execute_pipeline_run = AsyncMock(return_value=completed_run)

    mock_task = MagicMock()
    mock_session = AsyncMock()

    with (
        patch("app.modules.pipeline.tasks.get_pipeline_service", return_value=mock_service),
        patch("app.modules.pipeline.tasks.get_session_factory") as mock_factory,
    ):
        mock_factory.return_value.__aenter__.return_value = mock_session

        result = await _async_execute_pipeline_run(mock_task, str(run_id))

        assert result["status"] == "COMPLETED"
        assert result["pipeline_run_id"] == str(run_id)
        assert result["jobs_discovered"] == 10
        assert result["matches_qualified"] == 3


@pytest.mark.unit
async def test_schedule_candidate_runs_when_disabled() -> None:
    """_async_schedule_candidate_pipeline_runs exits as SKIPPED when scheduler disabled."""
    mock_task = MagicMock()
    with patch("app.modules.pipeline.tasks.get_settings") as mock_settings:
        mock_settings.return_value.pipeline_scheduler_enabled = False

        result = await _async_schedule_candidate_pipeline_runs(mock_task)

        assert result["status"] == "SKIPPED"
        assert result["reason"] == "scheduler_disabled"
