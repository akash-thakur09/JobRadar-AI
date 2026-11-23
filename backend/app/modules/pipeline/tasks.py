"""Celery asynchronous background tasks for Pipeline Orchestration and Scheduling."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import Task
from sqlalchemy import select

from app.core.runtime_settings import get_runtime_settings
from app.database.session import get_session_factory
from app.modules.candidate.models import CandidateProfile
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.service import get_pipeline_service
from app.workers.async_tasks import run_async_task
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.pipeline.tasks.execute_pipeline_run_task",
    queue="processing",
    max_retries=2,
    soft_time_limit=600,
    time_limit=720,
)
def execute_pipeline_run_task(self: Task, pipeline_run_id: str) -> dict[str, Any]:
    """Execute end-to-end pipeline orchestration run for candidate discovery, matching, and delivery."""
    return run_async_task(_async_execute_pipeline_run(self, pipeline_run_id))


@celery_app.task(
    bind=True,
    name="app.modules.pipeline.tasks.schedule_candidate_pipeline_runs_task",
    queue="processing",
    soft_time_limit=180,
    time_limit=240,
)
def schedule_candidate_pipeline_runs_task(self: Task) -> dict[str, Any]:
    """Periodic task evaluating all candidates and queuing automated discovery runs when due."""
    return run_async_task(_async_schedule_candidate_pipeline_runs(self))


async def _async_execute_pipeline_run(task: Task, pipeline_run_id_str: str) -> dict[str, Any]:
    """Async worker coordinator driving the pipeline run lifecycle."""
    try:
        run_uuid = uuid.UUID(pipeline_run_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for pipeline_run_id: {pipeline_run_id_str}")
        return {"status": "FAILED", "reason": "invalid_pipeline_run_uuid"}

    session_factory = get_session_factory()
    service = get_pipeline_service()

    try:
        async with session_factory() as session:
            final_run = await service.execute_pipeline_run(session=session, run_id=run_uuid)
            return {
                "status": final_run.status.value,
                "pipeline_run_id": str(final_run.id),
                "candidate_profile_id": str(final_run.candidate_profile_id),
                "jobs_discovered": final_run.jobs_discovered,
                "matches_qualified": final_run.matches_qualified,
                "resumes_generated": final_run.resumes_generated,
                "notifications_sent": final_run.notifications_sent,
                "error_summary": final_run.error_summary,
            }
    except Exception as exc:
        logger.error(
            f"Error during pipeline execution for run {pipeline_run_id_str}: {exc}",
            exc_info=True,
        )
        if task.request.retries < task.max_retries:
            retry_delay = 30 * (2**task.request.retries)
            raise task.retry(exc=exc, countdown=retry_delay) from exc
        return {
            "status": "FAILED",
            "pipeline_run_id": pipeline_run_id_str,
            "reason": str(exc),
        }


async def _async_schedule_candidate_pipeline_runs(_task: Task) -> dict[str, Any]:
    """Scan candidate profiles and queue automated discovery pipeline runs if due."""
    settings = get_runtime_settings()
    if not settings.pipeline_scheduler_enabled:
        logger.info("Pipeline scheduler is disabled via configuration; skipping automated run.")
        return {"status": "SKIPPED", "reason": "scheduler_disabled"}

    session_factory = get_session_factory()
    service = get_pipeline_service()
    scheduled_count = 0
    skipped_count = 0

    threshold_hours = settings.pipeline_discovery_interval_hours
    cutoff_time = datetime.now(UTC) - timedelta(hours=threshold_hours)

    async with session_factory() as session:
        # Fetch all candidate profiles
        candidates_stmt = select(CandidateProfile)
        candidates_result = await session.execute(candidates_stmt)
        candidates = list(candidates_result.scalars().all())

        for candidate in candidates:
            # Check for any active run (PENDING or RUNNING)
            active_run = await service.repository.get_active_run_for_candidate(
                session, candidate.id
            )
            if active_run is not None:
                logger.info(
                    f"Candidate {candidate.id} has an active pipeline run ({active_run.id}); skipping."
                )
                skipped_count += 1
                continue

            # Check timestamp of latest completed run
            latest_run_stmt = (
                select(PipelineRun)
                .where(
                    PipelineRun.candidate_profile_id == candidate.id,
                    PipelineRun.status.in_(
                        [
                            PipelineRunStatusEnum.COMPLETED,
                            PipelineRunStatusEnum.PARTIALLY_COMPLETED,
                        ]
                    ),
                )
                .order_by(PipelineRun.completed_at.desc())
                .limit(1)
            )
            latest_result = await session.execute(latest_run_stmt)
            latest_run = latest_result.scalar_one_or_none()

            # Schedule if candidate has never run or last run is older than threshold
            if latest_run is None or (
                latest_run.completed_at and latest_run.completed_at <= cutoff_time
            ):
                try:
                    await service.start_pipeline_run(
                        session=session,
                        candidate_profile_id=candidate.id,
                        trigger_type=PipelineTriggerTypeEnum.SCHEDULED,
                    )
                    scheduled_count += 1
                    logger.info(f"Queued scheduled pipeline run for candidate {candidate.id}")
                except Exception as sched_err:
                    logger.warning(
                        f"Failed to queue scheduled run for candidate {candidate.id}: {sched_err}"
                    )
                    skipped_count += 1
            else:
                skipped_count += 1

    return {
        "status": "SUCCESS",
        "scheduled_count": scheduled_count,
        "skipped_count": skipped_count,
    }
