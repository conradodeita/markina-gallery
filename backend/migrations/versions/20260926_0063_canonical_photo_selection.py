"""Permite seleção nova por galeria canônica e cliente sem derivada.

Revision ID: 20260926_0063
Revises: 20260926_0062
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_0063"
down_revision = "20260926_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("photo_selection", recreate=recreate) as batch:
        batch.add_column(sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
        batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=True)
        batch.create_foreign_key(
            "fk_photo_selection_parent_gallery", "parent_gallery", ["parent_gallery_id"], ["id"]
        )
        batch.create_check_constraint(
            "ck_photo_selection_gallery_scope",
            "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
            "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
        )
    op.create_index("ix_photo_selection_parent_gallery_id", "photo_selection", ["parent_gallery_id"])
    op.create_index(
        "uq_photo_selection_canonical", "photo_selection",
        ["parent_gallery_id", "photo_asset_id", "client_id"], unique=True,
        sqlite_where=sa.text("derived_gallery_id IS NULL"),
        postgresql_where=sa.text("derived_gallery_id IS NULL"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM photo_selection WHERE parent_gallery_id IS NOT NULL"
    )):
        raise RuntimeError("Há seleções canônicas. Preserve o schema ao reverter.")
    op.drop_index("uq_photo_selection_canonical", table_name="photo_selection")
    op.drop_index("ix_photo_selection_parent_gallery_id", table_name="photo_selection")
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("photo_selection", recreate=recreate) as batch:
        batch.drop_constraint("ck_photo_selection_gallery_scope", type_="check")
        batch.drop_constraint("fk_photo_selection_parent_gallery", type_="foreignkey")
        batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=False)
        batch.drop_column("parent_gallery_id")
