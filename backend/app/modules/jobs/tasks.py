"""Celery asynchronous background tasks for Job Normalization, Canonicalization, and Scheduling."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.database.session import get_session_factory
from app.modules.discovery.models import DiscoveryRun, DiscoveryRunStatusEnum, JobSource
from app.modules.jobs.service import get_job_service
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.jobs.tasks.process_raw_job_record_task",
    queue="processing",
    max_retries=3,
    soft_time_limit=120,
    time_limit=150,
)
def process_raw_job_record_task(self: Task, source_record_id: str) -> dict[str, Any]:
    """Execute normalization, fingerprinting, and canonicalization for a single raw record."""
    return asyncio.run(_async_process_raw_job_record(self, source_record_id))


@celery_app.task(
    name="app.modules.jobs.tasks.process_pending_raw_records_task",
    queue="processing",
    soft_time_limit=300,
    time_limit=360,
)
def process_pending_raw_records_task(batch_size: int = 100) -> dict[str, Any]:
    """Batch process pending uncanonicalized raw source records."""
    return asyncio.run(_async_process_pending_raw_records(batch_size))


@celery_app.task(
    name="app.modules.jobs.tasks.schedule_due_discovery_runs_task",
    queue="discovery",
    soft_time_limit=120,
    time_limit=150,
)
def schedule_due_discovery_runs_task() -> dict[str, Any]:
    """Periodic Celery Beat task to queue discovery runs for sources due for polling."""
    return asyncio.run(_async_schedule_due_discovery_runs())


async def _async_process_raw_job_record(task: Task, record_id_str: str) -> dict[str, Any]:
    """Async worker handling single record canonicalization with retries."""
    try:
        record_uuid = uuid.UUID(record_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for source_record_id: {record_id_str}")
        return {"status": "FAILED", "reason": "invalid_uuid"}

    session_factory = get_session_factory()
    service = get_job_service()

    try:
        async with session_factory() as session:
            job = await service.process_raw_record(session, record_uuid)
            await session.commit()

            if job:
                return {
                    "status": "SUCCESS",
                    "record_id": str(record_uuid),
                    "job_id": str(job.id),
                    "fingerprint": job.dedup_fingerprint_sha256,
                }
            return {
                "status": "NOT_FOUND",
                "record_id": str(record_uuid),
            }
    except Exception as exc:
        logger.warning(
            f"Transient or unexpected error processing raw job record {record_id_str}: {exc}. Retrying..."
        )
        retry_delay = 10 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc


async def _async_process_pending_raw_records(batch_size: int) -> dict[str, Any]:
    """Async worker handling batch canonicalization of pending records."""
    session_factory = get_session_factory()
    service = get_job_service()

    async with session_factory() as session:
        count = await service.process_pending_records(session, batch_size=batch_size)
        await session.commit()

    logger.info(f"Batch processed {count} pending raw job records.")
    return {"status": "SUCCESS", "processed_count": count}


async def _async_schedule_due_discovery_runs() -> dict[str, Any]:
    """Check all enabled JobSources and trigger discovery for those due for polling."""
    from app.modules.discovery.tasks import discover_source_jobs_task

    session_factory = get_session_factory()
    scheduled_sources: list[str] = []
    skipped_sources: list[str] = []

    async with session_factory() as session:
        sources_stmt = select(JobSource).where(JobSource.is_enabled.is_(True))
        sources = list((await session.execute(sources_stmt)).scalars().all())

        now = datetime.now(UTC)

        for source in sources:
            # Check if any run is currently running to prevent overlapping executions
            active_run_stmt = select(DiscoveryRun).where(
                DiscoveryRun.job_source_id == source.id,
                DiscoveryRun.status == DiscoveryRunStatusEnum.RUNNING,
            )
            active_run = (await session.execute(active_run_stmt)).scalar_one_or_none()
            if active_run:
                logger.info(
                    f"JobSource '{source.name}' ({source.id}) has a running discovery execution. Skipping."
                )
                skipped_sources.append(str(source.id))
                continue

            # Check timestamp of latest completed run
            latest_run_stmt = (
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.job_source_id == source.id,
                    DiscoveryRun.status == DiscoveryRunStatusEnum.COMPLETED,
                )
                .order_by(DiscoveryRun.completed_at.desc())
                .limit(1)
            )
            latest_run = (await session.execute(latest_run_stmt)).scalar_one_or_none()

            is_due = False
            if latest_run is None or latest_run.completed_at is None:
                # Never executed before
                is_due = True
            else:
                elapsed_seconds = (now - latest_run.completed_at).total_seconds()
                if elapsed_seconds >= (source.polling_interval_minutes * 60):
                    is_due = True

            if is_due:
                logger.info(
                    f"Scheduling discovery run for JobSource '{source.name}' ({source.id})."
                )
                scheduled_sources.append(str(source.id))
                discover_source_jobs_task.delay(str(source.id))

    return {
        "status": "SUCCESS",
        "scheduled_count": len(scheduled_sources),
        "scheduled_sources": scheduled_sources,
        "skipped_active_sources": skipped_sources,
    }
