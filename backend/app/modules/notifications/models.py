"""SQLAlchemy 2.0 models for Email Notification and Delivery tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.modules.notifications.enums import (
    NotificationDeliveryStatusEnum,
    NotificationTypeEnum,
)

if TYPE_CHECKING:
    from app.modules.candidate.models import CandidateProfile
    from app.modules.jobs.models import Job
    from app.modules.matching.models import JobMatch
    from app.modules.tailoring.models import TailoredResume


class NotificationDelivery(Base, TimestampMixin):
    """Tracks email delivery lifecycle, idempotency, attempts, and attachments for job match notifications."""

    __tablename__ = "notification_deliveries"

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
    tailored_resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tailored_resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        default=NotificationTypeEnum.IMMEDIATE_TAILORED_JOB.value,
        server_default=func.text(f"'{NotificationTypeEnum.IMMEDIATE_TAILORED_JOB.value}'"),
        nullable=False,
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[NotificationDeliveryStatusEnum] = mapped_column(
        Enum(
            NotificationDeliveryStatusEnum,
            name="notification_delivery_status_enum",
            create_type=False,
        ),
        default=NotificationDeliveryStatusEnum.PENDING,
        server_default=func.text("'PENDING'"),
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=func.text("0"),
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default=func.text("3"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        default="smtp",
        server_default=func.text("'smtp'"),
        nullable=False,
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    job: Mapped["Job"] = relationship("Job")
    job_match: Mapped["JobMatch"] = relationship("JobMatch")
    tailored_resume: Mapped["TailoredResume"] = relationship("TailoredResume")

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "recipient_email",
            name="uq_notification_deliveries_job_recipient",
        ),
        Index("idx_notifications_status", "status", "created_at"),
        Index("idx_notifications_candidate", "candidate_profile_id", "created_at"),
        Index("idx_notifications_job_match", "job_match_id"),
        Index("idx_notifications_tailored_resume", "tailored_resume_id"),
    )

