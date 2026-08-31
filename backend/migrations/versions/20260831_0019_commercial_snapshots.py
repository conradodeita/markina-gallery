"""Desacopla histórico comercial das entidades operacionais.

Revision ID: 20260831_0019
Revises: 20260831_0018
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0019"
down_revision = "20260831_0018"
branch_labels = None
depends_on = None

FK_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
}


def _replace_operational_foreign_keys(*, nullable: bool, ondelete: str | None) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "sale_order", recreate="always", naming_convention=FK_NAMING_CONVENTION
        ) as batch_op:
            batch_op.drop_constraint(
                "fk_sale_order_derived_gallery_id_derived_gallery", type_="foreignkey"
            )
            batch_op.alter_column(
                "derived_gallery_id", existing_type=sa.Uuid(), nullable=nullable
            )
            batch_op.create_foreign_key(
                "fk_sale_order_derived_gallery_id_derived_gallery",
                "derived_gallery",
                ["derived_gallery_id"],
                ["id"],
                ondelete=ondelete,
            )
        with op.batch_alter_table(
            "sale_order_item", recreate="always", naming_convention=FK_NAMING_CONVENTION
        ) as batch_op:
            batch_op.drop_constraint(
                "fk_sale_order_item_photo_asset_id_photo_asset", type_="foreignkey"
            )
            batch_op.alter_column(
                "photo_asset_id", existing_type=sa.Uuid(), nullable=nullable
            )
            batch_op.create_foreign_key(
                "fk_sale_order_item_photo_asset_id_photo_asset",
                "photo_asset",
                ["photo_asset_id"],
                ["id"],
                ondelete=ondelete,
            )
        return

    order_constraint = (
        "sale_order_derived_gallery_id_fkey"
        if nullable
        else "fk_sale_order_derived_gallery_id_derived_gallery"
    )
    item_constraint = (
        "sale_order_item_photo_asset_id_fkey"
        if nullable
        else "fk_sale_order_item_photo_asset_id_photo_asset"
    )
    op.drop_constraint(order_constraint, "sale_order", type_="foreignkey")
    op.alter_column("sale_order", "derived_gallery_id", nullable=nullable)
    op.create_foreign_key(
        (
            "fk_sale_order_derived_gallery_id_derived_gallery"
            if nullable
            else "sale_order_derived_gallery_id_fkey"
        ),
        "sale_order",
        "derived_gallery",
        ["derived_gallery_id"],
        ["id"],
        ondelete=ondelete,
    )
    op.drop_constraint(item_constraint, "sale_order_item", type_="foreignkey")
    op.alter_column("sale_order_item", "photo_asset_id", nullable=nullable)
    op.create_foreign_key(
        (
            "fk_sale_order_item_photo_asset_id_photo_asset"
            if nullable
            else "sale_order_item_photo_asset_id_fkey"
        ),
        "sale_order_item",
        "photo_asset",
        ["photo_asset_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    uuid = sa.Uuid()
    with op.batch_alter_table("sale_order") as batch_op:
        batch_op.add_column(sa.Column("derived_gallery_id_snapshot", uuid, nullable=True))
        batch_op.add_column(
            sa.Column("derived_gallery_name_snapshot", sa.String(200), nullable=True)
        )
        batch_op.add_column(sa.Column("parent_gallery_id_snapshot", uuid, nullable=True))
        batch_op.add_column(
            sa.Column("parent_gallery_name_snapshot", sa.String(200), nullable=True)
        )
    with op.batch_alter_table("sale_order_item") as batch_op:
        batch_op.add_column(sa.Column("photo_asset_id_snapshot", uuid, nullable=True))
        batch_op.add_column(
            sa.Column("checksum_sha256_snapshot", sa.String(64), nullable=True)
        )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE sale_order
            SET derived_gallery_id_snapshot = derived_gallery_id,
                derived_gallery_name_snapshot = (
                    SELECT derived_gallery.name
                    FROM derived_gallery
                    WHERE derived_gallery.id = sale_order.derived_gallery_id
                ),
                parent_gallery_id_snapshot = (
                    SELECT derived_gallery.parent_gallery_id
                    FROM derived_gallery
                    WHERE derived_gallery.id = sale_order.derived_gallery_id
                ),
                parent_gallery_name_snapshot = (
                    SELECT parent_gallery.name
                    FROM derived_gallery
                    JOIN parent_gallery
                      ON parent_gallery.id = derived_gallery.parent_gallery_id
                    WHERE derived_gallery.id = sale_order.derived_gallery_id
                )
            """
        )
    )
    bind.execute(
        sa.text(
            "UPDATE sale_order_item SET photo_asset_id_snapshot = photo_asset_id"
        )
    )
    missing_orders = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM sale_order
            WHERE derived_gallery_id_snapshot IS NULL
               OR derived_gallery_name_snapshot IS NULL
               OR parent_gallery_id_snapshot IS NULL
               OR parent_gallery_name_snapshot IS NULL
            """
        )
    ).scalar_one()
    missing_items = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM sale_order_item WHERE photo_asset_id_snapshot IS NULL"
        )
    ).scalar_one()
    if missing_orders or missing_items:
        raise RuntimeError(
            "Backfill comercial incompleto; a migration foi interrompida sem liberar exclusão."
        )

    with op.batch_alter_table("sale_order") as batch_op:
        batch_op.alter_column("derived_gallery_id_snapshot", existing_type=uuid, nullable=False)
        batch_op.alter_column(
            "derived_gallery_name_snapshot", existing_type=sa.String(200), nullable=False
        )
        batch_op.alter_column("parent_gallery_id_snapshot", existing_type=uuid, nullable=False)
        batch_op.alter_column(
            "parent_gallery_name_snapshot", existing_type=sa.String(200), nullable=False
        )
        batch_op.create_index(
            "ix_sale_order_derived_gallery_id_snapshot", ["derived_gallery_id_snapshot"]
        )
        batch_op.create_index(
            "ix_sale_order_parent_gallery_id_snapshot", ["parent_gallery_id_snapshot"]
        )
    with op.batch_alter_table("sale_order_item") as batch_op:
        batch_op.alter_column("photo_asset_id_snapshot", existing_type=uuid, nullable=False)
        batch_op.create_index(
            "ix_sale_order_item_photo_asset_id_snapshot", ["photo_asset_id_snapshot"]
        )

    _replace_operational_foreign_keys(nullable=True, ondelete="SET NULL")


def downgrade() -> None:
    bind = op.get_bind()
    null_orders = bind.execute(
        sa.text("SELECT COUNT(*) FROM sale_order WHERE derived_gallery_id IS NULL")
    ).scalar_one()
    null_items = bind.execute(
        sa.text("SELECT COUNT(*) FROM sale_order_item WHERE photo_asset_id IS NULL")
    ).scalar_one()
    if null_orders or null_items:
        raise RuntimeError(
            "Downgrade estrutural recusado: já existem referências operacionais removidas."
        )

    _replace_operational_foreign_keys(nullable=False, ondelete=None)
    with op.batch_alter_table("sale_order_item") as batch_op:
        batch_op.drop_index("ix_sale_order_item_photo_asset_id_snapshot")
        batch_op.drop_column("checksum_sha256_snapshot")
        batch_op.drop_column("photo_asset_id_snapshot")
    with op.batch_alter_table("sale_order") as batch_op:
        batch_op.drop_index("ix_sale_order_parent_gallery_id_snapshot")
        batch_op.drop_index("ix_sale_order_derived_gallery_id_snapshot")
        batch_op.drop_column("parent_gallery_name_snapshot")
        batch_op.drop_column("parent_gallery_id_snapshot")
        batch_op.drop_column("derived_gallery_name_snapshot")
        batch_op.drop_column("derived_gallery_id_snapshot")
