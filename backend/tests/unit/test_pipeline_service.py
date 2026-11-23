"""Unit tests for PipelineOrchestrationService workflow, idempotency, and error handling."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.candidate.models import CandidateProfile
from app.modules.discovery.adapters.base import DiscoveryResult, RawDiscoveredJob
from app.modules.discovery.models import JobSource, JobSourceTypeEnum
from app.modules.matching.models import EligibilityStatusEnum, JobMatch
from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.models import NotificationDelivery
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.exceptions import (
    ActivePipelineRunConflictError,
    PipelineError,
)
from app.modules.pipeline.models import PipelineRun
from app.modules.pipeline.service import PipelineOrchestrationService
from app.modules.tailoring.enums import TailoredResumeStatusEnum
from app.modules.tailoring.models import TailoredResume


@pytest.fixture
def candidate_fixture() -> CandidateProfile:
    """Fixture returning candidate profile."""
    return CandidateProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="Alex Mercer",
        headline="Senior Systems Architect",
    )


@pytest.fixture
def active_job_source() -> JobSource:
    """Fixture returning enabled job source."""
    return JobSource(
        id=uuid.uuid4(),
        name="TechCorp Greenhouse",
        source_type="GREENHOUSE",
        base_url="https://boards-api.greenhouse.io/v1/boards/techcorp",
        configuration={"board_token": "techcorp"},
        is_enabled=True,
    )


@pytest.mark.unit
async def test_start_pipeline_run_success(candidate_fixture: CandidateProfile) -> None:
    """start_pipeline_run validates candidate, checks idempotency, and enqueues task."""
    mock_repo = MagicMock()
    mock_repo.get_active_run_for_candidate = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(side_effect=lambda _s, r: r)

    mock_cand_repo = MagicMock()
    mock_cand_repo.get_profile = AsyncMock(return_value=candidate_fixture)

    service = PipelineOrchestrationService(
        repository=mock_repo,
        candidate_repository=mock_cand_repo,
    )

    mock_session = AsyncMock()
    with patch("app.modules.pipeline.tasks.execute_pipeline_run_task.delay") as mock_delay:
        run = await service.start_pipeline_run(
            session=mock_session,
            candidate_profile_id=candidate_fixture.id,
            trigger_type=PipelineTriggerTypeEnum.MANUAL,
        )

        assert run.candidate_profile_id == candidate_fixture.id
        assert run.status == PipelineRunStatusEnum.PENDING
        assert run.trigger_type == PipelineTriggerTypeEnum.MANUAL
        mock_repo.create.assert_called_once()
        mock_delay.assert_called_once_with(str(run.id))


@pytest.mark.unit
async def test_start_pipeline_run_candidate_not_found_raises_404() -> None:
    """start_pipeline_run raises PipelineError with 404 when candidate is missing."""
    mock_repo = MagicMock()
    mock_cand_repo = MagicMock()
    mock_cand_repo.get_profile = AsyncMock(return_value=None)

    service = PipelineOrchestrationService(
        repository=mock_repo,
        candidate_repository=mock_cand_repo,
    )

    mock_session = AsyncMock()
    cand_id = uuid.uuid4()
    with pytest.raises(PipelineError) as exc_info:
        await service.start_pipeline_run(
            session=mock_session,
            candidate_profile_id=cand_id,
        )

    assert exc_info.value.status_code == 404
    assert f"Candidate profile '{cand_id}' does not exist" in str(exc_info.value.message)


@pytest.mark.unit
async def test_start_pipeline_run_active_conflict_raises_409(
    candidate_fixture: CandidateProfile,
) -> None:
    """start_pipeline_run raises ActivePipelineRunConflictError if an active run exists."""
    existing_active = PipelineRun(
        id=uuid.uuid4(),
        candidate_profile_id=candidate_fixture.id,
        status=PipelineRunStatusEnum.RUNNING,
    )

    mock_repo = MagicMock()
    mock_repo.get_active_run_for_candidate = AsyncMock(return_value=existing_active)

    mock_cand_repo = MagicMock()
    mock_cand_repo.get_profile = AsyncMock(return_value=candidate_fixture)

    service = PipelineOrchestrationService(
        repository=mock_repo,
        candidate_repository=mock_cand_repo,
    )

    mock_session = AsyncMock()
    with pytest.raises(ActivePipelineRunConflictError) as exc_info:
        await service.start_pipeline_run(
            session=mock_session,
            candidate_profile_id=candidate_fixture.id,
        )

    assert exc_info.value.status_code == 409
    assert "already running" in str(exc_info.value.message)


@pytest.mark.unit
async def test_execute_pipeline_run_already_terminal_idempotency() -> None:
    """execute_pipeline_run returns immediately if run has already reached terminal status."""
    terminal_run = PipelineRun(
        id=uuid.uuid4(),
        candidate_profile_id=uuid.uuid4(),
        status=PipelineRunStatusEnum.COMPLETED,
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=terminal_run)

    service = PipelineOrchestrationService(repository=mock_repo)
    mock_session = AsyncMock()

    result = await service.execute_pipeline_run(session=mock_session, run_id=terminal_run.id)
    assert result.status == PipelineRunStatusEnum.COMPLETED


@pytest.mark.unit
async def test_execute_pipeline_run_full_workflow_success(
    candidate_fixture: CandidateProfile,
    active_job_source: JobSource,
) -> None:
    """execute_pipeline_run coordinates discovery, matching, tailoring, and delivery to COMPLETED."""
    run = PipelineRun(
        id=uuid.uuid4(),
        candidate_profile_id=candidate_fixture.id,
        status=PipelineRunStatusEnum.PENDING,
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)
    mock_repo.increment_metrics_atomic = AsyncMock()

    # Mock discovery
    mock_disc_repo = MagicMock()
    mock_disc_repo.persist_discovered_jobs = AsyncMock(return_value=(2, 0))

    mock_adapter = MagicMock()
    sample_jobs = [
        RawDiscoveredJob(
            external_id="1",
            source_url="https://techcorp.com/jobs/1",
            raw_payload={"title": "Backend Architect"},
        ),
        RawDiscoveredJob(
            external_id="2",
            source_url="https://techcorp.com/jobs/2",
            raw_payload={"title": "DevOps Lead"},
        ),
    ]
    mock_adapter.discover_jobs = AsyncMock(
        return_value=DiscoveryResult(
            source_identifier="techcorp",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            jobs=sample_jobs,
        )
    )

    # Mock normalization
    mock_job_service = MagicMock()
    mock_job_service.process_pending_records = AsyncMock(return_value=2)

    # Mock matching
    mock_match = JobMatch(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        candidate_profile_id=candidate_fixture.id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("90.00"),
        final_score=Decimal("90.00"),
    )
    mock_matching_service = MagicMock()
    mock_matching_service.repository.get_unmatched_jobs_for_candidate = AsyncMock(
        return_value=[MagicMock(id=mock_match.job_id)]
    )
    mock_matching_service.evaluate_job_for_candidate = AsyncMock(return_value=mock_match)

    # Mock semantic analysis
    mock_semantic_service = MagicMock()
    mock_semantic_service.evaluate_semantic_match = AsyncMock(return_value=mock_match)

    # Mock tailoring
    mock_tailored_resume = TailoredResume(
        id=uuid.uuid4(),
        generation_status=TailoredResumeStatusEnum.COMPLETED,
        storage_key="test.pdf",
    )
    mock_tailoring_service = MagicMock()
    mock_tailoring_service.request_tailoring = AsyncMock(return_value=mock_tailored_resume)
    mock_tailoring_service.execute_tailoring_pipeline = AsyncMock(return_value=mock_tailored_resume)

    # Mock notification
    mock_delivery = NotificationDelivery(
        id=uuid.uuid4(),
        status=NotificationDeliveryStatusEnum.SENT,
    )
    mock_notif_service = MagicMock()
    mock_notif_service.create_or_get_delivery_for_tailored_resume = AsyncMock(
        return_value=mock_delivery
    )
    mock_notif_service.execute_delivery_pipeline = AsyncMock(return_value=mock_delivery)

    service = PipelineOrchestrationService(
        repository=mock_repo,
        discovery_repository=mock_disc_repo,
        job_service=mock_job_service,
        matching_service=mock_matching_service,
        semantic_service=mock_semantic_service,
        tailoring_service=mock_tailoring_service,
        notification_service=mock_notif_service,
    )

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[active_job_source]))
            )
        )
    )

    with (
        patch(
            "app.modules.pipeline.service.get_adapter_for_source_type", return_value=mock_adapter
        ),
        patch("app.modules.pipeline.service.get_redis") as mock_redis,
    ):
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        mock_redis.return_value.lock.return_value = mock_lock

        final_run = await service.execute_pipeline_run(session=mock_session, run_id=run.id)

        assert final_run.status == PipelineRunStatusEnum.COMPLETED
        assert final_run.completed_at is not None
        assert final_run.error_summary is None


@pytest.mark.unit
async def test_execute_pipeline_run_partial_completion_classification(
    candidate_fixture: CandidateProfile,
    active_job_source: JobSource,
) -> None:
    """execute_pipeline_run classifies run as PARTIALLY_COMPLETED when a downstream step fails."""
    run = PipelineRun(
        id=uuid.uuid4(),
        candidate_profile_id=candidate_fixture.id,
        status=PipelineRunStatusEnum.PENDING,
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)
    mock_repo.increment_metrics_atomic = AsyncMock()

    mock_disc_repo = MagicMock()
    mock_disc_repo.persist_discovered_jobs = AsyncMock(return_value=(1, 0))

    mock_adapter = MagicMock()
    mock_adapter.discover_jobs = AsyncMock(
        return_value=DiscoveryResult(
            source_identifier="techcorp",
            source_type=JobSourceTypeEnum.GREENHOUSE,
            jobs=[
                RawDiscoveredJob(
                    external_id="1",
                    source_url="https://techcorp.com/jobs/1",
                    raw_payload={},
                )
            ],
        )
    )

    mock_job_service = MagicMock()
    mock_job_service.process_pending_records = AsyncMock(return_value=1)

    mock_match = JobMatch(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        candidate_profile_id=candidate_fixture.id,
        eligibility_status=EligibilityStatusEnum.ELIGIBLE,
        deterministic_score=Decimal("85.00"),
        final_score=Decimal("85.00"),
    )
    mock_matching_service = MagicMock()
    mock_matching_service.repository.get_unmatched_jobs_for_candidate = AsyncMock(
        return_value=[MagicMock(id=mock_match.job_id)]
    )
    mock_matching_service.evaluate_job_for_candidate = AsyncMock(return_value=mock_match)

    mock_semantic_service = MagicMock()
    mock_semantic_service.evaluate_semantic_match = AsyncMock(return_value=mock_match)

    # Fail tailoring phase
    mock_tailored_resume = TailoredResume(
        id=uuid.uuid4(),
        generation_status=TailoredResumeStatusEnum.FAILED,
        validation_error="Evidence hallucination detected",
    )
    mock_tailoring_service = MagicMock()
    mock_tailoring_service.request_tailoring = AsyncMock(return_value=mock_tailored_resume)
    mock_tailoring_service.execute_tailoring_pipeline = AsyncMock(return_value=mock_tailored_resume)

    service = PipelineOrchestrationService(
        repository=mock_repo,
        discovery_repository=mock_disc_repo,
        job_service=mock_job_service,
        matching_service=mock_matching_service,
        semantic_service=mock_semantic_service,
        tailoring_service=mock_tailoring_service,
    )

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[active_job_source]))
            )
        )
    )

    with (
        patch(
            "app.modules.pipeline.service.get_adapter_for_source_type", return_value=mock_adapter
        ),
        patch("app.modules.pipeline.service.get_redis") as mock_redis,
    ):
        mock_lock = AsyncMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        mock_redis.return_value.lock.return_value = mock_lock

        final_run = await service.execute_pipeline_run(session=mock_session, run_id=run.id)

        assert final_run.status == PipelineRunStatusEnum.PARTIALLY_COMPLETED
        assert "Evidence hallucination detected" in str(final_run.error_summary)


@pytest.mark.unit
async def test_cancel_pipeline_run_lifecycle() -> None:
    """cancel_pipeline_run transitions PENDING run to CANCELLED state."""
    run = PipelineRun(
        id=uuid.uuid4(),
        candidate_profile_id=uuid.uuid4(),
        status=PipelineRunStatusEnum.PENDING,
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)

    service = PipelineOrchestrationService(repository=mock_repo)
    mock_session = AsyncMock()

    cancelled = await service.cancel_pipeline_run(
        session=mock_session,
        run_id=run.id,
        reason="Operator requested halt",
    )

    assert cancelled.status == PipelineRunStatusEnum.CANCELLED
    assert cancelled.completed_at is not None
