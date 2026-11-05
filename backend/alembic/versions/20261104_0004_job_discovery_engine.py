"""Job discovery sources, execution runs, canonical jobs, and raw job source records.

Revision ID: 20261104_0004
Revises: 20261104_0003
Create Date: 2026-11-04 17:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261104_0004"
down_revision: str | None = "20261104_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enums
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE job_source_type_enum AS ENUM (
                'GREENHOUSE',
                'LEVER',
                'CAREER_PAGE',
                'MANUAL_FEED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE discovery_run_status_enum AS ENUM (
                'PENDING',
                'RUNNING',
                'COMPLETED',
                'FAILED',
                'PARTIAL'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE job_status_enum AS ENUM (
                'DISCOVERED',
                'NORMALIZED',
                'ELIGIBILITY_FAILED',
                'MATCHED',
                'REJECTED',
                'TAILORING',
                'TAILORED',
                'NOTIFIED',
                'ARCHIVED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # 2. Table: job_sources
    op.create_table(
        "job_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                "GREENHOUSE",
                "LEVER",
                "CAREER_PAGE",
                "MANUAL_FEED",
                name="job_source_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column(
            "polling_interval_minutes",
            sa.Integer(),
            server_default=sa.text("360"),
            nullable=False,
        ),
        sa.Column(
            "configuration",
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
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_job_sources_name"),
    )
    op.create_index("ix_job_sources_name", "job_sources", ["name"], unique=True)
    op.create_index(
        "idx_job_sources_polling",
        "job_sources",
        ["is_enabled", "polling_interval_minutes"],
    )

    # 3. Table: discovery_runs
    op.create_table(
        "discovery_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "PARTIAL",
                name="discovery_run_status_enum",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
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
        sa.Column("error_summary", sa.Text(), nullable=True),
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
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"],
            ["job_sources.id"],
            name="fk_discovery_runs_job_source_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_discovery_runs_source_time",
        "discovery_runs",
        ["job_source_id", "started_at"],
    )

    # 4. Table: jobs (Canonical Jobs Foundation)
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("canonical_company_name", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("canonical_application_url", sa.String(length=1024), nullable=False),
        sa.Column(
            "workplace_type",
            postgresql.ENUM(
                "REMOTE",
                "HYBRID",
                "ONSITE",
                "UNKNOWN",
                name="workplace_type_enum",
                create_type=False,
            ),
            server_default=sa.text("'UNKNOWN'"),
            nullable=False,
        ),
        sa.Column("normalized_location", sa.String(length=150), nullable=True),
        sa.Column(
            "employment_type",
            postgresql.ENUM(
                "FULL_TIME",
                "PART_TIME",
                "CONTRACT",
                "INTERNSHIP",
                "TEMPORARY",
                "UNKNOWN",
                name="employment_type_enum",
                create_type=False,
            ),
            server_default=sa.text("'UNKNOWN'"),
            nullable=False,
        ),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("dedup_fingerprint_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DISCOVERED",
                "NORMALIZED",
                "ELIGIBILITY_FAILED",
                "MATCHED",
                "REJECTED",
                "TAILORING",
                "TAILORED",
                "NOTIFIED",
                "ARCHIVED",
                name="job_status_enum",
                create_type=False,
            ),
            server_default=sa.text("'DISCOVERED'"),
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
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_fingerprint_sha256", name="uq_jobs_dedup_fingerprint"),
    )
    op.create_index(
        "idx_jobs_status_first_seen",
        "jobs",
        ["status", "first_seen_at"],
    )
    op.create_index(
        "idx_jobs_posted_at",
        "jobs",
        ["posted_at"],
    )

    # 5. Table: job_source_records (Raw Ingestion Persistence)
    op.create_table(
        "job_source_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_job_id", sa.String(length=255), nullable=False),
        sa.Column("source_job_url", sa.String(length=1024), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_posted_at", sa.String(length=100), nullable=True),
        sa.Column("payload_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=50),
            server_default=sa.text("'RAW'"),
            nullable=False,
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_source_records_job_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"],
            ["job_sources.id"],
            name="fk_job_source_records_job_source_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_source_id",
            "external_job_id",
            name="uq_job_source_record",
        ),
    )
    op.create_index(
        "idx_source_records_job_id",
        "job_source_records",
        ["job_id"],
    )
    op.create_index(
        "idx_source_records_source_external",
        "job_source_records",
        ["job_source_id", "external_job_id"],
    )
    op.create_index(
        "idx_source_records_hash",
        "job_source_records",
        ["payload_hash_sha256"],
    )


def downgrade() -> None:
    op.drop_table("job_source_records")
    op.drop_table("jobs")
    op.drop_table("discovery_runs")
    op.drop_table("job_sources")

    op.execute("DROP TYPE IF EXISTS job_status_enum;")
    op.execute("DROP TYPE IF EXISTS discovery_run_status_enum;")
    op.execute("DROP TYPE IF EXISTS job_source_type_enum;")
