"""Create pipeline_runs table and orchestration enums.

Revision ID: 20261105_0010
Revises: 20261105_0009
Create Date: 2026-11-05 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "20261105_0010"
down_revision: str | None = "20261105_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create pipeline enums
    pipeline_run_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "PARTIALLY_COMPLETED",
        "FAILED",
        "CANCELLED",
        name="pipeline_run_status_enum",
        create_type=False,
    )
    pipeline_run_status_enum.create(op.get_bind(), checkfirst=True)

    pipeline_trigger_type_enum = postgresql.ENUM(
        "MANUAL",
        "SCHEDULED",
        "API",
        name="pipeline_trigger_type_enum",
        create_type=False,
    )
    pipeline_trigger_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create pipeline_runs table
    op.create_table(
        "pipeline_runs",
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
            "trigger_type",
            pipeline_trigger_type_enum,
            server_default=sa.text("'MANUAL'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            pipeline_run_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "jobs_discovered",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_created",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_updated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_normalized",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_deduplicated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "jobs_evaluated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "matches_created",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "matches_qualified",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "semantic_analyses_completed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "semantic_analyses_failed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "resumes_generated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "resumes_failed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "notifications_sent",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "notifications_failed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "error_summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
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
    )

    # 3. Create Indexes
    op.create_index(
        "idx_pipeline_runs_candidate_profile_id",
        "pipeline_runs",
        ["candidate_profile_id"],
    )
    op.create_index(
        "idx_pipeline_runs_status",
        "pipeline_runs",
        ["status"],
    )
    op.create_index(
        "idx_pipeline_runs_created_at",
        "pipeline_runs",
        ["created_at"],
    )
    # Partial unique index enforcing at most one active run (PENDING or RUNNING) per candidate profile
    op.create_index(
        "uq_pipeline_runs_active_candidate",
        "pipeline_runs",
        ["candidate_profile_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')"),
    )


def downgrade() -> None:
    # 1. Drop Indexes
    op.drop_index("uq_pipeline_runs_active_candidate", table_name="pipeline_runs")
    op.drop_index("idx_pipeline_runs_created_at", table_name="pipeline_runs")
    op.drop_index("idx_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("idx_pipeline_runs_candidate_profile_id", table_name="pipeline_runs")

    # 2. Drop Table
    op.drop_table("pipeline_runs")

    # 3. Drop Enums
    pipeline_trigger_type_enum = postgresql.ENUM(
        "MANUAL",
        "SCHEDULED",
        "API",
        name="pipeline_trigger_type_enum",
    )
    pipeline_trigger_type_enum.drop(op.get_bind(), checkfirst=True)

    pipeline_run_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "PARTIALLY_COMPLETED",
        "FAILED",
        "CANCELLED",
        name="pipeline_run_status_enum",
    )
    pipeline_run_status_enum.drop(op.get_bind(), checkfirst=True)
