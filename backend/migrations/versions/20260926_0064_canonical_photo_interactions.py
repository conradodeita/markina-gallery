"""Permite favoritos, visualizações e comentários sem galeria derivada.

Revision ID: 20260926_0064
Revises: 20260926_0063
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_0064"
down_revision = "20260926_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    for table in ("photo_favorite", "photo_view", "photo_comment"):
        with op.batch_alter_table(table, recreate=recreate) as batch:
            batch.add_column(sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
            batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=True)
            batch.create_foreign_key(
                f"fk_{table}_parent_gallery", "parent_gallery", ["parent_gallery_id"], ["id"]
            )
            batch.create_check_constraint(
                f"ck_{table}_gallery_scope",
                "(parent_gallery_id IS NULL AND derived_gallery_id IS NOT NULL) OR "
                "(parent_gallery_id IS NOT NULL AND derived_gallery_id IS NULL)",
            )
        op.create_index(f"ix_{table}_parent_gallery_id", table, ["parent_gallery_id"])
    for table, columns in (
        ("photo_favorite", ["parent_gallery_id", "photo_asset_id", "client_id"]),
        ("photo_view", ["parent_gallery_id", "client_id", "photo_asset_id"]),
    ):
        op.create_index(
            f"uq_{table}_canonical", table, columns, unique=True,
            sqlite_where=sa.text("derived_gallery_id IS NULL"),
            postgresql_where=sa.text("derived_gallery_id IS NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("photo_favorite", "photo_view", "photo_comment"):
        if bind.scalar(sa.text(
            f"SELECT count(*) FROM {table} WHERE parent_gallery_id IS NOT NULL"
        )):
            raise RuntimeError("Há interações canônicas. Preserve o schema ao reverter.")
    for table in ("photo_favorite", "photo_view"):
        op.drop_index(f"uq_{table}_canonical", table_name=table)
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    for table in ("photo_favorite", "photo_view", "photo_comment"):
        op.drop_index(f"ix_{table}_parent_gallery_id", table_name=table)
        with op.batch_alter_table(table, recreate=recreate) as batch:
            batch.drop_constraint(f"ck_{table}_gallery_scope", type_="check")
            batch.drop_constraint(f"fk_{table}_parent_gallery", type_="foreignkey")
            batch.alter_column("derived_gallery_id", existing_type=sa.Uuid(), nullable=False)
            batch.drop_column("parent_gallery_id")
