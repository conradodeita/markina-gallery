"""Lotes auditados para exclusão explícita de mídia fria do tenant."""

import sqlalchemy as sa
from alembic import op

revision = "20261110_0122"
down_revision = "20261110_0121"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("previous_status", "next_status"):
        op.alter_column("platform_admin_event", column,
                        existing_type=sa.String(length=16), type_=sa.String(length=32))
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action",
        "platform_admin_event",
        "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
        "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
        "'tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened',"
        "'tenant.media_deletion_requested','tenant.media_deletion_retry')",
    )
    op.create_check_constraint(
        "ck_platform_admin_media_deletion_context",
        "platform_admin_event",
        "action NOT IN ('tenant.media_deletion_requested','tenant.media_deletion_retry') OR "
        "(result = 'success' AND tenant_id IS NOT NULL AND object_id IS NOT NULL "
        "AND previous_status IS NOT NULL AND next_status IS NOT NULL)",
    )
    op.drop_constraint(
        "ck_photographer_profile_fingerprint_key_version",
        "photographer_business_profile",
        type_="check",
    )
    op.alter_column(
        "photographer_business_profile",
        "cpf_fingerprint",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.alter_column(
        "photographer_business_profile",
        "cpf_fingerprint_key_version",
        existing_type=sa.String(length=40),
        existing_server_default=sa.text("'legacy-v0'"),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_photographer_profile_fingerprint_key_version",
        "photographer_business_profile",
        "(cpf_fingerprint IS NULL AND cpf_fingerprint_key_version IS NULL) OR "
        "(cpf_fingerprint IS NOT NULL AND cpf_fingerprint_key_version IS NOT NULL "
        "AND length(cpf_fingerprint_key_version) BETWEEN 1 AND 40)",
    )
    op.add_column(
        "media_archive_object",
        sa.Column("remote_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "tenant_closure_media_deletion_batch",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("closure_request_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_owner_admin_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("inventory_sha256", sa.String(length=64), nullable=False),
        sa.Column("object_count", sa.Integer(), nullable=False),
        sa.Column("verified_deleted_object_count", sa.Integer(), nullable=False),
        sa.Column("total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("last_error_code", sa.String(length=48), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_closure_media_deletion_batch_owner"),
        sa.UniqueConstraint("tenant_id", "request_id", name="uq_closure_media_deletion_batch_key"),
        sa.UniqueConstraint("closure_request_id", name="uq_closure_media_deletion_batch_closure"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["requested_by_owner_admin_id"], ["platform_owner.admin_user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["closure_request_id", "tenant_id"],
            ["tenant_closure_request.id", "tenant_closure_request.tenant_id"],
            name="fk_closure_media_deletion_batch_closure",
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'processing', 'attention_required', "
            "'reconciliation_required', 'completed')",
            name="ck_closure_media_deletion_batch_state",
        ),
        sa.CheckConstraint("object_count >= 0", name="ck_closure_media_deletion_batch_objects"),
        sa.CheckConstraint(
            "verified_deleted_object_count >= 0 "
            "AND verified_deleted_object_count <= object_count",
            name="ck_closure_media_deletion_batch_deleted_objects",
        ),
        sa.CheckConstraint("total_bytes >= 0", name="ck_closure_media_deletion_batch_bytes"),
        sa.CheckConstraint(
            "length(inventory_sha256) = 64",
            name="ck_closure_media_deletion_batch_inventory_sha256",
        ),
    )
    op.create_index(
        "ix_tenant_closure_media_deletion_batch_tenant_id",
        "tenant_closure_media_deletion_batch",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_closure_media_deletion_batch_state",
        "tenant_closure_media_deletion_batch",
        ["state"],
    )
    op.create_index(
        "ix_closure_media_deletion_batch_tenant_state",
        "tenant_closure_media_deletion_batch",
        ["tenant_id", "state", "requested_at"],
    )
    op.create_table(
        "tenant_closure_media_deletion_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "cycle_id", name="uq_closure_media_deletion_item_cycle"),
        sa.UniqueConstraint("operation_id", name="uq_closure_media_deletion_item_operation"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(
            ["batch_id", "tenant_id"],
            ["tenant_closure_media_deletion_batch.id", "tenant_closure_media_deletion_batch.tenant_id"],
            name="fk_closure_media_deletion_item_batch",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id", "cycle_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.cycle_id", "media_archive_operation.tenant_id"],
            name="fk_closure_media_deletion_item_operation",
        ),
    )
    op.create_index(
        "ix_tenant_closure_media_deletion_item_tenant_id",
        "tenant_closure_media_deletion_item",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_closure_media_deletion_item_batch_id",
        "tenant_closure_media_deletion_item",
        ["batch_id"],
    )
    op.create_index(
        "ix_closure_media_deletion_item_batch",
        "tenant_closure_media_deletion_item",
        ["tenant_id", "batch_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Exclusão auditada de mídia requer PostgreSQL.")
    connection.exec_driver_sql(
        "LOCK TABLE media_archive_object, photographer_business_profile, platform_admin_event, "
        "tenant_closure_media_deletion_batch, tenant_closure_media_deletion_item "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event "
        "WHERE action IN ('tenant.media_deletion_requested','tenant.media_deletion_retry'))"
    )):
        raise RuntimeError("Preserve auditorias de exclusão fria: rollback recusado.")
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM tenant_closure_media_deletion_batch)"
    )):
        raise RuntimeError("Preserve recibos de exclusão fria: rollback recusado.")
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM media_archive_object WHERE remote_deleted_at IS NOT NULL)"
    )):
        raise RuntimeError("Preserve checkpoints de remoção remota: rollback recusado.")
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM photographer_business_profile "
        "WHERE cpf_fingerprint IS NULL OR cpf_fingerprint_key_version IS NULL)"
    )):
        raise RuntimeError("Preserve perfis sem verificador CPF após exclusão: rollback recusado.")
    if connection.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM platform_admin_event "
        "WHERE length(previous_status) > 16 OR length(next_status) > 16)"
    )):
        raise RuntimeError("Preserve estados completos da auditoria: rollback recusado.")

    op.drop_constraint(
        "ck_platform_admin_media_deletion_context", "platform_admin_event", type_="check",
    )
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action",
        "platform_admin_event",
        "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
        "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
        "'tenant.host_activation_denied','media_archive.recovery_pricing_updated','tenant.reopened')",
    )
    op.drop_index("ix_closure_media_deletion_item_batch", table_name="tenant_closure_media_deletion_item")
    op.drop_index("ix_tenant_closure_media_deletion_item_batch_id", table_name="tenant_closure_media_deletion_item")
    op.drop_index("ix_tenant_closure_media_deletion_item_tenant_id", table_name="tenant_closure_media_deletion_item")
    op.drop_table("tenant_closure_media_deletion_item")
    op.drop_index("ix_closure_media_deletion_batch_tenant_state", table_name="tenant_closure_media_deletion_batch")
    op.drop_index("ix_tenant_closure_media_deletion_batch_state", table_name="tenant_closure_media_deletion_batch")
    op.drop_index("ix_tenant_closure_media_deletion_batch_tenant_id", table_name="tenant_closure_media_deletion_batch")
    op.drop_table("tenant_closure_media_deletion_batch")
    op.drop_column("media_archive_object", "remote_deleted_at")
    op.drop_constraint(
        "ck_photographer_profile_fingerprint_key_version",
        "photographer_business_profile",
        type_="check",
    )
    op.alter_column(
        "photographer_business_profile",
        "cpf_fingerprint",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.alter_column(
        "photographer_business_profile",
        "cpf_fingerprint_key_version",
        existing_type=sa.String(length=40),
        existing_server_default=sa.text("'legacy-v0'"),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_photographer_profile_fingerprint_key_version",
        "photographer_business_profile",
        "length(cpf_fingerprint_key_version) BETWEEN 1 AND 40",
    )
    for column in ("previous_status", "next_status"):
        op.alter_column("platform_admin_event", column,
                        existing_type=sa.String(length=32), type_=sa.String(length=16))
