"""Business service layer for Candidate Profile, Preferences, and Skills."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.modules.candidate.models import CandidatePreference, CandidateProfile, CandidateSkill
from app.modules.candidate.repository import CandidateRepository
from app.modules.candidate.schemas import (
    CandidatePreferencesUpdateRequest,
    CandidateProfileUpdateRequest,
    CandidateSkillCreateRequest,
    normalize_skill,
)


class CandidateService:
    """Service orchestrating candidate profile management and validation rules."""

    def __init__(self, repository: CandidateRepository | None = None) -> None:
        self.repository = repository or CandidateRepository()

    async def get_profile(self, session: AsyncSession) -> CandidateProfile:
        """Fetch the active candidate profile, bootstrapping default if uninitialized."""
        return await self.repository.get_or_create_default_profile(session)

    async def update_profile(
        self, session: AsyncSession, payload: CandidateProfileUpdateRequest
    ) -> CandidateProfile:
        """Update candidate profile attributes."""
        profile = await self.get_profile(session)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return profile

        return await self.repository.update_profile(session, profile, update_data)

    async def get_preferences(self, session: AsyncSession) -> CandidatePreference:
        """Fetch job matching preferences for the active candidate profile."""
        profile = await self.get_profile(session)
        preferences = await self.repository.get_preferences_by_profile_id(session, profile.id)
        if preferences is None:
            # Fallback re-bootstrap in case preferences were detached
            profile = await self.repository.get_or_create_default_profile(session)
            preferences = await self.repository.get_preferences_by_profile_id(session, profile.id)
            if preferences is None:
                raise EntityNotFoundError(
                    entity_name="CandidatePreference", identifier=str(profile.id)
                )

        return preferences

    async def update_preferences(
        self, session: AsyncSession, payload: CandidatePreferencesUpdateRequest
    ) -> CandidatePreference:
        """Update job search preferences and filters."""
        preferences = await self.get_preferences(session)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return preferences

        return await self.repository.update_preferences(session, preferences, update_data)

    async def list_skills(self, session: AsyncSession) -> list[CandidateSkill]:
        """List all verified candidate skills."""
        profile = await self.get_profile(session)
        return await self.repository.list_skills_by_profile_id(session, profile.id)

    async def add_skill(
        self, session: AsyncSession, payload: CandidateSkillCreateRequest
    ) -> CandidateSkill:
        """Add a verified skill after normalizing and checking uniqueness."""
        profile = await self.get_profile(session)
        normalized_name = normalize_skill(payload.skill_name)

        existing = await self.repository.get_skill_by_name(session, profile.id, normalized_name)
        if existing is not None:
            raise EntityAlreadyExistsError(entity_name="CandidateSkill", identifier=normalized_name)

        return await self.repository.create_skill(
            session=session,
            profile_id=profile.id,
            skill_name=normalized_name,
            category=payload.category,
            experience_months=payload.experience_months,
            is_core=payload.is_core,
        )

    async def delete_skill(self, session: AsyncSession, skill_id: uuid.UUID) -> None:
        """Remove a verified skill by identifier."""
        profile = await self.get_profile(session)
        skill = await self.repository.get_skill_by_id(session, profile.id, skill_id)
        if skill is None:
            raise EntityNotFoundError(entity_name="CandidateSkill", identifier=str(skill_id))

        await self.repository.delete_skill(session, skill)


# Default singleton instance for dependency injection
_candidate_service = CandidateService()


def get_candidate_service() -> CandidateService:
    """FastAPI dependency for accessing the candidate domain service."""
    return _candidate_service
