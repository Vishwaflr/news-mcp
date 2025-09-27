"""add_preview_jobs_table

Revision ID: c6186dc74ad9
Revises: e21397e52471
Create Date: 2025-09-26 07:53:38.833471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6186dc74ad9'
down_revision: Union[str, Sequence[str], None] = 'e21397e52471'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create preview_jobs table
    op.create_table(
        'preview_jobs',
        sa.Column('id', sa.String(length=50), primary_key=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='preview'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),

        # Selection configuration
        sa.Column('selection_mode', sa.String(length=50)),
        sa.Column('selection_count', sa.Integer()),
        sa.Column('selection_days', sa.Integer()),
        sa.Column('selection_hours', sa.Integer()),
        sa.Column('selection_feed_id', sa.Integer()),
        sa.Column('selection_item_ids', sa.dialects.postgresql.ARRAY(sa.Integer())),

        # Model parameters
        sa.Column('model_tag', sa.String(length=100)),
        sa.Column('model_temperature', sa.Float()),
        sa.Column('rate_per_second', sa.Float()),
        sa.Column('limit', sa.Integer()),

        # Filters
        sa.Column('unanalyzed_only', sa.Boolean(), server_default='true'),
        sa.Column('override_existing', sa.Boolean(), server_default='false'),

        # Estimates (stored as JSON)
        sa.Column('estimates', sa.dialects.postgresql.JSONB()),

        # Execution tracking
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('analysis_runs.id', ondelete='SET NULL')),
        sa.Column('triggered_by', sa.String(length=50), server_default='manual'),
        sa.Column('confirmed_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text())
    )

    # Create indexes
    op.create_index('idx_preview_jobs_status', 'preview_jobs', ['status'])
    op.create_index('idx_preview_jobs_created_at', 'preview_jobs', ['created_at'])
    op.create_index('idx_preview_jobs_run_id', 'preview_jobs', ['run_id'])

    # Add job_id column to analysis_runs table for backward reference
    op.add_column(
        'analysis_runs',
        sa.Column('job_id', sa.String(length=50), sa.ForeignKey('preview_jobs.id', ondelete='SET NULL'))
    )

    op.create_index('idx_analysis_runs_job_id', 'analysis_runs', ['job_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove job_id from analysis_runs
    op.drop_index('idx_analysis_runs_job_id', 'analysis_runs')
    op.drop_column('analysis_runs', 'job_id')

    # Drop indexes
    op.drop_index('idx_preview_jobs_run_id', 'preview_jobs')
    op.drop_index('idx_preview_jobs_created_at', 'preview_jobs')
    op.drop_index('idx_preview_jobs_status', 'preview_jobs')

    # Drop preview_jobs table
    op.drop_table('preview_jobs')
