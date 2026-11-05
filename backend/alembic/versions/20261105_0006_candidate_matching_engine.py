"""Candidate eligibility and deterministic matching engine schema.

Revision ID: 20261105_0006
Revises: 20261104_0005
Create Date: 2026-11-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "20261105_0006"
down_revision: str | None = "20261104_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create eligibility_status_enum
    eligibility_status_enum = postgresql.ENUM(
        "ELIGIBLE",
        "INELIGIBLE_EXPERIENCE",
        "INELIGIBLE_LOCATION",
        "INELIGIBLE_WORK_AUTH",
        "INELIGIBLE_MANDATORY_SKILL",
        name="eligibility_status_enum",
        create_type=False,
    )
    eligibility_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create job_matches table
    op.create_table(
        "job_matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "eligibility_status",
            sa.Enum(
                "ELIGIBLE",
                "INELIGIBLE_EXPERIENCE",
                "INELIGIBLE_LOCATION",
                "INELIGIBLE_WORK_AUTH",
                "INELIGIBLE_MANDATORY_SKILL",
                name="eligibility_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "deterministic_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "semantic_score",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "final_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "skill_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "experience_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "title_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "preference_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "match_explanation",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "match_explanation_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
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
        sa.UniqueConstraint("job_id", "candidate_profile_id", name="uq_job_matches_candidate_job"),
    )

    # 3. Create indexes
    op.create_index(
        "idx_job_matches_score",
        "job_matches",
        ["candidate_profile_id", sa.text("final_score DESC")],
    )
    op.create_index(
        "idx_job_matches_eligibility",
        "job_matches",
        ["candidate_profile_id", "eligibility_status"],
    )


def downgrade() -> None:
    op.drop_index("idx_job_matches_eligibility", table_name="job_matches")
    op.drop_index("idx_job_matches_score", table_name="job_matches")
    op.drop_table("job_matches")
    op.execute("DROP TYPE IF EXISTS eligibility_status_enum;")
