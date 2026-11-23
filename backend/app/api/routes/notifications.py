"""REST API routes for Notification Deliveries."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.schemas import (
    NotificationDeliveryListResponse,
    NotificationDeliveryRead,
    NotificationRetryRequest,
    NotificationRetryResponse,
)
from app.modules.notifications.service import (
    NotificationService,
    get_notification_service,
)
from app.modules.notifications.tasks import send_email_notification_task

router = APIRouter(prefix="/notifications", tags=["Email Notifications & Delivery"])


@router.get(
    "",
    response_model=NotificationDeliveryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notification deliveries",
    description="Retrieve paginated email delivery records with optional status and candidate filters.",
)
async def list_notifications(
    candidate_profile_id: uuid.UUID | None = Query(
        default=None, description="Filter by candidate profile ID"
    ),
    status: NotificationDeliveryStatusEnum | None = Query(
        default=None, description="Filter by delivery status"
    ),
    job_id: uuid.UUID | None = Query(default=None, description="Filter by job ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationDeliveryListResponse:
    """Query paginated notification deliveries."""
    return await service.list_deliveries(
        session=session,
        candidate_profile_id=candidate_profile_id,
        status=status,
        job_id=job_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationDeliveryRead,
    status_code=status.HTTP_200_OK,
    summary="Get notification delivery details",
    description="Retrieve complete status, timestamps, attempt counts, and errors for a specific delivery.",
)
async def get_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationDeliveryRead:
    """Fetch single notification delivery record."""
    delivery = await service.get_delivery(session=session, delivery_id=notification_id)

    job_title = delivery.job.title if delivery.job else None
    company_name = delivery.job.canonical_company_name if delivery.job else None
    match_score = float(delivery.job_match.final_score) if delivery.job_match else None

    return NotificationDeliveryRead(
        id=delivery.id,
        candidate_profile_id=delivery.candidate_profile_id,
        job_id=delivery.job_id,
        job_match_id=delivery.job_match_id,
        tailored_resume_id=delivery.tailored_resume_id,
        notification_type=delivery.notification_type,
        recipient_email=delivery.recipient_email,
        status=delivery.status,
        attempt_count=delivery.attempt_count,
        max_attempts=delivery.max_attempts,
        provider=delivery.provider,
        provider_message_id=delivery.provider_message_id,
        sent_at=delivery.sent_at,
        failed_at=delivery.failed_at,
        last_error=delivery.last_error,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
        job_title=job_title,
        company_name=company_name,
        match_score=match_score,
    )


@router.post(
    "/{notification_id}/retry",
    response_model=NotificationRetryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed notification delivery",
    description="Reset a failed notification to PENDING and re-enqueue Celery transmission task.",
)
async def retry_notification(
    notification_id: uuid.UUID,
    request: NotificationRetryRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationRetryResponse:
    """Trigger retry for failed notification delivery."""
    force = request.force if request else False
    delivery = await service.retry_delivery(
        session=session,
        delivery_id=notification_id,
        force=force,
    )
    await session.commit()

    # Dispatch Celery background task
    send_email_notification_task.delay(str(delivery.id))

    return NotificationRetryResponse(
        delivery_id=delivery.id,
        status=delivery.status,
        message="Notification delivery retry scheduled.",
    )
