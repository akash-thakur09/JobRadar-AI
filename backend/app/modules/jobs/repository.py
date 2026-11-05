"""Data access repository for Canonical Jobs and Raw Job Source Records."""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.models import Job, JobProcessingStatusEnum, JobSourceRecord, JobStatusEnum


class JobRepository:
    """Async repository providing persistence operations for canonical jobs and source records."""

    async def get_job_by_id(
        self, session: AsyncSession, job_id: uuid.UUID, load_sources: bool = True
    ) -> Job | None:
        """Fetch a canonical job by its primary key."""
        stmt = select(Job).where(Job.id == job_id)
        if load_sources:
            stmt = stmt.options(selectinload(Job.source_records))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_job_by_fingerprint(self, session: AsyncSession, fingerprint: str) -> Job | None:
        """Fetch a canonical job matching a deterministic SHA-256 fingerprint."""
        stmt = (
            select(Job)
            .options(selectinload(Job.source_records))
            .where(Job.dedup_fingerprint_sha256 == fingerprint)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_job(self, session: AsyncSession, job_data: dict[str, Any]) -> Job:
        """Persist a new canonical job record."""
        job = Job(**job_data)
        session.add(job)
        await session.flush()
        await session.refresh(job)
        return job

    async def update_job(self, session: AsyncSession, job: Job, update_data: dict[str, Any]) -> Job:
        """Apply updates to an existing canonical job."""
        for key, value in update_data.items():
            if hasattr(job, key) and value is not None:
                setattr(job, key, value)
        await session.flush()
        await session.refresh(job)
        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        search: str | None = None,
        status: JobStatusEnum | None = None,
        workplace_type: WorkplaceTypeEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """Fetch a paginated list of canonical jobs matching optional search and filter criteria."""
        base_query = select(Job)

        if status:
            base_query = base_query.where(Job.status == status)

        if workplace_type:
            base_query = base_query.where(Job.workplace_type == workplace_type)

        if search and search.strip():
            term = search.strip().replace("%", r"\%").replace("_", r"\_")
            search_filter = or_(
                Job.canonical_company_name.ilike(f"%{term}%"),
                Job.title.ilike(f"%{term}%"),
            )
            base_query = base_query.where(search_filter)

        # Count total matching records
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_items = (await session.execute(count_stmt)).scalar() or 0

        # Paginate results
        offset = (page - 1) * page_size
        paged_stmt = (
            base_query.options(selectinload(Job.source_records))
            .order_by(Job.first_seen_at.desc(), Job.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        jobs = list((await session.execute(paged_stmt)).scalars().all())

        return jobs, total_items

    async def get_source_record_by_id(
        self, session: AsyncSession, record_id: uuid.UUID, for_update: bool = False
    ) -> JobSourceRecord | None:
        """Fetch a job source record with optional row-level exclusive lock."""
        stmt = (
            select(JobSourceRecord)
            .options(selectinload(JobSourceRecord.job_source))
            .where(JobSourceRecord.id == record_id)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_source_records_for_job(
        self, session: AsyncSession, job_id: uuid.UUID
    ) -> list[JobSourceRecord]:
        """Fetch all raw source records associated with a canonical job."""
        stmt = (
            select(JobSourceRecord)
            .options(selectinload(JobSourceRecord.job_source))
            .where(JobSourceRecord.job_id == job_id)
            .order_by(JobSourceRecord.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_source_records(
        self, session: AsyncSession, limit: int = 100
    ) -> list[JobSourceRecord]:
        """Fetch raw source records that need canonicalization processing."""
        stmt = (
            select(JobSourceRecord)
            .options(selectinload(JobSourceRecord.job_source))
            .where(
                JobSourceRecord.processing_status.in_(
                    [JobProcessingStatusEnum.RAW.value, JobProcessingStatusEnum.PROCESSING.value]
                )
            )
            .order_by(JobSourceRecord.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_source_record(
        self, session: AsyncSession, record: JobSourceRecord, update_data: dict[str, Any]
    ) -> JobSourceRecord:
        """Apply updates to a job source record."""
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        await session.flush()
        await session.refresh(record)
        return record
