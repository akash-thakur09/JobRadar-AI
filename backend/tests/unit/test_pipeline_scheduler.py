"""Unit tests for StandalonePipelineScheduler leader election and configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.pipeline.scheduler import StandalonePipelineScheduler


@pytest.mark.unit
def test_scheduler_enabled_flag_reflects_settings() -> None:
    """StandalonePipelineScheduler.is_enabled reflects application configuration."""
    with patch("app.modules.pipeline.scheduler.get_runtime_settings") as mock_settings:
        mock_settings.return_value.pipeline_scheduler_enabled = False
        scheduler = StandalonePipelineScheduler()
        assert scheduler.is_enabled is False

        mock_settings.return_value.pipeline_scheduler_enabled = True
        scheduler_enabled = StandalonePipelineScheduler()
        assert scheduler_enabled.is_enabled is True


@pytest.mark.unit
async def test_scheduler_tick_standby_when_not_leader() -> None:
    """_execute_tick returns STANDBY when another instance holds leader lock."""
    scheduler = StandalonePipelineScheduler()

    mock_redis = MagicMock()
    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=False)
    mock_redis.lock = MagicMock(return_value=mock_lock)

    with patch("app.modules.pipeline.scheduler.get_redis", return_value=mock_redis):
        result = await scheduler._execute_tick()
        assert result["status"] == "STANDBY"
        mock_lock.acquire.assert_called_once()


@pytest.mark.unit
async def test_scheduler_tick_triggers_task_when_leader() -> None:
    """_execute_tick dispatches Celery periodic task when leader lock is acquired."""
    scheduler = StandalonePipelineScheduler()

    mock_redis = MagicMock()
    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock()
    mock_redis.lock = MagicMock(return_value=mock_lock)

    with (
        patch("app.modules.pipeline.scheduler.get_redis", return_value=mock_redis),
        patch(
            "app.modules.pipeline.scheduler.schedule_candidate_pipeline_runs_task.delay"
        ) as mock_delay,
    ):
        result = await scheduler._execute_tick()
        assert result["status"] == "TRIGGERED"
        mock_delay.assert_called_once()
        mock_lock.release.assert_called_once()
