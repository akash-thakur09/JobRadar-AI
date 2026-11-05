"""Unit tests for asynchronous Celery notification delivery tasks."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.notifications.email.exceptions import EmailTimeoutError
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.models import NotificationDelivery
from app.modules.notifications.tasks import _async_send_email_notification


@pytest.mark.unit
async def test_notification_task_invalid_uuid():
    """Passing an invalid UUID string aborts with status FAILED without querying database."""
    mock_task = MagicMock()
    result = await _async_send_email_notification(mock_task, "not-a-valid-uuid")

    assert result["status"] == "FAILED"
    assert result["reason"] == "invalid_notification_uuid"


@pytest.mark.unit
async def test_notification_task_already_sent_idempotency():
    """If delivery is already SENT, worker returns ALREADY_SENT without re-dispatching email."""
    mock_task = MagicMock()
    delivery_id = uuid.uuid4()

    mock_delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        tailored_resume_id=uuid.uuid4(),
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.SENT,
        provider_message_id="<sent-123@jobradar.ai>",
    )

    mock_service = MagicMock()
    mock_service.repository.get_by_id = AsyncMock(return_value=mock_delivery)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch(
        "app.modules.notifications.tasks.get_notification_service",
        return_value=mock_service,
    ):
        with patch(
            "app.modules.notifications.tasks.get_session_factory",
            return_value=mock_session_factory,
        ):
            result = await _async_send_email_notification(mock_task, str(delivery_id))

    assert result["status"] == "ALREADY_SENT"
    assert result["notification_id"] == str(delivery_id)
    assert result["provider_message_id"] == "<sent-123@jobradar.ai>"
    mock_service.execute_delivery_pipeline.assert_not_called()


@pytest.mark.unit
async def test_notification_task_successful_execution():
    """Worker executes delivery pipeline, commits transaction, and returns SENT status."""
    mock_task = MagicMock()
    delivery_id = uuid.uuid4()

    mock_delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        tailored_resume_id=uuid.uuid4(),
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.PENDING,
    )

    sent_delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=mock_delivery.candidate_profile_id,
        job_id=mock_delivery.job_id,
        job_match_id=mock_delivery.job_match_id,
        tailored_resume_id=mock_delivery.tailored_resume_id,
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.SENT,
        provider_message_id="<msg-456@jobradar.ai>",
        attempt_count=1,
    )

    mock_service = MagicMock()
    mock_service.repository.get_by_id = AsyncMock(return_value=mock_delivery)
    mock_service.execute_delivery_pipeline = AsyncMock(return_value=sent_delivery)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch(
        "app.modules.notifications.tasks.get_notification_service",
        return_value=mock_service,
    ):
        with patch(
            "app.modules.notifications.tasks.get_session_factory",
            return_value=mock_session_factory,
        ):
            result = await _async_send_email_notification(mock_task, str(delivery_id))

    assert result["status"] == "SENT"
    assert result["notification_id"] == str(delivery_id)
    assert result["provider_message_id"] == "<msg-456@jobradar.ai>"
    mock_session.commit.assert_called_once()


@pytest.mark.unit
async def test_notification_task_retries_on_timeout():
    """Transient timeout triggers task.retry with exponential backoff countdown."""
    mock_task = MagicMock()
    mock_task.request.retries = 0
    mock_task.max_retries = 3
    mock_task.retry = MagicMock(side_effect=Exception("RetryTriggered"))

    delivery_id = uuid.uuid4()
    mock_delivery = NotificationDelivery(
        id=delivery_id,
        candidate_profile_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        job_match_id=uuid.uuid4(),
        tailored_resume_id=uuid.uuid4(),
        recipient_email="candidate@example.com",
        status=NotificationDeliveryStatusEnum.PENDING,
    )

    mock_service = MagicMock()
    mock_service.repository.get_by_id = AsyncMock(return_value=mock_delivery)
    mock_service.execute_delivery_pipeline = AsyncMock(
        side_effect=EmailTimeoutError("SMTP timed out")
    )

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch(
        "app.modules.notifications.tasks.get_notification_service",
        return_value=mock_service,
    ):
        with patch(
            "app.modules.notifications.tasks.get_session_factory",
            return_value=mock_session_factory,
        ):
            with pytest.raises(Exception, match="RetryTriggered"):
                await _async_send_email_notification(mock_task, str(delivery_id))

    mock_task.retry.assert_called_once()

