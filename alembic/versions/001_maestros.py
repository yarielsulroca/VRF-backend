"""maestros y auth

Revision ID: 001_maestros
Revises:
Create Date: 2026-09-14
"""

from alembic import op

from vrf.adapters.outbound.postgres.models import Base

revision = "001_maestros"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
