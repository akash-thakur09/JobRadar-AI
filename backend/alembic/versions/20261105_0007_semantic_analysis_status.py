"""Add semantic_analysis_status to job_matches.

Revision ID: 20261105_0007
Revises: 20261105_0006
Create Date: 2026-11-05 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "20261105_0007"
down_revision: str | None = "20261105_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create semantic_analysis_status_enum
    semantic_analysis_status_enum = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "COMPLETED",
        "FAILED",
        "SKIPPED",
        name="semantic_analysis_status_enum",
        create_type=False,
    )
    semantic_analysis_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add column semantic_analysis_status to job_matches
    op.add_column(
        "job_matches",
        sa.Column(
            "semantic_analysis_status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                "SKIPPED",
                name="semantic_analysis_status_enum",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
    )

    # 3. Create index idx_job_matches_semantic_status
    op.create_index(
        "idx_job_matches_semantic_status",
        "job_matches",
        ["candidate_profile_id", "semantic_analysis_status"],
    )


def downgrade() -> None:
    op.drop_index("idx_job_matches_semantic_status", table_name="job_matches")
    op.drop_column("job_matches", "semantic_analysis_status")
    op.execute("DROP TYPE IF EXISTS semantic_analysis_status_enum;")
