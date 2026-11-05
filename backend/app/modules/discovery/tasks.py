"""Celery asynchronous background tasks for Job Discovery."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from app.database.session import get_session_factory
from app.modules.discovery.adapters.registry import get_adapter_for_source_type
from app.modules.discovery.exceptions import (
    NonRetryableDiscoveryError,
    RetryableDiscoveryError,
)
from app.modules.discovery.models import DiscoveryRunStatusEnum
from app.modules.discovery.repository import DiscoveryRepository
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.discovery.tasks.discover_source_jobs_task",
    queue="discovery",
    max_retries=3,
    soft_time_limit=300,
    time_limit=360,
)
def discover_source_jobs_task(self: Task, source_id: str) -> dict[str, Any]:
    """Execute asynchronous discovery run for a specific job source."""
    return asyncio.run(_async_discover_source_jobs(self, source_id))


async def _async_discover_source_jobs(task: Task, source_id_str: str) -> dict[str, Any]:
    """Internal async coordinator for job source discovery execution."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()

    try:
        source_uuid = uuid.UUID(source_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for source_id: {source_id_str}")
        return {"status": "FAILED", "reason": "invalid_uuid"}

    run_id: uuid.UUID | None = None

    async with session_factory() as session:
        source = await repo.get_source_by_id(session, source_uuid)
        if source is None:
            logger.warning(f"JobSource '{source_uuid}' not found. Aborting discovery.")
            return {"status": "FAILED", "reason": "source_not_found"}

        if not source.is_enabled:
            logger.info(f"JobSource '{source.name}' ({source.id}) is disabled. Skipping discovery.")
            return {"status": "SKIPPED", "reason": "source_disabled"}

        # Create discovery execution record
        run = await repo.create_discovery_run(
            session=session,
            job_source_id=source.id,
            status=DiscoveryRunStatusEnum.RUNNING,
        )
        await session.commit()
        run_id = run.id
        source_name = source.name
        source_type = source.source_type
        base_url = source.base_url
        config = dict(source.configuration)

    logger.info(f"Starting discovery run {run_id} for '{source_name}' ({source_type}).")

    try:
        adapter = get_adapter_for_source_type(source_type)
        adapter.validate_configuration(config)
        result = await adapter.discover_jobs(base_url, config)

        async with session_factory() as session:
            # Idempotently persist raw artifacts
            created_count, updated_count = await repo.persist_discovered_jobs(
                session=session,
                job_source_id=source_uuid,
                jobs=result.jobs,
            )

            # Mark discovery run as completed
            run_obj = await repo.get_discovery_run_by_id(session, run_id)
            if run_obj is not None:
                await repo.update_discovery_run(
                    session=session,
                    run=run_obj,
                    update_data={
                        "status": DiscoveryRunStatusEnum.COMPLETED,
                        "completed_at": datetime.now(UTC),
                        "jobs_discovered": len(result.jobs),
                        "jobs_created": created_count,
                        "jobs_updated": updated_count,
                        "error_summary": "; ".join(result.warnings) if result.warnings else None,
                    },
                )
            await session.commit()

        # Trigger downstream canonicalization if new or changed jobs were discovered
        if created_count > 0 or updated_count > 0:
            try:
                from app.modules.jobs.tasks import process_pending_raw_records_task

                process_pending_raw_records_task.delay(batch_size=100)
            except Exception as task_dispatch_err:
                logger.warning(
                    f"Failed to queue canonicalization after discovery run {run_id}: {task_dispatch_err}"
                )

        logger.info(
            f"Discovery run {run_id} completed successfully for '{source_name}'. "
            f"Discovered: {len(result.jobs)}, Created: {created_count}, Updated: {updated_count}."
        )
        return {
            "status": "COMPLETED",
            "run_id": str(run_id),
            "jobs_discovered": len(result.jobs),
            "jobs_created": created_count,
            "jobs_updated": updated_count,
        }

    except RetryableDiscoveryError as exc:
        logger.warning(f"Retryable error during discovery run {run_id} for '{source_name}': {exc}")
        if run_id is not None:
            await _record_run_failure(run_id, str(exc))

        # Exponential backoff retry: 30s, 60s, 120s
        retry_delay = 30 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc

    except (NonRetryableDiscoveryError, ValueError) as exc:
        logger.error(
            f"Non-retryable configuration or payload failure in run {run_id} for '{source_name}': {exc}"
        )
        if run_id is not None:
            await _record_run_failure(run_id, str(exc))
        return {"status": "FAILED", "run_id": str(run_id), "error": str(exc)}

    except Exception as exc:
        logger.exception(
            f"Unexpected unhandled error during discovery run {run_id} for '{source_name}': {exc}"
        )
        if run_id is not None:
            await _record_run_failure(run_id, f"Unhandled exception: {exc}")

        if task.request.retries < 2:
            raise task.retry(exc=exc, countdown=60) from exc
        return {"status": "FAILED", "run_id": str(run_id), "error": str(exc)}


async def _record_run_failure(run_id: uuid.UUID, error_message: str) -> None:
    """Helper to record failed status and diagnostic summary on a discovery run."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()
    try:
        async with session_factory() as session:
            run_obj = await repo.get_discovery_run_by_id(session, run_id)
            if run_obj is not None:
                await repo.update_discovery_run(
                    session=session,
                    run=run_obj,
                    update_data={
                        "status": DiscoveryRunStatusEnum.FAILED,
                        "completed_at": datetime.now(UTC),
                        "error_summary": error_message[:2000],
                    },
                )
                await session.commit()
    except Exception as err:
        logger.error(f"Failed to record failure status on run {run_id}: {err}")
