"""Pydantic schemas for Pipeline Runs and Orchestration Monitoring."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.resumes.schemas import PaginationMetadata


class PipelineRunCreateRequest(BaseModel):
    """Payload to initiate a new automated or manual pipeline run."""

    candidate_profile_id: uuid.UUID = Field(
        description="Target candidate profile for pipeline matching and tailoring",
    )
    trigger_type: PipelineTriggerTypeEnum = Field(
        default=PipelineTriggerTypeEnum.MANUAL,
        description="Source trigger initiating the pipeline run",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional custom metadata associated with the run",
    )


class PipelineRunMetrics(BaseModel):
    """Detailed operational metrics aggregated across pipeline execution phases."""

    model_config = ConfigDict(from_attributes=True)

    # Discovery & Normalization
    jobs_discovered: int = Field(default=0, description="Total raw jobs discovered from sources")
    jobs_created: int = Field(default=0, description="New raw source records persisted")
    jobs_updated: int = Field(default=0, description="Existing raw source records updated")
    jobs_normalized: int = Field(default=0, description="Raw records successfully normalized")
    jobs_deduplicated: int = Field(
        default=0, description="Records deduplicated into canonical jobs"
    )

    # Matching
    jobs_evaluated: int = Field(default=0, description="Jobs evaluated for eligibility and scoring")
    matches_created: int = Field(default=0, description="Candidate-specific match records created")
    matches_qualified: int = Field(
        default=0, description="Matches meeting the qualification threshold"
    )

    # Semantic Analysis
    semantic_analyses_completed: int = Field(
        default=0, description="LLM semantic evaluations completed"
    )
    semantic_analyses_failed: int = Field(
        default=0, description="LLM semantic evaluations that encountered errors"
    )

    # Resume Tailoring
    resumes_generated: int = Field(
        default=0, description="Validated tailored PDF resumes successfully generated"
    )
    resumes_failed: int = Field(
        default=0, description="Tailoring or PDF validation attempts that failed"
    )

    # Notifications
    notifications_sent: int = Field(
        default=0, description="Candidate email notifications successfully delivered"
    )
    notifications_failed: int = Field(
        default=0, description="Candidate email notifications that failed delivery"
    )


class PipelineRunSummary(BaseModel):
    """High-level summary of a pipeline run suitable for lists and dashboards."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    trigger_type: PipelineTriggerTypeEnum
    status: PipelineRunStatusEnum
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    jobs_discovered: int = 0
    matches_qualified: int = 0
    resumes_generated: int = 0
    notifications_sent: int = 0
    error_summary: str | None = None


class PipelineRunRead(BaseModel):
    """Complete detail representation of an orchestrated pipeline run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    trigger_type: PipelineTriggerTypeEnum
    status: PipelineRunStatusEnum
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    metrics: PipelineRunMetrics
    error_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="run_metadata")


class PipelineRunListResponse(BaseModel):
    """Paginated collection of pipeline runs."""

    items: list[PipelineRunSummary]
    pagination: PaginationMetadata


class PipelineRunCancelResponse(BaseModel):
    """Response returned upon successfully requesting pipeline run cancellation."""

    pipeline_run_id: uuid.UUID
    status: PipelineRunStatusEnum
    message: str
