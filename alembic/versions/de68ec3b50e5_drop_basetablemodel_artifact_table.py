"""Drop basetablemodel artifact table

Revision ID: de68ec3b50e5
Revises: e796582016c8
Create Date: 2025-09-22 10:03:25.857765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de68ec3b50e5'
down_revision: Union[str, Sequence[str], None] = 'e796582016c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the basetablemodel artifact table."""
    # This table was created by SQLModel but serves no purpose
    op.execute("DROP TABLE IF EXISTS basetablemodel CASCADE")


def downgrade() -> None:
    """We don't recreate the artifact table on downgrade."""
    # It was never supposed to exist
    pass
