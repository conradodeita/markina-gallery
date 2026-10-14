"""Distingue pastas de conteúdo e ativos técnicos de capa.

Revision ID: 20260831_0033
Revises: 20260831_0032
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0033"
down_revision = "20260831_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("photo_folder", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "purpose",
                    sa.String(length=24),
                    nullable=False,
                    server_default="content",
                )
            )
            batch_op.create_check_constraint(
                "ck_photo_folder_purpose",
                "purpose IN ('content', 'cover_assets')",
            )
    else:
        op.add_column(
            "photo_folder",
            sa.Column("purpose", sa.String(length=24), nullable=False, server_default="content"),
        )
        op.create_check_constraint(
            "ck_photo_folder_purpose",
            "photo_folder",
            "purpose IN ('content', 'cover_assets')",
        )
    op.create_index(
        "uq_photo_folder_cover_assets_parent",
        "photo_folder",
        ["parent_gallery_id"],
        unique=True,
        postgresql_where=sa.text("purpose = 'cover_assets'"),
        sqlite_where=sa.text("purpose = 'cover_assets'"),
    )
    op.execute(
        sa.text(
            "UPDATE parent_gallery SET cover_title_font = CASE "
            "WHEN cover_title_font IN ('sans-serif', 'DejaVuSans', 'monospace') THEN 'system-sans' "
            "WHEN cover_title_font IN ('serif', 'DejaVuSerif') THEN 'system-serif' "
            "ELSE cover_title_font END"
        )
    )


def downgrade() -> None:
    op.drop_index("uq_photo_folder_cover_assets_parent", table_name="photo_folder")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("photo_folder", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_photo_folder_purpose", type_="check")
            batch_op.drop_column("purpose")
    else:
        op.drop_constraint("ck_photo_folder_purpose", "photo_folder", type_="check")
        op.drop_column("photo_folder", "purpose")
