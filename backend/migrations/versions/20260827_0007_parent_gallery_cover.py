"""Adiciona referência opcional de capa à galeria-mãe.

Revision ID: 20260827_0007
Revises: 20260827_0006
"""

import sqlalchemy as sa
from alembic import op


revision = "20260827_0007"
down_revision = "20260827_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.add_column(sa.Column("cover_photo_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_parent_gallery_cover_photo", "photo_asset", ["cover_photo_id"], ["id"]
        )
        batch_op.create_index("ix_parent_gallery_cover_photo_id", ["cover_photo_id"])


def downgrade() -> None:
    with op.batch_alter_table("parent_gallery") as batch_op:
        batch_op.drop_index("ix_parent_gallery_cover_photo_id")
        batch_op.drop_constraint("fk_parent_gallery_cover_photo", type_="foreignkey")
        batch_op.drop_column("cover_photo_id")
