"""Pipeline orchestration domain exceptions with RFC 7807 problem detail semantics."""

import uuid
from typing import Any

from app.core.exceptions import DomainException


class PipelineError(DomainException):
    """Base exception for pipeline orchestration domain errors."""

    def __init__(
        self,
        message: str = "A pipeline orchestration error occurred.",
        status_code: int = 400,
        error_type: str = "pipeline-error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            error_type=error_type,
            invalid_params=invalid_params,
        )


class PipelineRunNotFoundError(PipelineError):
    """Raised when a requested pipeline run does not exist."""

    def __init__(self, pipeline_run_id: uuid.UUID) -> None:
        super().__init__(
            message=f"Pipeline run '{pipeline_run_id}' was not found.",
            status_code=404,
            error_type="pipeline-run-not-found",
        )
        self.pipeline_run_id = pipeline_run_id


class ActivePipelineRunConflictError(PipelineError):
    """Raised when attempting to start a pipeline run while another run is already active for the candidate."""

    def __init__(
        self, candidate_profile_id: uuid.UUID, active_run_id: uuid.UUID | None = None
    ) -> None:
        detail = (
            f"An active pipeline run is already running for candidate '{candidate_profile_id}'."
        )
        if active_run_id:
            detail += f" Active run ID: '{active_run_id}'."
        super().__init__(
            message=detail,
            status_code=409,
            error_type="active-pipeline-run-conflict",
        )
        self.candidate_profile_id = candidate_profile_id
        self.active_run_id = active_run_id


class InvalidPipelineRunStateTransitionError(PipelineError):
    """Raised when attempting an illegal pipeline run state transition."""

    def __init__(self, current_status: str, target_status: str, reason: str = "") -> None:
        msg = f"Cannot transition pipeline run from '{current_status}' to '{target_status}'."
        if reason:
            msg += f" {reason}"
        super().__init__(
            message=msg,
            status_code=409,
            error_type="invalid-pipeline-state-transition",
        )
        self.current_status = current_status
        self.target_status = target_status


class PipelineExecutionError(PipelineError):
    """Raised when an unrecoverable failure occurs during orchestrated execution."""

    def __init__(self, message: str, pipeline_run_id: uuid.UUID | None = None) -> None:
        super().__init__(
            message=f"Pipeline execution failure: {message}",
            status_code=500,
            error_type="pipeline-execution-failure",
        )
        self.pipeline_run_id = pipeline_run_id
