"""add_triggered_by_to_analysis_runs

Revision ID: 8fdd48058112
Revises: bc273d24eeea
Create Date: 2025-09-23 07:13:51.384399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fdd48058112'
down_revision: Union[str, Sequence[str], None] = 'bc273d24eeea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add triggered_by column to analysis_runs table."""
    # Add triggered_by column with default value 'manual'
    op.add_column('analysis_runs',
                  sa.Column('triggered_by', sa.String(20), nullable=False,
                           server_default='manual'))


def downgrade() -> None:
    """Remove triggered_by column from analysis_runs table."""
    op.drop_column('analysis_runs', 'triggered_by')
