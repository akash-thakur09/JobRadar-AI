"""Pipeline orchestration enums defining execution status and trigger types."""

from enum import StrEnum


class PipelineRunStatusEnum(StrEnum):
    """Lifecycle status states for an orchestrated pipeline run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        """Return True if status represents an immutable terminal state."""
        return self in (
            PipelineRunStatusEnum.COMPLETED,
            PipelineRunStatusEnum.PARTIALLY_COMPLETED,
            PipelineRunStatusEnum.FAILED,
            PipelineRunStatusEnum.CANCELLED,
        )

    @property
    def is_active(self) -> bool:
        """Return True if status represents an active, non-terminal execution."""
        return self in (PipelineRunStatusEnum.PENDING, PipelineRunStatusEnum.RUNNING)


class PipelineTriggerTypeEnum(StrEnum):
    """Trigger mechanisms initiating a pipeline run."""

    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"
    API = "API"
