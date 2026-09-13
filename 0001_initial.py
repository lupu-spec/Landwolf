"""Initial LandWolf schema baseline.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline placeholder.
    # Add/create the LandWolf production tables here once the canonical
    # SQLAlchemy metadata or verified SQL migration set is available.
    pass


def downgrade() -> None:
    pass
