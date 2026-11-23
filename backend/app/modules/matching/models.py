"""SQLAlchemy 2.0 models for Candidate-Job Matching and Eligibility results."""

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.candidate.models import CandidateProfile
    from app.modules.jobs.models import Job


class EligibilityStatusEnum(enum.StrEnum):
    """Outcomes for Layer 1 Deterministic Eligibility evaluation."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE_EXPERIENCE = "INELIGIBLE_EXPERIENCE"
    INELIGIBLE_LOCATION = "INELIGIBLE_LOCATION"
    INELIGIBLE_WORK_AUTH = "INELIGIBLE_WORK_AUTH"
    INELIGIBLE_MANDATORY_SKILL = "INELIGIBLE_MANDATORY_SKILL"


class SemanticAnalysisStatusEnum(enum.StrEnum):
    """Lifecycle states for Layer 3 LLM Semantic Analysis."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class JobMatch(Base, TimestampMixin):
    """Persisted candidate-job matching result with line-item score breakdown."""

    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    eligibility_status: Mapped[EligibilityStatusEnum] = mapped_column(
        Enum(
            EligibilityStatusEnum,
            name="eligibility_status_enum",
            create_type=False,
        ),
        nullable=False,
    )
    semantic_analysis_status: Mapped[SemanticAnalysisStatusEnum] = mapped_column(
        Enum(
            SemanticAnalysisStatusEnum,
            name="semantic_analysis_status_enum",
            create_type=False,
        ),
        default=SemanticAnalysisStatusEnum.PENDING,
        server_default=func.text("'PENDING'"),
        nullable=False,
    )
    deterministic_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    semantic_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    final_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    skill_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    experience_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    title_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    preference_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default=func.text("0.00"),
        nullable=False,
    )
    match_explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    match_explanation_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=func.text("'{}'::jsonb"),
        nullable=False,
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="matches",
    )
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="matches",
    )

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_profile_id", name="uq_job_matches_candidate_job"),
        Index("idx_job_matches_score", "candidate_profile_id", final_score.desc()),
        Index("idx_job_matches_eligibility", "candidate_profile_id", "eligibility_status"),
        Index(
            "idx_job_matches_semantic_status", "candidate_profile_id", "semantic_analysis_status"
        ),
    )

    @property
    def is_qualified(self) -> bool:
        """Candidate-specific qualification outcome (>= 50.00 score and eligible)."""
        return (
            self.eligibility_status == EligibilityStatusEnum.ELIGIBLE
            and self.deterministic_score >= Decimal("50.00")
        )
