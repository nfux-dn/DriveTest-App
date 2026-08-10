"""suite source provenance (branch, indexed commit, indexed_at)

Revision ID: a1b2c3d4e5f6
Revises: c759fd32fd85
Create Date: 2026-08-10 20:30:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'c759fd32fd85'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('suites', sa.Column('source_branch', sa.String(), nullable=True))
    op.add_column('suites', sa.Column('indexed_commit', sa.String(), nullable=True))
    op.add_column('suites', sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('suites', 'indexed_at')
    op.drop_column('suites', 'indexed_commit')
    op.drop_column('suites', 'source_branch')
