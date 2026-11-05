"""Create tailored_resumes table and lifecycle enums.

Revision ID: 20261105_0008
Revises: 20261105_0007
Create Date: 2026-11-05 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "20261105_0008"
down_revision: str | None = "20261105_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create rendering_strategy_enum
    rendering_strategy_enum = postgresql.ENUM(
        "PRESERVED",
        "FALLBACK",
        name="rendering_strategy_enum",
        create_type=False,
    )
    rendering_strategy_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create tailored_resume_status_enum
    tailored_resume_status_enum = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "VALIDATING",
        "RENDERING",
        "COMPLETED",
        "FAILED",
        name="tailored_resume_status_enum",
        create_type=False,
    )
    tailored_resume_status_enum.create(op.get_bind(), checkfirst=True)

    # 3. Create tailored_resumes table
    op.create_table(
        "tailored_resumes",
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
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rendering_strategy",
            sa.Enum(
                "PRESERVED",
                "FALLBACK",
                name="rendering_strategy_enum",
                create_type=False,
            ),
            server_default=sa.text("'FALLBACK'"),
            nullable=False,
        ),
        sa.Column(
            "generation_status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "VALIDATING",
                "RENDERING",
                "COMPLETED",
                "FAILED",
                name="tailored_resume_status_enum",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "tailored_content",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "mime_type",
            sa.String(length=100),
            server_default=sa.text("'application/pdf'"),
            nullable=False,
        ),
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "checksum_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "generation_attempts",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "validation_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "job_id",
            "resume_version_id",
            name="uq_tailored_resumes_job_resume",
        ),
    )

    # 4. Create indexes
    op.create_index(
        "idx_tailored_resumes_status",
        "tailored_resumes",
        ["generation_status"],
    )
    op.create_index(
        "idx_tailored_resumes_candidate_created",
        "tailored_resumes",
        ["candidate_profile_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_tailored_resumes_job_match",
        "tailored_resumes",
        ["job_match_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_tailored_resumes_job_match", table_name="tailored_resumes")
    op.drop_index("idx_tailored_resumes_candidate_created", table_name="tailored_resumes")
    op.drop_index("idx_tailored_resumes_status", table_name="tailored_resumes")
    op.drop_table("tailored_resumes")
    op.execute("DROP TYPE IF EXISTS tailored_resume_status_enum;")
    op.execute("DROP TYPE IF EXISTS rendering_strategy_enum;")
