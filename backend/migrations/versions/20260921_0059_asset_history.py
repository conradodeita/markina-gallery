"""Histórico textual independente do acervo; nenhuma exclusão automática."""

import sqlalchemy as sa
from alembic import op

revision = "20260921_0059"
down_revision = "20260920_0058"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sale_order", sa.Column("assets_removed_at", sa.DateTime(timezone=True)))
    op.drop_index("uq_sale_order_editable_draft", table_name="sale_order")
    op.create_index("uq_sale_order_editable_draft", "sale_order", ["derived_gallery_id", "client_id"], unique=True,
        sqlite_where=sa.text("frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL AND assets_removed_at IS NULL"),
        postgresql_where=sa.text("frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL AND assets_removed_at IS NULL"))
    with op.batch_alter_table("payment_group") as batch:
        batch.drop_constraint("ck_payment_group_state", type_="check")
        batch.create_check_constraint("ck_payment_group_state",
            "state IN ('draft', 'reported', 'confirmed', 'refused', 'unavailable')")
    op.create_table("removed_photo_movement",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        *[sa.Column(key, sa.Uuid(), nullable=False) for key in
          ("parent_gallery_id", "derived_gallery_id", "photo_id")],
        *[sa.Column(key, sa.String(200), nullable=False) for key in
          ("parent_gallery_name", "gallery_name", "folder_name")],
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "source_id", name="uq_removed_photo_movement_source"))
    for key in ("client_id", "parent_gallery_id", "derived_gallery_id", "photo_id"):
        op.create_index(f"ix_removed_photo_movement_{key}", "removed_photo_movement", [key])
    op.create_table("asset_file_cleanup",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paths", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_asset_file_cleanup_status", "asset_file_cleanup", ["status"])


def downgrade():
    db = op.get_bind()
    if any(db.execute(sa.text(query)).scalar() for query in (
        "SELECT count(*) FROM removed_photo_movement",
        "SELECT count(*) FROM asset_file_cleanup",
        "SELECT count(*) FROM sale_order WHERE assets_removed_at IS NOT NULL",
        "SELECT count(*) FROM payment_group WHERE state = 'unavailable'",
    )):
        raise RuntimeError("Histórico de exclusão existente; use código compatível, sem apagar registros.")
    op.drop_table("asset_file_cleanup")
    op.drop_table("removed_photo_movement")
    op.drop_index("uq_sale_order_editable_draft", table_name="sale_order")
    op.create_index("uq_sale_order_editable_draft", "sale_order", ["derived_gallery_id", "client_id"], unique=True,
        sqlite_where=sa.text("frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL"),
        postgresql_where=sa.text("frozen_at IS NULL AND payment_status = 'pending' AND checkout_key IS NOT NULL"))
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_column("assets_removed_at")
    with op.batch_alter_table("payment_group") as batch:
        batch.drop_constraint("ck_payment_group_state", type_="check")
        batch.create_check_constraint("ck_payment_group_state",
            "state IN ('draft', 'reported', 'confirmed', 'refused')")
