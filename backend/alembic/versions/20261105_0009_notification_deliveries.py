"""Create notification_deliveries table and lifecycle status enum.

Revision ID: 20261105_0009
Revises: 20261105_0008
Create Date: 2026-11-05 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "20261105_0009"
down_revision: str | None = "20261105_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create notification_delivery_status_enum
    notification_delivery_status_enum = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "SENT",
        "FAILED",
        name="notification_delivery_status_enum",
        create_type=False,
    )
    notification_delivery_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create notification_deliveries table
    op.create_table(
        "notification_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "candidate_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tailored_resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tailored_resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notification_type",
            sa.String(50),
            server_default=sa.text("'IMMEDIATE_TAILORED_JOB'"),
            nullable=False,
        ),
        sa.Column(
            "recipient_email",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "status",
            notification_delivery_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("3"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(50),
            server_default=sa.text("'smtp'"),
            nullable=False,
        ),
        sa.Column(
            "provider_message_id",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "job_id",
            "recipient_email",
            name="uq_notification_deliveries_job_recipient",
        ),
    )

    # 3. Create Indexes
    op.create_index(
        "idx_notifications_status",
        "notification_deliveries",
        ["status", "created_at"],
    )
    op.create_index(
        "idx_notifications_candidate",
        "notification_deliveries",
        ["candidate_profile_id", "created_at"],
    )
    op.create_index(
        "idx_notifications_job_match",
        "notification_deliveries",
        ["job_match_id"],
    )
    op.create_index(
        "idx_notifications_tailored_resume",
        "notification_deliveries",
        ["tailored_resume_id"],
    )


def downgrade() -> None:
    # 1. Drop Indexes
    op.drop_index("idx_notifications_tailored_resume", table_name="notification_deliveries")
    op.drop_index("idx_notifications_job_match", table_name="notification_deliveries")
    op.drop_index("idx_notifications_candidate", table_name="notification_deliveries")
    op.drop_index("idx_notifications_status", table_name="notification_deliveries")

    # 2. Drop Table
    op.drop_table("notification_deliveries")

    # 3. Drop Enum
    notification_delivery_status_enum = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "SENT",
        "FAILED",
        name="notification_delivery_status_enum",
    )
    notification_delivery_status_enum.drop(op.get_bind(), checkfirst=True)

