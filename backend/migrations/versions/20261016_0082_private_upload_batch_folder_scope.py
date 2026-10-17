"""Allow durable upload batches for canonical restricted folders."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0082"
down_revision = "20261014_0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_scope_private_upload_batch_asset_photo_asset_id",
        "private_upload_batch_asset", type_="unique",
    )
    with op.batch_alter_table("private_upload_batch") as batch:
        batch.alter_column(
            "derived_gallery_id", existing_type=sa.Uuid(), nullable=True
        )
        batch.add_column(sa.Column("parent_gallery_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("folder_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_private_upload_batch_parent_tenant",
            "parent_gallery", ["parent_gallery_id", "tenant_id"],
            ["id", "tenant_id"], ondelete="CASCADE",
        )
        batch.create_foreign_key(
            "fk_private_upload_batch_folder_parent_tenant",
            "photo_folder", ["folder_id", "parent_gallery_id", "tenant_id"],
            ["id", "parent_gallery_id", "tenant_id"], ondelete="CASCADE",
        )
        batch.create_index("ix_private_upload_batch_parent_gallery_id", ["parent_gallery_id"])
        batch.create_index("ix_private_upload_batch_folder_id", ["folder_id"])
        batch.create_check_constraint(
            "ck_private_upload_batch_scope",
            "(derived_gallery_id IS NOT NULL AND parent_gallery_id IS NULL AND folder_id IS NULL) OR "
            "(derived_gallery_id IS NULL AND parent_gallery_id IS NOT NULL AND folder_id IS NOT NULL)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text(
        "SELECT COUNT(*) FROM private_upload_batch WHERE folder_id IS NOT NULL"
    )):
        raise RuntimeError("Downgrade recusado: existem lotes associados a pastas canônicas.")
    if bind.scalar(sa.text("""
        SELECT COUNT(*) FROM (
            SELECT tenant_id, photo_asset_id FROM private_upload_batch_asset
            GROUP BY tenant_id, photo_asset_id HAVING COUNT(*) > 1
        ) AS duplicated_assets
    """)):
        raise RuntimeError("Downgrade recusado: uma foto pertence a mais de um lote.")
    with op.batch_alter_table("private_upload_batch") as batch:
        batch.drop_constraint("ck_private_upload_batch_scope", type_="check")
        batch.drop_index("ix_private_upload_batch_folder_id")
        batch.drop_index("ix_private_upload_batch_parent_gallery_id")
        batch.drop_constraint("fk_private_upload_batch_folder_parent_tenant", type_="foreignkey")
        batch.drop_constraint("fk_private_upload_batch_parent_tenant", type_="foreignkey")
        batch.drop_column("folder_id")
        batch.drop_column("parent_gallery_id")
        batch.alter_column(
            "derived_gallery_id", existing_type=sa.Uuid(), nullable=False
        )
    op.create_unique_constraint(
        "uq_scope_private_upload_batch_asset_photo_asset_id",
        "private_upload_batch_asset", ["tenant_id", "photo_asset_id"],
    )
