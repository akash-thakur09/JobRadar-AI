"""REST API route handlers for Candidate Profile, Preferences, and Skills."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.candidate.schemas import (
    CandidatePreferencesResponse,
    CandidatePreferencesUpdateRequest,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
    CandidateSkillCreateRequest,
    CandidateSkillResponse,
)
from app.modules.candidate.service import CandidateService, get_candidate_service

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.get(
    "/profile",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve candidate profile",
    description="Retrieve the active candidate profile details and contact information.",
)
async def get_candidate_profile(
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> CandidateProfileResponse:
    """Return the active candidate profile."""
    profile = await service.get_profile(session)
    return CandidateProfileResponse.model_validate(profile)


@router.put(
    "/profile",
    response_model=CandidateProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate profile",
    description="Update candidate professional summary, headline, contact details, or experience.",
)
async def update_candidate_profile(
    payload: CandidateProfileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> CandidateProfileResponse:
    """Update profile information and return the updated entity."""
    profile = await service.update_profile(session, payload)
    return CandidateProfileResponse.model_validate(profile)


@router.get(
    "/preferences",
    response_model=CandidatePreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve candidate preferences",
    description="Retrieve job search filters, preferred titles, workplace types, and match thresholds.",
)
async def get_candidate_preferences(
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> CandidatePreferencesResponse:
    """Return the candidate matching preferences."""
    preferences = await service.get_preferences(session)
    return CandidatePreferencesResponse.model_validate(preferences)


@router.put(
    "/preferences",
    response_model=CandidatePreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate preferences",
    description="Update relevance score thresholds, target job titles, locations, and employment types.",
)
async def update_candidate_preferences(
    payload: CandidatePreferencesUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> CandidatePreferencesResponse:
    """Update preferences and return the updated entity."""
    preferences = await service.update_preferences(session, payload)
    return CandidatePreferencesResponse.model_validate(preferences)


@router.get(
    "/skills",
    response_model=list[CandidateSkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate skills",
    description="List all verified candidate skills sorted by core priority and alphabetical order.",
)
async def list_candidate_skills(
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> list[CandidateSkillResponse]:
    """Return verified candidate skills."""
    skills = await service.list_skills(session)
    return [CandidateSkillResponse.model_validate(skill) for skill in skills]


@router.post(
    "/skills",
    response_model=CandidateSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add candidate skill",
    description="Add a verified skill to the candidate profile with automatic normalization and duplicate rejection.",
)
async def add_candidate_skill(
    payload: CandidateSkillCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> CandidateSkillResponse:
    """Add a verified skill after normalization."""
    skill = await service.add_skill(session, payload)
    return CandidateSkillResponse.model_validate(skill)


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete candidate skill",
    description="Remove a verified skill from the candidate profile.",
)
async def delete_candidate_skill(
    skill_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: CandidateService = Depends(get_candidate_service),
) -> None:
    """Delete a verified skill by identifier."""
    await service.delete_skill(session, skill_id)
