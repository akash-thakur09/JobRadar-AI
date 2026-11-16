"""Integration tests verifying PipelineRun persistence, constraints, and atomic metrics on live PostgreSQL."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session_factory
from app.modules.candidate.models import CandidateProfile, User
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.repository import PipelineRunRepository


@pytest.mark.integration
async def test_pipeline_run_db_lifecycle() -> None:
    """Verify PipelineRun CRUD, atomic metric increments, and lifecycle transitions on PostgreSQL."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]
    repo = PipelineRunRepository()

    async with session_factory() as session:
        # 1. Create candidate user & profile
        user = User(
            id=uuid.uuid4(),
            email=f"pipeline_candidate_{suffix}@test.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Pipeline Candidate {suffix}",
            headline="Lead Distributed Systems Engineer",
        )
        session.add(profile)
        await session.commit()

    async with session_factory() as session:
        # 2. Create PENDING pipeline run
        run = PipelineRun(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            trigger_type=PipelineTriggerTypeEnum.MANUAL,
            status=PipelineRunStatusEnum.PENDING,
            run_metadata={"environment": "integration-test"},
        )
        saved = await repo.create(session, run)
        await session.commit()
        run_id = saved.id

    async with session_factory() as session:
        # 3. Transition to RUNNING and perform atomic metric increments
        await repo.update_status(session, run_id, PipelineRunStatusEnum.RUNNING)
        await session.commit()

        # Atomic increment in two steps to test addition
        await repo.increment_metrics_atomic(
            session,
            run_id,
            jobs_discovered=10,
            jobs_created=8,
            matches_qualified=3,
        )
        await session.commit()

        await repo.increment_metrics_atomic(
            session,
            run_id,
            jobs_discovered=5,  # should become 15
            resumes_generated=3,
            notifications_sent=3,
        )
        await session.commit()

        # Finalize to COMPLETED
        await repo.update_status(session, run_id, PipelineRunStatusEnum.COMPLETED)
        await session.commit()

    # 4. Verify in a fresh session
    async with session_factory() as verify_session:
        fetched = await repo.get_by_id(verify_session, run_id)
        assert fetched is not None
        assert fetched.status == PipelineRunStatusEnum.COMPLETED
        assert fetched.started_at is not None
        assert fetched.completed_at is not None
        assert fetched.jobs_discovered == 15
        assert fetched.jobs_created == 8
        assert fetched.matches_qualified == 3
        assert fetched.resumes_generated == 3
        assert fetched.notifications_sent == 3
        assert fetched.run_metadata["environment"] == "integration-test"


@pytest.mark.integration
async def test_pipeline_run_partial_unique_constraint_enforces_single_active_run() -> None:
    """Verify PostgreSQL partial unique index prevents two active runs for the same candidate."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"active_lock_{suffix}@test.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Active Lock Candidate {suffix}",
        )
        session.add(profile)
        await session.commit()

    # Insert first active run (PENDING)
    async with session_factory() as session:
        run_1 = PipelineRun(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            status=PipelineRunStatusEnum.PENDING,
        )
        session.add(run_1)
        await session.commit()

    # Attempt to insert second active run (RUNNING) for SAME candidate
    async with session_factory() as session:
        run_2 = PipelineRun(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            status=PipelineRunStatusEnum.RUNNING,
        )
        session.add(run_2)
        with pytest.raises(IntegrityError):
            await session.commit()

    # Transition run_1 to COMPLETED
    async with session_factory() as session:
        stmt = select(PipelineRun).where(PipelineRun.id == run_1.id)
        active = (await session.execute(stmt)).scalar_one()
        active.transition_to(PipelineRunStatusEnum.RUNNING)
        active.transition_to(PipelineRunStatusEnum.COMPLETED)
        await session.commit()

    # Now inserting a new active run for candidate succeeds!
    async with session_factory() as session:
        run_3 = PipelineRun(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            status=PipelineRunStatusEnum.PENDING,
        )
        session.add(run_3)
        await session.commit()

        assert run_3.id is not None
        assert run_3.status == PipelineRunStatusEnum.PENDING


@pytest.mark.integration
async def test_pipeline_run_cascade_deletion() -> None:
    """Verify that deleting a CandidateProfile cascades and removes its pipeline runs."""
    session_factory = get_session_factory()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"cascade_{suffix}@test.com",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Cascade Candidate {suffix}",
        )
        session.add(profile)
        await session.flush()

        run = PipelineRun(
            id=uuid.uuid4(),
            candidate_profile_id=profile.id,
            status=PipelineRunStatusEnum.COMPLETED,
        )
        session.add(run)
        await session.commit()
        run_id = run.id
        cand_id = profile.id

    # Delete candidate profile
    async with session_factory() as session:
        cand_to_delete = await session.get(CandidateProfile, cand_id)
        assert cand_to_delete is not None
        await session.delete(cand_to_delete)
        await session.commit()

    # Verify pipeline run was cascade deleted
    async with session_factory() as verify_session:
        deleted_run = await verify_session.get(PipelineRun, run_id)
        assert deleted_run is None
