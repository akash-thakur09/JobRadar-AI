"""Data access repository for Candidate Profile, Preferences, and Skills."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candidate.models import (
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    EmploymentTypeEnum,
    User,
    WorkplaceTypeEnum,
)

DEFAULT_CANDIDATE_EMAIL = "candidate@jobradar.local"


class CandidateRepository:
    """Async repository providing persistence operations for candidate entities."""

    async def get_default_user(self, session: AsyncSession) -> User | None:
        """Fetch the primary candidate user record."""
        stmt = select(User).where(User.email == DEFAULT_CANDIDATE_EMAIL)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_default_profile(self, session: AsyncSession) -> CandidateProfile:
        """Retrieve the primary candidate profile or bootstrap a default singleton."""
        # Ensure default user exists
        user = await self.get_default_user(session)
        if user is None:
            user = User(
                email=DEFAULT_CANDIDATE_EMAIL,
                is_active=True,
            )
            session.add(user)
            await session.flush()

        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is not None:
            # Ensure preferences exist if not present
            pref = await self.get_preferences_by_profile_id(session, profile.id)
            if pref is None:
                pref = CandidatePreference(
                    candidate_profile_id=profile.id,
                    minimum_relevance_score=Decimal("70.00"),
                    preferred_titles=[],
                    preferred_workplace_types=[
                        WorkplaceTypeEnum.REMOTE,
                        WorkplaceTypeEnum.HYBRID,
                    ],
                    preferred_locations=[],
                    preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
                    max_job_age_days=14,
                )
                session.add(pref)
                await session.flush()
            return profile

        # Bootstrap candidate profile
        profile = CandidateProfile(
            user_id=user.id,
            full_name="Primary Candidate",
            headline="Software Engineer",
            total_experience_months=0,
        )
        session.add(profile)
        await session.flush()

        # Bootstrap matching preferences
        preferences = CandidatePreference(
            candidate_profile_id=profile.id,
            minimum_relevance_score=Decimal("70.00"),
            preferred_titles=[],
            preferred_workplace_types=[
                WorkplaceTypeEnum.REMOTE,
                WorkplaceTypeEnum.HYBRID,
            ],
            preferred_locations=[],
            preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
            max_job_age_days=14,
        )
        session.add(preferences)
        await session.flush()
        await session.refresh(profile)

        return profile

    async def get_profile(
        self, session: AsyncSession, profile_id: uuid.UUID | None = None
    ) -> CandidateProfile | None:
        """Retrieve a candidate profile by id or fetch the primary profile."""
        if profile_id is not None:
            stmt = select(CandidateProfile).where(CandidateProfile.id == profile_id)
        else:
            stmt = select(CandidateProfile).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        session: AsyncSession,
        profile: CandidateProfile,
        update_data: dict[str, Any],
    ) -> CandidateProfile:
        """Apply partial updates to a candidate profile."""
        for key, value in update_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        await session.flush()
        await session.refresh(profile)
        return profile

    async def get_preferences_by_profile_id(
        self, session: AsyncSession, profile_id: uuid.UUID
    ) -> CandidatePreference | None:
        """Fetch candidate preferences for a given profile."""
        stmt = select(CandidatePreference).where(
            CandidatePreference.candidate_profile_id == profile_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_preferences(
        self,
        session: AsyncSession,
        preferences: CandidatePreference,
        update_data: dict[str, Any],
    ) -> CandidatePreference:
        """Apply partial updates to candidate preferences."""
        for key, value in update_data.items():
            if hasattr(preferences, key) and value is not None:
                setattr(preferences, key, value)
        await session.flush()
        await session.refresh(preferences)
        return preferences

    async def list_skills_by_profile_id(
        self, session: AsyncSession, profile_id: uuid.UUID
    ) -> list[CandidateSkill]:
        """List all verified candidate skills ordered by core designation and name."""
        stmt = (
            select(CandidateSkill)
            .where(CandidateSkill.candidate_profile_id == profile_id)
            .order_by(CandidateSkill.is_core.desc(), CandidateSkill.skill_name.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_skill_by_name(
        self, session: AsyncSession, profile_id: uuid.UUID, skill_name: str
    ) -> CandidateSkill | None:
        """Find a candidate skill by its normalized name."""
        stmt = select(CandidateSkill).where(
            CandidateSkill.candidate_profile_id == profile_id,
            CandidateSkill.skill_name == skill_name,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_skill_by_id(
        self, session: AsyncSession, profile_id: uuid.UUID, skill_id: uuid.UUID
    ) -> CandidateSkill | None:
        """Find a candidate skill by its UUID."""
        stmt = select(CandidateSkill).where(
            CandidateSkill.candidate_profile_id == profile_id,
            CandidateSkill.id == skill_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_skill(
        self,
        session: AsyncSession,
        profile_id: uuid.UUID,
        skill_name: str,
        category: str,
        experience_months: int,
        is_core: bool,
    ) -> CandidateSkill:
        """Persist a new candidate verified skill."""
        skill = CandidateSkill(
            candidate_profile_id=profile_id,
            skill_name=skill_name,
            category=category,
            experience_months=experience_months,
            is_core=is_core,
        )
        session.add(skill)
        await session.flush()
        await session.refresh(skill)
        return skill

    async def delete_skill(self, session: AsyncSession, skill: CandidateSkill) -> None:
        """Remove a verified skill from the candidate profile."""
        await session.delete(skill)
        await session.flush()
