"""add_llm_instruction_fields_to_content_templates

Revision ID: 3d13c4217df7
Revises: 3f1e428c6eee
Create Date: 2025-10-03 06:22:19.862657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d13c4217df7'
down_revision: Union[str, Sequence[str], None] = '3f1e428c6eee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LLM instruction fields to content_templates for modular extensibility."""
    # Add system_instruction for role definition and constraints
    op.add_column('content_templates',
        sa.Column('system_instruction', sa.Text(), nullable=True,
                  comment='LLM role definition and behavioral constraints (e.g., "You are a security analyst...")'))

    # Add output_format for structured output types
    op.add_column('content_templates',
        sa.Column('output_format', sa.String(50), nullable=False, server_default='markdown',
                  comment='Output format: markdown, html, json'))

    # Add output_constraints for forbidden/required elements
    op.add_column('content_templates',
        sa.Column('output_constraints', sa.dialects.postgresql.JSONB(), nullable=True,
                  comment='Constraints like {forbidden: ["code_blocks"], required: ["sources"]}'))

    # Add few_shot_examples for prompt engineering
    op.add_column('content_templates',
        sa.Column('few_shot_examples', sa.dialects.postgresql.JSONB(), nullable=True,
                  comment='Array of example outputs to guide LLM generation'))

    # Add validation_rules for post-generation checks
    op.add_column('content_templates',
        sa.Column('validation_rules', sa.dialects.postgresql.JSONB(), nullable=True,
                  comment='Validation rules like {min_word_count: 500, require_sources: true}'))

    # Add enrichment_config placeholder for future enrichment modules
    op.add_column('content_templates',
        sa.Column('enrichment_config', sa.dialects.postgresql.JSONB(), nullable=True,
                  comment='Future: enrichment modules config (cve_lookup, web_search, etc.)'))

    # Set default system_instruction for existing templates
    op.execute("""
        UPDATE content_templates
        SET system_instruction = 'You are a professional analyst creating comprehensive reports. Provide clear, factual analysis without code examples or technical commands. Focus on insights, trends, and actionable information.'
        WHERE system_instruction IS NULL
    """)


def downgrade() -> None:
    """Remove LLM instruction fields."""
    op.drop_column('content_templates', 'enrichment_config')
    op.drop_column('content_templates', 'validation_rules')
    op.drop_column('content_templates', 'few_shot_examples')
    op.drop_column('content_templates', 'output_constraints')
    op.drop_column('content_templates', 'output_format')
    op.drop_column('content_templates', 'system_instruction')
