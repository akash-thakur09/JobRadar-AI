"""Pydantic schemas and DTOs for Candidate Profile, Preferences, and Skills."""

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum

# Canonical technology alias mapping dictionary
CANONICAL_SKILL_ALIASES: dict[str, str] = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "pgsql": "postgresql",
    "postgresql": "postgresql",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "aws": "aws",
    "amazon web services": "aws",
    "amazon aws": "aws",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "golang": "go",
    "go language": "go",
    "go": "go",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "rest api": "rest_apis",
    "restful api": "rest_apis",
    "restful web services": "rest_apis",
    "rest_apis": "rest_apis",
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    ".net": "dotnet",
    "dotnet": "dotnet",
    "docker": "docker",
    "python": "python",
    "py": "python",
}


def normalize_skill(raw_name: str) -> str:
    """Normalize a raw skill string into a canonical, lowercase identifier.

    Rules:
    1. Strip leading and trailing whitespace.
    2. Lowercase the entire string.
    3. Collapse multiple internal whitespace sequences into single spaces.
    4. Match against the canonical technology taxonomy.
    5. Handle common suffixes like '.js' -> stripped or direct mapped.
    """
    if not raw_name or not raw_name.strip():
        raise ValueError("Skill name cannot be empty or blank.")

    cleaned = re.sub(r"\s+", " ", raw_name.strip().lower())

    # Direct canonical lookup
    if cleaned in CANONICAL_SKILL_ALIASES:
        return CANONICAL_SKILL_ALIASES[cleaned]

    # Handle common patterns like <tech>.js if not in dictionary
    if cleaned.endswith(".js"):
        base_name = cleaned[:-3]
        if base_name in CANONICAL_SKILL_ALIASES:
            return CANONICAL_SKILL_ALIASES[base_name]
        return base_name

    return cleaned


# ==============================================================================
# Candidate Profile Schemas
# ==============================================================================


class CandidateProfileResponse(BaseModel):
    """Public representation of candidate profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    headline: str | None = None
    professional_summary: str | None = None
    current_role: str | None = None
    total_experience_months: int
    city: str | None = None
    country: str | None = None
    work_authorization: str | None = None
    created_at: datetime
    updated_at: datetime


class CandidateProfileUpdateRequest(BaseModel):
    """Payload for updating candidate profile information."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    headline: str | None = Field(default=None, max_length=255)
    professional_summary: str | None = None
    current_role: str | None = Field(default=None, max_length=150)
    total_experience_months: int | None = Field(default=None, ge=0)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    work_authorization: str | None = Field(default=None, max_length=50)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        """Ensure full_name is non-empty after trimming."""
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Full name cannot be blank or whitespace only.")
            return trimmed
        return v


# ==============================================================================
# Candidate Preferences Schemas
# ==============================================================================


class CandidatePreferencesResponse(BaseModel):
    """Public representation of candidate job matching preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    minimum_relevance_score: Decimal = Field(ge=Decimal("0.00"), le=Decimal("100.00"))
    preferred_titles: list[str]
    preferred_workplace_types: list[WorkplaceTypeEnum]
    preferred_locations: list[str]
    preferred_employment_types: list[EmploymentTypeEnum]
    max_job_age_days: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime


class CandidatePreferencesUpdateRequest(BaseModel):
    """Payload for updating candidate job preferences and filters."""

    minimum_relevance_score: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00")
    )
    preferred_titles: list[str] | None = None
    preferred_workplace_types: list[WorkplaceTypeEnum] | None = None
    preferred_locations: list[str] | None = None
    preferred_employment_types: list[EmploymentTypeEnum] | None = None
    max_job_age_days: int | None = Field(default=None, gt=0)

    @field_validator("preferred_titles", "preferred_locations")
    @classmethod
    def clean_string_lists(cls, v: list[str] | None) -> list[str] | None:
        """Strip whitespace and filter blank items in list fields."""
        if v is not None:
            cleaned = [item.strip() for item in v if item and item.strip()]
            return cleaned
        return v


# ==============================================================================
# Candidate Skills Schemas
# ==============================================================================


class CandidateSkillResponse(BaseModel):
    """Public representation of a candidate verified skill."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    skill_name: str
    category: str
    experience_months: int
    is_core: bool
    created_at: datetime


class CandidateSkillCreateRequest(BaseModel):
    """Payload for adding a verified skill to the candidate profile."""

    skill_name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="general", max_length=50)
    experience_months: int = Field(default=0, ge=0)
    is_core: bool = Field(default=False)

    @field_validator("skill_name")
    @classmethod
    def validate_and_normalize_skill_name(cls, v: str) -> str:
        """Enforce skill normalization during request validation."""
        return normalize_skill(v)

    @field_validator("category")
    @classmethod
    def clean_category(cls, v: str) -> str:
        """Strip and lowercase category."""
        trimmed = v.strip().lower()
        return trimmed or "general"
