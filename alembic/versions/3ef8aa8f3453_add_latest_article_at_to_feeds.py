"""add_latest_article_at_to_feeds

Revision ID: 3ef8aa8f3453
Revises: 9f81604f3222
Create Date: 2025-10-04 13:38:12.370600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ef8aa8f3453'
down_revision: Union[str, Sequence[str], None] = '9f81604f3222'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add latest_article_at column to feeds table
    op.add_column('feeds', sa.Column('latest_article_at', sa.DateTime(), nullable=True))

    # Populate with existing data
    op.execute("""
        UPDATE feeds f
        SET latest_article_at = (
            SELECT COALESCE(i.published, i.created_at)
            FROM items i
            WHERE i.feed_id = f.id
            ORDER BY COALESCE(i.published, i.created_at) DESC
            LIMIT 1
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('feeds', 'latest_article_at')
