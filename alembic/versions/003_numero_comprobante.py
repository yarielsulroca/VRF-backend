"""numero_comprobante texto

Revision ID: 003_numero_comprobante
Revises: 002_comprobantes
Create Date: 2026-09-18
"""

import sqlalchemy as sa
from alembic import op

revision = "003_numero_comprobante"
down_revision = "002_comprobantes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columnas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("comprobantes")}
    if "numero_comprobante" in columnas:
        return
    op.add_column(
        "comprobantes",
        sa.Column("numero_comprobante", sa.String(length=60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("comprobantes", "numero_comprobante")
