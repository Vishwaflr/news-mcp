"""rename_content_templates_to_special_reports

Revision ID: 9f81604f3222
Revises: 3d13c4217df7
Create Date: 2025-10-03 09:22:25.871768

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f81604f3222'
down_revision: Union[str, Sequence[str], None] = '3d13c4217df7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename content_templates table to special_reports and update related tables."""

    # 1. Rename the main table
    op.rename_table('content_templates', 'special_reports')

    # 2. Update foreign key constraints in generated_content table
    # Drop old constraint
    op.drop_constraint('generated_content_template_id_fkey', 'generated_content', type_='foreignkey')
    # Rename column for clarity
    op.alter_column('generated_content', 'template_id', new_column_name='special_report_id')
    # Add new constraint
    op.create_foreign_key(
        'generated_content_special_report_id_fkey',
        'generated_content', 'special_reports',
        ['special_report_id'], ['id'],
        ondelete='CASCADE'
    )

    # 3. Update foreign key in pending_content_generation table
    op.drop_constraint('pending_content_generation_template_id_fkey', 'pending_content_generation', type_='foreignkey')
    op.alter_column('pending_content_generation', 'template_id', new_column_name='special_report_id')
    op.create_foreign_key(
        'pending_content_generation_special_report_id_fkey',
        'pending_content_generation', 'special_reports',
        ['special_report_id'], ['id'],
        ondelete='CASCADE'
    )

    # 4. Rename index
    op.execute('ALTER INDEX IF EXISTS ix_content_templates_name RENAME TO ix_special_reports_name')


def downgrade() -> None:
    """Revert rename: special_reports back to content_templates."""

    # Reverse all changes
    op.execute('ALTER INDEX IF EXISTS ix_special_reports_name RENAME TO ix_content_templates_name')

    # pending_content_generation
    op.drop_constraint('pending_content_generation_special_report_id_fkey', 'pending_content_generation', type_='foreignkey')
    op.alter_column('pending_content_generation', 'special_report_id', new_column_name='template_id')
    op.create_foreign_key(
        'pending_content_generation_template_id_fkey',
        'pending_content_generation', 'content_templates',
        ['template_id'], ['id'],
        ondelete='CASCADE'
    )

    # generated_content
    op.drop_constraint('generated_content_special_report_id_fkey', 'generated_content', type_='foreignkey')
    op.alter_column('generated_content', 'special_report_id', new_column_name='template_id')
    op.create_foreign_key(
        'generated_content_template_id_fkey',
        'generated_content', 'content_templates',
        ['template_id'], ['id'],
        ondelete='CASCADE'
    )

    # Rename table back
    op.rename_table('special_reports', 'content_templates')
