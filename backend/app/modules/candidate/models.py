"""SQLAlchemy models for Candidate Profile, Preferences, and Skills."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class WorkplaceTypeEnum(StrEnum):
    """Enumeration of accepted workplace arrangements."""

    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentTypeEnum(StrEnum):
    """Enumeration of employment classifications."""

    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"
    UNKNOWN = "UNKNOWN"


class User(Base, TimestampMixin):
    """Core user account entity (future-proofed multi-tenant foundation)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    profile: Mapped["CandidateProfile | None"] = relationship(
        "CandidateProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CandidateProfile(Base, TimestampMixin):
    """Structured professional identity and profile for the candidate."""

    __tablename__ = "candidate_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),
        CheckConstraint("total_experience_months >= 0", name="chk_total_experience_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    headline: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    professional_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    current_role: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    total_experience_months: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    work_authorization: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )
    preferences: Mapped["CandidatePreference | None"] = relationship(
        "CandidatePreference",
        back_populates="profile",
        uselist=False,
        cascade="all, delete-orphan",
    )
    skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    resumes: Mapped[list["app.modules.resumes.models.MasterResume"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "MasterResume",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CandidatePreference(Base, TimestampMixin):
    """Job matching preferences, filters, and relevance thresholds."""

    __tablename__ = "candidate_preferences"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", name="uq_candidate_preferences_profile"),
        CheckConstraint(
            "minimum_relevance_score >= 0.00 AND minimum_relevance_score <= 100.00",
            name="chk_relevance_score_range",
        ),
        CheckConstraint("max_job_age_days > 0", name="chk_job_age_positive"),
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
    minimum_relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("70.00"),
        nullable=False,
    )
    preferred_titles: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )
    preferred_workplace_types: Mapped[list[WorkplaceTypeEnum]] = mapped_column(
        ARRAY(
            ENUM(
                WorkplaceTypeEnum,
                name="workplace_type_enum",
                create_type=False,
            )
        ),
        default=lambda: [WorkplaceTypeEnum.REMOTE, WorkplaceTypeEnum.HYBRID],
        nullable=False,
    )
    preferred_locations: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )
    preferred_employment_types: Mapped[list[EmploymentTypeEnum]] = mapped_column(
        ARRAY(
            ENUM(
                EmploymentTypeEnum,
                name="employment_type_enum",
                create_type=False,
            )
        ),
        default=lambda: [EmploymentTypeEnum.FULL_TIME],
        nullable=False,
    )
    max_job_age_days: Mapped[int] = mapped_column(
        Integer,
        default=14,
        nullable=False,
    )

    # Relationships
    profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="preferences",
    )


class CandidateSkill(Base):
    """Normalized candidate skill record for fast deterministic matching."""

    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "skill_name", name="uq_candidate_skill"),
        CheckConstraint(
            "experience_months >= 0", name="chk_candidate_skill_experience_non_negative"
        ),
        Index("idx_candidate_skills_lookup", "candidate_profile_id", "skill_name"),
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
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
    )
    experience_months: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_core: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="skills",
    )
