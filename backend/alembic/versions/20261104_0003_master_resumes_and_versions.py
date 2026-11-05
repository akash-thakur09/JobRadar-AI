"""Master resumes and parsed resume versions schema.

Revision ID: 20261104_0003
Revises: 20261104_0002
Create Date: 2026-11-04 16:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261104_0003"
down_revision: str | None = "20261104_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Table: master_resumes
    op.create_table(
        "master_resumes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
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
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_master_resumes_candidate_profile_id",
        "master_resumes",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_master_resumes_checksum_sha256",
        "master_resumes",
        ["checksum_sha256"],
    )
    op.create_index(
        "idx_master_resumes_active",
        "master_resumes",
        ["candidate_profile_id", "is_active"],
    )
    op.create_index(
        "idx_master_resumes_checksum",
        "master_resumes",
        ["candidate_profile_id", "checksum_sha256"],
    )
    op.create_index(
        "uq_master_resumes_single_active",
        "master_resumes",
        ["candidate_profile_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # 2. Table: resume_versions
    op.create_table(
        "resume_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("master_resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "structured_content",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("template_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_valid", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=30),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("parsing_error", sa.Text(), nullable=True),
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
            ["master_resume_id"],
            ["master_resumes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("master_resume_id", "version_number", name="uq_resume_versions_num"),
    )
    op.create_index(
        "ix_resume_versions_master_resume_id",
        "resume_versions",
        ["master_resume_id"],
    )
    op.create_index(
        "idx_resume_versions_master",
        "resume_versions",
        ["master_resume_id"],
    )
    op.create_index(
        "idx_resume_versions_jsonb_skills",
        "resume_versions",
        [sa.text("(structured_content->'skills')")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_resume_versions_jsonb_skills", table_name="resume_versions")
    op.drop_index("idx_resume_versions_master", table_name="resume_versions")
    op.drop_index("ix_resume_versions_master_resume_id", table_name="resume_versions")
    op.drop_table("resume_versions")

    op.drop_index("uq_master_resumes_single_active", table_name="master_resumes")
    op.drop_index("idx_master_resumes_checksum", table_name="master_resumes")
    op.drop_index("idx_master_resumes_active", table_name="master_resumes")
    op.drop_index("ix_master_resumes_checksum_sha256", table_name="master_resumes")
    op.drop_index("ix_master_resumes_candidate_profile_id", table_name="master_resumes")
    op.drop_table("master_resumes")
