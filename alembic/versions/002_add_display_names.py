"""Add human-readable name to configuration and collection.

Revision ID: 002
Revises: 001
Create Date: 2025-02-20

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("configuration", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("collection", sa.Column("name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("collection", "name")
    op.drop_column("configuration", "name")
