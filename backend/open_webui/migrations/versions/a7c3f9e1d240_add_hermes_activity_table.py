"""Add hermes_activity table

Revision ID: a7c3f9e1d240
Revises: f0bd01a18a3d
Create Date: 2026-08-03 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7c3f9e1d240'
down_revision: Union[str, None] = 'f0bd01a18a3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hermes_activity',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('reference', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hermes_activity_created', 'hermes_activity', ['created_at'])
    op.create_index('ix_hermes_activity_status_created', 'hermes_activity', ['status', 'created_at'])
    op.create_index('ix_hermes_activity_user_created', 'hermes_activity', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_hermes_activity_user_created', table_name='hermes_activity')
    op.drop_index('ix_hermes_activity_status_created', table_name='hermes_activity')
    op.drop_index('ix_hermes_activity_created', table_name='hermes_activity')
    op.drop_table('hermes_activity')
