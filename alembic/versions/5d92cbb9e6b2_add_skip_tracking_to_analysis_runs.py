"""add_skip_tracking_to_analysis_runs

Revision ID: 5d92cbb9e6b2
Revises: 2f2749931b3d
Create Date: 2025-09-29 17:03:36.753242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d92cbb9e6b2'
down_revision: Union[str, Sequence[str], None] = '2f2749931b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add skip tracking fields to analysis_runs and analysis_items tables."""

    # Add columns to analysis_runs table
    op.add_column('analysis_runs',
        sa.Column('planned_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('analysis_runs',
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('analysis_runs',
        sa.Column('skipped_items', sa.JSON(), nullable=False, server_default='[]')
    )

    # Add columns to analysis_run_items table (FIXED: correct table name!)
    op.add_column('analysis_run_items',
        sa.Column('skip_reason', sa.String(length=50), nullable=True)
    )
    op.add_column('analysis_run_items',
        sa.Column('skipped_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Create index for performance: quickly find recently analyzed items
    op.create_index(
        'idx_analysis_run_items_item_completed',
        'analysis_run_items',
        ['item_id', 'completed_at'],
        postgresql_where=sa.text("state = 'completed'")
    )

    # Update existing runs to set planned_count = queued_count (for backwards compatibility)
    op.execute("UPDATE analysis_runs SET planned_count = queued_count WHERE planned_count = 0")


def downgrade() -> None:
    """Remove skip tracking fields."""

    # Drop the index first
    op.drop_index('idx_analysis_run_items_item_completed', 'analysis_run_items')

    # Remove columns from analysis_run_items
    op.drop_column('analysis_run_items', 'skipped_at')
    op.drop_column('analysis_run_items', 'skip_reason')

    # Remove columns from analysis_runs
    op.drop_column('analysis_runs', 'skipped_items')
    op.drop_column('analysis_runs', 'skipped_count')
    op.drop_column('analysis_runs', 'planned_count')
