"""Pydantic schemas and DTOs for Job Discovery Sources and Execution Runs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.discovery.models import DiscoveryRunStatusEnum, JobSourceTypeEnum


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


class DiscoveryRunSummary(BaseModel):
    """Compact summary of a discovery execution run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_source_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    status: DiscoveryRunStatusEnum
    jobs_discovered: int
    jobs_created: int
    jobs_updated: int
    error_summary: str | None = None
    created_at: datetime


class DiscoveryRunResponse(DiscoveryRunSummary):
    """Full detail of a discovery execution run."""

    pass


class JobSourceCreateRequest(BaseModel):
    """Payload to register a new job discovery source."""

    name: str = Field(min_length=1, max_length=100, description="Human-readable identifier")
    source_type: JobSourceTypeEnum = Field(description="Platform adapter type")
    base_url: str = Field(min_length=8, max_length=512, description="API root or portal URL")
    is_enabled: bool = Field(default=True, description="Enable automatic discovery polling")
    polling_interval_minutes: int = Field(
        default=360,
        ge=15,
        le=10080,
        description="Polling interval in minutes (default: 6 hours)",
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific parameters (e.g. board_token, company_id)",
    )


class JobSourceUpdateRequest(BaseModel):
    """Partial update payload for a registered job discovery source."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=8, max_length=512)
    is_enabled: bool | None = None
    polling_interval_minutes: int | None = Field(default=None, ge=15, le=10080)
    configuration: dict[str, Any] | None = None


class JobSourceResponse(BaseModel):
    """Public representation of a job discovery source."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: JobSourceTypeEnum
    base_url: str
    is_enabled: bool
    polling_interval_minutes: int
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    latest_run: DiscoveryRunSummary | None = None


class DiscoveryTriggerRequest(BaseModel):
    """Payload to trigger immediate asynchronous discovery runs."""

    source_id: uuid.UUID | None = Field(
        default=None,
        description="Specific source UUID to trigger, or null to trigger all enabled sources.",
    )


class RawJobRecordResponse(BaseModel):
    """Detailed response for an ingested raw source record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_source_id: uuid.UUID
    job_id: uuid.UUID | None = None
    external_job_id: str
    source_job_url: str
    raw_payload: dict[str, Any]
    raw_posted_at: str | None = None
    payload_hash_sha256: str
    processing_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
