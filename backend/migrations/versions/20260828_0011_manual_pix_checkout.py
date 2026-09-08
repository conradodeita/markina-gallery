"""Adiciona regras comerciais e snapshots para checkout PIX manual.

Revision ID: 20260828_0011
Revises: 20260828_0010
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op


revision = "20260828_0011"
down_revision = "20260828_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "price_rule",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False),
        sa.Column("maximum_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id", "minimum_quantity"),
        sa.CheckConstraint("minimum_quantity >= 1"),
        sa.CheckConstraint("maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity"),
        sa.CheckConstraint("unit_price_cents >= 0"),
    )
    op.create_index("ix_price_rule_derived_gallery_id", "price_rule", ["derived_gallery_id"])
    op.create_table(
        "pix_checkout_settings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("derived_gallery_id", uuid, sa.ForeignKey("derived_gallery.id"), nullable=False),
        sa.Column("copy_paste", sa.Text(), nullable=True),
        sa.Column("qr_code_payload", sa.Text(), nullable=True),
        sa.Column("instructions", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("derived_gallery_id"),
    )
    op.add_column("sale_order", sa.Column("price_rule_snapshot", sa.JSON(), nullable=True))
    op.add_column("sale_order", sa.Column("sales_message_snapshot", sa.Text(), nullable=True))
    op.add_column("sale_order", sa.Column("pix_copy_paste_snapshot", sa.Text(), nullable=True))
    op.add_column("sale_order", sa.Column("pix_qr_code_snapshot", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sale_order", "pix_qr_code_snapshot")
    op.drop_column("sale_order", "pix_copy_paste_snapshot")
    op.drop_column("sale_order", "sales_message_snapshot")
    op.drop_column("sale_order", "price_rule_snapshot")
    op.drop_table("pix_checkout_settings")
    op.drop_table("price_rule")
