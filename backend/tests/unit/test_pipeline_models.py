"""Unit tests for PipelineRun lifecycle states, state transitions, and models."""

import uuid
from datetime import UTC, datetime

import pytest

from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.exceptions import InvalidPipelineRunStateTransitionError
from app.modules.pipeline.models import PipelineRun


@pytest.mark.unit
def test_pipeline_run_initial_state() -> None:
    """Verify default initial state and enum representations."""
    candidate_id = uuid.uuid4()
    run = PipelineRun(
        candidate_profile_id=candidate_id,
        trigger_type=PipelineTriggerTypeEnum.MANUAL,
        status=PipelineRunStatusEnum.PENDING,
    )

    assert run.candidate_profile_id == candidate_id
    assert run.trigger_type == PipelineTriggerTypeEnum.MANUAL
    assert run.status == PipelineRunStatusEnum.PENDING
    assert run.started_at is None
    assert run.completed_at is None
    assert run.status.is_active is True
    assert run.status.is_terminal is False


@pytest.mark.unit
def test_valid_pipeline_state_transitions() -> None:
    """Verify all permitted state transitions in the lifecycle."""
    candidate_id = uuid.uuid4()

    # PENDING -> RUNNING
    run = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.PENDING,
    )
    run.transition_to(PipelineRunStatusEnum.RUNNING)
    assert run.status == PipelineRunStatusEnum.RUNNING
    assert run.started_at is not None
    assert run.completed_at is None
    assert run.status.is_active is True

    # RUNNING -> COMPLETED
    run.transition_to(PipelineRunStatusEnum.COMPLETED)
    assert run.status == PipelineRunStatusEnum.COMPLETED
    assert run.completed_at is not None
    assert run.status.is_terminal is True
    assert run.status.is_active is False

    # PENDING -> CANCELLED
    pending_run = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.PENDING,
    )
    pending_run.transition_to(PipelineRunStatusEnum.CANCELLED, reason="User cancelled before start")
    assert pending_run.status == PipelineRunStatusEnum.CANCELLED
    assert pending_run.completed_at is not None

    # RUNNING -> PARTIALLY_COMPLETED
    running_run_1 = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.RUNNING,
        started_at=datetime.now(UTC),
    )
    running_run_1.transition_to(
        PipelineRunStatusEnum.PARTIALLY_COMPLETED,
        error_summary="1 notification failed",
    )
    assert running_run_1.status == PipelineRunStatusEnum.PARTIALLY_COMPLETED
    assert running_run_1.error_summary == "1 notification failed"

    # RUNNING -> FAILED
    running_run_2 = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.RUNNING,
        started_at=datetime.now(UTC),
    )
    running_run_2.transition_to(
        PipelineRunStatusEnum.FAILED,
        error_summary="Critical database timeout",
    )
    assert running_run_2.status == PipelineRunStatusEnum.FAILED
    assert running_run_2.error_summary == "Critical database timeout"


@pytest.mark.unit
def test_invalid_pipeline_state_transitions_raise_error() -> None:
    """Verify illegal status transitions raise InvalidPipelineRunStateTransitionError."""
    candidate_id = uuid.uuid4()

    # Cannot transition PENDING directly to COMPLETED
    run = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.PENDING,
    )
    with pytest.raises(InvalidPipelineRunStateTransitionError) as exc_info:
        run.transition_to(PipelineRunStatusEnum.COMPLETED)
    assert exc_info.value.status_code == 409
    assert "Cannot transition pipeline run from 'PENDING' to 'COMPLETED'" in str(
        exc_info.value.message
    )

    # Cannot transition terminal states
    terminal_run = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.COMPLETED,
    )
    with pytest.raises(InvalidPipelineRunStateTransitionError):
        terminal_run.transition_to(PipelineRunStatusEnum.RUNNING)

    failed_run = PipelineRun(
        candidate_profile_id=candidate_id,
        status=PipelineRunStatusEnum.FAILED,
    )
    with pytest.raises(InvalidPipelineRunStateTransitionError):
        failed_run.transition_to(PipelineRunStatusEnum.COMPLETED)
