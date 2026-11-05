"""Unit tests for asynchronous discovery Celery background tasks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.discovery.adapters.base import DiscoveryResult, RawDiscoveredJob
from app.modules.discovery.exceptions import (
    InvalidSourceConfigError,
    RateLimitExceededError,
)
from app.modules.discovery.models import (
    DiscoveryRun,
    DiscoveryRunStatusEnum,
    JobSource,
    JobSourceTypeEnum,
)
from app.modules.discovery.tasks import _async_discover_source_jobs


@pytest.mark.asyncio
async def test_async_discover_source_jobs_success() -> None:
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mock_source = JobSource(
        id=source_id,
        name="Test Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        is_enabled=True,
        configuration={"board_token": "testco"},
    )
    mock_run = DiscoveryRun(
        id=run_id,
        job_source_id=source_id,
        status=DiscoveryRunStatusEnum.RUNNING,
    )

    discovered_job = RawDiscoveredJob(
        external_id="101",
        source_url="https://boards.greenhouse.io/testco/jobs/101",
        raw_payload={"id": 101, "title": "Software Engineer"},
        raw_posted_at="2026-11-01",
    )
    mock_result = DiscoveryResult(
        source_identifier="testco",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        jobs=[discovered_job],
    )

    mock_task = MagicMock()
    mock_task.request.retries = 0

    with (
        patch("app.modules.discovery.tasks.DiscoveryRepository") as MockRepoClass,
        patch("app.modules.discovery.tasks.get_adapter_for_source_type") as mock_get_adapter,
        patch("app.modules.discovery.tasks.get_session_factory") as mock_factory,
    ):
        mock_repo = MockRepoClass.return_value
        mock_repo.get_source_by_id = AsyncMock(return_value=mock_source)
        mock_repo.create_discovery_run = AsyncMock(return_value=mock_run)
        mock_repo.get_discovery_run_by_id = AsyncMock(return_value=mock_run)
        mock_repo.persist_discovered_jobs = AsyncMock(return_value=(1, 0))
        mock_repo.update_discovery_run = AsyncMock(return_value=mock_run)

        mock_adapter = MagicMock()
        mock_adapter.validate_configuration = MagicMock()
        mock_adapter.discover_jobs = AsyncMock(return_value=mock_result)
        mock_get_adapter.return_value = mock_adapter

        mock_session = AsyncMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        result = await _async_discover_source_jobs(mock_task, str(source_id))

    assert result["status"] == "COMPLETED"
    assert result["jobs_discovered"] == 1
    assert result["jobs_created"] == 1
    assert result["jobs_updated"] == 0


@pytest.mark.asyncio
async def test_async_discover_source_jobs_retryable_failure() -> None:
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mock_source = JobSource(
        id=source_id,
        name="Rate Limited Source",
        source_type=JobSourceTypeEnum.LEVER,
        base_url="https://api.lever.co",
        is_enabled=True,
        configuration={"company_id": "limited"},
    )
    mock_run = DiscoveryRun(
        id=run_id,
        job_source_id=source_id,
        status=DiscoveryRunStatusEnum.RUNNING,
    )

    mock_task = MagicMock()
    mock_task.request.retries = 0
    mock_task.retry.side_effect = RuntimeError("RetryTriggered")

    with (
        patch("app.modules.discovery.tasks.DiscoveryRepository") as MockRepoClass,
        patch("app.modules.discovery.tasks.get_adapter_for_source_type") as mock_get_adapter,
        patch("app.modules.discovery.tasks.get_session_factory") as mock_factory,
        patch(
            "app.modules.discovery.tasks._record_run_failure", new_callable=AsyncMock
        ) as mock_record_fail,
    ):
        mock_repo = MockRepoClass.return_value
        mock_repo.get_source_by_id = AsyncMock(return_value=mock_source)
        mock_repo.create_discovery_run = AsyncMock(return_value=mock_run)

        mock_adapter = MagicMock()
        mock_adapter.validate_configuration = MagicMock()
        mock_adapter.discover_jobs = AsyncMock(
            side_effect=RateLimitExceededError("Lever", retry_after=30)
        )
        mock_get_adapter.return_value = mock_adapter

        mock_session = AsyncMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with pytest.raises(RuntimeError, match="RetryTriggered"):
            await _async_discover_source_jobs(mock_task, str(source_id))

        mock_record_fail.assert_awaited_once()
        mock_task.retry.assert_called_once()


@pytest.mark.asyncio
async def test_async_discover_source_jobs_non_retryable_config_failure() -> None:
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mock_source = JobSource(
        id=source_id,
        name="Bad Config Source",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards-api.greenhouse.io",
        is_enabled=True,
        configuration={"bad": "config"},
    )
    mock_run = DiscoveryRun(
        id=run_id,
        job_source_id=source_id,
        status=DiscoveryRunStatusEnum.RUNNING,
    )

    mock_task = MagicMock()
    mock_task.request.retries = 0

    with (
        patch("app.modules.discovery.tasks.DiscoveryRepository") as MockRepoClass,
        patch("app.modules.discovery.tasks.get_adapter_for_source_type") as mock_get_adapter,
        patch("app.modules.discovery.tasks.get_session_factory") as mock_factory,
        patch(
            "app.modules.discovery.tasks._record_run_failure", new_callable=AsyncMock
        ) as mock_record_fail,
    ):
        mock_repo = MockRepoClass.return_value
        mock_repo.get_source_by_id = AsyncMock(return_value=mock_source)
        mock_repo.create_discovery_run = AsyncMock(return_value=mock_run)

        mock_adapter = MagicMock()
        mock_adapter.validate_configuration.side_effect = InvalidSourceConfigError(
            "Missing board token"
        )
        mock_get_adapter.return_value = mock_adapter

        mock_session = AsyncMock()
        mock_factory.return_value = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        result = await _async_discover_source_jobs(mock_task, str(source_id))

    assert result["status"] == "FAILED"
    mock_record_fail.assert_awaited_once()
    mock_task.retry.assert_not_called()
