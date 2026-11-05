"""Pydantic schemas and DTOs for Canonical Jobs and Normalization."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum
from app.modules.jobs.models import JobStatusEnum


class PaginationMetadata(BaseModel):
    """Standard pagination envelope metadata."""

    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total count of matching items")
    total_pages: int = Field(ge=0, description="Total pages available")
    has_next: bool = Field(description="Whether a next page exists")
    has_prev: bool = Field(description="Whether a previous page exists")


class PaginatedResponse[T](BaseModel):
    """Generic envelope for paginated resource collections."""

    items: list[T]
    pagination: PaginationMetadata


class NormalizedJobDTO(BaseModel):
    """Internal provider-independent normalized job representation."""

    model_config = ConfigDict(extra="ignore")

    source_record_id: uuid.UUID
    job_source_id: uuid.UUID
    external_job_id: str
    company_name: str
    title: str
    description_text: str
    application_url: str
    normalized_location: str | None = None
    workplace_type: WorkplaceTypeEnum = WorkplaceTypeEnum.UNKNOWN
    employment_type: EmploymentTypeEnum = EmploymentTypeEnum.UNKNOWN
    posted_at: datetime | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    normalization_warnings: list[str] = Field(default_factory=list)


class JobSourceRecordResponse(BaseModel):
    """Provenance and raw payload audit record for a discovered job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_source_id: uuid.UUID
    external_job_id: str
    source_job_url: str
    raw_payload: dict[str, Any]
    raw_posted_at: str | None = None
    payload_hash_sha256: str
    processing_status: str
    processing_error: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime


class JobSummaryResponse(BaseModel):
    """Compact summary of a canonical job opportunity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_company_name: str
    title: str
    canonical_application_url: str
    workplace_type: WorkplaceTypeEnum
    normalized_location: str | None = None
    employment_type: EmploymentTypeEnum
    posted_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    status: JobStatusEnum
    created_at: datetime


class JobDetailResponse(JobSummaryResponse):
    """Full detail of a canonical job including sanitized description and source provenance."""

    description_text: str
    dedup_fingerprint_sha256: str
    source_count: int = 1
    sources: list[JobSourceRecordResponse] = []


class JobProcessPendingResponse(BaseModel):
    """Summary of batch normalization trigger execution."""

    queued_count: int
    processed_count: int
    message: str
