"""Initial baseline migration enabling PostgreSQL trigram extension.

Revision ID: 20261104_0001
Revises:
Create Date: 2026-11-04 14:40:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261104_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable PostgreSQL trigram extension approved in STACK_DECISIONS.md
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
