"""Mantém o carrinho editável até a comunicação do pagamento.

Revision ID: 20260910_0053
Revises: 20260909_0052
"""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0053"
down_revision = "20260909_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sale_order") as batch:
        batch.add_column(sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True))

    # Todo pedido anterior já teve a seleção consumida pelo checkout antigo e
    # precisa continuar sendo um snapshot imutável, inclusive quando pendente.
    op.execute(sa.text("UPDATE sale_order SET frozen_at = created_at"))
    op.create_index("ix_sale_order_frozen_at", "sale_order", ["frozen_at"])
    op.create_index(
        "uq_sale_order_editable_draft",
        "sale_order",
        ["derived_gallery_id", "client_id"],
        unique=True,
        sqlite_where=sa.text(
            "frozen_at IS NULL AND payment_status = 'pending' "
            "AND checkout_key IS NOT NULL"
        ),
        postgresql_where=sa.text(
            "frozen_at IS NULL AND payment_status = 'pending' "
            "AND checkout_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_sale_order_editable_draft", table_name="sale_order")
    op.drop_index("ix_sale_order_frozen_at", table_name="sale_order")
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_column("frozen_at")
