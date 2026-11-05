"""Unit tests for Candidate-Job Matching REST API routes."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import EntityNotFoundError
from app.database.session import get_db_session
from app.main import create_app
from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.schemas import PaginatedResponse, PaginationMetadata
from app.modules.matching.models import EligibilityStatusEnum
from app.modules.matching.schemas import (
    JobMatchDetailResponse,
    JobMatchSummaryResponse,
)
from app.modules.matching.service import MatchingService, get_matching_service


@pytest.fixture
def mock_matching_service() -> AsyncMock:
    return AsyncMock(spec=MatchingService)


@pytest.fixture
def test_app(mock_matching_service: AsyncMock):
    app = create_app()
    app.dependency_overrides[get_matching_service] = lambda: mock_matching_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return app


@pytest.mark.asyncio
async def test_list_matches_endpoint(test_app, mock_matching_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    match_id = uuid.uuid4()
    job_id = uuid.uuid4()
    cand_id = uuid.uuid4()

    mock_matching_service.list_matches.return_value = PaginatedResponse[JobMatchSummaryResponse](
        items=[
            JobMatchSummaryResponse(
                id=match_id,
                job_id=job_id,
                candidate_profile_id=cand_id,
                eligibility_status=EligibilityStatusEnum.ELIGIBLE,
                deterministic_score=Decimal("88.00"),
                semantic_score=None,
                final_score=Decimal("88.00"),
                skill_score=Decimal("35.00"),
                experience_score=Decimal("20.00"),
                title_score=Decimal("15.00"),
                preference_score=Decimal("15.00"),
                match_explanation="Strong match on core skills",
                created_at=now,
                updated_at=now,
                job_title="Staff Backend Engineer",
                company_name="Stripe",
                workplace_type=WorkplaceTypeEnum.REMOTE,
                normalized_location="San Francisco, CA",
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

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/matches?min_score=80.0&eligibility=ELIGIBLE")

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total_items"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == str(match_id)
    assert item["job_title"] == "Staff Backend Engineer"
    assert item["deterministic_score"] == "88.00"
    assert item["eligibility_status"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_get_match_detail_success(test_app, mock_matching_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    match_id = uuid.uuid4()
    job_id = uuid.uuid4()
    cand_id = uuid.uuid4()

    mock_matching_service.get_match.return_value = JobMatchDetailResponse(
        id=match_id,
        job_id=job_id,
        candidate_profile_id=cand_id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("92.50"),
        semantic_score=None,
        final_score=Decimal("92.50"),
        skill_score=Decimal("40.00"),
        experience_score=Decimal("20.00"),
        title_score=Decimal("15.00"),
        preference_score=Decimal("15.00"),
        match_explanation="Perfect match across all vectors.",
        match_explanation_details={"total": 92.5},
        created_at=now,
        updated_at=now,
        job_title="Principal Engineer",
        company_name="Netflix",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        normalized_location="Los Gatos, CA",
        job=None,
    )

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/matches/{match_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(match_id)
    assert data["deterministic_score"] == "92.50"
    assert data["match_explanation"] == "Perfect match across all vectors."
    assert data["company_name"] == "Netflix"


@pytest.mark.asyncio
async def test_get_match_detail_not_found(test_app, mock_matching_service: AsyncMock) -> None:
    missing_id = uuid.uuid4()
    mock_matching_service.get_match.side_effect = EntityNotFoundError("JobMatch", missing_id)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/matches/{missing_id}")

    assert response.status_code == 404
    data = response.json()
    assert "Not Found" in data["title"]
    assert str(missing_id) in data["detail"]


@pytest.mark.asyncio
async def test_reevaluate_job_match(test_app, mock_matching_service: AsyncMock) -> None:
    now = datetime.now(UTC)
    match_id = uuid.uuid4()
    job_id = uuid.uuid4()
    cand_id = uuid.uuid4()

    mock_match = AsyncMock()
    mock_match.id = match_id
    mock_match.candidate_profile_id = cand_id

    mock_matching_service.evaluate_job_for_candidate.return_value = mock_match

    detail = JobMatchDetailResponse(
        id=match_id,
        job_id=job_id,
        candidate_profile_id=cand_id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("75.00"),
        semantic_score=None,
        final_score=Decimal("75.00"),
        skill_score=Decimal("30.00"),
        experience_score=Decimal("20.00"),
        title_score=Decimal("15.00"),
        preference_score=Decimal("10.00"),
        match_explanation="Re-evaluated successfully.",
        match_explanation_details={},
        created_at=now,
        updated_at=now,
        job_title="Software Architect",
        company_name="Google",
        workplace_type=WorkplaceTypeEnum.REMOTE,
        normalized_location="Sunnyvale, CA",
        job=None,
    )
    mock_matching_service.get_match.return_value = detail

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/matches/{job_id}/re-evaluate")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["candidate_profile_id"] == str(cand_id)
    assert data["match"]["id"] == str(match_id)
    assert data["match"]["deterministic_score"] == "75.00"
    assert "Successfully evaluated" in data["message"]
