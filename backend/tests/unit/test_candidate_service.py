"""Unit tests for CandidateService business logic."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    WorkplaceTypeEnum,
)
from app.modules.candidate.schemas import (
    CandidatePreferencesUpdateRequest,
    CandidateProfileUpdateRequest,
    CandidateSkillCreateRequest,
)
from app.modules.candidate.service import CandidateService


@pytest.fixture
def mock_candidate_profile() -> CandidateProfile:
    """Provide a mock candidate profile instance."""
    profile_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    profile = CandidateProfile(
        id=profile_id,
        user_id=user_id,
        full_name="Alex Smith",
        headline="Senior Systems Architect",
        professional_summary="Architecting scalable backend pipelines.",
        current_role="Staff Engineer",
        total_experience_months=72,
        city="Seattle",
        country="USA",
        work_authorization="US Citizen",
        created_at=now,
        updated_at=now,
    )
    return profile


@pytest.fixture
def mock_candidate_preferences(mock_candidate_profile: CandidateProfile) -> CandidatePreference:
    """Provide a mock candidate preferences instance."""
    now = datetime.now(UTC)
    return CandidatePreference(
        id=uuid.uuid4(),
        candidate_profile_id=mock_candidate_profile.id,
        minimum_relevance_score=Decimal("75.00"),
        preferred_titles=["Staff Engineer", "Principal Architect"],
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_locations=["Seattle", "Remote"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=7,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_service_get_profile(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service retrieves profile from repository."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    result = await service.get_profile(session)

    assert result == mock_candidate_profile
    mock_repo.get_or_create_default_profile.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_service_update_profile(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service updates profile attributes."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile

    updated_profile = CandidateProfile(
        id=mock_candidate_profile.id,
        user_id=mock_candidate_profile.user_id,
        full_name="Alexander Smith",
        headline="Principal Engineer",
        total_experience_months=84,
        created_at=mock_candidate_profile.created_at,
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_profile.return_value = updated_profile
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    payload = CandidateProfileUpdateRequest(
        full_name="Alexander Smith",
        headline="Principal Engineer",
        total_experience_months=84,
    )
    result = await service.update_profile(session, payload)

    assert result.full_name == "Alexander Smith"
    assert result.headline == "Principal Engineer"
    mock_repo.update_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_update_profile_empty_payload(
    mock_candidate_profile: CandidateProfile,
) -> None:
    """Verify service returns profile unchanged when payload has no unset values."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    payload = CandidateProfileUpdateRequest()
    result = await service.update_profile(session, payload)

    assert result == mock_candidate_profile
    mock_repo.update_profile.assert_not_called()


