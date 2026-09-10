"""Adiciona mídia privada, correção financeira e reabertura de galeria.

Revision ID: 20260909_0052
Revises: 20260908_0051
"""

import sqlalchemy as sa
from alembic import op

revision = "20260909_0052"
down_revision = "20260908_0051"
branch_labels = None
depends_on = None


def _add_media_scope() -> None:
    bind = op.get_bind()
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    with op.batch_alter_table("photo_asset", recreate=recreate) as batch:
        batch.drop_constraint("fk_photo_asset_folder_gallery", type_="foreignkey")
        batch.add_column(sa.Column("derived_gallery_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_photo_asset_private_gallery",
            "derived_gallery",
            ["derived_gallery_id"],
            ["id"],
            ondelete="CASCADE",
        )
    with op.batch_alter_table("photo_folder", recreate=recreate) as batch:
        batch.drop_constraint("uq_photo_folder_position", type_="unique")
        batch.add_column(sa.Column("derived_gallery_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_photo_folder_private_gallery",
            "derived_gallery",
            ["derived_gallery_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_unique_constraint(
            "uq_photo_folder_id_parent_private",
            ["id", "parent_gallery_id", "derived_gallery_id"],
        )
        batch.create_check_constraint(
            "ck_photo_folder_private_content_only",
            "purpose != 'cover_assets' OR derived_gallery_id IS NULL",
        )
    with op.batch_alter_table("photo_asset", recreate=recreate) as batch:
        batch.create_foreign_key(
            "fk_photo_asset_folder_gallery",
            "photo_folder",
            ["folder_id", "parent_gallery_id"],
            ["id", "parent_gallery_id"],
        )
        batch.create_foreign_key(
            "fk_photo_asset_folder_scope",
            "photo_folder",
            ["folder_id", "parent_gallery_id", "derived_gallery_id"],
            ["id", "parent_gallery_id", "derived_gallery_id"],
        )
    op.create_index(
        "uq_photo_folder_public_position",
        "photo_folder",
        ["parent_gallery_id", "position"],
        unique=True,
        sqlite_where=sa.text("derived_gallery_id IS NULL"),
        postgresql_where=sa.text("derived_gallery_id IS NULL"),
    )
    op.create_index(
        "uq_photo_folder_private_position",
        "photo_folder",
        ["derived_gallery_id", "position"],
        unique=True,
        sqlite_where=sa.text("derived_gallery_id IS NOT NULL"),
        postgresql_where=sa.text("derived_gallery_id IS NOT NULL"),
    )
    op.create_index("ix_photo_folder_derived_gallery_id", "photo_folder", ["derived_gallery_id"])
    op.create_index("ix_photo_asset_derived_gallery_id", "photo_asset", ["derived_gallery_id"])
    op.create_index(
        "ix_photo_asset_private_scope", "photo_asset", ["derived_gallery_id", "created_at"]
    )

    for table_name in ("photo_face_embedding", "facial_job"):
        with op.batch_alter_table(table_name, recreate=recreate) as batch:
            batch.add_column(sa.Column("derived_gallery_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_private_gallery",
                "derived_gallery",
                ["derived_gallery_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch.create_index(f"ix_{table_name}_derived_gallery_id", ["derived_gallery_id"])
    op.create_index(
        "ix_face_embedding_private_model",
        "photo_face_embedding",
        ["derived_gallery_id", "model_version", "quality_version"],
    )


def _create_operation_tables() -> None:
    with op.batch_alter_table("sale_order") as batch:
        batch.add_column(sa.Column("payment_message_snapshot", sa.Text(), nullable=True))
    with op.batch_alter_table("payment_notification_outbox") as batch:
        batch.add_column(sa.Column("rendered_body_snapshot", sa.Text(), nullable=True))
    with op.batch_alter_table("sale_order_item") as batch:
        batch.add_column(sa.Column("folder_id_snapshot", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("folder_name_snapshot", sa.String(length=200), nullable=True))
    op.create_table(
        "payment_confirmation_correction",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "payment_communication_id",
            sa.Uuid(),
            sa.ForeignKey("payment_communication.id"),
            nullable=False,
        ),
        sa.Column("sale_order_id", sa.Uuid(), sa.ForeignKey("sale_order.id"), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("previous_communication_status", sa.String(length=20), nullable=False),
        sa.Column("previous_order_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "payment_communication_id",
            "idempotency_key",
            name="uq_payment_confirmation_correction_idempotency",
        ),
    )
    for column in ("payment_communication_id", "sale_order_id", "actor_admin_id"):
        op.create_index(
            f"ix_payment_confirmation_correction_{column}",
            "payment_confirmation_correction",
            [column],
        )
    op.create_index(
        "ix_payment_confirmation_correction_order_created",
        "payment_confirmation_correction",
        ["sale_order_id", "created_at"],
    )

    op.create_table(
        "gallery_reopening_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "derived_gallery_id",
            sa.Uuid(),
            sa.ForeignKey("derived_gallery.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_by_client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("decided_by_admin_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "derived_gallery_id",
            "idempotency_key",
            name="uq_gallery_reopening_request_idempotency",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'refused')",
            name="ck_gallery_reopening_request_status",
        ),
    )
    for column in (
        "derived_gallery_id",
        "requested_by_client_id",
        "status",
        "decided_by_admin_id",
    ):
        op.create_index(f"ix_gallery_reopening_request_{column}", "gallery_reopening_request", [column])
    op.create_index(
        "uq_gallery_reopening_request_pending",
        "gallery_reopening_request",
        ["derived_gallery_id"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_gallery_reopening_request_status_created",
        "gallery_reopening_request",
        ["status", "created_at"],
    )

    op.create_table(
        "gallery_reopening_notification_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "gallery_reopening_request_id",
            sa.Uuid(),
            sa.ForeignKey("gallery_reopening_request.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("recipient_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="skipped"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('skipped', 'queued', 'processing', 'sent', 'failed')",
            name="ck_gallery_reopening_notification_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_gallery_reopening_notification_attempts"),
    )
    op.create_index(
        "ix_reopening_notice_request",
        "gallery_reopening_notification_outbox",
        ["gallery_reopening_request_id"],
    )
    op.create_index(
        "ix_gallery_reopening_notification_outbox_status",
        "gallery_reopening_notification_outbox",
        ["status"],
    )


def upgrade() -> None:
    _add_media_scope()
    _create_operation_tables()


def downgrade() -> None:
    bind = op.get_bind()
    private_count = bind.execute(
        sa.text(
            "SELECT (SELECT count(*) FROM photo_asset WHERE derived_gallery_id IS NOT NULL) + "
            "(SELECT count(*) FROM photo_folder WHERE derived_gallery_id IS NOT NULL)"
        )
    ).scalar_one()
    operation_count = bind.execute(
        sa.text(
            "SELECT (SELECT count(*) FROM payment_confirmation_correction) + "
            "(SELECT count(*) FROM gallery_reopening_request)"
        )
    ).scalar_one()
    if private_count or operation_count:
        raise RuntimeError(
            "Downgrade recusado: mídia privada ou histórico operacional não é representável."
        )

    op.drop_table("gallery_reopening_notification_outbox")
    op.drop_table("gallery_reopening_request")
    op.drop_table("payment_confirmation_correction")
    with op.batch_alter_table("payment_notification_outbox") as batch:
        batch.drop_column("rendered_body_snapshot")
    with op.batch_alter_table("sale_order") as batch:
        batch.drop_column("payment_message_snapshot")
    with op.batch_alter_table("sale_order_item") as batch:
        batch.drop_column("folder_name_snapshot")
        batch.drop_column("folder_id_snapshot")
    op.drop_index("ix_face_embedding_private_model", table_name="photo_face_embedding")
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    for table_name in ("facial_job", "photo_face_embedding"):
        with op.batch_alter_table(table_name, recreate=recreate) as batch:
            batch.drop_index(f"ix_{table_name}_derived_gallery_id")
            batch.drop_constraint(f"fk_{table_name}_private_gallery", type_="foreignkey")
            batch.drop_column("derived_gallery_id")

    op.drop_index("ix_photo_asset_private_scope", table_name="photo_asset")
    op.drop_index("ix_photo_asset_derived_gallery_id", table_name="photo_asset")
    op.drop_index("ix_photo_folder_derived_gallery_id", table_name="photo_folder")
    op.drop_index("uq_photo_folder_private_position", table_name="photo_folder")
    op.drop_index("uq_photo_folder_public_position", table_name="photo_folder")
    with op.batch_alter_table("photo_asset", recreate=recreate) as batch:
        batch.drop_constraint("fk_photo_asset_folder_scope", type_="foreignkey")
        batch.drop_constraint("fk_photo_asset_folder_gallery", type_="foreignkey")
        batch.drop_constraint("fk_photo_asset_private_gallery", type_="foreignkey")
        batch.drop_column("derived_gallery_id")
    with op.batch_alter_table("photo_folder", recreate=recreate) as batch:
        batch.drop_constraint("ck_photo_folder_private_content_only", type_="check")
        batch.drop_constraint("uq_photo_folder_id_parent_private", type_="unique")
        batch.drop_constraint("fk_photo_folder_private_gallery", type_="foreignkey")
        batch.drop_column("derived_gallery_id")
        batch.create_unique_constraint(
            "uq_photo_folder_position", ["parent_gallery_id", "position"]
        )
    with op.batch_alter_table("photo_asset", recreate=recreate) as batch:
        batch.create_foreign_key(
            "fk_photo_asset_folder_gallery",
            "photo_folder",
            ["folder_id", "parent_gallery_id"],
            ["id", "parent_gallery_id"],
        )
