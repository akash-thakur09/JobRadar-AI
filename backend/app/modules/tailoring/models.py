"""SQLAlchemy 2.0 models for Job-Specific Tailored Resumes."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.modules.tailoring.enums import RenderingStrategyEnum, TailoredResumeStatusEnum

if TYPE_CHECKING:
    from app.modules.candidate.models import CandidateProfile
    from app.modules.jobs.models import Job
    from app.modules.matching.models import JobMatch
    from app.modules.resumes.models import ResumeVersion


class TailoredResume(Base, TimestampMixin):
    """Persisted tailored resume artifact generated for a qualified job opportunity."""

    __tablename__ = "tailored_resumes"

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
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rendering_strategy: Mapped[RenderingStrategyEnum] = mapped_column(
        Enum(
            RenderingStrategyEnum,
            name="rendering_strategy_enum",
            create_type=False,
        ),
        default=RenderingStrategyEnum.FALLBACK,
        server_default=func.text("'FALLBACK'"),
        nullable=False,
    )
    generation_status: Mapped[TailoredResumeStatusEnum] = mapped_column(
        Enum(
            TailoredResumeStatusEnum,
            name="tailored_resume_status_enum",
            create_type=False,
        ),
        default=TailoredResumeStatusEnum.PENDING,
        server_default=func.text("'PENDING'"),
        nullable=False,
    )
    tailored_content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=func.text("'{}'::jsonb"),
        nullable=False,
    )
    validation_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=func.text("'{}'::jsonb"),
        nullable=False,
    )
    storage_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        default="application/pdf",
        server_default=func.text("'application/pdf'"),
        nullable=False,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    generation_attempts: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=func.text("1"),
        nullable=False,
    )
    validation_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped["Job"] = relationship("Job")
    job_match: Mapped["JobMatch"] = relationship("JobMatch")
    resume_version: Mapped["ResumeVersion"] = relationship("ResumeVersion")

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "resume_version_id",
            name="uq_tailored_resumes_job_resume",
        ),
        Index("idx_tailored_resumes_status", "generation_status"),
        Index(
            "idx_tailored_resumes_candidate_created",
            "candidate_profile_id",
            text("created_at DESC"),
        ),
        Index("idx_tailored_resumes_job_match", "job_match_id"),
    )
