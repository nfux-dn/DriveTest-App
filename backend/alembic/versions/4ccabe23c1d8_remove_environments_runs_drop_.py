"""remove environments; runs drop environment_id

Revision ID: 4ccabe23c1d8
Revises: 2ff21a4c71ca
Create Date: 2026-08-10 08:04:02.675192

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4ccabe23c1d8'
down_revision: str | None = '2ff21a4c71ca'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the runs FK + column BEFORE the referenced environments table.
    op.drop_constraint(op.f('runs_environment_id_fkey'), 'runs', type_='foreignkey')
    op.drop_column('runs', 'environment_id')
    op.drop_table('environments')


def downgrade() -> None:
    # Recreate environments first, then re-add the runs column + FK.
    op.create_table(
        'environments',
        sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column('platform', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('system_type', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('software_version', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('capabilities_json', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('enabled', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('environments_pkey')),
    )
    op.add_column('runs', sa.Column('environment_id', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('runs_environment_id_fkey'), 'runs', 'environments', ['environment_id'], ['id'])
