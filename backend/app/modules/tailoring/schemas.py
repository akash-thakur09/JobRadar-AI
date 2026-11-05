"""Pydantic schemas and DTOs for the Resume Tailoring domain."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum


class TailoredExperienceItem(BaseModel):
    """Job experience block with truthful rewritten bullets."""

    company: str = Field(description="Employer name sourced from verified evidence")
    title: str = Field(description="Role title sourced from verified evidence")
    location: str | None = Field(default=None, description="Location of employment")
    start_date: str | None = Field(default=None, description="Start date from evidence")
    end_date: str | None = Field(default=None, description="End date from evidence")
    bullet_points: list[str] = Field(
        min_length=1,
        description="Factual, keyword-tailored achievement bullet points",
    )


class TailoredProjectItem(BaseModel):
    """Verified project entry relevant to the target job."""

    name: str = Field(description="Project name")
    description: str = Field(description="Project description tailored to relevance")
    technologies: list[str] = Field(
        default_factory=list,
        description="Verified technologies utilized in this project",
    )
    link: str | None = Field(default=None, description="Repository or live URL")


class TailoredEducationItem(BaseModel):
    """Verified education credential."""

    institution: str = Field(description="College, university, or institution")
    degree: str = Field(description="Degree or credential awarded")
    field_of_study: str | None = Field(default=None, description="Major or field")
    graduation_date: str | None = Field(default=None, description="Graduation year or date")


class TailoredResumeContent(BaseModel):
    """Strict structured representation of the tailored resume content."""

    headline: str = Field(description="Targeted professional headline")
    professional_summary: str = Field(
        description="Concise, truthful executive summary emphasizing relevant background"
    )
    skills: list[str] = Field(
        min_length=1,
        description="Verified candidate skills reordered by relevance to target job",
    )
    experience: list[TailoredExperienceItem] = Field(
        min_length=1,
        description="Employment history with evidence-grounded bullet points",
    )
    projects: list[TailoredProjectItem] = Field(
        default_factory=list,
        description="Selected relevant candidate projects",
    )
    education: list[TailoredEducationItem] = Field(
        default_factory=list,
        description="Verified academic qualifications",
    )
    tailoring_notes: str | None = Field(
        default=None,
        description="Internal summary of strategic alignment and framing choices",
    )


class ClaimValidationReport(BaseModel):
    """Audit report produced by the ClaimValidator ensuring strict truthfulness."""

    is_valid: bool = Field(default=True, description="Whether content passed claim verification")
    supported_skills: list[str] = Field(default_factory=list)
    unsupported_skills: list[str] = Field(default_factory=list)
    supported_metrics: list[str] = Field(default_factory=list)
    unsupported_metrics: list[str] = Field(default_factory=list)
    repaired_claims: list[str] = Field(default_factory=list)
    violations_detected: list[str] = Field(default_factory=list)


class TailorResumeRequest(BaseModel):
    """Request payload to initiate or re-run resume tailoring."""

    job_match_id: uuid.UUID = Field(description="Qualified JobMatch identifier")
    resume_version_id: uuid.UUID | None = Field(
        default=None,
        description="Optional explicit ResumeVersion; defaults to active master resume",
    )
    force_regenerate: bool = Field(
        default=False,
        description="Force re-generation even if an artifact already exists",
    )


class TailoredResumeSummaryResponse(BaseModel):
    """Summary DTO for a tailored resume artifact."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    job_id: uuid.UUID
    job_match_id: uuid.UUID
    resume_version_id: uuid.UUID
    rendering_strategy: RenderingStrategyEnum
    generation_status: TailoredResumeStatusEnum
    file_name: str | None = None
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None
    generation_attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class TailoredResumeDetailResponse(TailoredResumeSummaryResponse):
    """Detailed DTO containing tailored structured content and validation audit trail."""

    tailored_content: dict[str, Any] = Field(default_factory=dict)
    validation_metadata: dict[str, Any] = Field(default_factory=dict)
    validation_error: str | None = None
