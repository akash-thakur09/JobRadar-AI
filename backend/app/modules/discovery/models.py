"""SQLAlchemy 2.0 models for Job Discovery Sources and Execution Runs."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.jobs.models import JobSourceRecord


class JobSourceTypeEnum(enum.StrEnum):
    """Supported upstream job board and discovery adapter types."""

    GREENHOUSE = "GREENHOUSE"
    LEVER = "LEVER"
    CAREER_PAGE = "CAREER_PAGE"
    MANUAL_FEED = "MANUAL_FEED"


class DiscoveryRunStatusEnum(enum.StrEnum):
    """Lifecycle status for an asynchronous discovery execution run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class JobSource(Base, TimestampMixin):
    """Registry of job boards, ATS portals, and discovery endpoints."""

    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    source_type: Mapped[JobSourceTypeEnum] = mapped_column(
        Enum(JobSourceTypeEnum, name="job_source_type_enum"),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=func.text("TRUE"),
        nullable=False,
    )
    polling_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        default=360,
        server_default=func.text("360"),
        nullable=False,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=func.text("'{}'::jsonb"),
        nullable=False,
    )

    # Relationships
    runs: Mapped[list["DiscoveryRun"]] = relationship(
        "DiscoveryRun",
        back_populates="job_source",
        cascade="all, delete-orphan",
        order_by="desc(DiscoveryRun.started_at)",
    )
    records: Mapped[list["JobSourceRecord"]] = relationship(
        "JobSourceRecord",
        back_populates="job_source",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_job_sources_name"),
        Index("idx_job_sources_polling", "is_enabled", "polling_interval_minutes"),
    )


class DiscoveryRun(Base, TimestampMixin):
    """Execution audit logs for discovery adapter runs."""

    __tablename__ = "discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    job_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[DiscoveryRunStatusEnum] = mapped_column(
        Enum(DiscoveryRunStatusEnum, name="discovery_run_status_enum"),
        default=DiscoveryRunStatusEnum.PENDING,
        server_default=func.text("'PENDING'"),
        nullable=False,
    )
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
    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    job_source: Mapped["JobSource"] = relationship(
        "JobSource",
        back_populates="runs",
    )

    __table_args__ = (Index("idx_discovery_runs_source_time", "job_source_id", "started_at"),)
