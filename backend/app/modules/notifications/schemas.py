"""Pydantic schemas and DTOs for the Email Notification and Delivery domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.notifications.enums import (
    NotificationDeliveryStatusEnum,
)
from app.modules.resumes.schemas import PaginationMetadata


class NotificationDeliverySummary(BaseModel):
    """Compact summary of a notification delivery record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_profile_id: uuid.UUID
    job_id: uuid.UUID
    job_match_id: uuid.UUID
    tailored_resume_id: uuid.UUID
    notification_type: str
    recipient_email: str
    status: NotificationDeliveryStatusEnum
    attempt_count: int
    max_attempts: int
    provider: str
    provider_message_id: str | None = None
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NotificationDeliveryRead(NotificationDeliverySummary):
    """Detailed representation of a notification delivery record including errors and job info."""

    last_error: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    match_score: float | None = None


class NotificationDeliveryListResponse(BaseModel):
    """Paginated collection of notification delivery records."""

    items: list[NotificationDeliverySummary]
    pagination: PaginationMetadata


class NotificationRetryRequest(BaseModel):
    """Optional request payload for manual notification retry."""

    force: bool = Field(
        default=False,
        description="Whether to override attempt count boundaries if permitted by administrative rules",
    )


class NotificationRetryResponse(BaseModel):
    """Response payload for a dispatched notification retry."""

    delivery_id: uuid.UUID
    status: NotificationDeliveryStatusEnum
    message: str
