"""SQLAlchemy 2.0 models for Canonical Jobs and Raw Job Source Records."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CHAR,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.modules.candidate.models import EmploymentTypeEnum, WorkplaceTypeEnum

if TYPE_CHECKING:
    from app.modules.discovery.models import JobSource
    from app.modules.matching.models import JobMatch


class JobStatusEnum(enum.StrEnum):
    """Canonical lifecycle state machine for job opportunities."""

    DISCOVERED = "DISCOVERED"
    NORMALIZED = "NORMALIZED"
    ELIGIBILITY_FAILED = "ELIGIBILITY_FAILED"
    MATCHED = "MATCHED"
    REJECTED = "REJECTED"
    TAILORING = "TAILORING"
    TAILORED = "TAILORED"
    NOTIFIED = "NOTIFIED"
    ARCHIVED = "ARCHIVED"


class JobProcessingStatusEnum(enum.StrEnum):
    """Status tracking for raw job source record processing lifecycle."""

    RAW = "RAW"
    PROCESSING = "PROCESSING"
    CANONICALIZED = "CANONICALIZED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Job(Base, TimestampMixin):
    """Canonical deduplicated job representation across all discovery sources."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    canonical_company_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    canonical_application_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    workplace_type: Mapped[WorkplaceTypeEnum] = mapped_column(
        Enum(WorkplaceTypeEnum, name="workplace_type_enum"),
        default=WorkplaceTypeEnum.UNKNOWN,
        server_default=func.text("'UNKNOWN'"),
        nullable=False,
    )
    normalized_location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    employment_type: Mapped[EmploymentTypeEnum] = mapped_column(
        Enum(EmploymentTypeEnum, name="employment_type_enum"),
        default=EmploymentTypeEnum.UNKNOWN,
        server_default=func.text("'UNKNOWN'"),
        nullable=False,
    )
    description_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    dedup_fingerprint_sha256: Mapped[str] = mapped_column(
        CHAR(64),
        unique=True,
        nullable=False,
    )
    status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum, name="job_status_enum"),
        default=JobStatusEnum.DISCOVERED,
        server_default=func.text("'DISCOVERED'"),
        nullable=False,
    )

    # Relationships
    source_records: Mapped[list["JobSourceRecord"]] = relationship(
        "JobSourceRecord",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("dedup_fingerprint_sha256", name="uq_jobs_dedup_fingerprint"),
        Index("idx_jobs_status_first_seen", "status", "first_seen_at"),
        Index("idx_jobs_posted_at", "posted_at"),
    )


class JobSourceRecord(Base, TimestampMixin):
    """Provenance and raw payload persistence for every discovered job."""

    __tablename__ = "job_source_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_job_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_job_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    raw_posted_at: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    payload_hash_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="RAW",
        server_default=func.text("'RAW'"),
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    job: Mapped["Job | None"] = relationship(
        "Job",
        back_populates="source_records",
    )
    job_source: Mapped["JobSource"] = relationship(
        "JobSource",
        back_populates="records",
    )

    __table_args__ = (
        UniqueConstraint("job_source_id", "external_job_id", name="uq_job_source_record"),
        Index("idx_source_records_source_external", "job_source_id", "external_job_id"),
        Index("idx_source_records_status", "processing_status"),
    )
