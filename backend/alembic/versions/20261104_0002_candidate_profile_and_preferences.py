"""Candidate profile, preferences, and verified skills schema.

Revision ID: 20261104_0002
Revises: 20261104_0001
Create Date: 2026-11-04 15:55:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261104_0002"
down_revision: str | None = "20261104_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enums
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE workplace_type_enum AS ENUM ('REMOTE', 'HYBRID', 'ONSITE', 'UNKNOWN');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE employment_type_enum AS ENUM ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP', 'TEMPORARY', 'UNKNOWN');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # 2. Table: users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 3. Table: candidate_profiles
    op.create_table(
        "candidate_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=True),
        sa.Column("professional_summary", sa.Text(), nullable=True),
        sa.Column("current_role", sa.String(length=150), nullable=True),
        sa.Column(
            "total_experience_months",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("work_authorization", sa.String(length=50), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),
        sa.CheckConstraint(
            "total_experience_months >= 0",
            name="chk_total_experience_non_negative",
        ),
    )
    op.create_index("ix_candidate_profiles_user_id", "candidate_profiles", ["user_id"], unique=True)

    # 4. Table: candidate_preferences
    op.create_table(
        "candidate_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "minimum_relevance_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("70.00"),
            nullable=False,
        ),
        sa.Column(
            "preferred_titles",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_workplace_types",
            postgresql.ARRAY(
                postgresql.ENUM(
                    "REMOTE",
                    "HYBRID",
                    "ONSITE",
                    "UNKNOWN",
                    name="workplace_type_enum",
                    create_type=False,
                )
            ),
            server_default=sa.text("'{REMOTE, HYBRID}'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_locations",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_employment_types",
            postgresql.ARRAY(
                postgresql.ENUM(
                    "FULL_TIME",
                    "PART_TIME",
                    "CONTRACT",
                    "INTERNSHIP",
                    "TEMPORARY",
                    "UNKNOWN",
                    name="employment_type_enum",
                    create_type=False,
                )
            ),
            server_default=sa.text("'{FULL_TIME}'"),
            nullable=False,
        ),
        sa.Column("max_job_age_days", sa.Integer(), server_default=sa.text("14"), nullable=False),
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
        sa.UniqueConstraint("candidate_profile_id", name="uq_candidate_preferences_profile"),
        sa.CheckConstraint(
            "minimum_relevance_score >= 0.00 AND minimum_relevance_score <= 100.00",
            name="chk_relevance_score_range",
        ),
        sa.CheckConstraint("max_job_age_days > 0", name="chk_job_age_positive"),
    )
    op.create_index(
        "ix_candidate_preferences_candidate_profile_id",
        "candidate_preferences",
        ["candidate_profile_id"],
        unique=True,
    )

    # 5. Table: candidate_skills
    op.create_table(
        "candidate_skills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column(
            "category", sa.String(length=50), server_default=sa.text("'general'"), nullable=False
        ),
        sa.Column(
            "experience_months",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("is_core", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column(
            "created_at",
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
        sa.UniqueConstraint("candidate_profile_id", "skill_name", name="uq_candidate_skill"),
        sa.CheckConstraint(
            "experience_months >= 0",
            name="chk_candidate_skill_experience_non_negative",
        ),
    )
    op.create_index(
        "idx_candidate_skills_lookup",
        "candidate_skills",
        ["candidate_profile_id", "skill_name"],
    )
    op.create_index(
        "ix_candidate_skills_candidate_profile_id",
        "candidate_skills",
        ["candidate_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_skills_candidate_profile_id", table_name="candidate_skills")
    op.drop_index("idx_candidate_skills_lookup", table_name="candidate_skills")
    op.drop_table("candidate_skills")

    op.drop_index(
        "ix_candidate_preferences_candidate_profile_id",
        table_name="candidate_preferences",
    )
    op.drop_table("candidate_preferences")

    op.drop_index("ix_candidate_profiles_user_id", table_name="candidate_profiles")
    op.drop_table("candidate_profiles")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS employment_type_enum;")
    op.execute("DROP TYPE IF EXISTS workplace_type_enum;")
