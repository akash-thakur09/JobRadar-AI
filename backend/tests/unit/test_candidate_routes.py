"""Unit tests for Candidate Profile, Preferences, and Skills REST API endpoints."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.database.session import get_db_session
from app.main import create_app
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.candidate.service import get_candidate_service


@pytest.fixture
def sample_profile() -> CandidateProfile:
    """Return a populated CandidateProfile model."""
    now = datetime.now(UTC)
    return CandidateProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="Morgan Freeman",
        headline="Principal Cloud Architect",
        professional_summary="Designing distributed multi-region systems.",
        current_role="Staff Engineer",
        total_experience_months=96,
        city="Austin",
        country="USA",
        work_authorization="US Citizen",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_preferences(sample_profile: CandidateProfile) -> CandidatePreference:
    """Return a populated CandidatePreference model."""
    now = datetime.now(UTC)
    return CandidatePreference(
        id=uuid.uuid4(),
        candidate_profile_id=sample_profile.id,
        minimum_relevance_score=Decimal("80.00"),
        preferred_titles=["Cloud Architect", "Principal Engineer"],
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_locations=["Austin", "Remote"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=14,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_skill(sample_profile: CandidateProfile) -> CandidateSkill:
    """Return a populated CandidateSkill model."""
    return CandidateSkill(
        id=uuid.uuid4(),
        candidate_profile_id=sample_profile.id,
        skill_name="kubernetes",
        category="devops",
        experience_months=48,
        is_core=True,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_get_candidate_profile_endpoint(sample_profile: CandidateProfile) -> None:
    """GET /api/v1/candidate/profile returns candidate profile."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.get_profile.return_value = sample_profile

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/candidate/profile")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_profile.id)
    assert data["full_name"] == sample_profile.full_name
    assert data["total_experience_months"] == 96


@pytest.mark.asyncio
async def test_update_candidate_profile_endpoint(sample_profile: CandidateProfile) -> None:
    """PUT /api/v1/candidate/profile updates profile and returns updated entity."""
    app = create_app()
    mock_service = AsyncMock()
    updated_profile = CandidateProfile(
        id=sample_profile.id,
        user_id=sample_profile.user_id,
        full_name="Morgan A. Freeman",
        headline="Distinguished Architect",
        professional_summary=sample_profile.professional_summary,
        current_role=sample_profile.current_role,
        total_experience_months=100,
        city="Austin",
        country="USA",
        work_authorization="US Citizen",
        created_at=sample_profile.created_at,
        updated_at=datetime.now(UTC),
    )
    mock_service.update_profile.return_value = updated_profile

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/candidate/profile",
            json={"full_name": "Morgan A. Freeman", "total_experience_months": 100},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Morgan A. Freeman"
    assert data["total_experience_months"] == 100


@pytest.mark.asyncio
async def test_update_candidate_profile_validation_error() -> None:
    """PUT /api/v1/candidate/profile with invalid payload returns RFC 7807 problem details."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/candidate/profile",
            json={"total_experience_months": -5},
        )

    assert response.status_code == 422
    data = response.json()
    assert "type" in data
    assert "invalid_params" in data


@pytest.mark.asyncio
async def test_get_candidate_preferences_endpoint(
    sample_preferences: CandidatePreference,
) -> None:
    """GET /api/v1/candidate/preferences returns preferences."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.get_preferences.return_value = sample_preferences

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/candidate/preferences")

    assert response.status_code == 200
    data = response.json()
    assert data["minimum_relevance_score"] == "80.00"
    assert data["preferred_workplace_types"] == ["REMOTE"]
    assert data["max_job_age_days"] == 14


@pytest.mark.asyncio
async def test_update_candidate_preferences_endpoint(
    sample_preferences: CandidatePreference,
) -> None:
    """PUT /api/v1/candidate/preferences updates preferences."""
    app = create_app()
    mock_service = AsyncMock()
    updated_prefs = CandidatePreference(
        id=sample_preferences.id,
        candidate_profile_id=sample_preferences.candidate_profile_id,
        minimum_relevance_score=Decimal("85.00"),
        preferred_titles=["VP of Engineering"],
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE, WorkplaceTypeEnum.HYBRID],
        preferred_locations=["Remote"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=21,
        created_at=sample_preferences.created_at,
        updated_at=datetime.now(UTC),
    )
    mock_service.update_preferences.return_value = updated_prefs

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/candidate/preferences",
            json={
                "minimum_relevance_score": 85.00,
                "preferred_titles": ["VP of Engineering"],
                "max_job_age_days": 21,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["minimum_relevance_score"] == "85.00"
    assert data["max_job_age_days"] == 21


@pytest.mark.asyncio
async def test_update_candidate_preferences_validation_error() -> None:
    """PUT /api/v1/candidate/preferences with invalid score returns 422."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/candidate/preferences",
            json={"minimum_relevance_score": 150.00},
        )

    assert response.status_code == 422
    data = response.json()
    assert "minimum_relevance_score" in str(data)


@pytest.mark.asyncio
async def test_list_candidate_skills_endpoint(sample_skill: CandidateSkill) -> None:
    """GET /api/v1/candidate/skills returns verified skills."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.list_skills.return_value = [sample_skill]

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/candidate/skills")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["skill_name"] == "kubernetes"
    assert data[0]["is_core"] is True


@pytest.mark.asyncio
async def test_add_candidate_skill_endpoint(sample_skill: CandidateSkill) -> None:
    """POST /api/v1/candidate/skills creates skill and returns 201."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.add_skill.return_value = sample_skill

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/candidate/skills",
            json={
                "skill_name": "k8s",
                "category": "devops",
                "experience_months": 48,
                "is_core": True,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["skill_name"] == "kubernetes"


@pytest.mark.asyncio
async def test_add_candidate_skill_duplicate_conflict() -> None:
    """POST /api/v1/candidate/skills with duplicate skill returns 409 Conflict."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.add_skill.side_effect = EntityAlreadyExistsError(
        entity_name="CandidateSkill", identifier="kubernetes"
    )

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/candidate/skills",
            json={"skill_name": "kubernetes"},
        )

    assert response.status_code == 409
    data = response.json()
    assert data["status"] == 409
    assert "already exists" in data["detail"]


@pytest.mark.asyncio
async def test_delete_candidate_skill_endpoint() -> None:
    """DELETE /api/v1/candidate/skills/{id} returns 204 No Content."""
    app = create_app()
    mock_service = AsyncMock()
    mock_service.delete_skill.return_value = None

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    skill_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/candidate/skills/{skill_id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_candidate_skill_not_found() -> None:
    """DELETE /api/v1/candidate/skills/{id} for non-existent skill returns 404."""
    app = create_app()
    mock_service = AsyncMock()
    skill_id = uuid.uuid4()
    mock_service.delete_skill.side_effect = EntityNotFoundError(
        entity_name="CandidateSkill", identifier=str(skill_id)
    )

    app.dependency_overrides[get_candidate_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/candidate/skills/{skill_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["status"] == 404
    assert "was not found" in data["detail"]
