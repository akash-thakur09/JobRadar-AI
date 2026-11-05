"""Integration tests for Canonicalization and Deduplication against live PostgreSQL."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.candidate.models import WorkplaceTypeEnum
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.jobs.models import (
    Job,
    JobProcessingStatusEnum,
    JobSourceRecord,
    JobStatusEnum,
)
from app.modules.jobs.service import JobService


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(
            f"Live PostgreSQL not reachable ({detail}). Skipping canonicalization DB tests."
        )


@pytest.mark.integration
async def test_cross_source_canonicalization_and_deduplication() -> None:
    """Verify end-to-end normalization, cross-source deduplication, and updates on live DB."""
    session_factory = get_session_factory()
    service = JobService()

    unique_suffix = uuid.uuid4().hex[:8]
    company_name = f"InnoTech {unique_suffix} Inc."
    gh_source_name = f"Greenhouse-{unique_suffix}"
    lever_source_name = f"Lever-{unique_suffix}"

    now = datetime.now(UTC)

    async with session_factory() as session:
        # 1. Create two JobSources (Greenhouse & Lever)
        gh_source = JobSource(
            name=gh_source_name,
            source_type=JobSourceTypeEnum.GREENHOUSE,
            base_url="https://boards-api.greenhouse.io",
            configuration={"company_name": company_name},
            is_enabled=True,
        )
        lever_source = JobSource(
            name=lever_source_name,
            source_type=JobSourceTypeEnum.LEVER,
            base_url="https://api.lever.co",
            configuration={"company_name": company_name},
            is_enabled=True,
        )
        session.add_all([gh_source, lever_source])
        await session.flush()
        gh_source_id = gh_source.id
        lever_source_id = lever_source.id

        # 2. Insert raw Greenhouse source record
        # Note: "Sr. Backend Engineer" vs "Senior Backend Engineer"
        gh_record = JobSourceRecord(
            job_source_id=gh_source_id,
            external_job_id=f"gh-job-{unique_suffix}",
            source_job_url="https://boards.greenhouse.io/innotech/jobs/1001?gh_jid=1001&utm_source=linkedin",
            raw_payload={
                "id": 1001,
                "title": "Sr. Backend Engineer",
                "location": {"name": "San Francisco, CA (Remote)"},
                "content": "<p>Build high-throughput event processing pipelines.</p>",
                "updated_at": "2026-11-01T10:00:00Z",
                "metadata": [{"name": "Employment Type", "value": "Full-Time"}],
            },
            payload_hash_sha256="hash-gh-1",
            processing_status="RAW",
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(gh_record)
        await session.flush()
        gh_record_id = gh_record.id

        await session.commit()

    # 3. Process raw Greenhouse record
    async with session_factory() as session:
        canonical_job = await service.process_raw_record(session, gh_record_id)
        assert canonical_job is not None
        canonical_job_id = canonical_job.id
        await session.commit()

    # 4. Verify canonical job state in database
    async with session_factory() as session:
        job_stmt = select(Job).where(Job.id == canonical_job_id)
        job = (await session.execute(job_stmt)).scalar_one()

        assert job.canonical_company_name == company_name
        assert job.title == "Sr. Backend Engineer"
        # Verify URL sanitization stripped tracking parameters
        assert job.canonical_application_url == "https://boards.greenhouse.io/innotech/jobs/1001"
        assert job.workplace_type == WorkplaceTypeEnum.REMOTE
        assert "Build high-throughput event processing pipelines." in job.description_text
        assert job.status == JobStatusEnum.DISCOVERED

        # Verify raw record was updated and linked
        rec_stmt = select(JobSourceRecord).where(JobSourceRecord.id == gh_record_id)
        saved_gh_record = (await session.execute(rec_stmt)).scalar_one()
        assert saved_gh_record.job_id == canonical_job_id
        assert saved_gh_record.processing_status == JobProcessingStatusEnum.CANONICALIZED.value

    # 5. Insert raw Lever record representing the EXACT SAME job posted on Lever
    # Title is "Senior Backend Engineer", location is "San Francisco, CA (Remote)"
    async with session_factory() as session:
        lever_record = JobSourceRecord(
            job_source_id=lever_source_id,
            external_job_id=f"lever-job-{unique_suffix}",
            source_job_url="https://jobs.lever.co/innotech/2002?lever-origin=applied&utm_source=indeed",
            raw_payload={
                "id": "2002",
                "text": "Senior Backend Engineer",
                "hostedUrl": "https://jobs.lever.co/innotech/2002?lever-origin=applied",
                "workplaceType": "remote",
                "categories": {
                    "location": "San Francisco, CA (Remote)",
                    "commitment": "Full-time",
                },
                "description": "<p>Build high-throughput event processing pipelines.</p>",
                "createdAt": 1761000000000,
            },
            payload_hash_sha256="hash-lever-1",
            processing_status="RAW",
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(lever_record)
        await session.flush()
        lever_record_id = lever_record.id
        await session.commit()

    # 6. Process raw Lever record - should detect deduplication match
    async with session_factory() as session:
        dedup_job = await service.process_raw_record(session, lever_record_id)
        assert dedup_job is not None
        # Assert cross-source deduplication resolved to the SAME canonical job!
        assert dedup_job.id == canonical_job_id
        await session.commit()

    # 7. Verify both records are linked to the single canonical job
    async with session_factory() as session:
        sources_stmt = select(JobSourceRecord).where(JobSourceRecord.job_id == canonical_job_id)
        linked_sources = list((await session.execute(sources_stmt)).scalars().all())
        assert len(linked_sources) == 2
        linked_ids = {s.id for s in linked_sources}
        assert gh_record_id in linked_ids
        assert lever_record_id in linked_ids

        for s in linked_sources:
            assert s.processing_status == JobProcessingStatusEnum.CANONICALIZED.value

    # 8. Test description update propagation when upstream description changes
    async with session_factory() as session:
        rec_stmt = select(JobSourceRecord).where(JobSourceRecord.id == gh_record_id)
        rec = (await session.execute(rec_stmt)).scalar_one()
        rec.raw_payload = {
            "id": 1001,
            "title": "Sr. Backend Engineer",
            "location": {"name": "San Francisco, CA (Remote)"},
            "content": "<p>Build high-throughput event processing pipelines with AI agents.</p>",
            "updated_at": "2026-11-03T10:00:00Z",
        }
        rec.processing_status = "RAW"
        await session.commit()

    async with session_factory() as session:
        updated_job = await service.process_raw_record(session, gh_record_id)
        assert updated_job is not None
        assert "with AI agents" in updated_job.description_text
        await session.commit()

    # 9. Test revival of ARCHIVED job
    async with session_factory() as session:
        job_stmt = select(Job).where(Job.id == canonical_job_id)
        job = (await session.execute(job_stmt)).scalar_one()
        job.status = JobStatusEnum.ARCHIVED
        await session.commit()

    async with session_factory() as session:
        rec_stmt = select(JobSourceRecord).where(JobSourceRecord.id == lever_record_id)
        rec = (await session.execute(rec_stmt)).scalar_one()
        rec.processing_status = "RAW"
        await session.commit()

    async with session_factory() as session:
        revived_job = await service.process_raw_record(session, lever_record_id)
        assert revived_job is not None
        assert revived_job.status == JobStatusEnum.DISCOVERED
        await session.commit()

    # 10. Clean up test data
    async with session_factory() as session:
        # Delete job sources (cascades or cleans up records and jobs)
        await session.delete(await session.get(Job, canonical_job_id))
        await session.delete(await session.get(JobSource, gh_source_id))
        await session.delete(await session.get(JobSource, lever_source_id))
        await session.commit()
