"""Integration tests for Job Discovery PostgreSQL persistence and idempotency."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.discovery.adapters.base import RawDiscoveredJob
from app.modules.discovery.models import (
    DiscoveryRunStatusEnum,
    JobSourceTypeEnum,
)
from app.modules.discovery.repository import DiscoveryRepository, compute_payload_hash
from app.modules.jobs.models import JobSourceRecord


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping discovery DB tests.")


@pytest.mark.integration
async def test_job_source_lifecycle() -> None:
    """Verify JobSource persistence, querying, and updating."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()

    unique_name = f"Test Source {uuid.uuid4()}"
    async with session_factory() as session:
        source = await repo.create_source(
            session=session,
            source_data={
                "name": unique_name,
                "source_type": JobSourceTypeEnum.GREENHOUSE,
                "base_url": "https://boards-api.greenhouse.io",
                "is_enabled": True,
                "polling_interval_minutes": 360,
                "configuration": {"board_token": "testco"},
            },
        )
        source_id = source.id
        await session.commit()

    # Query back and update
    async with session_factory() as session:
        fetched = await repo.get_source_by_id(session, source_id)
        assert fetched is not None
        assert fetched.name == unique_name
        assert fetched.source_type == JobSourceTypeEnum.GREENHOUSE
        assert fetched.configuration["board_token"] == "testco"

        await repo.update_source(
            session, fetched, {"is_enabled": False, "polling_interval_minutes": 120}
        )
        await session.commit()

    async with session_factory() as session:
        updated = await repo.get_source_by_id(session, source_id)
        assert updated is not None
        assert updated.is_enabled is False
        assert updated.polling_interval_minutes == 120

        # Cleanup
        await session.delete(updated)
        await session.commit()


@pytest.mark.integration
async def test_job_source_unique_name_constraint() -> None:
    """Verify PostgreSQL enforces unique constraint on job_sources.name."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()
    dup_name = f"Unique Source {uuid.uuid4()}"

    async with session_factory() as session:
        await repo.create_source(
            session=session,
            source_data={
                "name": dup_name,
                "source_type": JobSourceTypeEnum.LEVER,
                "base_url": "https://api.lever.co",
                "configuration": {"company_id": "c1"},
            },
        )
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            await repo.create_source(
                session=session,
                source_data={
                    "name": dup_name,
                    "source_type": JobSourceTypeEnum.LEVER,
                    "base_url": "https://api.lever.co",
                    "configuration": {"company_id": "c2"},
                },
            )
            await session.commit()

    # Cleanup
    async with session_factory() as session:
        src = await repo.get_source_by_name(session, dup_name)
        if src:
            await session.delete(src)
            await session.commit()


@pytest.mark.integration
async def test_discovery_run_lifecycle() -> None:
    """Verify DiscoveryRun creation, metric updating, and status lifecycle."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()

    async with session_factory() as session:
        source = await repo.create_source(
            session=session,
            source_data={
                "name": f"Run Test Source {uuid.uuid4()}",
                "source_type": JobSourceTypeEnum.GREENHOUSE,
                "base_url": "https://boards-api.greenhouse.io",
                "configuration": {"board_token": "runco"},
            },
        )
        source_id = source.id

        run = await repo.create_discovery_run(
            session=session,
            job_source_id=source_id,
            status=DiscoveryRunStatusEnum.RUNNING,
        )
        run_id = run.id
        await session.commit()

    # Update run metrics
    async with session_factory() as session:
        fetched_run = await repo.get_discovery_run_by_id(session, run_id)
        assert fetched_run is not None
        assert fetched_run.status == DiscoveryRunStatusEnum.RUNNING

        await repo.update_discovery_run(
            session=session,
            run=fetched_run,
            update_data={
                "status": DiscoveryRunStatusEnum.COMPLETED,
                "jobs_discovered": 5,
                "jobs_created": 4,
                "jobs_updated": 1,
            },
        )
        await session.commit()

    async with session_factory() as session:
        completed_run = await repo.get_discovery_run_by_id(session, run_id)
        assert completed_run is not None
        assert completed_run.status == DiscoveryRunStatusEnum.COMPLETED
        assert completed_run.jobs_discovered == 5
        assert completed_run.jobs_created == 4

        # Cleanup source (cascades to runs)
        src = await repo.get_source_by_id(session, source_id)
        if src:
            await session.delete(src)
            await session.commit()


