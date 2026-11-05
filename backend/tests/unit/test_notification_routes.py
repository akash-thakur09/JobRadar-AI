"""Unit tests for Notification Deliveries API endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.main import create_app
from app.modules.jobs.models import Job
from app.modules.matching.models import JobMatch
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.exceptions import (
    DeliveryMaxRetriesExceededError,
    DeliveryNotFoundError,
    InvalidStateTransitionError,
)
from app.modules.notifications.models import NotificationDelivery
from app.modules.notifications.schemas import (
    NotificationDeliveryListResponse,
    NotificationDeliverySummary,
)
from app.modules.notifications.service import get_notification_service
from app.modules.resumes.schemas import PaginationMetadata


@pytest.fixture
def mock_notif_service() -> MagicMock:
    """Fixture providing mock NotificationService."""
    return MagicMock()


@pytest.fixture
def client(mock_notif_service: MagicMock) -> httpx.AsyncClient:
    """Async test client with dependency overrides."""
    app = create_app()
    app.dependency_overrides[get_notification_service] = lambda: mock_notif_service
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
async def test_list_notifications_endpoint(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """GET /api/v1/notifications returns 200 OK with paginated deliveries."""
    delivery_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_id = uuid.uuid4()

    summary = NotificationDeliverySummary(
        id=delivery_id,
        candidate_profile_id=candidate_id,
        job_id=job_id,
        job_match_id=uuid.uuid4(),
        tailored_resume_id=uuid.uuid4(),
        notification_type="IMMEDIATE_TAILORED_JOB",
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.SENT,
        attempt_count=1,
        max_attempts=3,
        provider="mock",
        provider_message_id="<test@jobradar.ai>",
        sent_at=datetime.now(UTC),
        failed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    pagination = PaginationMetadata(
        page=1,
        page_size=20,
        total_items=1,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )

    mock_notif_service.list_deliveries = AsyncMock(
        return_value=NotificationDeliveryListResponse(items=[summary], pagination=pagination)
    )

    response = await client.get("/api/v1/notifications")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(delivery_id)
    assert data["pagination"]["total_items"] == 1


@pytest.mark.unit
async def test_get_notification_endpoint_success(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """GET /api/v1/notifications/{id} returns 200 OK with detailed delivery fields."""
    delivery_id = uuid.uuid4()
    job = Job(id=uuid.uuid4(), canonical_company_name="Acme", title="Engineer")
    job_match = JobMatch(id=uuid.uuid4(), final_score=95.0)

    delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=job.id,
        job_match_id=job_match.id,
        tailored_resume_id=uuid.uuid4(),
        notification_type="IMMEDIATE_TAILORED_JOB",
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.SENT,
        attempt_count=1,
        max_attempts=3,
        provider="smtp",
        provider_message_id="<msg-123@jobradar.ai>",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    delivery.job = job
    delivery.job_match = job_match

    mock_notif_service.get_delivery = AsyncMock(return_value=delivery)

    response = await client.get(f"/api/v1/notifications/{delivery_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(delivery_id)
    assert data["recipient_email"] == "candidate@example.com"
    assert data["company_name"] == "Acme"
    assert data["job_title"] == "Engineer"


@pytest.mark.unit
async def test_get_notification_endpoint_not_found(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """GET /api/v1/notifications/{id} with unknown ID returns 404 RFC 7807 problem details."""
    delivery_id = uuid.uuid4()
    mock_notif_service.get_delivery = AsyncMock(side_effect=DeliveryNotFoundError(delivery_id))

    response = await client.get(f"/api/v1/notifications/{delivery_id}")

    assert response.status_code == 404
    data = response.json()
    assert "was not found" in data["detail"]


@pytest.mark.unit
async def test_retry_notification_endpoint_success(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """POST /api/v1/notifications/{id}/retry returns 202 Accepted and dispatches background task."""
    delivery_id = uuid.uuid4()
    retried_delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        tailored_resume_id=uuid.uuid4(),
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.PENDING,
    )
    mock_notif_service.retry_delivery = AsyncMock(return_value=retried_delivery)

    with patch(
        "app.api.routes.notifications.send_email_notification_task.delay"
    ) as mock_celery_task:
        response = await client.post(f"/api/v1/notifications/{delivery_id}/retry")

        assert response.status_code == 202
        data = response.json()
        assert data["delivery_id"] == str(delivery_id)
        assert data["status"] == "PENDING"
        mock_celery_task.assert_called_once_with(str(delivery_id))


@pytest.mark.unit
async def test_retry_notification_endpoint_invalid_state_conflict(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """POST /api/v1/notifications/{id}/retry on SENT returns 409 Conflict."""
    delivery_id = uuid.uuid4()
    mock_notif_service.retry_delivery = AsyncMock(
        side_effect=InvalidStateTransitionError(
            current_status="SENT",
            target_status="PENDING",
            reason="Cannot retry an already delivered notification.",
        )
    )

    response = await client.post(f"/api/v1/notifications/{delivery_id}/retry")

    assert response.status_code == 409
    data = response.json()
    assert "Cannot transition notification delivery" in data["detail"]


@pytest.mark.unit
async def test_retry_notification_endpoint_max_retries_exceeded(
    client: httpx.AsyncClient, mock_notif_service: MagicMock
):
    """POST /api/v1/notifications/{id}/retry when max retries exceeded returns 400."""
    delivery_id = uuid.uuid4()
    mock_notif_service.retry_delivery = AsyncMock(
        side_effect=DeliveryMaxRetriesExceededError(
            delivery_id=delivery_id,
            attempt_count=3,
            max_attempts=3,
        )
    )

    response = await client.post(f"/api/v1/notifications/{delivery_id}/retry")

    assert response.status_code == 400
    data = response.json()
    assert "has reached maximum retry attempts" in data["detail"]

