"""add_category_and_semantic_tags_to_sentiment

Revision ID: d81bbc503793
Revises: 3ef8aa8f3453
Create Date: 2025-10-04 20:02:25.357038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd81bbc503793'
down_revision: Union[str, Sequence[str], None] = '3ef8aa8f3453'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category and semantic_tags to existing sentiment_json.

    sentiment_json is JSON type - we convert to jsonb, update, convert back.
    """
    # Add category and semantic_tags to existing records
    op.execute("""
        UPDATE item_analysis
        SET sentiment_json = (
            jsonb_set(
                jsonb_set(
                    COALESCE(sentiment_json::jsonb, '{}'::jsonb),
                    '{category}',
                    '"panorama"'::jsonb,
                    true
                ),
                '{semantic_tags}',
                '{"actor": "Unknown", "theme": "General", "region": "Global"}'::jsonb,
                true
            )
        )::json
        WHERE sentiment_json IS NOT NULL
        AND (sentiment_json::jsonb)->>'category' IS NULL
    """)


def downgrade() -> None:
    """Remove category and semantic_tags from sentiment_json."""
    op.execute("""
        UPDATE item_analysis
        SET sentiment_json = sentiment_json - 'category' - 'semantic_tags'
        WHERE sentiment_json IS NOT NULL
    """)
