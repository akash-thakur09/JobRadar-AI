"""Database repository for persisting and querying PipelineRun entities."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.models import PipelineRun


class PipelineRunRepository:
    """Repository handling CRUD, atomic metric updates, and active-run queries for PipelineRun."""

    async def create(self, session: AsyncSession, run: PipelineRun) -> PipelineRun:
        """Persist a new PipelineRun record."""
        session.add(run)
        await session.flush()
        return run

    async def get_by_id(self, session: AsyncSession, run_id: uuid.UUID) -> PipelineRun | None:
        """Retrieve a pipeline run by primary key ID."""
        stmt = select(PipelineRun).where(PipelineRun.id == run_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_run_for_candidate(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> PipelineRun | None:
        """Find any currently active (PENDING or RUNNING) pipeline run for the candidate."""
        stmt = (
            select(PipelineRun)
            .where(
                PipelineRun.candidate_profile_id == candidate_profile_id,
                PipelineRun.status.in_(
                    [PipelineRunStatusEnum.PENDING, PipelineRunStatusEnum.RUNNING]
                ),
            )
            .order_by(PipelineRun.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        target_status: PipelineRunStatusEnum,
        error_summary: str | None = None,
    ) -> PipelineRun | None:
        """Transition status of a pipeline run enforcing transition rules."""
        run = await self.get_by_id(session, run_id)
        if run is None:
            return None

        run.transition_to(target_status, error_summary=error_summary)
        await session.flush()
        return run

    async def increment_metrics_atomic(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        **metric_increments: int,
    ) -> None:
        """Atomically increment operational metrics using database-level addition.

        Guarantees thread-safe and process-safe counter updates without lost-update races.
        Example: increment_metrics_atomic(session, run_id, jobs_discovered=10, jobs_created=5)
        """
        valid_metric_fields = {
            "jobs_discovered",
            "jobs_created",
            "jobs_updated",
            "jobs_normalized",
            "jobs_deduplicated",
            "jobs_evaluated",
            "matches_created",
            "matches_qualified",
            "semantic_analyses_completed",
            "semantic_analyses_failed",
            "resumes_generated",
            "resumes_failed",
            "notifications_sent",
            "notifications_failed",
        }

        values_to_update: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        for field, amount in metric_increments.items():
            if field in valid_metric_fields and amount != 0:
                col = getattr(PipelineRun, field)
                values_to_update[field] = col + amount

        if len(values_to_update) > 1:
            stmt = update(PipelineRun).where(PipelineRun.id == run_id).values(**values_to_update)
            await session.execute(stmt)
            await session.flush()

    async def list_runs(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        status: PipelineRunStatusEnum | None = None,
        trigger_type: PipelineTriggerTypeEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PipelineRun], int]:
        """Query paginated pipeline runs with optional filters."""
        query = select(PipelineRun)
        count_query = select(func.count(PipelineRun.id))

        if candidate_profile_id is not None:
            query = query.where(PipelineRun.candidate_profile_id == candidate_profile_id)
            count_query = count_query.where(
                PipelineRun.candidate_profile_id == candidate_profile_id
            )

        if status is not None:
            query = query.where(PipelineRun.status == status)
            count_query = count_query.where(PipelineRun.status == status)

        if trigger_type is not None:
            query = query.where(PipelineRun.trigger_type == trigger_type)
            count_query = count_query.where(PipelineRun.trigger_type == trigger_type)

        total_result = await session.execute(count_query)
        total = total_result.scalar_one() or 0

        offset = (page - 1) * page_size
        query = query.order_by(PipelineRun.created_at.desc()).offset(offset).limit(page_size)

        result = await session.execute(query)
        runs = list(result.scalars().all())

        return runs, total
