"""Integration test verifying concurrency controls, duplicate run prevention, and distributed locks."""

import uuid
import pytest
from app.database.session import get_session_factory
from app.infrastructure.redis import get_redis
from app.modules.candidate.models import CandidateProfile, User
from app.modules.pipeline.enums import PipelineRunStatusEnum, PipelineTriggerTypeEnum
from app.modules.pipeline.exceptions import ActivePipelineRunConflictError
from app.modules.pipeline.service import PipelineOrchestrationService


@pytest.mark.integration
async def test_duplicate_pipeline_run_prevention() -> None:
    """Verify that multiple simultaneous pipeline runs for the same candidate are rejected."""
    session_factory = get_session_factory()
    service = PipelineOrchestrationService()
    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        # 1. Create User and Candidate Profile
        user = User(id=uuid.uuid4(), email=f"lock_test_{suffix}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name=f"Lock Candidate {suffix}",
            headline="Concurrency Engineer",
        )
        session.add(profile)
        await session.commit()

        # 2. Start first pipeline run -> should succeed and set status to PENDING
        run1 = await service.start_pipeline_run(
            session=session,
            candidate_profile_id=profile.id,
            trigger_type=PipelineTriggerTypeEnum.MANUAL,
        )
        assert run1.status == PipelineRunStatusEnum.PENDING

        # 3. Attempt to start a second pipeline run while the first is active -> should fail with Conflict
        with pytest.raises(ActivePipelineRunConflictError) as exc_info:
            await service.start_pipeline_run(
                session=session,
                candidate_profile_id=profile.id,
                trigger_type=PipelineTriggerTypeEnum.MANUAL,
            )
        assert exc_info.value.status_code == 409
        assert "already running" in str(exc_info.value.message)

        # 4. Mark run1 as COMPLETED
        run1.status = PipelineRunStatusEnum.COMPLETED
        await session.commit()

        # 5. Starting a new run should now succeed
        run2 = await service.start_pipeline_run(
            session=session,
            candidate_profile_id=profile.id,
            trigger_type=PipelineTriggerTypeEnum.MANUAL,
        )
        assert run2.status == PipelineRunStatusEnum.PENDING
        assert run2.id != run1.id

        # Clean up
        run2.status = PipelineRunStatusEnum.CANCELLED
        await session.commit()


@pytest.mark.integration
async def test_redis_distributed_locking() -> None:
    """Verify Redis distributed lock behavior and mutual exclusion."""
    redis = get_redis()
    lock_key = f"test:lock:concurrency:{uuid.uuid4().hex[:8]}"

    lock1 = redis.lock(lock_key, timeout=10.0, blocking_timeout=0.1)
    lock2 = redis.lock(lock_key, timeout=10.0, blocking_timeout=0.1)

    # 1. First lock acquisition succeeds
    acquired1 = await lock1.acquire()
    assert acquired1 is True

    # 2. Second lock acquisition fails immediately due to lock1
    acquired2 = await lock2.acquire()
    assert acquired2 is False

    # 3. Release first lock
    await lock1.release()

    # 4. Second lock can now be acquired
    acquired3 = await lock2.acquire()
    assert acquired3 is True

    await lock2.release()
