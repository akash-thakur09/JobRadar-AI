"""Data access repository for JobMatch persistence and queries."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.candidate.models import CandidateProfile
from app.modules.jobs.models import Job, JobStatusEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.resumes.models import MasterResume


class MatchingRepository:
    """Async repository managing database operations for JobMatch entities."""

    async def get_match_by_id(
        self, session: AsyncSession, match_id: uuid.UUID, load_job: bool = True
    ) -> JobMatch | None:
        """Fetch a match by its primary key."""
        stmt = select(JobMatch).where(JobMatch.id == match_id)
        if load_job:
            stmt = stmt.options(selectinload(JobMatch.job))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_match_with_relations(
        self, session: AsyncSession, match_id: uuid.UUID
    ) -> JobMatch | None:
        """Fetch a match by ID loading job and candidate profile with skills."""
        stmt = (
            select(JobMatch)
            .where(JobMatch.id == match_id)
            .options(
                selectinload(JobMatch.job),
                selectinload(JobMatch.candidate_profile).selectinload(CandidateProfile.skills),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_resume_for_candidate(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> MasterResume | None:
        """Fetch candidate's active master resume along with parsed versions."""
        stmt = (
            select(MasterResume)
            .where(
                MasterResume.candidate_profile_id == candidate_profile_id,
                MasterResume.is_active == True,  # noqa: E712
            )
            .options(selectinload(MasterResume.versions))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_match_by_job_and_candidate(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        candidate_profile_id: uuid.UUID,
        load_job: bool = True,
    ) -> JobMatch | None:
        """Fetch a match record for a specific candidate and job pair."""
        stmt = select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.candidate_profile_id == candidate_profile_id,
        )
        if load_job:
            stmt = stmt.options(selectinload(JobMatch.job))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_match(self, session: AsyncSession, match_data: dict[str, Any]) -> JobMatch:
        """Atomically persist or update a candidate-job match result.

        Guarantees idempotency and prevents duplicate matches for the same (job_id, candidate_profile_id).
        """
        job_id = match_data["job_id"]
        candidate_profile_id = match_data["candidate_profile_id"]

        existing = await self.get_match_by_job_and_candidate(
            session=session,
            job_id=job_id,
            candidate_profile_id=candidate_profile_id,
            load_job=False,
        )

        now = datetime.now(UTC)

        if existing:
            for key, value in match_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = now
            await session.flush()
            await session.refresh(existing)
            return existing

        match_obj = JobMatch(**match_data)
        match_obj.created_at = now
        match_obj.updated_at = now
        session.add(match_obj)
        await session.flush()
        await session.refresh(match_obj)
        return match_obj

    async def list_matches(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        min_score: Decimal | None = None,
        eligibility_status: EligibilityStatusEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JobMatch], int]:
        """Fetch paginated matches for a candidate sorted by final score descending."""
        base_query = select(JobMatch).where(JobMatch.candidate_profile_id == candidate_profile_id)

        if eligibility_status:
            base_query = base_query.where(JobMatch.eligibility_status == eligibility_status)

        if min_score is not None:
            base_query = base_query.where(JobMatch.final_score >= min_score)

        # Count total items
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_items = (await session.execute(count_stmt)).scalar() or 0

        # Paginate results
        offset = (page - 1) * page_size
        paged_stmt = (
            base_query.options(selectinload(JobMatch.job))
            .order_by(JobMatch.final_score.desc(), JobMatch.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        matches = list((await session.execute(paged_stmt)).scalars().all())

        return matches, total_items

    async def get_unmatched_jobs_for_candidate(
        self, session: AsyncSession, candidate_profile_id: uuid.UUID, limit: int = 100
    ) -> list[Job]:
        """Query canonical jobs that have not yet been evaluated for the given candidate."""
        subquery = (
            select(JobMatch.job_id)
            .where(JobMatch.candidate_profile_id == candidate_profile_id)
            .scalar_subquery()
        )

        stmt = (
            select(Job)
            .where(
                Job.id.not_in(subquery),
                Job.status != JobStatusEnum.ARCHIVED,
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
