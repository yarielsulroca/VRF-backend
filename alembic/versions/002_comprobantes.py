"""comprobantes y archivos

Revision ID: 002_comprobantes
Revises: 001_maestros
Create Date: 2026-09-14
"""

from alembic import op

from vrf.adapters.outbound.postgres.models import Base

revision = "002_comprobantes"
down_revision = "001_maestros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    op.drop_table("archivos")
    op.drop_table("comprobantes")
