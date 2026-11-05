"""Unit tests for Tailored Resumes API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.exceptions import EntityNotFoundError
from app.main import create_app
from app.modules.candidate.models import CandidateProfile
from app.modules.candidate.service import get_candidate_service
from app.modules.resumes.schemas import PaginationMetadata
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.exceptions import TailoringError
from app.modules.tailoring.models import TailoredResume
from app.modules.tailoring.service import get_tailoring_service


@pytest.fixture
def mock_tailoring_service() -> MagicMock:
    """Fixture providing mock TailoringService."""
    return MagicMock()


@pytest.fixture
def mock_candidate_service() -> MagicMock:
    """Fixture providing mock CandidateService."""
    service = MagicMock()
    service.get_profile = AsyncMock(
        return_value=CandidateProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            full_name="Tester",
        )
    )
    return service


@pytest.fixture
def client(
    mock_tailoring_service: MagicMock, mock_candidate_service: MagicMock
) -> httpx.AsyncClient:
    """Async test client with dependency overrides."""
    app = create_app()
    app.dependency_overrides[get_tailoring_service] = lambda: mock_tailoring_service
    app.dependency_overrides[get_candidate_service] = lambda: mock_candidate_service
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
async def test_create_tailored_resume_endpoint_success(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """POST /api/v1/tailored-resumes returns 202 Accepted with summary."""
    match_id = uuid.uuid4()
    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=match_id,
        resume_version_id=uuid.uuid4(),
        rendering_strategy=RenderingStrategyEnum.FALLBACK,
        generation_status=TailoredResumeStatusEnum.PENDING,
        generation_attempts=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_tailoring_service.request_tailoring = AsyncMock(return_value=record)

    response = await client.post("/api/v1/tailored-resumes", json={"job_match_id": str(match_id)})

    assert response.status_code == 202
    data = response.json()
    assert data["id"] == str(record.id)
    assert data["generation_status"] == "PENDING"


@pytest.mark.unit
async def test_create_tailored_resume_invalid_uuid(client: httpx.AsyncClient):
    """POST /api/v1/tailored-resumes with malformed UUID returns 422."""
    response = await client.post("/api/v1/tailored-resumes", json={"job_match_id": "not-a-uuid"})
    assert response.status_code == 422


@pytest.mark.unit
async def test_create_tailored_resume_not_found(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """POST /api/v1/tailored-resumes for non-existent match returns 404 RFC 7807."""
    mock_tailoring_service.request_tailoring = AsyncMock(
        side_effect=EntityNotFoundError("JobMatch", "some-id")
    )
    response = await client.post(
        "/api/v1/tailored-resumes", json={"job_match_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["title"].lower() or "not found" in data["detail"].lower()


@pytest.mark.unit
async def test_create_tailored_resume_unqualified(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """POST /api/v1/tailored-resumes for unqualified match returns 400 RFC 7807."""
    mock_tailoring_service.request_tailoring = AsyncMock(
        side_effect=TailoringError("JobMatch is not qualified", status_code=400)
    )
    response = await client.post(
        "/api/v1/tailored-resumes", json={"job_match_id": str(uuid.uuid4())}
    )
    assert response.status_code == 400


@pytest.mark.unit
async def test_get_tailored_resume_endpoint_success(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """GET /api/v1/tailored-resumes/{id} returns 200 with details."""
    resume_id = uuid.uuid4()
    record = TailoredResume(
        id=resume_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        resume_version_id=uuid.uuid4(),
        rendering_strategy=RenderingStrategyEnum.FALLBACK,
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        tailored_content={"headline": "Backend Engineer"},
        validation_metadata={"is_valid": True},
        generation_attempts=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_tailoring_service.get_tailored_resume = AsyncMock(return_value=record)

    response = await client.get(f"/api/v1/tailored-resumes/{resume_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(resume_id)
    assert data["generation_status"] == "COMPLETED"
    assert data["tailored_content"]["headline"] == "Backend Engineer"


@pytest.mark.unit
async def test_get_tailored_resume_endpoint_not_found(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """GET /api/v1/tailored-resumes/{id} for non-existent ID returns 404."""
    mock_tailoring_service.get_tailored_resume = AsyncMock(
        side_effect=EntityNotFoundError("TailoredResume", "test-id")
    )
    response = await client.get(f"/api/v1/tailored-resumes/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.unit
async def test_download_tailored_resume_endpoint_success(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """GET /api/v1/tailored-resumes/{id}/download returns PDF binary with attachment header."""
    resume_id = uuid.uuid4()
    dummy_pdf = b"%PDF-1.4 test binary stream"
    mock_tailoring_service.download_tailored_pdf = AsyncMock(
        return_value=(dummy_pdf, "Tailored_Resume.pdf", "application/pdf")
    )

    response = await client.get(f"/api/v1/tailored-resumes/{resume_id}/download")

    assert response.status_code == 200
    assert response.content == dummy_pdf
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "Tailored_Resume.pdf" in response.headers["content-disposition"]


@pytest.mark.unit
async def test_download_tailored_resume_not_completed(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """GET /api/v1/tailored-resumes/{id}/download before completion returns 400."""
    mock_tailoring_service.download_tailored_pdf = AsyncMock(
        side_effect=TailoringError("Tailored resume is not ready for download", status_code=400)
    )
    response = await client.get(f"/api/v1/tailored-resumes/{uuid.uuid4()}/download")
    assert response.status_code == 400


@pytest.mark.unit
async def test_list_tailored_resumes_endpoint(
    client: httpx.AsyncClient, mock_tailoring_service: MagicMock
):
    """GET /api/v1/tailored-resumes returns paginated envelope."""
    record = TailoredResume(
        id=uuid.uuid4(),
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        resume_version_id=uuid.uuid4(),
        rendering_strategy=RenderingStrategyEnum.FALLBACK,
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        generation_attempts=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    pagination = PaginationMetadata(
        page=1,
        page_size=20,
        total_items=1,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )
    mock_tailoring_service.list_tailored_resumes = AsyncMock(return_value=([record], pagination))

    response = await client.get("/api/v1/tailored-resumes")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 1
    assert data["pagination"]["total_items"] == 1
