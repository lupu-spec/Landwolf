"""Create the current LandWolf application schema.

Revision ID: 0001_landwolf_initial
Revises:
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op

from app.db.session import Base
import app.models.entities  # noqa: F401 - registers ORM tables

revision: str = "0001_landwolf_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use the application's canonical SQLAlchemy metadata so this baseline
    # creates the exact tables/columns expected by the current codebase.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
