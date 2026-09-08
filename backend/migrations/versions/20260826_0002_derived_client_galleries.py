"""Cria acervos privados, galerias derivadas e histórico comercial.

Revision ID: 20260826_0002
Revises: 20260825_0001
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0002"
down_revision = "20260825_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "parent_gallery",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("event_name", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_parent_gallery_event_name", "parent_gallery", ["event_name"])
    op.create_table(
        "photo_asset",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("parent_gallery_id", uuid, sa.ForeignKey("parent_gallery.id"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(512), nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_photo_asset_parent_gallery_id", "photo_asset", ["parent_gallery_id"])
    op.create_table(
        "derived_gallery",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("parent_gallery_id", uuid, sa.ForeignKey("parent_gallery.id"), nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("custom_message", sa.Text(), nullable=True),
        sa.Column("selection_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_enabled", sa.Boolean(), nullable=False),
        sa.Column("favorites_enabled", sa.Boolean(), nullable=False),
        sa.Column("comments_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_derived_gallery_parent_gallery_id", "derived_gallery", ["parent_gallery_id"])
    op.create_index("ix_derived_gallery_client_id", "derived_gallery", ["client_id"])
    op.create_table(
        "derived_gallery_photo",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id", "photo_asset_id"),
    )
    op.create_index("ix_derived_gallery_photo_derived_gallery_id", "derived_gallery_photo", ["derived_gallery_id"])
    op.create_index("ix_derived_gallery_photo_photo_asset_id", "derived_gallery_photo", ["photo_asset_id"])
    for table in ("photo_selection", "photo_favorite"):
        op.create_table(
            table,
            sa.Column("id", uuid, primary_key=True),
            sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
            sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
            sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("derived_gallery_id", "photo_asset_id", "client_id"),
        )
        op.create_index(f"ix_{table}_derived_gallery_id", table, ["derived_gallery_id"])
        op.create_index(f"ix_{table}_photo_asset_id", table, ["photo_asset_id"])
        op.create_index(f"ix_{table}_client_id", table, ["client_id"])
    op.create_table(
        "photo_comment",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_photo_comment_derived_gallery_id", "photo_comment", ["derived_gallery_id"])
    op.create_index("ix_photo_comment_photo_asset_id", "photo_comment", ["photo_asset_id"])
    op.create_index("ix_photo_comment_client_id", "photo_comment", ["client_id"])
    op.create_table(
        "sale_order",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("payment_status", sa.String(16), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("payment_status IN ('pending', 'confirmed', 'cancelled')"),
        sa.CheckConstraint("total_cents >= 0"),
    )
    op.create_index("ix_sale_order_derived_gallery_id", "sale_order", ["derived_gallery_id"])
    op.create_index("ix_sale_order_client_id", "sale_order", ["client_id"])
    op.create_index("ix_sale_order_payment_status", "sale_order", ["payment_status"])
    op.create_table(
        "sale_order_item",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("sale_order_id", uuid, sa.ForeignKey("sale_order.id"), nullable=False),
        sa.Column("photo_asset_id", uuid, sa.ForeignKey("photo_asset.id"), nullable=False),
        sa.Column("filename_snapshot", sa.String(512), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.UniqueConstraint("sale_order_id", "photo_asset_id"),
        sa.CheckConstraint("unit_price_cents >= 0"),
    )
    op.create_index("ix_sale_order_item_sale_order_id", "sale_order_item", ["sale_order_id"])
    op.create_index("ix_sale_order_item_photo_asset_id", "sale_order_item", ["photo_asset_id"])


def downgrade() -> None:
    for table in (
        "sale_order_item",
        "sale_order",
        "photo_comment",
        "photo_favorite",
        "photo_selection",
        "derived_gallery_photo",
        "derived_gallery",
        "photo_asset",
        "parent_gallery",
    ):
        op.drop_table(table)
