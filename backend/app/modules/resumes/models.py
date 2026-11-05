"""SQLAlchemy models for Master Resumes and Resume Versions."""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class ResumeProcessingStatus(StrEnum):
    """Lifecycle states for resume parsing and extraction."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MasterResume(Base, TimestampMixin):
    """Metadata and storage pointer for uploaded candidate master resume source files."""

    __tablename__ = "master_resumes"
    __table_args__ = (
        Index("idx_master_resumes_active", "candidate_profile_id", "is_active"),
        Index("idx_master_resumes_checksum", "candidate_profile_id", "checksum_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    candidate_profile: Mapped["app.modules.candidate.models.CandidateProfile"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CandidateProfile",
        back_populates="resumes",
    )
    versions: Mapped[list["ResumeVersion"]] = relationship(
        "ResumeVersion",
        back_populates="master_resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersion.version_number.desc()",
        lazy="selectin",
    )


class ResumeVersion(Base, TimestampMixin):
    """Structured extraction, template metadata, and versioning for a master resume."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("master_resume_id", "version_number", name="uq_resume_versions_num"),
        Index("idx_resume_versions_master", "master_resume_id"),
        Index(
            "idx_resume_versions_jsonb_skills",
            text("(structured_content->'skills')"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    master_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    structured_content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    template_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(30),
        default=ResumeProcessingStatus.PENDING.value,
        nullable=False,
    )
    parsing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    master_resume: Mapped["MasterResume"] = relationship(
        "MasterResume",
        back_populates="versions",
    )
