"""add pending auto analysis queue

Revision ID: 2f2749931b3d
Revises: c6186dc74ad9
Create Date: 2025-09-27 15:56:55.516309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f2749931b3d'
down_revision: Union[str, Sequence[str], None] = 'c6186dc74ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pending_auto_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), nullable=False),
        sa.Column('item_ids', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('analysis_run_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['feed_id'], ['feeds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_run_id'], ['analysis_runs.id'], ondelete='SET NULL')
    )
    op.create_index('ix_pending_auto_analysis_feed_id', 'pending_auto_analysis', ['feed_id'])
    op.create_index('ix_pending_auto_analysis_status', 'pending_auto_analysis', ['status'])
    op.create_index('ix_pending_auto_analysis_created_at', 'pending_auto_analysis', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_pending_auto_analysis_created_at', 'pending_auto_analysis')
    op.drop_index('ix_pending_auto_analysis_status', 'pending_auto_analysis')
    op.drop_index('ix_pending_auto_analysis_feed_id', 'pending_auto_analysis')
    op.drop_table('pending_auto_analysis')
