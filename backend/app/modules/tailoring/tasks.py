"""Celery asynchronous tasks for Resume Tailoring and PDF generation."""

import asyncio
import logging
import uuid
from typing import Any

from celery import Task

from app.database.session import get_session_factory
from app.infrastructure.redis import get_redis
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.service import get_tailoring_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.tailoring.tasks.generate_tailored_resume_task",
    queue="tailoring",
    max_retries=2,
    soft_time_limit=180,
    time_limit=240,
)
def generate_tailored_resume_task(self: Task, tailored_resume_id: str) -> dict[str, Any]:
    """Execute end-to-end resume tailoring pipeline for a requested tailored resume."""
    return asyncio.run(_async_generate_tailored_resume(self, tailored_resume_id))


async def _async_generate_tailored_resume(
    task: Task, tailored_resume_id_str: str
) -> dict[str, Any]:
    """Async worker driving the resume tailoring pipeline with distributed locking."""
    try:
        resume_uuid = uuid.UUID(tailored_resume_id_str)
    except ValueError:
        logger.error(
            f"Invalid UUID string provided for tailored_resume_id: {tailored_resume_id_str}"
        )
        return {"status": "FAILED", "reason": "invalid_tailored_resume_uuid"}

    session_factory = get_session_factory()
    service = get_tailoring_service()
    redis_client = get_redis()
    lock_key = f"lock:tailoring:{resume_uuid}"

    # Distributed lock protection (timeout 200s covers soft task limit)
    acquired = False
    lock = None
    try:
        lock = redis_client.lock(lock_key, timeout=200.0, blocking_timeout=5.0)
        acquired = await lock.acquire()
    except Exception as redis_exc:
        logger.warning(
            f"Redis lock error for tailoring record {tailored_resume_id_str}: {redis_exc}; proceeding unlocked."
        )
        lock = None
        acquired = True

    if not acquired:
        logger.info(
            f"Another worker is already processing tailoring record {tailored_resume_id_str}; skipping."
        )
        return {"status": "LOCKED", "tailored_resume_id": tailored_resume_id_str}

    try:
        async with session_factory() as session:
            # Check idempotency: if already COMPLETED, avoid re-running
            existing = await service.repository.get_by_id(
                session=session,
                tailored_resume_id=resume_uuid,
                load_relations=False,
            )
            if existing and existing.generation_status == TailoredResumeStatusEnum.COMPLETED:
                return {
                    "status": "ALREADY_COMPLETED",
                    "tailored_resume_id": tailored_resume_id_str,
                    "storage_key": existing.storage_key,
                }

            record = await service.execute_tailoring_pipeline(
                session=session,
                tailored_resume_id=resume_uuid,
            )
            await session.commit()

            # Milestone 9 Pipeline Integration:
            # Trigger immediate email notification task if tailoring completed successfully
            delivery_id = None
            if record.generation_status == TailoredResumeStatusEnum.COMPLETED:
                try:
                    from app.modules.notifications.service import get_notification_service
                    from app.modules.notifications.tasks import send_email_notification_task

                    notif_service = get_notification_service()
                    delivery = await notif_service.create_or_get_delivery_for_tailored_resume(
                        session=session,
                        tailored_resume_id=record.id,
                    )
                    await session.commit()
                    delivery_id = str(delivery.id)
                    send_email_notification_task.delay(delivery_id)
                    logger.info(
                        f"Scheduled immediate email notification task for delivery {delivery_id}"
                    )
                except Exception as notif_exc:
                    logger.warning(
                        f"Could not dispatch email notification for tailored resume {record.id}: {notif_exc}"
                    )

            return {
                "status": "SUCCESS"
                if record.generation_status == TailoredResumeStatusEnum.COMPLETED
                else "FAILED",
                "tailored_resume_id": str(record.id),
                "generation_status": record.generation_status.value,
                "file_name": record.file_name,
                "file_size_bytes": record.file_size_bytes,
                "checksum_sha256": record.checksum_sha256,
                "validation_error": record.validation_error,
                "notification_delivery_id": delivery_id,
            }
    except Exception as exc:
        logger.warning(
            f"Error during resume tailoring pipeline for record {tailored_resume_id_str}: {exc}. Retrying..."
        )
        retry_delay = 10 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc
    finally:
        if lock is not None and acquired:
            try:
                await lock.release()
            except Exception:
                pass
