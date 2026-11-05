"""Unit tests for Job Normalization and Discovery Celery tasks."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.discovery.models import (
    DiscoveryRun,
    DiscoveryRunStatusEnum,
    JobSource,
    JobSourceTypeEnum,
)
from app.modules.jobs.models import Job
from app.modules.jobs.tasks import (
    _async_process_pending_raw_records,
    _async_process_raw_job_record,
    _async_schedule_due_discovery_runs,
)


@pytest.mark.asyncio
async def test_async_process_raw_job_record_success() -> None:
    task = MagicMock()
    record_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = MagicMock(spec=Job)
    mock_job.id = job_id
    mock_job.dedup_fingerprint_sha256 = "dummyfingerprint"

    mock_service = AsyncMock()
    mock_service.process_raw_record.return_value = mock_job

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.jobs.tasks.get_job_service", return_value=mock_service),
        patch("app.modules.jobs.tasks.get_session_factory", return_value=mock_session_factory),
    ):
        result = await _async_process_raw_job_record(task, str(record_id))

    assert result["status"] == "SUCCESS"
    assert result["record_id"] == str(record_id)
    assert result["job_id"] == str(job_id)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_process_raw_job_record_invalid_uuid() -> None:
    task = MagicMock()
    result = await _async_process_raw_job_record(task, "invalid-not-uuid")
    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_uuid"


@pytest.mark.asyncio
async def test_async_process_pending_raw_records_success() -> None:
    mock_service = AsyncMock()
    mock_service.process_pending_records.return_value = 5

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.jobs.tasks.get_job_service", return_value=mock_service),
        patch("app.modules.jobs.tasks.get_session_factory", return_value=mock_session_factory),
    ):
        result = await _async_process_pending_raw_records(batch_size=50)

    assert result["status"] == "SUCCESS"
    assert result["processed_count"] == 5
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_schedule_due_discovery_runs() -> None:
    # Source 1: Due (never run before)
    source1 = JobSource(
        id=uuid.uuid4(),
        name="Source 1",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://api.greenhouse.io",
        configuration={"board_token": "src1"},
        polling_interval_minutes=60,
        is_enabled=True,
    )
    # Source 2: Active running execution (should be skipped)
    source2 = JobSource(
        id=uuid.uuid4(),
        name="Source 2",
        source_type=JobSourceTypeEnum.LEVER,
        base_url="https://api.lever.co",
        configuration={"company_id": "src2"},
        polling_interval_minutes=30,
        is_enabled=True,
    )

    mock_session = AsyncMock()
    # 1. Sources query returns [source1, source2]
    # 2. Source 1 active run query returns None
    # 3. Source 1 latest run query returns None (never executed) -> is_due = True
    # 4. Source 2 active run query returns an active DiscoveryRun(status=RUNNING) -> skipped
    mock_sources_result = MagicMock()
    mock_sources_result.scalars.return_value.all.return_value = [source1, source2]

    mock_no_active_run = MagicMock()
    mock_no_active_run.scalar_one_or_none.return_value = None

    mock_no_latest_run = MagicMock()
    mock_no_latest_run.scalar_one_or_none.return_value = None

    active_run = DiscoveryRun(
        id=uuid.uuid4(),
        job_source_id=source2.id,
        status=DiscoveryRunStatusEnum.RUNNING,
        started_at=datetime.now(UTC),
    )
    mock_has_active_run = MagicMock()
    mock_has_active_run.scalar_one_or_none.return_value = active_run

    mock_session.execute.side_effect = [
        mock_sources_result,  # sources query
        mock_no_active_run,  # source1 active run check
        mock_no_latest_run,  # source1 latest run check
        mock_has_active_run,  # source2 active run check
    ]

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with (
        patch("app.modules.jobs.tasks.get_session_factory", return_value=mock_session_factory),
        patch("app.modules.discovery.tasks.discover_source_jobs_task.delay") as mock_delay,
    ):
        result = await _async_schedule_due_discovery_runs()

    assert result["status"] == "SUCCESS"
    assert result["scheduled_count"] == 1
    assert str(source1.id) in result["scheduled_sources"]
    assert str(source2.id) in result["skipped_active_sources"]
    mock_delay.assert_called_once_with(str(source1.id))
