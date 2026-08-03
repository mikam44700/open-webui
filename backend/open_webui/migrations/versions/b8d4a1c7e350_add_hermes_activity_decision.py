"""Add decision columns to hermes_activity

Revision ID: b8d4a1c7e350
Revises: a7c3f9e1d240
Create Date: 2026-08-03 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b8d4a1c7e350'
down_revision: Union[str, None] = 'a7c3f9e1d240'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Who signed off, and when. Kept as real columns rather than folded into
    # `meta`: this is the answer to "who approved this" when a shipment is held
    # at the port, and that answer has to survive and stay queryable.
    op.add_column('hermes_activity', sa.Column('decided_by', sa.Text(), nullable=True))
    op.add_column('hermes_activity', sa.Column('decided_at', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('hermes_activity', 'decided_at')
    op.drop_column('hermes_activity', 'decided_by')
