"""add_updated_at_to_categories

Revision ID: bc273d24eeea
Revises: 6bc647f8b1f0
Create Date: 2025-09-23 05:58:54.577647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc273d24eeea'
down_revision: Union[str, Sequence[str], None] = '6bc647f8b1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at column to categories table."""
    # Add updated_at column with default value set to current timestamp
    op.add_column('categories',
                  sa.Column('updated_at', sa.TIMESTAMP(), nullable=False,
                           server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    """Remove updated_at column from categories table."""
    op.drop_column('categories', 'updated_at')
