"""add geopolitical indexes

Revision ID: geopolitical_001
Revises: 5d92cbb9e6b2
Create Date: 2025-10-01

Description:
    Add indexes for geopolitical analysis queries on item_analysis table.
    These indexes improve query performance for:
    - Filtering by stability_score
    - Filtering by security_relevance
    - Filtering by escalation_potential
    - Searching affected countries/blocs (GIN index for JSONB arrays)

    Note: No schema changes needed - geopolitical data is stored in existing
    sentiment_json JSONB column, which is schema-less.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'geopolitical_001'
down_revision = '5d92cbb9e6b2'
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes for geopolitical queries"""

    # Index for stability_score queries
    # Example: WHERE (sentiment_json->'geopolitical'->>'stability_score')::float <= -0.5
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_stability
        ON item_analysis ((CAST(sentiment_json->'geopolitical'->>'stability_score' AS FLOAT)))
    """)

    # Index for security_relevance queries
    # Example: WHERE (sentiment_json->'geopolitical'->>'security_relevance')::float >= 0.7
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_security
        ON item_analysis ((CAST(sentiment_json->'geopolitical'->>'security_relevance' AS FLOAT)))
    """)

    # Index for escalation_potential queries
    # Example: WHERE (sentiment_json->'geopolitical'->>'escalation_potential')::float >= 0.6
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_escalation
        ON item_analysis ((CAST(sentiment_json->'geopolitical'->>'escalation_potential' AS FLOAT)))
    """)

    # GIN index for impact_affected array containment queries
    # Example: WHERE sentiment_json->'geopolitical'->'impact_affected' ? 'RU'
    # Example: WHERE sentiment_json->'geopolitical'->'impact_affected' ?| array['RU', 'CN']
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_affected_gin
        ON item_analysis USING GIN ((sentiment_json->'geopolitical'->'impact_affected'))
    """)

    # GIN index for impact_beneficiaries array containment queries
    # Example: WHERE sentiment_json->'geopolitical'->'impact_beneficiaries' ? 'UA'
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_beneficiaries_gin
        ON item_analysis USING GIN ((sentiment_json->'geopolitical'->'impact_beneficiaries'))
    """)

    # GIN index for regions_affected array containment queries
    # Example: WHERE sentiment_json->'geopolitical'->'regions_affected' ? 'Eastern_Europe'
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_regions_gin
        ON item_analysis USING GIN ((sentiment_json->'geopolitical'->'regions_affected'))
    """)

    # Index for conflict_type queries
    # Example: WHERE sentiment_json->'geopolitical'->>'conflict_type' = 'interstate_war'
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_conflict_type
        ON item_analysis ((sentiment_json->'geopolitical'->>'conflict_type'))
    """)

    # Index for time_horizon queries
    # Example: WHERE sentiment_json->'geopolitical'->>'time_horizon' = 'immediate'
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_geopolitical_time_horizon
        ON item_analysis ((sentiment_json->'geopolitical'->>'time_horizon'))
    """)


def downgrade():
    """Remove geopolitical indexes"""

    op.execute("DROP INDEX IF EXISTS idx_geopolitical_stability")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_security")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_escalation")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_affected_gin")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_beneficiaries_gin")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_regions_gin")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_conflict_type")
    op.execute("DROP INDEX IF EXISTS idx_geopolitical_time_horizon")
