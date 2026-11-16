"""Catálogo e leases para o arquivo frio de mídia."""

import sqlalchemy as sa
from alembic import op

revision = "20261108_0112"
down_revision = "20261108_0111"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Catálogo de arquivo frio requer PostgreSQL.")

    op.create_table(
        "media_archive_cycle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("parent_gallery_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("state", sa.String(32), server_default="local", nullable=False),
        sa.Column("manifest_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("manifest", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=True),
        sa.Column("object_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "state IN ('local', 'archiving', 'archived', 'restoring', 'reconciliation_required', 'deleting', 'deleted')",
            name="ck_media_archive_cycle_state",
        ),
        sa.CheckConstraint("cycle_number >= 1", name="ck_media_archive_cycle_number"),
        sa.CheckConstraint("manifest_version >= 1", name="ck_media_archive_cycle_manifest_version"),
        sa.CheckConstraint("object_count >= 0", name="ck_media_archive_cycle_object_count"),
        sa.CheckConstraint("total_bytes >= 0", name="ck_media_archive_cycle_total_bytes"),
        sa.CheckConstraint(
            "manifest_sha256 IS NULL OR length(manifest_sha256) = 64",
            name="ck_media_archive_cycle_manifest_sha256",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["folder_id", "parent_gallery_id", "tenant_id"],
            ["photo_folder.id", "photo_folder.parent_gallery_id", "photo_folder.tenant_id"],
            name="fk_media_archive_cycle_folder_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["parent_gallery_id", "tenant_id"], ["parent_gallery.id", "parent_gallery.tenant_id"],
            name="fk_media_archive_cycle_parent_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_media_archive_cycle_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "folder_id", "cycle_number",
            name="uq_media_archive_cycle_folder_number",
        ),
    )
    op.create_index("ix_media_archive_cycle_tenant_id", "media_archive_cycle", ["tenant_id"])
    op.create_index("ix_media_archive_cycle_parent_gallery_id", "media_archive_cycle", ["parent_gallery_id"])
    op.create_index("ix_media_archive_cycle_folder_id", "media_archive_cycle", ["folder_id"])
    op.create_index("ix_media_archive_cycle_state", "media_archive_cycle", ["state"])
    op.create_index(
        "ix_media_archive_cycle_tenant_folder_state", "media_archive_cycle",
        ["tenant_id", "folder_id", "state"],
    )

    op.create_table(
        "media_archive_operation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("stage", sa.String(48), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("actor_type", sa.String(16), server_default="system", nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("last_error_code", sa.String(32), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token", sa.String(64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "operation_type IN ('archive', 'restore', 'delete_remote')",
            name="ck_media_archive_operation_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'failed', 'reconciliation_required', 'completed', 'cancelled')",
            name="ck_media_archive_operation_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_media_archive_operation_attempts"),
        sa.CheckConstraint("actor_type IN ('tenant', 'owner', 'system')", name="ck_media_archive_operation_actor"),
        sa.CheckConstraint(
            "length(idempotency_key) BETWEEN 1 AND 200",
            name="ck_media_archive_operation_idempotency_key",
        ),
        sa.CheckConstraint(
            "status != 'processing' OR (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_media_archive_operation_processing_lease",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_operation_cycle_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_media_archive_operation_id_tenant"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_media_archive_operation_idempotency"),
    )
    op.create_index("ix_media_archive_operation_tenant_id", "media_archive_operation", ["tenant_id"])
    op.create_index("ix_media_archive_operation_cycle_id", "media_archive_operation", ["cycle_id"])
    op.create_index("ix_media_archive_operation_operation_type", "media_archive_operation", ["operation_type"])
    op.create_index("ix_media_archive_operation_status", "media_archive_operation", ["status"])
    op.create_index("ix_media_archive_operation_lease_expires_at", "media_archive_operation", ["lease_expires_at"])
    op.create_index(
        "ix_media_archive_operation_queue", "media_archive_operation",
        ["status", "operation_type", "created_at"],
    )
    op.create_index(
        "uq_media_archive_operation_active_cycle", "media_archive_operation",
        ["tenant_id", "cycle_id"], unique=True,
        postgresql_where=sa.text("status IN ('queued', 'processing', 'reconciliation_required')"),
    )

    op.create_table(
        "media_archive_object",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("remote_object_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "object_type IN ('source', 'derivative', 'commercial_media', 'cover_asset', 'cover_thumbnail', 'manifest')",
            name="ck_media_archive_object_type",
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_media_archive_object_size"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_media_archive_object_sha256"),
        sa.CheckConstraint("length(source_ref) BETWEEN 1 AND 255", name="ck_media_archive_object_source_ref"),
        sa.CheckConstraint("length(mime_type) BETWEEN 1 AND 127", name="ck_media_archive_object_mime_type"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_object_cycle_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_media_archive_object_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "cycle_id", "source_ref",
            name="uq_media_archive_object_cycle_source",
        ),
    )
    op.create_index("ix_media_archive_object_tenant_id", "media_archive_object", ["tenant_id"])
    op.create_index("ix_media_archive_object_cycle_id", "media_archive_object", ["cycle_id"])
    op.create_index("ix_media_archive_object_cycle", "media_archive_object", ["tenant_id", "cycle_id"])

    op.create_table(
        "media_archive_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("cycle_state_before", sa.String(32), nullable=True),
        sa.Column("cycle_state_after", sa.String(32), nullable=True),
        sa.Column("operation_status_before", sa.String(32), nullable=True),
        sa.Column("operation_status_after", sa.String(32), nullable=True),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("actor_type IN ('tenant', 'owner', 'system')", name="ck_media_archive_event_actor"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_event_cycle_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"], ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_event_operation_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_archive_event_tenant_id", "media_archive_event", ["tenant_id"])
    op.create_index("ix_media_archive_event_cycle_id", "media_archive_event", ["cycle_id"])
    op.create_index("ix_media_archive_event_operation_id", "media_archive_event", ["operation_id"])
    op.create_index(
        "ix_media_archive_event_tenant_created", "media_archive_event", ["tenant_id", "created_at"],
    )

    op.create_table(
        "media_archive_coordinator",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_operation_id", sa.Uuid(), nullable=True),
        sa.Column("lease_token", sa.String(64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_media_archive_coordinator_singleton"),
        sa.CheckConstraint(
            "(active_operation_id IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL) OR "
            "(active_operation_id IS NOT NULL AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_media_archive_coordinator_lease_shape",
        ),
        sa.ForeignKeyConstraint(
            ["active_operation_id"], ["media_archive_operation.id"],
            name="fk_media_archive_coordinator_operation",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(sa.text(
        "INSERT INTO media_archive_coordinator (id, updated_at) VALUES (1, now())"
    ))

    op.create_table(
        "media_archive_space_reservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("volume_key", sa.String(64), nullable=False),
        sa.Column("reserved_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("reserved_bytes >= 0", name="ck_media_archive_space_reservation_bytes"),
        sa.CheckConstraint("status IN ('active', 'released')", name="ck_media_archive_space_reservation_status"),
        sa.CheckConstraint("length(volume_key) = 64", name="ck_media_archive_space_reservation_volume_key"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"], ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_space_reservation_operation_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "operation_id", "volume_key", name="uq_media_archive_space_reservation",
        ),
    )
    op.create_index("ix_media_archive_space_reservation_tenant_id", "media_archive_space_reservation", ["tenant_id"])
    op.create_index("ix_media_archive_space_reservation_operation_id", "media_archive_space_reservation", ["operation_id"])
    op.create_index("ix_media_archive_space_reservation_status", "media_archive_space_reservation", ["status"])
    op.create_index(
        "ix_media_archive_space_reservation_volume_status",
        "media_archive_space_reservation", ["volume_key", "status"],
    )

    op.execute(sa.text("""
        CREATE FUNCTION reject_media_archive_event_change() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'media archive events are append-only'; END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_event_immutable BEFORE UPDATE OR DELETE ON media_archive_event
        FOR EACH ROW EXECUTE FUNCTION reject_media_archive_event_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_event_no_truncate BEFORE TRUNCATE ON media_archive_event
        FOR EACH STATEMENT EXECUTE FUNCTION reject_media_archive_event_change()
    """))


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Catálogo de arquivo frio requer PostgreSQL.")
    bind = op.get_bind()
    bind.exec_driver_sql(
        "LOCK TABLE media_archive_coordinator, media_archive_cycle, media_archive_event, "
        "media_archive_object, media_archive_operation, media_archive_space_reservation "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    for table in (
        "media_archive_event", "media_archive_object", "media_archive_operation",
        "media_archive_cycle", "media_archive_space_reservation",
    ):
        if bind.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table} LIMIT 1)")):
            raise RuntimeError("Preserve o catálogo de arquivo frio: rollback recusado com dados.")
    op.execute(sa.text("DROP TRIGGER media_archive_event_immutable ON media_archive_event"))
    op.execute(sa.text("DROP TRIGGER media_archive_event_no_truncate ON media_archive_event"))
    op.execute(sa.text("DROP FUNCTION reject_media_archive_event_change()"))
    op.drop_table("media_archive_space_reservation")
    op.drop_table("media_archive_coordinator")
    op.drop_index("ix_media_archive_event_tenant_created", table_name="media_archive_event")
    op.drop_index("ix_media_archive_event_operation_id", table_name="media_archive_event")
    op.drop_index("ix_media_archive_event_cycle_id", table_name="media_archive_event")
    op.drop_index("ix_media_archive_event_tenant_id", table_name="media_archive_event")
    op.drop_table("media_archive_event")
    op.drop_index("ix_media_archive_object_cycle", table_name="media_archive_object")
    op.drop_index("ix_media_archive_object_cycle_id", table_name="media_archive_object")
    op.drop_index("ix_media_archive_object_tenant_id", table_name="media_archive_object")
    op.drop_table("media_archive_object")
    op.drop_index("uq_media_archive_operation_active_cycle", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_queue", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_lease_expires_at", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_status", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_operation_type", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_cycle_id", table_name="media_archive_operation")
    op.drop_index("ix_media_archive_operation_tenant_id", table_name="media_archive_operation")
    op.drop_table("media_archive_operation")
    op.drop_index("ix_media_archive_cycle_tenant_folder_state", table_name="media_archive_cycle")
    op.drop_index("ix_media_archive_cycle_state", table_name="media_archive_cycle")
    op.drop_index("ix_media_archive_cycle_folder_id", table_name="media_archive_cycle")
    op.drop_index("ix_media_archive_cycle_parent_gallery_id", table_name="media_archive_cycle")
    op.drop_index("ix_media_archive_cycle_tenant_id", table_name="media_archive_cycle")
    op.drop_table("media_archive_cycle")
