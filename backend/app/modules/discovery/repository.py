"""Data access repository for Job Sources, Discovery Runs, and Raw Job Source Records."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.discovery.adapters.base import RawDiscoveredJob
from app.modules.discovery.models import DiscoveryRun, DiscoveryRunStatusEnum, JobSource
from app.modules.jobs.models import JobSourceRecord


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a JSON payload dictionary."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class DiscoveryRepository:
    """Async repository providing persistence operations for discovery entities."""

    # =========================================================================
    # Job Source Queries
    # =========================================================================

    async def get_source_by_id(
        self, session: AsyncSession, source_id: uuid.UUID
    ) -> JobSource | None:
        """Fetch a job source by primary key."""
        stmt = (
            select(JobSource).options(selectinload(JobSource.runs)).where(JobSource.id == source_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_source_by_name(self, session: AsyncSession, name: str) -> JobSource | None:
        """Fetch a job source by unique name."""
        stmt = select(JobSource).where(JobSource.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sources(
        self, session: AsyncSession, is_enabled: bool | None = None
    ) -> list[JobSource]:
        """Fetch job sources optionally filtered by enabled status."""
        stmt = select(JobSource).options(selectinload(JobSource.runs)).order_by(JobSource.name)
        if is_enabled is not None:
            stmt = stmt.where(JobSource.is_enabled == is_enabled)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_source(self, session: AsyncSession, source_data: dict[str, Any]) -> JobSource:
        """Persist a new job source record."""
        source = JobSource(**source_data)
        session.add(source)
        await session.flush()
        await session.refresh(source)
        return source

    async def update_source(
        self, session: AsyncSession, source: JobSource, update_data: dict[str, Any]
    ) -> JobSource:
        """Apply partial updates to a job source."""
        for key, value in update_data.items():
            if hasattr(source, key) and value is not None:
                setattr(source, key, value)
        await session.flush()
        await session.refresh(source)
        return source

    # =========================================================================
    # Discovery Run Queries
    # =========================================================================

    async def create_discovery_run(
        self,
        session: AsyncSession,
        job_source_id: uuid.UUID,
        status: DiscoveryRunStatusEnum = DiscoveryRunStatusEnum.PENDING,
    ) -> DiscoveryRun:
        """Initialize an execution log for a discovery run."""
        run = DiscoveryRun(
            job_source_id=job_source_id,
            status=status,
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()
        await session.refresh(run)
        return run

    async def get_discovery_run_by_id(
        self, session: AsyncSession, run_id: uuid.UUID
    ) -> DiscoveryRun | None:
        """Fetch a discovery run record by ID."""
        stmt = select(DiscoveryRun).where(DiscoveryRun.id == run_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_discovery_run(
        self, session: AsyncSession, run: DiscoveryRun, update_data: dict[str, Any]
    ) -> DiscoveryRun:
        """Update discovery run status, timing, and counters."""
        for key, value in update_data.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await session.flush()
        await session.refresh(run)
        return run

    async def list_discovery_runs(
        self,
        session: AsyncSession,
        job_source_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DiscoveryRun], int]:
        """Fetch paginated discovery runs optionally filtered by job_source_id."""
        stmt = select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc())
        count_stmt = select(func.count(DiscoveryRun.id))

        if job_source_id is not None:
            stmt = stmt.where(DiscoveryRun.job_source_id == job_source_id)
            count_stmt = count_stmt.where(DiscoveryRun.job_source_id == job_source_id)

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        count_result = await session.execute(count_stmt)
        total_items = count_result.scalar_one()

        items_result = await session.execute(stmt)
        runs = list(items_result.scalars().all())

        return runs, total_items

    async def get_latest_run_for_source(
        self, session: AsyncSession, job_source_id: uuid.UUID
    ) -> DiscoveryRun | None:
        """Fetch the most recent execution run for a source."""
        stmt = (
            select(DiscoveryRun)
            .where(DiscoveryRun.job_source_id == job_source_id)
            .order_by(DiscoveryRun.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # =========================================================================
    # Raw Job Ingestion & Idempotent Persistence
    # =========================================================================

    async def persist_discovered_jobs(
        self,
        session: AsyncSession,
        job_source_id: uuid.UUID,
        jobs: list[RawDiscoveredJob],
    ) -> tuple[int, int]:
        """Idempotently persist discovered raw job artifacts into job_source_records.

        Guarantees:
        - Prevents duplicate rows for the same (job_source_id, external_job_id).
        - Existing records update last_seen_at.
        - Material payload changes update payload_hash_sha256, raw_payload, and reset processing_status to 'RAW'.

        Returns:
            tuple[jobs_created, jobs_updated]
        """
        now = datetime.now(UTC)
        jobs_created = 0
        jobs_updated = 0

        for job in jobs:
            payload_hash = compute_payload_hash(job.raw_payload)

            stmt = select(JobSourceRecord).where(
                JobSourceRecord.job_source_id == job_source_id,
                JobSourceRecord.external_job_id == job.external_id,
            )
            result = await session.execute(stmt)
            existing_record = result.scalar_one_or_none()

            if existing_record is None:
                record = JobSourceRecord(
                    job_source_id=job_source_id,
                    external_job_id=job.external_id,
                    source_job_url=job.source_url,
                    raw_payload=job.raw_payload,
                    raw_posted_at=job.raw_posted_at,
                    payload_hash_sha256=payload_hash,
                    processing_status="RAW",
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(record)
                jobs_created += 1
            else:
                existing_record.last_seen_at = now
                if existing_record.payload_hash_sha256 != payload_hash:
                    existing_record.raw_payload = job.raw_payload
                    existing_record.source_job_url = job.source_url
                    existing_record.raw_posted_at = job.raw_posted_at
                    existing_record.payload_hash_sha256 = payload_hash
                    existing_record.processing_status = "RAW"
                    jobs_updated += 1

        await session.flush()
        return jobs_created, jobs_updated

    async def list_job_source_records(
        self,
        session: AsyncSession,
        job_source_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JobSourceRecord], int]:
        """Fetch paginated raw source records."""
        target_source_id = job_source_id or source_id
        stmt = select(JobSourceRecord).order_by(JobSourceRecord.first_seen_at.desc())
        count_stmt = select(func.count(JobSourceRecord.id))

        if target_source_id is not None:
            stmt = stmt.where(JobSourceRecord.job_source_id == target_source_id)
            count_stmt = count_stmt.where(JobSourceRecord.job_source_id == target_source_id)

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        count_result = await session.execute(count_stmt)
        total_items = count_result.scalar_one()

        items_result = await session.execute(stmt)
        records = list(items_result.scalars().all())

        return records, total_items
