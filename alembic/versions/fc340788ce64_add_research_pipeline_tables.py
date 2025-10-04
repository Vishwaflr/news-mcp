"""add_research_pipeline_tables

Revision ID: fc340788ce64
Revises: d81bbc503793
Create Date: 2025-10-04 21:12:53.508729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fc340788ce64'
down_revision: Union[str, Sequence[str], None] = 'd81bbc503793'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create research_templates table
    op.create_table(
        'research_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Filter Configuration (JSONB for flexible filtering)
        sa.Column('filter_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        # LLM Prompt Configuration
        sa.Column('agent_role', sa.Text(), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('query_template', sa.Text(), nullable=True),

        # Output Definition
        sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        # Storage Configuration
        sa.Column('storage_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Metadata
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_templates_active', 'research_templates', ['active'])
    op.create_index('ix_research_templates_name', 'research_templates', ['name'])

    # Create research_runs table
    op.create_table(
        'research_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('filter_used', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('prompt_used', sa.Text(), nullable=False),

        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        # Metrics
        sa.Column('articles_count', sa.Integer(), nullable=True),
        sa.Column('queries_generated', sa.Integer(), nullable=True),
        sa.Column('queries_executed', sa.Integer(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['research_templates.id'], ondelete='SET NULL')
    )
    op.create_index('ix_research_runs_status', 'research_runs', ['status'])
    op.create_index('ix_research_runs_started_at', 'research_runs', ['started_at'])

    # Create research_queries table
    op.create_table(
        'research_queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),

        # Perplexity execution
        sa.Column('perplexity_executed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('perplexity_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('executed_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE')
    )
    op.create_index('ix_research_queries_run_id', 'research_queries', ['run_id'])
    op.create_index('ix_research_queries_executed', 'research_queries', ['perplexity_executed'])

    # Create research_results table
    op.create_table(
        'research_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.Integer(), nullable=True),

        # Result classification
        sa.Column('result_type', sa.String(50), nullable=False),

        # Structured data (based on output_schema)
        sa.Column('structured_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['query_id'], ['research_queries.id'], ondelete='SET NULL')
    )
    op.create_index('ix_research_results_run_id', 'research_results', ['run_id'])
    op.create_index('ix_research_results_type', 'research_results', ['result_type'])

    # Create research_article_links table (many-to-many)
    op.create_table(
        'research_article_links',
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('research_run_id', 'item_id'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE')
    )
    op.create_index('ix_research_article_links_item_id', 'research_article_links', ['item_id'])


def downgrade() -> None:
    op.drop_table('research_article_links')
    op.drop_table('research_results')
    op.drop_table('research_queries')
    op.drop_table('research_runs')
    op.drop_table('research_templates')
