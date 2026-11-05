"""Unit tests for Canonical Jobs API routes."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db_session
from app.main import create_app
from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.jobs.exceptions import JobNotFoundError
from app.modules.jobs.models import JobStatusEnum
from app.modules.jobs.schemas import (
    JobDetailResponse,
    JobSourceRecordResponse,
    JobSummaryResponse,
    PaginatedResponse,
    PaginationMetadata,
)
from app.modules.jobs.service import JobService, get_job_service


@pytest.fixture
def mock_job_service() -> AsyncMock:
    return AsyncMock(spec=JobService)


@pytest.fixture
def test_app(mock_job_service: AsyncMock):
    app = create_app()
    app.dependency_overrides[get_job_service] = lambda: mock_job_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return app


@pytest.mark.asyncio
async def test_list_jobs_endpoint(test_app, mock_job_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    job_id = uuid.uuid4()

    mock_job_service.list_jobs.return_value = PaginatedResponse[JobSummaryResponse](
        items=[
            JobSummaryResponse(
                id=job_id,
                canonical_company_name="Google",
                title="Staff AI Engineer",
                canonical_application_url="https://careers.google.com/jobs/1",
                workplace_type=WorkplaceTypeEnum.HYBRID,
                normalized_location="Mountain View, CA",
                employment_type=EmploymentTypeEnum.FULL_TIME,
                posted_at=now,
                first_seen_at=now,
                last_seen_at=now,
                status=JobStatusEnum.DISCOVERED,
                created_at=now,
            )
        ],
        pagination=PaginationMetadata(
            page=1,
            page_size=20,
            total_items=1,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/jobs?search=Google&workplace_type=HYBRID")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["canonical_company_name"] == "Google"
    assert data["pagination"]["total_items"] == 1


@pytest.mark.asyncio
async def test_get_job_endpoint_success(test_app, mock_job_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()

    mock_job_service.get_job.return_value = JobDetailResponse(
        id=job_id,
        canonical_company_name="Stripe",
        title="Senior Backend Engineer",
        canonical_application_url="https://stripe.com/jobs/1",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        normalized_location="Remote",
        employment_type=EmploymentTypeEnum.FULL_TIME,
        posted_at=now,
        first_seen_at=now,
        last_seen_at=now,
        status=JobStatusEnum.DISCOVERED,
        created_at=now,
        description_text="Build global payments infrastructure.",
        dedup_fingerprint_sha256="abcd" * 16,
        source_count=1,
        sources=[
            JobSourceRecordResponse(
                id=uuid.uuid4(),
                job_id=job_id,
                job_source_id=source_id,
                external_job_id="gh-123",
                source_job_url="https://boards.greenhouse.io/stripe/jobs/123",
                raw_payload={"title": "Senior Backend Engineer"},
                payload_hash_sha256="hash123",
                processing_status="CANONICALIZED",
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
            )
        ],
    )

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job_id)
    assert data["canonical_company_name"] == "Stripe"
    assert "global payments infrastructure" in data["description_text"]
    assert data["source_count"] == 1


@pytest.mark.asyncio
async def test_get_job_endpoint_not_found(test_app, mock_job_service: AsyncMock) -> None:
    job_id = uuid.uuid4()
    mock_job_service.get_job.side_effect = JobNotFoundError(job_id)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == 404
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_job_sources_endpoint(test_app, mock_job_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()

    mock_job_service.get_job_sources.return_value = [
        JobSourceRecordResponse(
            id=uuid.uuid4(),
            job_id=job_id,
            job_source_id=source_id,
            external_job_id="gh-123",
            source_job_url="https://boards.greenhouse.io/stripe/jobs/123",
            raw_payload={"title": "Senior Backend Engineer"},
            payload_hash_sha256="hash123",
            processing_status="CANONICALIZED",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
        )
    ]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/jobs/{job_id}/sources")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["external_job_id"] == "gh-123"


@pytest.mark.asyncio
async def test_process_pending_jobs_endpoint(test_app, mock_job_service: AsyncMock) -> None:
    mock_job_service.process_pending_records.return_value = 12

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/jobs/process-pending?batch_size=50")

    assert response.status_code == 200
    data = response.json()
    assert data["processed_count"] == 12
    assert "Successfully processed 12" in data["message"]