@pytest.mark.asyncio
async def test_service_get_preferences(
    mock_candidate_profile: CandidateProfile,
    mock_candidate_preferences: CandidatePreference,
) -> None:
    """Verify service fetches preferences for candidate profile."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    mock_repo.get_preferences_by_profile_id.return_value = mock_candidate_preferences
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    result = await service.get_preferences(session)

    assert result == mock_candidate_preferences
    mock_repo.get_preferences_by_profile_id.assert_awaited_once_with(
        session, mock_candidate_profile.id
    )


@pytest.mark.asyncio
async def test_service_update_preferences(
    mock_candidate_profile: CandidateProfile,
    mock_candidate_preferences: CandidatePreference,
) -> None:
    """Verify service updates preference attributes."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    mock_repo.get_preferences_by_profile_id.return_value = mock_candidate_preferences

    updated_prefs = CandidatePreference(
        id=mock_candidate_preferences.id,
        candidate_profile_id=mock_candidate_profile.id,
        minimum_relevance_score=Decimal("80.00"),
        preferred_titles=["Architect"],
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
        preferred_locations=["Remote"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=10,
        created_at=mock_candidate_preferences.created_at,
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_preferences.return_value = updated_prefs
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    payload = CandidatePreferencesUpdateRequest(
        minimum_relevance_score=Decimal("80.00"),
        max_job_age_days=10,
    )
    result = await service.update_preferences(session, payload)

    assert result.minimum_relevance_score == Decimal("80.00")
    assert result.max_job_age_days == 10
    mock_repo.update_preferences.assert_awaited_once()


@pytest.mark.asyncio
async def test_service_list_skills(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service returns list of candidate skills."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile

    skills = [
        CandidateSkill(
            id=uuid.uuid4(),
            candidate_profile_id=mock_candidate_profile.id,
            skill_name="postgresql",
            category="database",
            experience_months=48,
            is_core=True,
            created_at=datetime.now(UTC),
        )
    ]
    mock_repo.list_skills_by_profile_id.return_value = skills
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    result = await service.list_skills(session)

    assert len(result) == 1
    assert result[0].skill_name == "postgresql"


@pytest.mark.asyncio
async def test_service_add_skill_success(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service normalizes and creates new skill."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    mock_repo.get_skill_by_name.return_value = None

    new_skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_profile_id=mock_candidate_profile.id,
        skill_name="postgresql",
        category="database",
        experience_months=24,
        is_core=True,
        created_at=datetime.now(UTC),
    )
    mock_repo.create_skill.return_value = new_skill
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    payload = CandidateSkillCreateRequest(
        skill_name="Postgres",
        category="database",
        experience_months=24,
        is_core=True,
    )
    result = await service.add_skill(session, payload)

    assert result.skill_name == "postgresql"
    mock_repo.create_skill.assert_awaited_once_with(
        session=session,
        profile_id=mock_candidate_profile.id,
        skill_name="postgresql",
        category="database",
        experience_months=24,
        is_core=True,
    )


@pytest.mark.asyncio
async def test_service_add_skill_duplicate_raises_conflict(
    mock_candidate_profile: CandidateProfile,
) -> None:
    """Verify service raises EntityAlreadyExistsError when normalized skill exists."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile

    existing_skill = CandidateSkill(
        id=uuid.uuid4(),
        candidate_profile_id=mock_candidate_profile.id,
        skill_name="postgresql",
        category="database",
        experience_months=12,
        is_core=False,
        created_at=datetime.now(UTC),
    )
    mock_repo.get_skill_by_name.return_value = existing_skill
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    payload = CandidateSkillCreateRequest(skill_name="PostgreSQL")

    with pytest.raises(EntityAlreadyExistsError) as exc_info:
        await service.add_skill(session, payload)

    assert "postgresql" in str(exc_info.value)
    mock_repo.create_skill.assert_not_called()


@pytest.mark.asyncio
async def test_service_delete_skill_success(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service deletes verified skill."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile

    skill_id = uuid.uuid4()
    existing_skill = CandidateSkill(
        id=skill_id,
        candidate_profile_id=mock_candidate_profile.id,
        skill_name="docker",
        category="devops",
        experience_months=12,
        is_core=False,
        created_at=datetime.now(UTC),
    )
    mock_repo.get_skill_by_id.return_value = existing_skill
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    await service.delete_skill(session, skill_id)

    mock_repo.delete_skill.assert_awaited_once_with(session, existing_skill)


@pytest.mark.asyncio
async def test_service_delete_skill_not_found(mock_candidate_profile: CandidateProfile) -> None:
    """Verify service raises EntityNotFoundError when deleting non-existent skill."""
    mock_repo = AsyncMock()
    mock_repo.get_or_create_default_profile.return_value = mock_candidate_profile
    mock_repo.get_skill_by_id.return_value = None
    service = CandidateService(repository=mock_repo)

    session = AsyncMock()
    skill_id = uuid.uuid4()

    with pytest.raises(EntityNotFoundError) as exc_info:
        await service.delete_skill(session, skill_id)

    assert str(skill_id) in str(exc_info.value)
    mock_repo.delete_skill.assert_not_called()
