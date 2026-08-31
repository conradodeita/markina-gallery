"""Adiciona operações duráveis e manifesto mínimo de mídia histórica.

Revision ID: 20260831_0018
Revises: 20260830_0017
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0018"
down_revision = "20260830_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "gallery_lifecycle_operation",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.Column("target_parent_gallery_id", uuid, nullable=False),
        sa.Column("target_client_id", uuid, nullable=True),
        sa.Column("actor_admin_id", uuid, nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("destructive_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_gallery_lifecycle_operation_idempotency"
        ),
        sa.CheckConstraint(
            "operation_type IN ('delete_parent_gallery', 'unlink_client')",
            name="ck_gallery_lifecycle_operation_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'preparing_history', 'removing_storage', "
            "'removing_records', 'completed', 'failed')",
            name="ck_gallery_lifecycle_operation_status",
        ),
        sa.CheckConstraint(
            "(operation_type = 'delete_parent_gallery' AND target_client_id IS NULL) OR "
            "(operation_type = 'unlink_client' AND target_client_id IS NOT NULL)",
            name="ck_gallery_lifecycle_operation_target",
        ),
    )
    for column in (
        "operation_type",
        "target_parent_gallery_id",
        "target_client_id",
        "actor_admin_id",
        "status",
    ):
        op.create_index(
            f"ix_gallery_lifecycle_operation_{column}",
            "gallery_lifecycle_operation",
            [column],
        )

    op.create_table(
        "commercial_history_media",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "sale_order_item_id",
            uuid,
            sa.ForeignKey("sale_order_item.id"),
            nullable=False,
        ),
        sa.Column("preview_storage_key", sa.String(1024), nullable=True),
        sa.Column("delivery_storage_key", sa.String(1024), nullable=True),
        sa.Column("delivery_reference", sa.String(2048), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("media_type", sa.String(120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "sale_order_item_id", name="uq_commercial_history_media_item"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'preparing', 'ready', 'failed')",
            name="ck_commercial_history_media_status",
        ),
        sa.CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="ck_commercial_history_media_size",
        ),
    )
    op.create_index(
        "ix_commercial_history_media_sale_order_item_id",
        "commercial_history_media",
        ["sale_order_item_id"],
    )
    op.create_index(
        "ix_commercial_history_media_status", "commercial_history_media", ["status"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_history_media_status", table_name="commercial_history_media"
    )
    op.drop_index(
        "ix_commercial_history_media_sale_order_item_id",
        table_name="commercial_history_media",
    )
    op.drop_table("commercial_history_media")
    for column in reversed(
        (
            "operation_type",
            "target_parent_gallery_id",
            "target_client_id",
            "actor_admin_id",
            "status",
        )
    ):
        op.drop_index(
            f"ix_gallery_lifecycle_operation_{column}",
            table_name="gallery_lifecycle_operation",
        )
    op.drop_table("gallery_lifecycle_operation")
