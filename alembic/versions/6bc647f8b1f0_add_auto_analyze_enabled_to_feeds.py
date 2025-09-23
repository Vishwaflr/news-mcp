"""Add auto_analyze_enabled to feeds table

Revision ID: 6bc647f8b1f0
Revises: de68ec3b50e5
Create Date: 2025-09-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bc647f8b1f0'
down_revision: Union[str, Sequence[str], None] = 'de68ec3b50e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auto_analyze_enabled column to feeds table."""
    op.add_column('feeds', sa.Column('auto_analyze_enabled', sa.Boolean(), nullable=False, default=False))


def downgrade() -> None:
    """Remove auto_analyze_enabled column from feeds table."""
    op.drop_column('feeds', 'auto_analyze_enabled')