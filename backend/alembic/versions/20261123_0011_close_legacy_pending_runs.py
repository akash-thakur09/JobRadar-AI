"""Close queued records left behind by the old discovery and tailoring workers."""

import sqlalchemy as sa
from alembic import op

revision = "20261123_0011"
down_revision = "20261105_0010"
branch_labels = None
depends_on = None

DISCOVERY_FAILURE = "This run predates linked discovery tracking. Start a new discovery run."
TAILORING_FAILURE = "This request predates reliable background tailoring. Regenerate the resume."


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE discovery_runs
            SET status = 'FAILED', completed_at = CURRENT_TIMESTAMP, error_summary = :reason
            WHERE status = 'PENDING' AND completed_at IS NULL AND error_summary IS NULL
        """),
        {"reason": DISCOVERY_FAILURE},
    )
    connection.execute(
        sa.text("""
            UPDATE tailored_resumes
            SET generation_status = 'FAILED', completed_at = CURRENT_TIMESTAMP, validation_error = :reason
            WHERE generation_status = 'PENDING' AND validation_error IS NULL
        """),
        {"reason": TAILORING_FAILURE},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE discovery_runs
            SET status = 'PENDING', completed_at = NULL, error_summary = NULL
            WHERE status = 'FAILED' AND error_summary = :reason
        """),
        {"reason": DISCOVERY_FAILURE},
    )
    connection.execute(
        sa.text("""
            UPDATE tailored_resumes
            SET generation_status = 'PENDING', completed_at = NULL, validation_error = NULL
            WHERE generation_status = 'FAILED' AND validation_error = :reason
        """),
        {"reason": TAILORING_FAILURE},
    )
