"""Integration tests for Candidate Profile, Preferences, and Skills PostgreSQL persistence."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    User,
    WorkplaceTypeEnum,
)
from app.modules.candidate.repository import CandidateRepository


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping DB integration tests.")


@pytest.mark.integration
async def test_candidate_repository_lifecycle() -> None:
    """Verify repository methods with real database transactions."""
    session_factory = get_session_factory()
    repo = CandidateRepository()

    async with session_factory() as session:
        # Test bootstrapping default profile
        profile = await repo.get_or_create_default_profile(session)
        assert profile is not None
        assert profile.user_id is not None
        profile_id = profile.id

        # Test updating profile
        await repo.update_profile(
            session,
            profile,
            {"headline": "Lead Platform Engineer", "total_experience_months": 60},
        )
        assert profile.headline == "Lead Platform Engineer"
        assert profile.total_experience_months == 60

        # Test preferences retrieval and update
        prefs = await repo.get_preferences_by_profile_id(session, profile_id)
        assert prefs is not None
        await repo.update_preferences(
            session,
            prefs,
            {"minimum_relevance_score": Decimal("82.00"), "max_job_age_days": 10},
        )
        assert prefs.minimum_relevance_score == Decimal("82.00")
        assert prefs.max_job_age_days == 10

        # Test adding skill
        skill = await repo.create_skill(
            session,
            profile_id=profile_id,
            skill_name="rust",
            category="language",
            experience_months=18,
            is_core=True,
        )
        assert skill.skill_name == "rust"

        # Test listing skills
        skills = await repo.list_skills_by_profile_id(session, profile_id)
        assert any(s.skill_name == "rust" for s in skills)

        # Test deleting skill
        await repo.delete_skill(session, skill)
        skills_after = await repo.list_skills_by_profile_id(session, profile_id)
        assert not any(s.skill_name == "rust" for s in skills_after)

        await session.rollback()


@pytest.mark.integration
async def test_db_unique_skill_constraint() -> None:
    """Verify PostgreSQL enforces unique constraint on (candidate_profile_id, skill_name)."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"unique_skill_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Constraint Tester",
            total_experience_months=12,
        )
        session.add(profile)
        await session.flush()

        skill1 = CandidateSkill(
            candidate_profile_id=profile.id,
            skill_name="python",
            category="language",
        )
        session.add(skill1)
        await session.flush()

        skill2 = CandidateSkill(
            candidate_profile_id=profile.id,
            skill_name="python",
            category="language",
        )
        session.add(skill2)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()


@pytest.mark.integration
async def test_db_check_constraints() -> None:
    """Verify database enforces non-negative experience and score ranges."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"chk_test_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        # Check total_experience_months >= 0
        invalid_profile = CandidateProfile(
            user_id=user.id,
            full_name="Invalid Experience",
            total_experience_months=-10,
        )
        session.add(invalid_profile)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()

    async with session_factory() as session:
        user = User(email=f"chk_test2_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Valid Profile",
            total_experience_months=10,
        )
        session.add(profile)
        await session.flush()

        # Check minimum_relevance_score range [0, 100]
        invalid_prefs = CandidatePreference(
            candidate_profile_id=profile.id,
            minimum_relevance_score=Decimal("150.00"),
            preferred_titles=[],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_locations=[],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=14,
        )
        session.add(invalid_prefs)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.integration
async def test_db_foreign_key_cascade_deletion() -> None:
    """Verify deleting a User cascades to CandidateProfile, Preferences, and Skills."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"cascade_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()
        user_id = user.id

        profile = CandidateProfile(
            user_id=user_id,
            full_name="Cascade Tester",
            total_experience_months=20,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.id

        prefs = CandidatePreference(
            candidate_profile_id=profile_id,
            minimum_relevance_score=Decimal("70.00"),
            preferred_titles=["Engineer"],
            preferred_workplace_types=[WorkplaceTypeEnum.REMOTE],
            preferred_locations=["Remote"],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=14,
        )
        session.add(prefs)

        skill = CandidateSkill(
            candidate_profile_id=profile_id,
            skill_name="fastapi",
            category="framework",
        )
        session.add(skill)
        await session.flush()
        await session.commit()

    # In a new session, delete the User
    async with session_factory() as session:
        user_to_delete = await session.get(User, user_id)
        assert user_to_delete is not None
        await session.delete(user_to_delete)
        await session.commit()

    # Verify all child entities were cascade deleted
    async with session_factory() as session:
        profile_query = await session.execute(
            select(CandidateProfile).where(CandidateProfile.id == profile_id)
        )
        assert profile_query.scalar_one_or_none() is None

        prefs_query = await session.execute(
            select(CandidatePreference).where(
                CandidatePreference.candidate_profile_id == profile_id
            )
        )
        assert prefs_query.scalar_one_or_none() is None

        skills_query = await session.execute(
            select(CandidateSkill).where(CandidateSkill.candidate_profile_id == profile_id)
        )
        assert len(list(skills_query.scalars().all())) == 0
