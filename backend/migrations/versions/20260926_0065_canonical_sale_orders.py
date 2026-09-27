"""Associa pedidos novos ao par galeria canônica e cliente.

Revision ID: 20260926_0065
Revises: 20260926_0064
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_0065"
down_revision = "20260926_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("sale_order", recreate=recreate) as batch:
        batch.add_column(sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
        batch.alter_column("derived_gallery_id_snapshot", existing_type=sa.Uuid(), nullable=True)
        batch.create_foreign_key(
            "fk_sale_order_parent_gallery", "parent_gallery", ["parent_gallery_id"], ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_sale_order_canonical_state", "gallery_client_state",
            ["parent_gallery_id", "client_id"], ["parent_gallery_id", "client_id"],
        )
        batch.create_unique_constraint(
            "uq_sale_order_canonical_checkout_key",
            ["parent_gallery_id", "client_id", "checkout_key"],
        )
    op.create_index("ix_sale_order_parent_gallery_id", "sale_order", ["parent_gallery_id"])
    op.create_index(
        "uq_sale_order_canonical_editable_draft", "sale_order",
        ["parent_gallery_id", "client_id"], unique=True,
        sqlite_where=sa.text(
            "parent_gallery_id IS NOT NULL AND frozen_at IS NULL AND "
            "payment_status = 'pending' AND checkout_key IS NOT NULL "
            "AND assets_removed_at IS NULL"
        ),
        postgresql_where=sa.text(
            "parent_gallery_id IS NOT NULL AND frozen_at IS NULL AND "
            "payment_status = 'pending' AND checkout_key IS NOT NULL "
            "AND assets_removed_at IS NULL"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text(
        "SELECT count(*) FROM sale_order WHERE parent_gallery_id IS NOT NULL "
        "OR derived_gallery_id_snapshot IS NULL"
    )):
        raise RuntimeError("Há pedidos canônicos. Preserve o schema ao reverter.")
    op.drop_index("uq_sale_order_canonical_editable_draft", table_name="sale_order")
    op.drop_index("ix_sale_order_parent_gallery_id", table_name="sale_order")
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("sale_order", recreate=recreate) as batch:
        batch.drop_constraint("uq_sale_order_canonical_checkout_key", type_="unique")
        batch.drop_constraint("fk_sale_order_canonical_state", type_="foreignkey")
        batch.drop_constraint("fk_sale_order_parent_gallery", type_="foreignkey")
        batch.alter_column("derived_gallery_id_snapshot", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("parent_gallery_id")
