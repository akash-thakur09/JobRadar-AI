"""Unit tests for Job Discovery REST API routes."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.database.session import get_db_session
from app.main import create_app
from app.modules.discovery.models import DiscoveryRunStatusEnum, JobSourceTypeEnum
from app.modules.discovery.schemas import (
    DiscoveryRunResponse,
    JobSourceResponse,
    PaginatedResponse,
    PaginationMetadata,
    RawJobRecordResponse,
)
from app.modules.discovery.service import DiscoveryService, get_discovery_service


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock(spec=DiscoveryService)


@pytest.fixture
def test_app(mock_service: AsyncMock):
    app = create_app()
    app.dependency_overrides[get_discovery_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return app


@pytest.mark.asyncio
async def test_list_job_sources_endpoint(test_app, mock_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    source_id = uuid.uuid4()
    mock_service.list_sources.return_value = [
        JobSourceResponse(
            id=source_id,
            name="Stripe Greenhouse",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            base_url="https://boards-api.greenhouse.io",
            is_enabled=True,
            polling_interval_minutes=360,
            configuration={"board_token": "stripe"},
            created_at=now,
            updated_at=now,
            latest_run=None,
        )
    ]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/discovery/sources")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Stripe Greenhouse"
    assert data[0]["source_type"] == "GREENHOUSE"


@pytest.mark.asyncio
async def test_create_job_source_endpoint_success(test_app, mock_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    source_id = uuid.uuid4()
    mock_service.create_source.return_value = JobSourceResponse(
        id=source_id,
        name="Netflix Lever",
        source_type=JobSourceTypeEnum.LEVER,
        base_url="https://api.lever.co",
        is_enabled=True,
        polling_interval_minutes=360,
        configuration={"company_id": "netflix"},
        created_at=now,
        updated_at=now,
    )

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/discovery/sources",
            json={
                "name": "Netflix Lever",
                "source_type": "LEVER",
                "base_url": "https://api.lever.co",
                "is_enabled": True,
                "polling_interval_minutes": 360,
                "configuration": {"company_id": "netflix"},
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Netflix Lever"
    assert data["source_type"] == "LEVER"


@pytest.mark.asyncio
async def test_create_job_source_conflict_rfc7807(test_app, mock_service: AsyncMock) -> None:
    mock_service.create_source.side_effect = EntityAlreadyExistsError("JobSource", "Duplicate Name")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/discovery/sources",
            json={
                "name": "Duplicate Name",
                "source_type": "GREENHOUSE",
                "base_url": "https://boards-api.greenhouse.io",
                "configuration": {"board_token": "dup"},
            },
        )

    assert response.status_code == 409
    data = response.json()
    assert data["type"] == "https://api.jobradar.ai/v1/errors/conflict"
    assert "already exists" in data["detail"]


@pytest.mark.asyncio
async def test_get_job_source_not_found_rfc7807(test_app, mock_service: AsyncMock) -> None:
    random_id = uuid.uuid4()
    mock_service.get_source.side_effect = EntityNotFoundError("JobSource", random_id)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/discovery/sources/{random_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["type"] == "https://api.jobradar.ai/v1/errors/not-found"


@pytest.mark.asyncio
async def test_trigger_source_discovery_endpoint(test_app, mock_service: AsyncMock) -> None:
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service.trigger_discovery_for_source.return_value = DiscoveryRunResponse(
        id=run_id,
        job_source_id=source_id,
        started_at=now,
        completed_at=None,
        status=DiscoveryRunStatusEnum.PENDING,
        jobs_discovered=0,
        jobs_created=0,
        jobs_updated=0,
        created_at=now,
    )

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/discovery/sources/{source_id}/discover")

    assert response.status_code == 202
    data = response.json()
    assert data["id"] == str(run_id)
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_trigger_all_discovery_endpoint(test_app, mock_service: AsyncMock) -> None:
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service.trigger_discovery.return_value = [
        DiscoveryRunResponse(
            id=run_id,
            job_source_id=source_id,
            started_at=now,
            status=DiscoveryRunStatusEnum.PENDING,
            jobs_discovered=0,
            jobs_created=0,
            jobs_updated=0,
            created_at=now,
        )
    ]

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/discovery/trigger", json={})

    assert response.status_code == 202
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(run_id)


@pytest.mark.asyncio
async def test_list_discovery_runs_endpoint(test_app, mock_service: AsyncMock) -> None:
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service.list_discovery_runs.return_value = PaginatedResponse[DiscoveryRunResponse](
        items=[
            DiscoveryRunResponse(
                id=run_id,
                job_source_id=source_id,
                started_at=now,
                completed_at=now,
                status=DiscoveryRunStatusEnum.COMPLETED,
                jobs_discovered=10,
                jobs_created=8,
                jobs_updated=2,
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
        response = await client.get("/api/v1/discovery/runs")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["jobs_discovered"] == 10
    assert data["pagination"]["total_items"] == 1


@pytest.mark.asyncio
async def test_list_raw_records_endpoint(test_app, mock_service: AsyncMock) -> None:
    record_id = uuid.uuid4()
    source_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service.list_raw_job_records.return_value = PaginatedResponse[RawJobRecordResponse](
        items=[
            RawJobRecordResponse(
                id=record_id,
                job_source_id=source_id,
                external_job_id="ext-100",
                source_job_url="https://example.com/jobs/100",
                raw_payload={"title": "Engineer"},
                raw_posted_at="2026-11-01",
                payload_hash_sha256="abc123hash",
                processing_status="RAW",
                first_seen_at=now,
                last_seen_at=now,
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
        response = await client.get("/api/v1/discovery/records")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["external_job_id"] == "ext-100"
