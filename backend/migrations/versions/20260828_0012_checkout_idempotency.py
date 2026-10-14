"""Preserva instruções PIX e chave idempotente no pedido.

Revision ID: 20260828_0012
Revises: 20260828_0011
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op


revision = "20260828_0012"
down_revision = "20260828_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ``batch_alter_table`` mantém o DDL direto no PostgreSQL e permite a
    # cópia segura de tabela no SQLite usado pela verificação sintética.
    with op.batch_alter_table("sale_order") as batch_op:
        batch_op.add_column(sa.Column("pix_instructions_snapshot", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("checkout_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uq_sale_order_gallery_client_checkout_key",
            ["derived_gallery_id", "client_id", "checkout_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sale_order") as batch_op:
        batch_op.drop_constraint("uq_sale_order_gallery_client_checkout_key", type_="unique")
        batch_op.drop_column("checkout_key")
        batch_op.drop_column("pix_instructions_snapshot")
