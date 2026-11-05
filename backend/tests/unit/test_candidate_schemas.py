"""Unit tests for candidate schemas and skill normalization."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.candidate.schemas import (
    CandidatePreferencesUpdateRequest,
    CandidateProfileUpdateRequest,
    CandidateSkillCreateRequest,
    normalize_skill,
)


def test_normalize_skill_variations() -> None:
    """Verify that varied casing, punctuation, and aliases normalize to canonical forms."""
    assert normalize_skill("React") == "react"
    assert normalize_skill("react.js") == "react"
    assert normalize_skill("REACTJS") == "react"
    assert normalize_skill("  PostgreSQL  ") == "postgresql"
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("psql") == "postgresql"
    assert normalize_skill("AWS") == "aws"
    assert normalize_skill("Amazon Web Services") == "aws"
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("Golang") == "go"
    assert normalize_skill("Go Language") == "go"
    assert normalize_skill("typescript") == "typescript"
    assert normalize_skill("TS") == "typescript"
    assert normalize_skill("REST API") == "rest_apis"
    assert normalize_skill("restful api") == "rest_apis"
    assert normalize_skill("Node.js") == "nodejs"
    assert normalize_skill("C++") == "cpp"
    assert normalize_skill("C#") == "csharp"
    assert normalize_skill(".NET") == "dotnet"
    assert normalize_skill("Docker") == "docker"
    assert normalize_skill("Vue.js") == "vue"


def test_normalize_skill_empty_raises_error() -> None:
    """Verify that empty or whitespace-only skill names raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_skill("")

    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_skill("   ")


def test_candidate_profile_update_schema_valid() -> None:
    """Verify valid candidate profile update payload."""
    payload = CandidateProfileUpdateRequest(
        full_name="Jane Doe",
        headline="Senior Backend Engineer",
        professional_summary="Experienced distributed systems developer.",
        total_experience_months=48,
        city="San Francisco",
        country="USA",
        work_authorization="US Citizen",
    )
    assert payload.full_name == "Jane Doe"
    assert payload.total_experience_months == 48


def test_candidate_profile_update_schema_invalid_experience() -> None:
    """Verify negative total experience months is rejected."""
    with pytest.raises(ValidationError):
        CandidateProfileUpdateRequest(total_experience_months=-5)


def test_candidate_profile_update_schema_blank_full_name() -> None:
    """Verify blank full_name is rejected."""
    with pytest.raises(ValidationError):
        CandidateProfileUpdateRequest(full_name="   ")


def test_candidate_preferences_update_schema_valid() -> None:
    """Verify valid candidate preferences update payload."""
    payload = CandidatePreferencesUpdateRequest(
        minimum_relevance_score=Decimal("85.50"),
        preferred_titles=["Backend Engineer", "Platform Engineer"],
        preferred_workplace_types=[WorkplaceTypeEnum.REMOTE, WorkplaceTypeEnum.HYBRID],
        preferred_locations=["San Francisco", "New York"],
        preferred_employment_types=[EmploymentTypeEnum.FULL_TIME],
        max_job_age_days=10,
    )
    assert payload.minimum_relevance_score == Decimal("85.50")
    assert payload.max_job_age_days == 10
    assert payload.preferred_workplace_types == [
        WorkplaceTypeEnum.REMOTE,
        WorkplaceTypeEnum.HYBRID,
    ]


@pytest.mark.parametrize("invalid_score", [Decimal("-1.00"), Decimal("100.01"), Decimal("150.00")])
def test_candidate_preferences_update_schema_invalid_score(invalid_score: Decimal) -> None:
    """Verify minimum_relevance_score out of range [0.00, 100.00] is rejected."""
    with pytest.raises(ValidationError):
        CandidatePreferencesUpdateRequest(minimum_relevance_score=invalid_score)


@pytest.mark.parametrize("invalid_age", [0, -1, -10])
def test_candidate_preferences_update_schema_invalid_job_age(invalid_age: int) -> None:
    """Verify non-positive max_job_age_days is rejected."""
    with pytest.raises(ValidationError):
        CandidatePreferencesUpdateRequest(max_job_age_days=invalid_age)


def test_candidate_preferences_string_list_sanitization() -> None:
    """Verify empty elements and whitespace are stripped from string lists."""
    payload = CandidatePreferencesUpdateRequest(
        preferred_titles=["  Backend Engineer  ", "", "   ", "Platform Engineer"]
    )
    assert payload.preferred_titles == ["Backend Engineer", "Platform Engineer"]


def test_candidate_skill_create_schema_normalizes_skill_name() -> None:
    """Verify CandidateSkillCreateRequest automatically normalizes skill_name."""
    payload = CandidateSkillCreateRequest(
        skill_name="  React.js  ",
        category="frontend",
        experience_months=36,
        is_core=True,
    )
    assert payload.skill_name == "react"
    assert payload.category == "frontend"
    assert payload.experience_months == 36
    assert payload.is_core is True


def test_candidate_skill_create_schema_invalid_experience() -> None:
    """Verify negative experience_months is rejected."""
    with pytest.raises(ValidationError):
        CandidateSkillCreateRequest(skill_name="Python", experience_months=-1)
