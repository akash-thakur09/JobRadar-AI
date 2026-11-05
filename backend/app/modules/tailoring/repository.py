"""Data access repository for TailoredResume persistence and queries."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume


class TailoringRepository:
    """Async repository managing database operations for TailoredResume entities."""

    async def get_by_id(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
        load_relations: bool = True,
    ) -> TailoredResume | None:
        """Fetch a tailored resume by ID with optional eager loading of relationships."""
        stmt = select(TailoredResume).where(TailoredResume.id == tailored_resume_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(TailoredResume.candidate_profile),
                selectinload(TailoredResume.job),
                selectinload(TailoredResume.job_match),
                selectinload(TailoredResume.resume_version),
            )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_job_and_version(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        resume_version_id: uuid.UUID,
    ) -> TailoredResume | None:
        """Fetch tailored resume by unique constraint (job_id, resume_version_id)."""
        stmt = (
            select(TailoredResume)
            .where(
                TailoredResume.job_id == job_id,
                TailoredResume.resume_version_id == resume_version_id,
            )
            .options(
                selectinload(TailoredResume.candidate_profile),
                selectinload(TailoredResume.job),
                selectinload(TailoredResume.job_match),
                selectinload(TailoredResume.resume_version),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_job_match(
        self,
        session: AsyncSession,
        job_match_id: uuid.UUID,
    ) -> TailoredResume | None:
        """Fetch tailored resume associated with a specific JobMatch."""
        stmt = (
            select(TailoredResume)
            .where(TailoredResume.job_match_id == job_match_id)
            .order_by(TailoredResume.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        job_id: uuid.UUID,
        job_match_id: uuid.UUID,
        resume_version_id: uuid.UUID,
        rendering_strategy: RenderingStrategyEnum = RenderingStrategyEnum.FALLBACK,
        generation_status: TailoredResumeStatusEnum = TailoredResumeStatusEnum.PENDING,
    ) -> TailoredResume:
        """Persist a new TailoredResume record in initial status."""
        tailored_resume = TailoredResume(
            candidate_profile_id=candidate_profile_id,
            job_id=job_id,
            job_match_id=job_match_id,
            resume_version_id=resume_version_id,
            rendering_strategy=rendering_strategy,
            generation_status=generation_status,
            tailored_content={},
            validation_metadata={},
            generation_attempts=1,
        )
        session.add(tailored_resume)
        await session.flush()
        await session.refresh(tailored_resume)
        return tailored_resume

    async def list_for_candidate(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TailoredResume], int]:
        """Fetch paginated tailored resumes for a candidate profile."""
        count_stmt = select(func.count(TailoredResume.id)).where(
            TailoredResume.candidate_profile_id == candidate_profile_id
        )
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar_one()

        offset = (page - 1) * page_size
        items_stmt = (
            select(TailoredResume)
            .where(TailoredResume.candidate_profile_id == candidate_profile_id)
            .order_by(TailoredResume.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items_result = await session.execute(items_stmt)
        items = list(items_result.scalars().all())

        return items, total_count

    async def save(self, session: AsyncSession, tailored_resume: TailoredResume) -> TailoredResume:
        """Save updates to a tailored resume record."""
        await session.flush()
        await session.refresh(tailored_resume)
        return tailored_resume
