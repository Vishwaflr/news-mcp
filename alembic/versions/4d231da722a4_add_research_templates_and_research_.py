"""Add research_templates and research_runs tables for Perplexity integration

Revision ID: 4d231da722a4
Revises: fc340788ce64
Create Date: 2025-10-05 12:36:30.680099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d231da722a4'
down_revision: Union[str, Sequence[str], None] = 'fc340788ce64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create research_templates table
    op.create_table(
        'research_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Perplexity Function Configuration
        sa.Column('perplexity_function', sa.String(100), nullable=False),
        sa.Column('function_parameters', sa.JSON(), nullable=False, server_default='{}'),

        # LLM Configuration
        sa.Column('llm_model', sa.String(50), nullable=False),
        sa.Column('llm_prompt', sa.Text(), nullable=False),
        sa.Column('llm_temperature', sa.Numeric(precision=3, scale=2), nullable=False, server_default='0.7'),
        sa.Column('system_instruction', sa.Text(), nullable=True),

        # Output Configuration
        sa.Column('output_format', sa.String(50), nullable=False, server_default='markdown'),
        sa.Column('output_schema', sa.JSON(), nullable=True),

        # Scheduling
        sa.Column('schedule_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cron_expression', sa.String(100), nullable=True),

        # Metadata
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True, server_default='[]'),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for research_templates
    op.create_index('idx_research_templates_name', 'research_templates', ['name'], unique=True)
    op.create_index('idx_research_templates_active', 'research_templates', ['is_active'])
    op.create_index('idx_research_templates_schedule', 'research_templates', ['schedule_enabled', 'cron_expression'])

    # Create research_runs table
    op.create_table(
        'research_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),

        # Execution Tracking
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=False),

        # Query and Results
        sa.Column('query_text', sa.Text(), nullable=True),
        sa.Column('result_content', sa.Text(), nullable=True),
        sa.Column('result_metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Cost Tracking
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('perplexity_cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('llm_cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),

        # Timing
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),

        # Audit
        sa.Column('triggered_by', sa.String(100), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['research_templates.id'], ondelete='SET NULL')
    )

    # Create indexes for research_runs
    op.create_index('idx_research_runs_template', 'research_runs', ['template_id'])
    op.create_index('idx_research_runs_status', 'research_runs', ['status'])
    op.create_index('idx_research_runs_created', 'research_runs', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop research_runs table and indexes
    op.drop_index('idx_research_runs_created', table_name='research_runs')
    op.drop_index('idx_research_runs_status', table_name='research_runs')
    op.drop_index('idx_research_runs_template', table_name='research_runs')
    op.drop_table('research_runs')

    # Drop research_templates table and indexes
    op.drop_index('idx_research_templates_schedule', table_name='research_templates')
    op.drop_index('idx_research_templates_active', table_name='research_templates')
    op.drop_index('idx_research_templates_name', table_name='research_templates')
    op.drop_table('research_templates')