@pytest.mark.integration
async def test_raw_job_idempotent_discovery_and_updates() -> None:
    """Verify repeated discovery runs do not duplicate raw jobs, and material changes update hashes."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()

    async with session_factory() as session:
        source = await repo.create_source(
            session=session,
            source_data={
                "name": f"Idempotent Test {uuid.uuid4()}",
                "source_type": JobSourceTypeEnum.GREENHOUSE,
                "base_url": "https://boards-api.greenhouse.io",
                "configuration": {"board_token": "idempotentco"},
            },
        )
        source_id = source.id
        await session.commit()

    job_a = RawDiscoveredJob(
        external_id="ext-001",
        source_url="https://example.com/jobs/001",
        raw_payload={"title": "Backend Engineer", "dept": "Platform"},
        raw_posted_at="2026-11-01",
    )
    job_b = RawDiscoveredJob(
        external_id="ext-002",
        source_url="https://example.com/jobs/002",
        raw_payload={"title": "Frontend Engineer", "dept": "Product"},
        raw_posted_at="2026-11-01",
    )

    # 1. First Discovery Pass: Both jobs are new
    async with session_factory() as session:
        created1, updated1 = await repo.persist_discovered_jobs(
            session=session,
            job_source_id=source_id,
            jobs=[job_a, job_b],
        )
        await session.commit()
        assert created1 == 2
        assert updated1 == 0

    # Verify rows in DB
    async with session_factory() as session:
        records, total = await repo.list_job_source_records(session, source_id=source_id)
        assert total == 2
        rec_map = {r.external_job_id: r for r in records}
        assert "ext-001" in rec_map
        assert "ext-002" in rec_map
        orig_hash_a = rec_map["ext-001"].payload_hash_sha256
        assert orig_hash_a == compute_payload_hash(job_a.raw_payload)

    # 2. Second Discovery Pass with identical payloads: Idempotent skip
    async with session_factory() as session:
        created2, updated2 = await repo.persist_discovered_jobs(
            session=session,
            job_source_id=source_id,
            jobs=[job_a, job_b],
        )
        await session.commit()
        assert created2 == 0
        assert updated2 == 0

    # Verify no duplicate records were created
    async with session_factory() as session:
        _, total = await repo.list_job_source_records(session, source_id=source_id)
        assert total == 2

    # 3. Third Discovery Pass: job_a payload changed upstream
    job_a_modified = RawDiscoveredJob(
        external_id="ext-001",
        source_url="https://example.com/jobs/001",
        raw_payload={"title": "Senior Backend Engineer", "dept": "Platform Architecture"},
        raw_posted_at="2026-11-04",
    )

    async with session_factory() as session:
        created3, updated3 = await repo.persist_discovered_jobs(
            session=session,
            job_source_id=source_id,
            jobs=[job_a_modified, job_b],
        )
        await session.commit()
        assert created3 == 0
        assert updated3 == 1  # job_a was updated!

    # Verify updated payload and new hash in DB
    async with session_factory() as session:
        records, total = await repo.list_job_source_records(session, source_id=source_id)
        assert total == 2
        rec_map = {r.external_job_id: r for r in records}
        assert rec_map["ext-001"].raw_payload["title"] == "Senior Backend Engineer"
        assert rec_map["ext-001"].payload_hash_sha256 != orig_hash_a
        assert rec_map["ext-001"].payload_hash_sha256 == compute_payload_hash(
            job_a_modified.raw_payload
        )

        # Cleanup
        for r in records:
            await session.delete(r)
        src = await repo.get_source_by_id(session, source_id)
        if src:
            await session.delete(src)
        await session.commit()


@pytest.mark.integration
async def test_raw_job_unique_constraint() -> None:
    """Verify PostgreSQL enforces unique constraint on (job_source_id, external_job_id)."""
    session_factory = get_session_factory()
    repo = DiscoveryRepository()

    async with session_factory() as session:
        source = await repo.create_source(
            session=session,
            source_data={
                "name": f"Constraint Test {uuid.uuid4()}",
                "source_type": JobSourceTypeEnum.LEVER,
                "base_url": "https://api.lever.co",
                "configuration": {"company_id": "c_constraint"},
            },
        )
        source_id = source.id
        await session.commit()

    async with session_factory() as session:
        r1 = JobSourceRecord(
            job_source_id=source_id,
            external_job_id="dup-job-id",
            source_job_url="https://jobs.lever.co/c/dup-job-id",
            raw_payload={"text": "Engineer"},
            payload_hash_sha256="hash123",
            processing_status="RAW",
        )
        session.add(r1)
        await session.flush()

        r2 = JobSourceRecord(
            job_source_id=source_id,
            external_job_id="dup-job-id",
            source_job_url="https://jobs.lever.co/c/dup-job-id",
            raw_payload={"text": "Duplicate"},
            payload_hash_sha256="hash456",
            processing_status="RAW",
        )
        session.add(r2)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()

    # Cleanup
    async with session_factory() as session:
        src = await repo.get_source_by_id(session, source_id)
        if src:
            await session.delete(src)
            await session.commit()
