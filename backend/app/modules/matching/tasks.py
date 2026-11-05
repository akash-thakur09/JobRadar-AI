"""Celery asynchronous background tasks for Candidate-Job Matching and Scoring."""

import asyncio
import uuid
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from app.database.session import get_session_factory
from app.infrastructure.redis import get_redis
from app.modules.matching.models import SemanticAnalysisStatusEnum
from app.modules.matching.semantic_service import get_semantic_service
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
    bind=True,
    name="app.modules.matching.tasks.evaluate_semantic_matching_task",
    queue="tailoring",
    max_retries=2,
    soft_time_limit=60,
    time_limit=90,
)
def evaluate_semantic_matching_task(self: Task, match_id: str) -> dict[str, Any]:
    """Execute Layer 3 LLM Semantic Analysis for a qualified candidate-job match."""
    return asyncio.run(_async_evaluate_semantic_matching(self, match_id))


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

            semantic_dispatched = False
            if match.is_qualified:
                try:
                    evaluate_semantic_matching_task.delay(str(match.id))
                    semantic_dispatched = True
                except Exception as dispatch_err:
                    logger.warning(
                        f"Could not dispatch semantic evaluation for match {match.id}: {dispatch_err}"
                    )

            return {
                "status": "SUCCESS",
                "match_id": str(match.id),
                "job_id": str(match.job_id),
                "candidate_profile_id": str(match.candidate_profile_id),
                "eligibility_status": match.eligibility_status.value,
                "deterministic_score": float(match.deterministic_score),
                "final_score": float(match.final_score),
                "semantic_dispatched": semantic_dispatched,
            }

    except Exception as exc:
        logger.warning(f"Error during matching evaluation for job {job_id_str}: {exc}. Retrying...")
        retry_delay = 5 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc


async def _async_evaluate_semantic_matching(task: Task, match_id_str: str) -> dict[str, Any]:
    """Async worker executing Layer 3 LLM Semantic Analysis with distributed lock."""
    try:
        match_uuid = uuid.UUID(match_id_str)
    except ValueError:
        logger.error(f"Invalid UUID string provided for match_id: {match_id_str}")
        return {"status": "FAILED", "reason": "invalid_match_uuid"}

    session_factory = get_session_factory()
    semantic_service = get_semantic_service()
    redis_client = get_redis()
    lock_key = f"lock:semantic_matching:{match_uuid}"

    # Distributed lock protection (timeout 120s covers hard task limit of 90s)
    try:
        lock = redis_client.lock(lock_key, timeout=120.0, blocking_timeout=5.0)
        acquired = await lock.acquire()
    except Exception as redis_exc:
        logger.warning(
            f"Redis lock error for match {match_id_str}: {redis_exc}; proceeding unlocked."
        )
        lock = None
        acquired = True

    if not acquired:
        logger.info(
            f"Another worker is already evaluating semantic match for {match_id_str}; skipping."
        )
        return {"status": "LOCKED", "match_id": match_id_str}

    try:
        async with session_factory() as session:
            # Check idempotency: if already COMPLETED, avoid re-running LLM
            existing = await semantic_service.repository.get_match_by_id(
                session, match_uuid, load_job=False
            )
            if (
                existing
                and existing.semantic_analysis_status == SemanticAnalysisStatusEnum.COMPLETED
            ):
                return {
                    "status": "ALREADY_COMPLETED",
                    "match_id": match_id_str,
                    "final_score": float(existing.final_score),
                }

            match = await semantic_service.evaluate_semantic_match(session, match_uuid)
            await session.commit()

            return {
                "status": "SUCCESS",
                "match_id": str(match.id),
                "semantic_status": match.semantic_analysis_status.value,
                "final_score": float(match.final_score),
                "semantic_score": float(match.semantic_score) if match.semantic_score else None,
            }
    except Exception as exc:
        logger.warning(
            f"Error during semantic matching for match {match_id_str}: {exc}. Retrying..."
        )
        retry_delay = 10 * (2**task.request.retries)
        raise task.retry(exc=exc, countdown=retry_delay) from exc
    finally:
        if lock is not None and acquired:
            try:
                await lock.release()
            except Exception:
                pass


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
