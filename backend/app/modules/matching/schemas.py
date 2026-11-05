"""Pydantic schemas and DTOs for Candidate-Job Matching and Scoring."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.schemas import JobSummaryResponse
from app.modules.matching.models import EligibilityStatusEnum


class JobMatchSummaryResponse(BaseModel):
    """Summary representation of a candidate-job match evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    eligibility_status: EligibilityStatusEnum
    deterministic_score: Decimal
    semantic_score: Decimal | None = None
    final_score: Decimal
    skill_score: Decimal
    experience_score: Decimal
    title_score: Decimal
    preference_score: Decimal
    match_explanation: str
    is_qualified: bool = False
    created_at: datetime
    updated_at: datetime

    # Denormalized job information for convenience
    job_title: str | None = None
    company_name: str | None = None
    workplace_type: WorkplaceTypeEnum | None = None
    normalized_location: str | None = None


class JobMatchDetailResponse(JobMatchSummaryResponse):
    """Detailed match evaluation with full line-item scoring and explanation audit trail."""

    match_explanation_details: dict[str, Any] = Field(default_factory=dict)
    job: JobSummaryResponse | None = None


class JobMatchReevaluateResponse(BaseModel):
    """Outcome of manually re-triggering job match evaluation."""

    job_id: uuid.UUID
    candidate_profile_id: uuid.UUID
    match: JobMatchDetailResponse
    message: str
