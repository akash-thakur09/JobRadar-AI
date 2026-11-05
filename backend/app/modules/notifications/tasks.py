"""Celery background tasks for asynchronous, reliable email notification delivery."""

import asyncio
import logging
import random
import uuid
from typing import Any

from celery import Task

from app.database.session import get_session_factory
from app.infrastructure.redis import get_redis
from app.modules.notifications.email.exceptions import (
    EmailConnectionError,
    EmailTimeoutError,
)
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.service import get_notification_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.notifications.tasks.send_email_notification_task",
    queue="notifications",
    max_retries=3,
    soft_time_limit=30,
    time_limit=45,
)
def send_email_notification_task(self: Task, notification_id: str) -> dict[str, Any]:
    """Execute asynchronous email transmission for a target NotificationDelivery record."""
    return asyncio.run(_async_send_email_notification(self, notification_id))


async def _async_send_email_notification(task: Task, notification_id_str: str) -> dict[str, Any]:
    """Async worker driving email notification delivery with distributed locking and idempotent state checks."""
    try:
        delivery_uuid = uuid.UUID(notification_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for notification_id: {notification_id_str}")
        return {"status": "FAILED", "reason": "invalid_notification_uuid"}

    session_factory = get_session_factory()
    service = get_notification_service()
    redis_client = get_redis()
    lock_key = f"lock:notification_delivery:{delivery_uuid}"

    # Distributed lock protection
    acquired = False
    lock = None
    try:
        lock = redis_client.lock(lock_key, timeout=60.0, blocking_timeout=3.0)
        acquired = await lock.acquire()
    except Exception as redis_exc:
        logger.warning(
            f"Redis lock error for notification {notification_id_str}: {redis_exc}; proceeding unlocked."
        )
        lock = None
        acquired = True

    if not acquired:
        logger.info(
            f"Another worker is already processing notification delivery {notification_id_str}; skipping."
        )
        return {"status": "LOCKED", "notification_id": notification_id_str}

    try:
        async with session_factory() as session:
            # 1. Idempotency pre-flight check: if already SENT, avoid duplicate dispatch
            existing = await service.repository.get_by_id(
                session=session,
                delivery_id=delivery_uuid,
                load_relations=False,
            )
            if existing and existing.status == NotificationDeliveryStatusEnum.SENT:
                logger.info(
                    f"Notification {notification_id_str} is already SENT; terminating task."
                )
                return {
                    "status": "ALREADY_SENT",
                    "notification_id": notification_id_str,
                    "provider_message_id": existing.provider_message_id,
                }

            # 2. Execute delivery pipeline
            try:
                record = await service.execute_delivery_pipeline(
                    session=session,
                    delivery_id=delivery_uuid,
                )
                await session.commit()

                return {
                    "status": record.status.value,
                    "notification_id": str(record.id),
                    "recipient_email": record.recipient_email,
                    "provider_message_id": record.provider_message_id,
                    "attempt_count": record.attempt_count,
                }

            except (EmailTimeoutError, EmailConnectionError) as retryable_exc:
                await session.commit()
                logger.warning(
                    f"Transient delivery error for notification {notification_id_str} on attempt {task.request.retries + 1}: {retryable_exc}"
                )
                if task.request.retries < task.max_retries:
                    backoff = min(10 * (2**task.request.retries) + random.uniform(1.0, 5.0), 300)
                    raise task.retry(exc=retryable_exc, countdown=backoff) from retryable_exc
                return {
                    "status": "FAILED",
                    "notification_id": notification_id_str,
                    "reason": f"Max retries exceeded: {retryable_exc}",
                }

            except Exception as unhandled_exc:
                await session.commit()
                logger.error(
                    f"Non-retryable failure for notification {notification_id_str}: {unhandled_exc}",
                    exc_info=True,
                )
                return {
                    "status": "FAILED",
                    "notification_id": notification_id_str,
                    "reason": str(unhandled_exc),
                }

    finally:
        if lock is not None and acquired:
            try:
                await lock.release()
            except Exception as release_exc:
                logger.debug(
                    f"Failed to release Redis lock for notification {notification_id_str}: {release_exc}"
                )
