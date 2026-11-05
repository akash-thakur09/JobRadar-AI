"""Job normalization and deduplication indexes and processing error auditing.

Revision ID: 20261104_0005
Revises: 20261104_0004
Create Date: 2026-11-04 18:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261104_0005"
down_revision: str | None = "20261104_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Auditing column on job_source_records
    op.add_column(
        "job_source_records",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )

    # 2. Status lookup index for background normalization workers
    op.create_index(
        "idx_source_records_status",
        "job_source_records",
        ["processing_status"],
    )

    # 3. Trigram fuzzy search indexes on canonical company name and title
    op.create_index(
        "idx_jobs_company_trgm",
        "jobs",
        ["canonical_company_name"],
        postgresql_using="gin",
        postgresql_ops={"canonical_company_name": "gin_trgm_ops"},
    )
    op.create_index(
        "idx_jobs_title_trgm",
        "jobs",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_title_trgm", table_name="jobs")
    op.drop_index("idx_jobs_company_trgm", table_name="jobs")
    op.drop_index("idx_source_records_status", table_name="job_source_records")
    op.drop_column("job_source_records", "processing_error")
