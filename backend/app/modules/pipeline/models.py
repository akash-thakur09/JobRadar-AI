"""SQLAlchemy 2.0 model for Pipeline Runs and Orchestration Tracking."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.modules.pipeline.enums import (
    PipelineRunStatusEnum,
    PipelineTriggerTypeEnum,
)
from app.modules.pipeline.exceptions import InvalidPipelineRunStateTransitionError

if TYPE_CHECKING:
    from app.modules.candidate.models import CandidateProfile


class PipelineRun(Base, TimestampMixin):
    """Tracks end-to-end execution lifecycle, metrics, and state of an orchestrated pipeline run."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[PipelineTriggerTypeEnum] = mapped_column(
        Enum(
            PipelineTriggerTypeEnum,
            name="pipeline_trigger_type_enum",
            create_type=False,
        ),
        default=PipelineTriggerTypeEnum.MANUAL,
        server_default=func.text("'MANUAL'"),
        nullable=False,
    )
    status: Mapped[PipelineRunStatusEnum] = mapped_column(
        Enum(
            PipelineRunStatusEnum,
            name="pipeline_run_status_enum",
            create_type=False,
        ),
        default=PipelineRunStatusEnum.PENDING,
        server_default=func.text("'PENDING'"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Discovery & Normalization metrics
    jobs_discovered: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    jobs_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    jobs_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    jobs_normalized: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    jobs_deduplicated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )

    # Matching metrics
    jobs_evaluated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    matches_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    matches_qualified: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )

    # Semantic analysis metrics
    semantic_analyses_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    semantic_analyses_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )

    # Tailoring metrics
    resumes_generated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    resumes_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )

    # Notification metrics
    notifications_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    notifications_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )

    # Error summary and metadata
    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=func.text("'{}'::jsonb"),
        nullable=False,
    )

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile")

    __table_args__ = (
        Index("ix_pipeline_runs_created_at", "created_at"),
        Index(
            "uq_pipeline_runs_active_candidate",
            "candidate_profile_id",
            unique=True,
            postgresql_where=(
                status.in_([PipelineRunStatusEnum.PENDING, PipelineRunStatusEnum.RUNNING])
            ),
        ),
    )

    def transition_to(
        self,
        target_status: PipelineRunStatusEnum,
        reason: str = "",
        error_summary: str | None = None,
    ) -> None:
        """Validate and apply a lifecycle state transition.

        Allowed transitions:
            PENDING -> RUNNING, CANCELLED
            RUNNING -> COMPLETED, PARTIALLY_COMPLETED, FAILED, CANCELLED
        """
        valid_transitions: dict[PipelineRunStatusEnum, set[PipelineRunStatusEnum]] = {
            PipelineRunStatusEnum.PENDING: {
                PipelineRunStatusEnum.RUNNING,
                PipelineRunStatusEnum.CANCELLED,
            },
            PipelineRunStatusEnum.RUNNING: {
                PipelineRunStatusEnum.COMPLETED,
                PipelineRunStatusEnum.PARTIALLY_COMPLETED,
                PipelineRunStatusEnum.FAILED,
                PipelineRunStatusEnum.CANCELLED,
            },
            PipelineRunStatusEnum.COMPLETED: set(),
            PipelineRunStatusEnum.PARTIALLY_COMPLETED: set(),
            PipelineRunStatusEnum.FAILED: set(),
            PipelineRunStatusEnum.CANCELLED: set(),
        }

        allowed = valid_transitions.get(self.status, set())
        if target_status not in allowed:
            raise InvalidPipelineRunStateTransitionError(
                current_status=self.status.value,
                target_status=target_status.value,
                reason=reason or f"Transition not allowed from state '{self.status.value}'",
            )

        now = datetime.now(UTC)
        self.status = target_status

        if target_status == PipelineRunStatusEnum.RUNNING and not self.started_at:
            self.started_at = now
        elif target_status.is_terminal:
            self.completed_at = now

        if error_summary:
            self.error_summary = error_summary
