"""Domain service orchestrating pipeline runs, scheduling, and reliable execution."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.redis import get_redis
from app.modules.candidate.repository import CandidateRepository
from app.modules.discovery.adapters.registry import get_adapter_for_source_type
from app.modules.discovery.models import JobSource
from app.modules.discovery.repository import DiscoveryRepository
from app.modules.jobs.service import JobService, get_job_service
from app.modules.matching.models import JobMatch
from app.modules.matching.semantic_service import SemanticAnalysisService, get_semantic_service
from app.modules.matching.service import MatchingService, get_matching_service
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.service import NotificationService, get_notification_service
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.exceptions import (
    ActivePipelineRunConflictError,
    PipelineError,
    PipelineRunNotFoundError,
)
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.repository import PipelineRunRepository
from app.modules.pipeline.schemas import (
    PipelineRunListResponse,
    PipelineRunMetrics,
    PipelineRunRead,
    PipelineRunSummary,
)
from app.modules.resumes.schemas import PaginationMetadata
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.schemas import TailorResumeRequest
from app.modules.tailoring.service import TailoringService, get_tailoring_service

logger = logging.getLogger(__name__)


class PipelineOrchestrationService:
    """Coordinates and observes end-to-end job discovery, canonicalization, matching, tailoring, and delivery."""

    def __init__(
        self,
        repository: PipelineRunRepository | None = None,
        candidate_repository: CandidateRepository | None = None,
        discovery_repository: DiscoveryRepository | None = None,
        job_service: JobService | None = None,
        matching_service: MatchingService | None = None,
        semantic_service: SemanticAnalysisService | None = None,
        tailoring_service: TailoringService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.repository = repository or PipelineRunRepository()
        self.candidate_repository = candidate_repository or CandidateRepository()
        self.discovery_repository = discovery_repository or DiscoveryRepository()
        self.job_service = job_service or get_job_service()
        self.matching_service = matching_service or get_matching_service()
        self.semantic_service = semantic_service or get_semantic_service()
        self.tailoring_service = tailoring_service or get_tailoring_service()
        self.notification_service = notification_service or get_notification_service()

    async def start_pipeline_run(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        trigger_type: PipelineTriggerTypeEnum = PipelineTriggerTypeEnum.MANUAL,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineRun:
        """Validate candidate, check active run idempotency, persist PENDING run, and enqueue Celery task.

        Returns HTTP 202 Accepted representation.
        """
        # 1. Verify candidate profile exists
        candidate = await self.candidate_repository.get_profile(session, candidate_profile_id)
        if candidate is None:
            raise PipelineError(
                f"Candidate profile '{candidate_profile_id}' does not exist.",
                status_code=404,
                error_type="candidate-profile-not-found",
            )

        # 2. Prevent overlapping runs for the same candidate (Database Check)
        active_run = await self.repository.get_active_run_for_candidate(
            session, candidate_profile_id
        )
        if active_run is not None:
            logger.warning(
                f"Active pipeline run '{active_run.id}' already exists for candidate '{candidate_profile_id}'"
            )
            raise ActivePipelineRunConflictError(
                candidate_profile_id=candidate_profile_id,
                active_run_id=active_run.id,
            )

        # 3. Create persistent PipelineRun in PENDING state
        pipeline_run = PipelineRun(
            candidate_profile_id=candidate_profile_id,
            trigger_type=trigger_type,
            status=PipelineRunStatusEnum.PENDING,
            run_metadata=metadata or {},
        )
        saved = await self.repository.create(session, pipeline_run)
        await session.commit()
        logger.info(
            f"Created PipelineRun '{saved.id}' for candidate '{candidate_profile_id}' (trigger: {trigger_type.value})"
        )

        # 4. Enqueue background orchestration task
        try:
            from app.modules.pipeline.tasks import execute_pipeline_run_task

            execute_pipeline_run_task.delay(str(saved.id))
            logger.info(f"Dispatched execute_pipeline_run_task for run '{saved.id}'")
        except Exception as task_dispatch_err:
            logger.warning(
                f"Could not asynchronously dispatch pipeline run task: {task_dispatch_err}. Will execute when picked up."
            )

        return saved

    async def execute_pipeline_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        batch_size: int = 100,
    ) -> PipelineRun:
        """Worker-executed orchestration pipeline coordinating discovery, matching, tailoring, and delivery."""
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise PipelineRunNotFoundError(run_id)

        if run.status.is_terminal:
            logger.info(
                f"Pipeline run '{run_id}' is already in terminal state '{run.status.value}'. Skipping execution."
            )
            return run

        settings = get_settings()
        redis_client = get_redis()
        lock_key = f"lock:pipeline_run:candidate:{run.candidate_profile_id}"
        lock = None
        acquired = False

        # Acquire distributed lock to prevent concurrent workers from running the same candidate
        try:
            lock = redis_client.lock(
                lock_key,
                timeout=float(settings.pipeline_lock_ttl_seconds),
                blocking_timeout=5.0,
            )
            acquired = await lock.acquire()
        except Exception as redis_exc:
            logger.warning(
                f"Redis lock acquisition error for candidate {run.candidate_profile_id}: {redis_exc}; proceeding unlocked."
            )
            acquired = True

        if not acquired:
            logger.warning(
                f"Concurrent worker holds lock for candidate {run.candidate_profile_id}; aborting run {run_id}."
            )
            raise ActivePipelineRunConflictError(
                candidate_profile_id=run.candidate_profile_id,
            )

        phase_errors: list[str] = []
        had_critical_failure = False

        try:
            # Transition to RUNNING
            run.transition_to(PipelineRunStatusEnum.RUNNING)
            await session.commit()
            logger.info(f"Pipeline run '{run_id}' transitioned to RUNNING.")

            # =========================================================================
            # PHASE 1: Job Discovery (Greenhouse, Lever, etc.)
            # =========================================================================
            sources_stmt = select(JobSource).where(JobSource.is_enabled.is_(True))
            sources_result = await session.execute(sources_stmt)
            sources = list(sources_result.scalars().all())

            discovered_total = 0
            created_total = 0
            updated_total = 0

            for source in sources:
                try:
                    adapter = get_adapter_for_source_type(source.source_type)
                    adapter.validate_configuration(dict(source.configuration))
                    result = await adapter.discover_jobs(
                        source.base_url, dict(source.configuration)
                    )

                    c_count, u_count = await self.discovery_repository.persist_discovered_jobs(
                        session=session,
                        job_source_id=source.id,
                        jobs=result.jobs,
                    )
                    await session.commit()

                    discovered_total += len(result.jobs)
                    created_total += c_count
                    updated_total += u_count
                except Exception as source_err:
                    err_msg = f"Discovery failed for source '{source.name}': {source_err}"
                    logger.warning(err_msg)
                    phase_errors.append(err_msg)

            await self.repository.increment_metrics_atomic(
                session,
                run_id,
                jobs_discovered=discovered_total,
                jobs_created=created_total,
                jobs_updated=updated_total,
            )
            await session.commit()

            # =========================================================================
            # PHASE 2: Job Normalization & Canonicalization
            # =========================================================================
            try:
                normalized_count = await self.job_service.process_pending_records(
                    session=session, batch_size=batch_size
                )
                await session.commit()
                await self.repository.increment_metrics_atomic(
                    session,
                    run_id,
                    jobs_normalized=normalized_count,
                    jobs_deduplicated=0,  # deduplication handled internally in canonicalization
                )
                await session.commit()
            except Exception as norm_err:
                err_msg = f"Normalization & Canonicalization phase failed: {norm_err}"
                logger.warning(err_msg)
                phase_errors.append(err_msg)

            # =========================================================================
            # PHASE 3: Deterministic Candidate Matching (Layer 1 & 2)
            # =========================================================================
            qualified_matches: list[JobMatch] = []
            try:
                unmatched_jobs = (
                    await self.matching_service.repository.get_unmatched_jobs_for_candidate(
                        session=session,
                        candidate_profile_id=run.candidate_profile_id,
                        limit=batch_size,
                    )
                )

                evaluated_count = 0
                matches_created_count = 0
                matches_qualified_count = 0

                for job in unmatched_jobs:
                    try:
                        match = await self.matching_service.evaluate_job_for_candidate(
                            session=session,
                            job_id=job.id,
                            candidate_profile_id=run.candidate_profile_id,
                        )
                        evaluated_count += 1
                        matches_created_count += 1
                        if match.is_qualified:
                            matches_qualified_count += 1
                            qualified_matches.append(match)
                    except Exception as eval_err:
                        logger.warning(f"Error evaluating match for job {job.id}: {eval_err}")
                        continue

                await session.commit()
                await self.repository.increment_metrics_atomic(
                    session,
                    run_id,
                    jobs_evaluated=evaluated_count,
                    matches_created=matches_created_count,
                    matches_qualified=matches_qualified_count,
                )
                await session.commit()
            except Exception as match_err:
                err_msg = f"Matching phase failed: {match_err}"
                logger.warning(err_msg)
                phase_errors.append(err_msg)

            # =========================================================================
            # PHASE 4: Downstream Qualified Workflows (Semantic, Tailoring, Notifications)
            # =========================================================================
            for q_match in qualified_matches:
                # 4A. Layer 3 Semantic Analysis
                try:
                    semantic_match = await self.semantic_service.evaluate_semantic_match(
                        session=session, match_id=q_match.id
                    )
                    await session.commit()
                    await self.repository.increment_metrics_atomic(
                        session, run_id, semantic_analyses_completed=1
                    )
                    await session.commit()
                except Exception as sem_err:
                    logger.warning(f"Semantic analysis failed for match {q_match.id}: {sem_err}")
                    phase_errors.append(f"Semantic analysis for match {q_match.id}: {sem_err}")
                    await self.repository.increment_metrics_atomic(
                        session, run_id, semantic_analyses_failed=1
                    )
                    await session.commit()
                    semantic_match = q_match

                # 4B. Resume Tailoring (only if still qualified)
                if semantic_match.is_qualified:
                    tailored_success = False
                    tailored_record = None
                    try:
                        tailor_request = TailorResumeRequest(job_match_id=q_match.id)
                        tailored_record = await self.tailoring_service.request_tailoring(
                            session=session, request=tailor_request
                        )
                        await session.commit()

                        tailored_record = await self.tailoring_service.execute_tailoring_pipeline(
                            session=session, tailored_resume_id=tailored_record.id
                        )
                        await session.commit()

                        if tailored_record.generation_status == TailoredResumeStatusEnum.COMPLETED:
                            tailored_success = True
                            await self.repository.increment_metrics_atomic(
                                session, run_id, resumes_generated=1
                            )
                            await session.commit()
                        else:
                            await self.repository.increment_metrics_atomic(
                                session, run_id, resumes_failed=1
                            )
                            await session.commit()
                            phase_errors.append(
                                f"Tailoring for match {q_match.id}: {tailored_record.validation_error}"
                            )
                    except Exception as tail_err:
                        logger.warning(
                            f"Tailoring pipeline failed for match {q_match.id}: {tail_err}"
                        )
                        phase_errors.append(f"Tailoring for match {q_match.id}: {tail_err}")
                        await self.repository.increment_metrics_atomic(
                            session, run_id, resumes_failed=1
                        )
                        await session.commit()

                    # 4C. Immediate Email Notification Delivery
                    if tailored_success and tailored_record is not None:
                        try:
                            delivery = await self.notification_service.create_or_get_delivery_for_tailored_resume(
                                session=session, tailored_resume_id=tailored_record.id
                            )
                            await session.commit()

                            final_delivery = (
                                await self.notification_service.execute_delivery_pipeline(
                                    session=session, delivery_id=delivery.id
                                )
                            )
                            await session.commit()

                            if final_delivery.status == NotificationDeliveryStatusEnum.SENT:
                                await self.repository.increment_metrics_atomic(
                                    session, run_id, notifications_sent=1
                                )
                                await session.commit()
                            else:
                                await self.repository.increment_metrics_atomic(
                                    session, run_id, notifications_failed=1
                                )
                                await session.commit()
                                phase_errors.append(
                                    f"Notification for match {q_match.id}: {final_delivery.last_error}"
                                )
                        except Exception as notif_err:
                            logger.warning(
                                f"Notification delivery failed for tailored resume {tailored_record.id}: {notif_err}"
                            )
                            phase_errors.append(
                                f"Notification for tailored resume {tailored_record.id}: {notif_err}"
                            )
                            await self.repository.increment_metrics_atomic(
                                session, run_id, notifications_failed=1
                            )
                            await session.commit()

        except Exception as unhandled_err:
            logger.error(
                f"Critical unhandled exception during pipeline run '{run_id}': {unhandled_err}",
                exc_info=True,
            )
            had_critical_failure = True
            phase_errors.append(f"Critical execution error: {unhandled_err}")

        finally:
            # Release Redis lock
            if lock is not None and acquired:
                try:
                    await lock.release()
                except Exception:
                    pass

        # =========================================================================
        # PHASE 5: Final Status Classification & Run Finalization
        # =========================================================================
        final_run = await self.repository.get_by_id(session, run_id)
        if final_run is None:
            raise PipelineRunNotFoundError(run_id)

        error_summary_text = "; ".join(phase_errors) if phase_errors else None

        if had_critical_failure:
            target_status = PipelineRunStatusEnum.FAILED
        elif (
            len(phase_errors) > 0
            or (final_run.resumes_failed or 0) > 0
            or (final_run.notifications_failed or 0) > 0
            or (final_run.semantic_analyses_failed or 0) > 0
        ):
            target_status = PipelineRunStatusEnum.PARTIALLY_COMPLETED
        else:
            target_status = PipelineRunStatusEnum.COMPLETED

        final_run.transition_to(target_status, error_summary=error_summary_text)
        await session.commit()
        logger.info(f"Pipeline run '{run_id}' finalized with status '{target_status.value}'.")
        return final_run

    async def cancel_pipeline_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        reason: str = "User cancelled run",
    ) -> PipelineRun:
        """Cancel a non-terminal pipeline run."""
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise PipelineRunNotFoundError(run_id)

        run.transition_to(PipelineRunStatusEnum.CANCELLED, reason=reason)
        await session.commit()
        logger.info(f"Pipeline run '{run_id}' successfully cancelled.")
        return run

    async def get_pipeline_run(self, session: AsyncSession, run_id: uuid.UUID) -> PipelineRunRead:
        """Fetch complete detail representation of a pipeline run."""
        run = await self.repository.get_by_id(session, run_id)
        if run is None:
            raise PipelineRunNotFoundError(run_id)

        metrics = PipelineRunMetrics(
            jobs_discovered=run.jobs_discovered,
            jobs_created=run.jobs_created,
            jobs_updated=run.jobs_updated,
            jobs_normalized=run.jobs_normalized,
            jobs_deduplicated=run.jobs_deduplicated,
            jobs_evaluated=run.jobs_evaluated,
            matches_created=run.matches_created,
            matches_qualified=run.matches_qualified,
            semantic_analyses_completed=run.semantic_analyses_completed,
            semantic_analyses_failed=run.semantic_analyses_failed,
            resumes_generated=run.resumes_generated,
            resumes_failed=run.resumes_failed,
            notifications_sent=run.notifications_sent,
            notifications_failed=run.notifications_failed,
        )

        return PipelineRunRead(
            id=run.id,
            candidate_profile_id=run.candidate_profile_id,
            trigger_type=run.trigger_type,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
            metrics=metrics,
            error_summary=run.error_summary,
            run_metadata=run.run_metadata,
        )

    async def list_pipeline_runs(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        status: PipelineRunStatusEnum | None = None,
        trigger_type: PipelineTriggerTypeEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PipelineRunListResponse:
        """Return paginated list of pipeline runs with metadata."""
        items, total_items = await self.repository.list_runs(
            session=session,
            candidate_profile_id=candidate_profile_id,
            status=status,
            trigger_type=trigger_type,
            page=page,
            page_size=page_size,
        )

        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        summaries = [
            PipelineRunSummary(
                id=item.id,
                candidate_profile_id=item.candidate_profile_id,
                trigger_type=item.trigger_type,
                status=item.status,
                started_at=item.started_at,
                completed_at=item.completed_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
                jobs_discovered=item.jobs_discovered,
                matches_qualified=item.matches_qualified,
                resumes_generated=item.resumes_generated,
                notifications_sent=item.notifications_sent,
                error_summary=item.error_summary,
            )
            for item in items
        ]

        return PipelineRunListResponse(items=summaries, pagination=pagination)


_pipeline_service_instance: PipelineOrchestrationService | None = None


def get_pipeline_service() -> PipelineOrchestrationService:
    """Return shared PipelineOrchestrationService singleton."""
    global _pipeline_service_instance
    if _pipeline_service_instance is None:
        _pipeline_service_instance = PipelineOrchestrationService()
    return _pipeline_service_instance
