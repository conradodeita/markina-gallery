"""Consolida uma referência compartilhada por foto na galeria privada.

Revision ID: 20260901_0039
Revises: 20260901_0038
"""

from alembic import op
import sqlalchemy as sa

revision = "20260901_0039"
down_revision = "20260901_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM derived_gallery_photo WHERE id IN ("
            "SELECT id FROM ("
            "SELECT id, ROW_NUMBER() OVER ("
            "PARTITION BY derived_gallery_id, photo_asset_id "
            "ORDER BY created_at, id"
            ") AS duplicate_position FROM derived_gallery_photo"
            ") AS ranked WHERE duplicate_position > 1)"
        )
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("derived_gallery_photo", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_derived_gallery_photo_origin", type_="unique")
            batch_op.create_unique_constraint(
                "uq_derived_gallery_photo_asset",
                ["derived_gallery_id", "photo_asset_id"],
            )
    else:
        op.drop_constraint(
            "uq_derived_gallery_photo_origin",
            "derived_gallery_photo",
            type_="unique",
        )
        op.create_unique_constraint(
            "uq_derived_gallery_photo_asset",
            "derived_gallery_photo",
            ["derived_gallery_id", "photo_asset_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("derived_gallery_photo", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_derived_gallery_photo_asset", type_="unique")
            batch_op.create_unique_constraint(
                "uq_derived_gallery_photo_origin",
                ["derived_gallery_id", "photo_asset_id", "origin"],
            )
    else:
        op.drop_constraint(
            "uq_derived_gallery_photo_asset",
            "derived_gallery_photo",
            type_="unique",
        )
        op.create_unique_constraint(
            "uq_derived_gallery_photo_origin",
            "derived_gallery_photo",
            ["derived_gallery_id", "photo_asset_id", "origin"],
        )
