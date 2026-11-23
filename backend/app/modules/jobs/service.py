"""Domain service orchestrating job normalization, canonical resolution, and deduplication."""

import logging
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.jobs.deduplicator import compute_dedup_fingerprint
from app.modules.jobs.exceptions import JobNotFoundError
from app.modules.jobs.models import (
    Job,
    JobProcessingStatusEnum,
    JobStatusEnum,
)
from app.modules.jobs.normalizers.registry import get_normalizer_for_source_type
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import (
    JobDetailResponse,
    JobSourceRecordResponse,
    JobSummaryResponse,
    PaginatedResponse,
    PaginationMetadata,
)

logger = logging.getLogger(__name__)


class JobService:
    """Service orchestrating canonicalization, deduplication, and job retrieval."""

    def __init__(self, repository: JobRepository | None = None) -> None:
        self.repository = repository or JobRepository()

    async def process_raw_record(self, session: AsyncSession, record_id: uuid.UUID) -> Job | None:
        """Process a raw JobSourceRecord into a normalized and canonical Job entity.

        Ensures idempotency, transactional locking, and cross-source deduplication.

        Args:
            session: Async database session.
            record_id: UUID of the JobSourceRecord to process.

        Returns:
            The associated or newly created canonical Job, or None if record missing.
        """
        record = await self.repository.get_source_record_by_id(
            session=session, record_id=record_id, for_update=True
        )
        if not record:
            logger.warning(
                "JobSourceRecord not found during processing",
                extra={"record_id": str(record_id)},
            )
            return None

        # Short-circuit if already successfully canonicalized
        if (
            record.processing_status == JobProcessingStatusEnum.CANONICALIZED.value
            and record.job_id is not None
        ):
            existing = await self.repository.get_job_by_id(session, record.job_id)
            if existing:
                return existing

        await self.repository.update_source_record(
            session,
            record,
            {
                "processing_status": JobProcessingStatusEnum.PROCESSING.value,
                "processing_error": None,
            },
        )

        try:
            source = record.job_source
            normalizer = get_normalizer_for_source_type(source.source_type)
            dto = normalizer.normalize(record, source)

            fingerprint = compute_dedup_fingerprint(
                company_name=dto.company_name,
                title=dto.title,
                location=dto.normalized_location,
                workplace_type=dto.workplace_type,
            )

            existing_job = await self.repository.get_job_by_fingerprint(session, fingerprint)
            now = datetime.now(UTC)

            if existing_job:
                # Deduplication hit: associate with existing canonical job
                update_fields: dict[str, Any] = {"last_seen_at": now}

                # Revive archived job if re-discovered
                if existing_job.status == JobStatusEnum.ARCHIVED:
                    update_fields["status"] = JobStatusEnum.DISCOVERED
                    update_fields["first_seen_at"] = now

                # Update description text if modified upstream
                if dto.description_text and dto.description_text != existing_job.description_text:
                    update_fields["description_text"] = dto.description_text

                # Update posted_at if newer
                if dto.posted_at and (
                    existing_job.posted_at is None or dto.posted_at > existing_job.posted_at
                ):
                    update_fields["posted_at"] = dto.posted_at

                # Backfill normalized location if previously absent
                if dto.normalized_location and not existing_job.normalized_location:
                    update_fields["normalized_location"] = dto.normalized_location

                job = await self.repository.update_job(session, existing_job, update_fields)
            else:
                # Deduplication miss: create new canonical job
                new_job_data = {
                    "canonical_company_name": dto.company_name,
                    "title": dto.title,
                    "canonical_application_url": dto.application_url,
                    "workplace_type": dto.workplace_type,
                    "normalized_location": dto.normalized_location,
                    "employment_type": dto.employment_type,
                    "description_text": dto.description_text,
                    "posted_at": dto.posted_at,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "dedup_fingerprint_sha256": fingerprint,
                    "status": JobStatusEnum.DISCOVERED,
                }
                job = await self.repository.create_job(session, new_job_data)

            # Link raw record to canonical job and mark CANONICALIZED
            await self.repository.update_source_record(
                session,
                record,
                {
                    "job_id": job.id,
                    "processing_status": JobProcessingStatusEnum.CANONICALIZED.value,
                    "processing_error": None,
                },
            )

            logger.info(
                "Successfully canonicalized job source record",
                extra={
                    "record_id": str(record.id),
                    "job_id": str(job.id),
                    "fingerprint": fingerprint,
                    "is_new": existing_job is None,
                },
            )

            # Trigger matching evaluation for new or revived canonical job
            if existing_job is None or (
                existing_job and existing_job.status == JobStatusEnum.ARCHIVED
            ):
                try:
                    from app.modules.matching.tasks import evaluate_job_matching_task

                    evaluate_job_matching_task.delay(str(job.id))
                except Exception as dispatch_err:
                    logger.warning(
                        f"Could not dispatch matching task for job {job.id}: {dispatch_err}"
                    )

            return job

        except Exception as exc:
            logger.exception(
                "Failed to normalize and canonicalize job source record",
                extra={"record_id": str(record.id), "error": str(exc)},
            )
            await self.repository.update_source_record(
                session,
                record,
                {
                    "processing_status": JobProcessingStatusEnum.FAILED.value,
                    "processing_error": str(exc)[:2000],
                },
            )
            raise

    async def process_pending_records(self, session: AsyncSession, batch_size: int = 100) -> int:
        """Fetch and process pending uncanonicalized job source records in a batch.

        Args:
            session: Async database session.
            batch_size: Maximum records to process in one pass.

        Returns:
            Number of successfully canonicalized records.
        """
        pending = await self.repository.get_pending_source_records(session, limit=batch_size)
        processed_count = 0

        for record in pending:
            try:
                res = await self.process_raw_record(session, record.id)
                if res is not None:
                    processed_count += 1
            except Exception:
                # Continue processing subsequent records in batch even if one fails
                logger.warning(
                    "Skipping failed record in batch processing",
                    extra={"record_id": str(record.id)},
                )
                continue

        return processed_count

    async def get_job(self, session: AsyncSession, job_id: uuid.UUID) -> JobDetailResponse:
        """Fetch full details and provenance of a canonical job."""
        job = await self.repository.get_job_by_id(session, job_id, load_sources=True)
        if not job:
            raise JobNotFoundError(job_id)

        source_responses = [
            JobSourceRecordResponse.model_validate(src) for src in job.source_records
        ]

        return JobDetailResponse(
            id=job.id,
            canonical_company_name=job.canonical_company_name,
            title=job.title,
            canonical_application_url=job.canonical_application_url,
            workplace_type=job.workplace_type,
            normalized_location=job.normalized_location,
            employment_type=job.employment_type,
            posted_at=job.posted_at,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            status=job.status,
            created_at=job.created_at,
            description_text=job.description_text,
            dedup_fingerprint_sha256=job.dedup_fingerprint_sha256,
            source_count=len(source_responses),
            sources=source_responses,
        )

    async def list_jobs(
        self,
        session: AsyncSession,
        search: str | None = None,
        status: JobStatusEnum | None = None,
        workplace_type: WorkplaceTypeEnum | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[JobSummaryResponse]:
        """Query canonical jobs with filtering, search, and pagination."""
        jobs, total_items = await self.repository.list_jobs(
            session=session,
            search=search,
            status=status,
            workplace_type=workplace_type,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        items = [JobSummaryResponse.model_validate(job) for job in jobs]

        return PaginatedResponse[JobSummaryResponse](
            items=items,
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1 and total_pages > 0,
            ),
        )

    async def get_job_sources(
        self, session: AsyncSession, job_id: uuid.UUID
    ) -> list[JobSourceRecordResponse]:
        """Fetch all source records linked to a canonical job."""
        job = await self.repository.get_job_by_id(session, job_id, load_sources=False)
        if not job:
            raise JobNotFoundError(job_id)

        records = await self.repository.get_source_records_for_job(session, job_id)
        return [JobSourceRecordResponse.model_validate(rec) for rec in records]


def get_job_service() -> JobService:
    """Dependency provider for JobService."""
    return JobService()
