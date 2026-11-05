"""Celery asynchronous background tasks for Candidate-Job Matching and Scoring."""

import asyncio
import uuid
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from app.database.session import get_session_factory
from app.modules.matching.service import get_matching_service
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.matching.tasks.evaluate_job_matching_task",
    queue="processing",
    max_retries=3,
    soft_time_limit=30,
    time_limit=45,
)
def evaluate_job_matching_task(
    self: Task, job_id: str, candidate_profile_id: str | None = None
) -> dict[str, Any]:
    """Execute Layer 1 Eligibility and Layer 2 Scoring for a canonical job."""
    return asyncio.run(_async_evaluate_job_matching(self, job_id, candidate_profile_id))


@celery_app.task(
    name="app.modules.matching.tasks.evaluate_pending_job_matches_task",
    queue="processing",
    soft_time_limit=300,
    time_limit=360,
)
def evaluate_pending_job_matches_task(
    batch_size: int = 100, candidate_profile_id: str | None = None
) -> dict[str, Any]:
    """Batch evaluate unmatched canonical jobs for a candidate."""
    return asyncio.run(_async_evaluate_pending_matches(batch_size, candidate_profile_id))


async def _async_evaluate_job_matching(
    task: Task, job_id_str: str, candidate_profile_id_str: str | None
) -> dict[str, Any]:
    """Async worker handling candidate-job matching evaluation."""
    try:
        job_uuid = uuid.UUID(job_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for job_id: {job_id_str}")
        return {"status": "FAILED", "reason": "invalid_job_uuid"}

    candidate_uuid: uuid.UUID | None = None
    if candidate_profile_id_str:
        try:
            candidate_uuid = uuid.UUID(candidate_profile_id_str)
        except ValueError:
            logger.error(
                f"Invalid UUID string for candidate_profile_id: {candidate_profile_id_str}"
            )
            return {"status": "FAILED", "reason": "invalid_candidate_uuid"}

    session_factory = get_session_factory()
    service = get_matching_service()

    try:
        async with session_factory() as session:
            match = await service.evaluate_job_for_candidate(
                session=session,
                job_id=job_uuid,
                candidate_profile_id=candidate_uuid,
            )
            await session.commit()

            return {
                "status": "SUCCESS",
                "match_id": str(match.id),
                "job_id": str(match.job_id),
                "candidate_profile_id": str(match.candidate_profile_id),
                "eligibility_status": match.eligibility_status.value,
                "deterministic_score": float(match.deterministic_score),
                "final_score": float(match.final_score),
            }

    except Exception as exc:
        logger.warning(f"Error during matching evaluation for job {job_id_str}: {exc}. Retrying...")
        retry_delay = 5 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc


async def _async_evaluate_pending_matches(
    batch_size: int, candidate_profile_id_str: str | None
) -> dict[str, Any]:
    """Async worker batch evaluating all pending unmatched jobs."""
    candidate_uuid: uuid.UUID | None = None
    if candidate_profile_id_str:
        try:
            candidate_uuid = uuid.UUID(candidate_profile_id_str)
        except ValueError:
            logger.error(f"Invalid UUID for candidate_profile_id: {candidate_profile_id_str}")
            return {"status": "FAILED", "reason": "invalid_candidate_uuid"}

    session_factory = get_session_factory()
    service = get_matching_service()

    async with session_factory() as session:
        evaluated_count = await service.evaluate_pending_job_matches(
            session=session,
            candidate_profile_id=candidate_uuid,
            batch_size=batch_size,
        )
        await session.commit()

    logger.info(f"Batch evaluated {evaluated_count} unmatched jobs.")
    return {"status": "SUCCESS", "evaluated_count": evaluated_count}
