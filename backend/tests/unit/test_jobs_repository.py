"""Unit tests for JobRepository database access functions."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.models import (
    Job,
    JobSourceRecord,
    JobStatusEnum,
)
from app.modules.jobs.repository import JobRepository


@pytest.fixture
def repo() -> JobRepository:
    return JobRepository()


@pytest.mark.asyncio
async def test_repo_get_job_by_fingerprint(repo: JobRepository) -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    dummy_job = MagicMock(spec=Job)
    mock_result.scalar_one_or_none.return_value = dummy_job
    session.execute.return_value = mock_result

    job = await repo.get_job_by_fingerprint(session, "test-fingerprint")
    assert job == dummy_job
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repo_list_jobs_with_filters(repo: JobRepository) -> None:
    session = AsyncMock()
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1

    mock_items_result = MagicMock()
    dummy_job = MagicMock(spec=Job)
    mock_items_result.scalars.return_value.all.return_value = [dummy_job]

    session.execute.side_effect = [mock_count_result, mock_items_result]

    jobs, total = await repo.list_jobs(
        session,
        search="Software",
        status=JobStatusEnum.DISCOVERED,
        workplace_type=WorkplaceTypeEnum.REMOTE,
        page=1,
        page_size=10,
    )

    assert total == 1
    assert jobs == [dummy_job]
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_repo_get_source_records_for_job(repo: JobRepository) -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    dummy_record = MagicMock(spec=JobSourceRecord)
    mock_result.scalars.return_value.all.return_value = [dummy_record]
    session.execute.return_value = mock_result

    job_id = uuid.uuid4()
    records = await repo.get_source_records_for_job(session, job_id)
    assert records == [dummy_record]


@pytest.mark.asyncio
async def test_repo_get_pending_source_records(repo: JobRepository) -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    dummy_record = MagicMock(spec=JobSourceRecord)
    mock_result.scalars.return_value.all.return_value = [dummy_record]
    session.execute.return_value = mock_result

    pending = await repo.get_pending_source_records(session, limit=25)
    assert pending == [dummy_record]


@pytest.mark.asyncio
async def test_repo_update_source_record(repo: JobRepository) -> None:
    session = AsyncMock()
    record = JobSourceRecord(
        id=uuid.uuid4(),
        job_source_id=uuid.uuid4(),
        external_job_id="test-1",
        source_job_url="https://example.com",
        raw_payload={},
        payload_hash_sha256="hash",
        processing_status="RAW",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    updated = await repo.update_source_record(
        session, record, {"processing_status": "CANONICALIZED", "processing_error": None}
    )
    assert updated.processing_status == "CANONICALIZED"
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(record)
