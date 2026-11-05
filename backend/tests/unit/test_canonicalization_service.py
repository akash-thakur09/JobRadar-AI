"""Unit tests for Job Canonicalization and Normalization Service."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.exceptions import JobNotFoundError
from app.modules.jobs.models import (
    Job,
    JobProcessingStatusEnum,
    JobSourceRecord,
    JobStatusEnum,
)
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.service import JobService


@pytest.fixture
def mock_job_repo() -> AsyncMock:
    return AsyncMock(spec=JobRepository)


@pytest.fixture
def job_service(mock_job_repo: AsyncMock) -> JobService:
    return JobService(repository=mock_job_repo)


def _make_source() -> JobSource:
    return JobSource(
        id=uuid.uuid4(),
        name="Stripe Greenhouse",
        source_type=JobSourceTypeEnum.GREENHOUSE,
        base_url="https://boards.greenhouse.io",
        configuration={"company_name": "Stripe"},
        is_enabled=True,
    )


def _make_raw_record(source: JobSource) -> JobSourceRecord:
    now = datetime.now(UTC)
    record = JobSourceRecord(
        id=uuid.uuid4(),
        job_source_id=source.id,
        external_job_id="gh-123",
        source_job_url="https://boards.greenhouse.io/stripe/jobs/123",
        raw_payload={
            "id": 123,
            "title": "Senior Backend Engineer",
            "content": "<p>Build APIs</p>",
            "location": {"name": "Remote"},
        },
        payload_hash_sha256="hash123",
        processing_status="RAW",
        first_seen_at=now,
        last_seen_at=now,
    )
    record.job_source = source
    return record


@pytest.mark.asyncio
async def test_process_raw_record_creates_new_canonical_job(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    record = _make_raw_record(source)

    mock_job_repo.get_source_record_by_id.return_value = record
    mock_job_repo.get_job_by_fingerprint.return_value = None

    created_job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Stripe",
        title="Senior Backend Engineer",
        canonical_application_url="https://boards.greenhouse.io/stripe/jobs/123",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.UNKNOWN,
        description_text="Build APIs",
        dedup_fingerprint_sha256="dummyfingerprint1234567890",
        status=JobStatusEnum.DISCOVERED,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    mock_job_repo.create_job.return_value = created_job

    session = AsyncMock()
    result = await job_service.process_raw_record(session, record.id)

    assert result == created_job
    mock_job_repo.create_job.assert_awaited_once()
    # Check that record was updated to CANONICALIZED and linked to job.id
    mock_job_repo.update_source_record.assert_awaited()
    last_update_call = mock_job_repo.update_source_record.await_args_list[-1]
    assert last_update_call[0][2]["job_id"] == created_job.id
    assert (
        last_update_call[0][2]["processing_status"] == JobProcessingStatusEnum.CANONICALIZED.value
    )


@pytest.mark.asyncio
async def test_process_raw_record_deduplicates_existing_canonical_job(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    record = _make_raw_record(source)

    existing_job = Job(
        id=uuid.uuid4(),
        canonical_company_name="Stripe",
        title="Senior Backend Engineer",
        canonical_application_url="https://boards.greenhouse.io/stripe/jobs/123",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.UNKNOWN,
        description_text="Old description text",
        dedup_fingerprint_sha256="dummyfingerprint1234567890",
        status=JobStatusEnum.ARCHIVED,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    mock_job_repo.get_source_record_by_id.return_value = record
    mock_job_repo.get_job_by_fingerprint.return_value = existing_job
    mock_job_repo.update_job.return_value = existing_job

    session = AsyncMock()
    result = await job_service.process_raw_record(session, record.id)

    assert result == existing_job
    mock_job_repo.create_job.assert_not_awaited()
    mock_job_repo.update_job.assert_awaited_once()

    # Verify update arguments: archived job revived to DISCOVERED and description updated
    update_data = mock_job_repo.update_job.await_args_list[0][0][2]
    assert update_data["status"] == JobStatusEnum.DISCOVERED
    assert update_data["description_text"] == "Build APIs"
    assert "last_seen_at" in update_data


@pytest.mark.asyncio
async def test_process_raw_record_already_canonicalized_returns_existing(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    record = _make_raw_record(source)
    canonical_job_id = uuid.uuid4()
    record.processing_status = JobProcessingStatusEnum.CANONICALIZED.value
    record.job_id = canonical_job_id

    existing_job = Job(
        id=canonical_job_id,
        canonical_company_name="Stripe",
        title="Senior Backend Engineer",
        canonical_application_url="https://boards.greenhouse.io/stripe/jobs/123",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.UNKNOWN,
        description_text="Build APIs",
        dedup_fingerprint_sha256="dummyfingerprint",
        status=JobStatusEnum.DISCOVERED,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    mock_job_repo.get_source_record_by_id.return_value = record
    mock_job_repo.get_job_by_id.return_value = existing_job

    session = AsyncMock()
    result = await job_service.process_raw_record(session, record.id)

    assert result == existing_job
    mock_job_repo.create_job.assert_not_awaited()
    mock_job_repo.update_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_raw_record_not_found(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    mock_job_repo.get_source_record_by_id.return_value = None
    session = AsyncMock()
    result = await job_service.process_raw_record(session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_process_raw_record_handles_failure(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    source.source_type = JobSourceTypeEnum.CAREER_PAGE  # Will trigger ValueError in registry
    record = _make_raw_record(source)

    mock_job_repo.get_source_record_by_id.return_value = record

    session = AsyncMock()
    with pytest.raises(ValueError):
        await job_service.process_raw_record(session, record.id)

    # Check that status was marked as FAILED with error message
    last_update = mock_job_repo.update_source_record.await_args_list[-1]
    assert last_update[0][2]["processing_status"] == JobProcessingStatusEnum.FAILED.value
    assert "No job normalizer registered" in last_update[0][2]["processing_error"]


@pytest.mark.asyncio
async def test_process_pending_records_batch(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    rec1 = _make_raw_record(source)
    rec2 = _make_raw_record(source)

    mock_job_repo.get_pending_source_records.return_value = [rec1, rec2]

    # Mock process_raw_record
    job_service.process_raw_record = AsyncMock(
        side_effect=[MagicMock(spec=Job), MagicMock(spec=Job)]
    )  # type: ignore[method-assign]

    session = AsyncMock()
    processed_count = await job_service.process_pending_records(session, batch_size=50)

    assert processed_count == 2
    mock_job_repo.get_pending_source_records.assert_awaited_once_with(session, limit=50)


@pytest.mark.asyncio
async def test_get_job_success_and_not_found(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        canonical_company_name="Stripe",
        title="Software Engineer",
        canonical_application_url="https://stripe.com/jobs/1",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        description_text="Build payments",
        dedup_fingerprint_sha256="abcd" * 16,
        status=JobStatusEnum.DISCOVERED,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    job.source_records = []

    mock_job_repo.get_job_by_id.return_value = job

    session = AsyncMock()
    detail = await job_service.get_job(session, job_id)
    assert detail.id == job_id
    assert detail.canonical_company_name == "Stripe"
    assert detail.source_count == 0

    mock_job_repo.get_job_by_id.return_value = None
    with pytest.raises(JobNotFoundError):
        await job_service.get_job(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_list_jobs_pagination(job_service: JobService, mock_job_repo: AsyncMock) -> None:
    job = Job(
        id=uuid.uuid4(),
        canonical_company_name="GitHub",
        title="Developer Advocate",
        canonical_application_url="https://github.com/jobs/1",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        employment_type=EmploymentTypeEnum.FULL_TIME,
        description_text="Developer relations",
        dedup_fingerprint_sha256="1234" * 16,
        status=JobStatusEnum.DISCOVERED,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    job.source_records = []

    mock_job_repo.list_jobs.return_value = ([job], 1)

    session = AsyncMock()
    response = await job_service.list_jobs(session, search="GitHub", page=1, page_size=10)

    assert len(response.items) == 1
    assert response.pagination.total_items == 1
    assert response.pagination.total_pages == 1
    assert not response.pagination.has_next
    assert not response.pagination.has_prev


@pytest.mark.asyncio
async def test_process_pending_records_skips_failed_items(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    source = _make_source()
    rec1 = _make_raw_record(source)
    rec2 = _make_raw_record(source)

    mock_job_repo.get_pending_source_records.return_value = [rec1, rec2]
    # First fails with RuntimeError, second succeeds
    job_service.process_raw_record = AsyncMock(  # type: ignore[method-assign]
        side_effect=[RuntimeError("Network blip"), MagicMock(spec=Job)]
    )

    session = AsyncMock()
    processed_count = await job_service.process_pending_records(session, batch_size=10)
    assert processed_count == 1


@pytest.mark.asyncio
async def test_get_job_sources_success_and_not_found(
    job_service: JobService, mock_job_repo: AsyncMock
) -> None:
    job_id = uuid.uuid4()
    source = _make_source()
    rec = _make_raw_record(source)
    rec.job_id = job_id
    rec.created_at = datetime.now(UTC)

    mock_job_repo.get_job_by_id.return_value = MagicMock(spec=Job)
    mock_job_repo.get_source_records_for_job.return_value = [rec]

    session = AsyncMock()
    sources = await job_service.get_job_sources(session, job_id)
    assert len(sources) == 1
    assert sources[0].external_job_id == rec.external_job_id

    mock_job_repo.get_job_by_id.return_value = None
    with pytest.raises(JobNotFoundError):
        await job_service.get_job_sources(session, uuid.uuid4())


def test_get_job_service_factory() -> None:
    from app.modules.jobs.service import get_job_service

    svc = get_job_service()
    assert isinstance(svc, JobService)
