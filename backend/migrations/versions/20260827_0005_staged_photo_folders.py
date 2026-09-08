"""Cria pastas/lotes preparados para liberação controlada.

Revision ID: 20260827_0005
Revises: 20260826_0004
"""

import sqlalchemy as sa
from alembic import op


revision = "20260827_0005"
down_revision = "20260826_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "photo_folder",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_gallery_id", sa.Uuid(), sa.ForeignKey("parent_gallery.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="preparing"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_gallery_id", "position", name="uq_photo_folder_position"),
        sa.CheckConstraint("status IN ('preparing', 'released', 'failed')"),
    )
    op.create_index("ix_photo_folder_parent_gallery_id", "photo_folder", ["parent_gallery_id"])
    op.create_index("ix_photo_folder_status", "photo_folder", ["status"])
    with op.batch_alter_table("photo_asset") as batch_op:
        batch_op.add_column(sa.Column("folder_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_photo_asset_folder", "photo_folder", ["folder_id"], ["id"])
        batch_op.create_index("ix_photo_asset_folder_id", ["folder_id"])


def downgrade() -> None:
    with op.batch_alter_table("photo_asset") as batch_op:
        batch_op.drop_index("ix_photo_asset_folder_id")
        batch_op.drop_constraint("fk_photo_asset_folder", type_="foreignkey")
        batch_op.drop_column("folder_id")
    op.drop_index("ix_photo_folder_status", table_name="photo_folder")
    op.drop_index("ix_photo_folder_parent_gallery_id", table_name="photo_folder")
    op.drop_table("photo_folder")
