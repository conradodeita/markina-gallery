"""Adicionar preço, reserva e ledger da recuperação de arquivo frio."""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0114"
down_revision = "20261109_0113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Cobrança de recuperação de arquivo frio requer PostgreSQL.")

    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action", "platform_admin_event",
        "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
        "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
        "'tenant.host_activation_denied','media_archive.recovery_pricing_updated')",
    )

    op.create_unique_constraint(
        "uq_media_archive_operation_id_cycle_tenant",
        "media_archive_operation",
        ["id", "cycle_id", "tenant_id"],
    )

    op.create_table(
        "media_archive_recovery_pricing",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recovery_fee_credits", sa.Integer(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_media_archive_recovery_pricing_singleton"),
        sa.CheckConstraint(
            "recovery_fee_credits IS NULL OR recovery_fee_credits > 0",
            name="ck_media_archive_recovery_fee_positive",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_media_archive_recovery_pricing_updated_by_owner",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_archive_recovery_pricing"),
    )
    op.execute(sa.text(
        "INSERT INTO media_archive_recovery_pricing "
        "(id, recovery_fee_credits, updated_by_admin_id, updated_at) VALUES (1, NULL, NULL, now())"
    ))

    op.create_table(
        "media_archive_recovery_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("requester_type", sa.String(16), server_default="tenant", nullable=False),
        sa.Column("requested_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_tenant_admin_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by_owner_admin_id", sa.Uuid(), nullable=True),
        sa.Column("retry_of_operation_id", sa.Uuid(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("fee_credits_snapshot", sa.Integer(), nullable=True),
        sa.Column("owner_exempt", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("duration_days IN (7, 14, 30)", name="ck_media_archive_recovery_duration"),
        sa.CheckConstraint(
            "fee_credits_snapshot IS NULL OR fee_credits_snapshot > 0",
            name="ck_media_archive_recovery_fee_snapshot",
        ),
        sa.CheckConstraint(
            "(owner_exempt AND fee_credits_snapshot IS NULL) OR "
            "(NOT owner_exempt AND fee_credits_snapshot IS NOT NULL)",
            name="ck_media_archive_recovery_fee_shape",
        ),
        sa.CheckConstraint(
            "(requester_type = 'tenant' AND requested_by_tenant_admin_id = requested_by_admin_id "
            "AND requested_by_owner_admin_id IS NULL AND retry_of_operation_id IS NULL) OR "
            "(requester_type = 'owner' AND requested_by_tenant_admin_id IS NULL "
            "AND requested_by_owner_admin_id = requested_by_admin_id AND retry_of_operation_id IS NOT NULL)",
            name="ck_media_archive_recovery_request_actor_shape",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_media_archive_recovery_request_tenant"),
        sa.ForeignKeyConstraint(
            ["operation_id", "cycle_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.cycle_id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_recovery_request_operation_scope",
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id", "tenant_id"], ["media_archive_cycle.id", "media_archive_cycle.tenant_id"],
            name="fk_media_archive_recovery_request_cycle_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "requested_by_tenant_admin_id"], ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_media_archive_recovery_request_actor_membership",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_owner_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_media_archive_recovery_request_actor_owner",
        ),
        sa.ForeignKeyConstraint(
            ["retry_of_operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_recovery_request_retry_operation_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_archive_recovery_request"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_media_archive_recovery_request_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "operation_id", name="uq_media_archive_recovery_request_operation",
        ),
    )
    op.create_index(
        "ix_media_archive_recovery_request_tenant_id", "media_archive_recovery_request", ["tenant_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_request_operation_id", "media_archive_recovery_request", ["operation_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_request_cycle_id", "media_archive_recovery_request", ["cycle_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_request_tenant_created",
        "media_archive_recovery_request", ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_media_archive_recovery_request_cycle",
        "media_archive_recovery_request", ["tenant_id", "cycle_id", "created_at"],
    )

    op.create_table(
        "media_archive_recovery_credit_reservation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("reserved_credits", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), server_default="reserved", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("reserved_credits >= 0", name="ck_media_archive_recovery_reserved_credits"),
        sa.CheckConstraint(
            "status IN ('reserved', 'reconciliation_required', 'consumed', 'released', 'exempt')",
            name="ck_media_archive_recovery_reservation_status",
        ),
        sa.CheckConstraint(
            "(status = 'exempt' AND reserved_credits = 0) OR "
            "(status <> 'exempt' AND reserved_credits > 0)",
            name="ck_media_archive_recovery_reservation_amount",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_media_archive_recovery_reservation_tenant"),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_recovery_credit_reservation_operation_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_archive_recovery_credit_reservation"),
        sa.UniqueConstraint(
            "id", "tenant_id", name="uq_media_archive_recovery_credit_reservation_id_tenant",
        ),
        sa.UniqueConstraint(
            "tenant_id", "operation_id", name="uq_media_archive_recovery_credit_reservation_operation",
        ),
    )
    op.create_index(
        "ix_media_archive_recovery_credit_reservation_tenant_id",
        "media_archive_recovery_credit_reservation", ["tenant_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_credit_reservation_operation_id",
        "media_archive_recovery_credit_reservation", ["operation_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_credit_reservation_status",
        "media_archive_recovery_credit_reservation", ["status"],
    )
    op.create_index(
        "ix_media_archive_recovery_credit_pending",
        "media_archive_recovery_credit_reservation", ["tenant_id", "status"],
    )

    op.add_column(
        "photographer_credit_entry", sa.Column("archive_operation_id", sa.Uuid(), nullable=True),
    )
    op.drop_constraint("ck_credit_entry_type", "photographer_credit_entry", type_="check")
    op.drop_constraint("ck_credit_entry_delta", "photographer_credit_entry", type_="check")
    op.create_check_constraint(
        "ck_credit_entry_type", "photographer_credit_entry",
        "entry_type IN ('owner_grant', 'grant_revocation', 'purchase', "
        "'upload_consumption', 'archive_recovery', 'purchase_reversal', 'correction')",
    )
    op.create_check_constraint(
        "ck_credit_entry_delta", "photographer_credit_entry",
        "(entry_type IN ('owner_grant', 'purchase') AND delta > 0) OR "
        "(entry_type IN ('grant_revocation', 'upload_consumption', 'archive_recovery', 'purchase_reversal') AND delta < 0) OR "
        "(entry_type = 'correction' AND delta <> 0)",
    )
    op.create_check_constraint(
        "ck_credit_entry_archive_operation", "photographer_credit_entry",
        "(entry_type = 'archive_recovery' AND archive_operation_id IS NOT NULL "
        "AND operation_id IS NULL AND delta < 0) OR "
        "(entry_type <> 'archive_recovery' AND archive_operation_id IS NULL)",
    )
    op.create_foreign_key(
        "fk_credit_entry_archive_operation_tenant",
        "photographer_credit_entry", "media_archive_operation",
        ["archive_operation_id", "tenant_id"], ["id", "tenant_id"],
    )
    op.create_index(
        "uq_credit_entry_archive_operation_consumption",
        "photographer_credit_entry", ["tenant_id", "archive_operation_id"],
        unique=True,
        postgresql_where=sa.text(
            "entry_type = 'archive_recovery' AND archive_operation_id IS NOT NULL"
        ),
    )

    op.create_table(
        "media_archive_recovery_credit_allocation_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("source_entry_id", sa.Uuid(), nullable=False),
        sa.Column("credit_entry_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('reserved', 'consumed', 'released')",
            name="ck_media_archive_credit_allocation_event_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_media_archive_credit_allocation_quantity"),
        sa.CheckConstraint(
            "(event_type IN ('reserved', 'released') AND credit_entry_id IS NULL) OR "
            "(event_type = 'consumed' AND credit_entry_id IS NOT NULL)",
            name="ck_media_archive_credit_allocation_event_context",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_media_archive_credit_allocation_tenant"),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["media_archive_operation.id", "media_archive_operation.tenant_id"],
            name="fk_media_archive_credit_allocation_operation_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_media_archive_credit_allocation_source_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["credit_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_media_archive_credit_allocation_entry_tenant",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_archive_recovery_credit_allocation_event"),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_media_archive_credit_allocation_idempotency",
        ),
        sa.UniqueConstraint(
            "id", "tenant_id",
            name="uq_archive_recovery_alloc_event_tenant",
        ),
    )
    op.create_index(
        "ix_media_archive_recovery_credit_allocation_event_tenant_id",
        "media_archive_recovery_credit_allocation_event", ["tenant_id"],
    )
    op.create_index(
        "ix_media_archive_recovery_credit_allocation_event_operation_id",
        "media_archive_recovery_credit_allocation_event", ["operation_id"],
    )
    op.create_index(
        "ix_media_archive_credit_allocation_source_history",
        "media_archive_recovery_credit_allocation_event", ["tenant_id", "source_entry_id", "occurred_at"],
    )
    op.create_index(
        "ix_media_archive_credit_allocation_operation_history",
        "media_archive_recovery_credit_allocation_event", ["tenant_id", "operation_id", "occurred_at"],
    )

    op.execute(sa.text("""
        CREATE FUNCTION reject_media_archive_recovery_credit_allocation_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'media archive recovery credit allocation is append-only'
                USING ERRCODE = '55000';
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_credit_allocation_immutable
        BEFORE UPDATE OR DELETE ON media_archive_recovery_credit_allocation_event
        FOR EACH ROW EXECUTE FUNCTION reject_media_archive_recovery_credit_allocation_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_credit_allocation_no_truncate
        BEFORE TRUNCATE ON media_archive_recovery_credit_allocation_event
        FOR EACH STATEMENT EXECUTE FUNCTION reject_media_archive_recovery_credit_allocation_change()
    """))
    op.execute(sa.text("""
        CREATE FUNCTION reject_media_archive_recovery_request_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'media archive recovery requests are immutable'
                USING ERRCODE = '55000';
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_request_immutable
        BEFORE UPDATE OR DELETE ON media_archive_recovery_request
        FOR EACH ROW EXECUTE FUNCTION reject_media_archive_recovery_request_change()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_request_no_truncate
        BEFORE TRUNCATE ON media_archive_recovery_request
        FOR EACH STATEMENT EXECUTE FUNCTION reject_media_archive_recovery_request_change()
    """))
    op.execute(sa.text("""
        CREATE FUNCTION protect_media_archive_recovery_reservation_identity()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                RAISE EXCEPTION 'media archive recovery reservations are historical'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
                OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
                OR NEW.operation_id IS DISTINCT FROM OLD.operation_id
                OR NEW.reserved_credits IS DISTINCT FROM OLD.reserved_credits
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
            THEN
                RAISE EXCEPTION 'media archive recovery reservation identity is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_reservation_identity
        BEFORE UPDATE OR DELETE ON media_archive_recovery_credit_reservation
        FOR EACH ROW EXECUTE FUNCTION protect_media_archive_recovery_reservation_identity()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER media_archive_recovery_reservation_no_truncate
        BEFORE TRUNCATE ON media_archive_recovery_credit_reservation
        FOR EACH STATEMENT EXECUTE FUNCTION protect_media_archive_recovery_reservation_identity()
    """))


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Cobrança de recuperação de arquivo frio requer PostgreSQL.")

    bind = op.get_bind()
    bind.exec_driver_sql(
        "LOCK TABLE media_archive_recovery_credit_allocation_event, "
        "media_archive_recovery_credit_reservation, media_archive_recovery_request, "
        "media_archive_recovery_pricing, photographer_credit_entry, "
        "media_archive_operation, platform_admin_event "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    has_recovery_data = bind.scalar(sa.text("""
        SELECT EXISTS (SELECT 1 FROM media_archive_recovery_credit_allocation_event LIMIT 1)
            OR EXISTS (SELECT 1 FROM media_archive_recovery_credit_reservation LIMIT 1)
            OR EXISTS (SELECT 1 FROM media_archive_recovery_request LIMIT 1)
            OR EXISTS (
                SELECT 1 FROM media_archive_recovery_pricing
                WHERE recovery_fee_credits IS NOT NULL LIMIT 1
            )
            OR EXISTS (
                SELECT 1 FROM photographer_credit_entry
                WHERE archive_operation_id IS NOT NULL OR entry_type = 'archive_recovery' LIMIT 1
            )
            OR EXISTS (
                SELECT 1 FROM media_archive_operation WHERE operation_type = 'restore' LIMIT 1
            )
            OR EXISTS (
                SELECT 1 FROM platform_admin_event
                WHERE action = 'media_archive.recovery_pricing_updated' LIMIT 1
            )
    """))
    if has_recovery_data:
        raise RuntimeError("Preserve cobranças de recuperação: rollback recusado com dados ou preço definido.")

    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_credit_allocation_immutable "
        "ON media_archive_recovery_credit_allocation_event"
    ))
    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_credit_allocation_no_truncate "
        "ON media_archive_recovery_credit_allocation_event"
    ))
    op.execute(sa.text("DROP FUNCTION reject_media_archive_recovery_credit_allocation_change()"))
    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_request_immutable ON media_archive_recovery_request"
    ))
    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_request_no_truncate ON media_archive_recovery_request"
    ))
    op.execute(sa.text("DROP FUNCTION reject_media_archive_recovery_request_change()"))
    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_reservation_identity "
        "ON media_archive_recovery_credit_reservation"
    ))
    op.execute(sa.text(
        "DROP TRIGGER media_archive_recovery_reservation_no_truncate "
        "ON media_archive_recovery_credit_reservation"
    ))
    op.execute(sa.text("DROP FUNCTION protect_media_archive_recovery_reservation_identity()"))
    op.drop_table("media_archive_recovery_credit_allocation_event")
    op.drop_table("media_archive_recovery_credit_reservation")
    op.drop_table("media_archive_recovery_request")
    op.drop_table("media_archive_recovery_pricing")

    op.drop_index(
        "uq_credit_entry_archive_operation_consumption", table_name="photographer_credit_entry",
    )
    op.drop_constraint(
        "fk_credit_entry_archive_operation_tenant", "photographer_credit_entry", type_="foreignkey",
    )
    op.drop_constraint(
        "ck_credit_entry_archive_operation", "photographer_credit_entry", type_="check",
    )
    op.drop_column("photographer_credit_entry", "archive_operation_id")
    op.drop_constraint("ck_credit_entry_type", "photographer_credit_entry", type_="check")
    op.drop_constraint("ck_credit_entry_delta", "photographer_credit_entry", type_="check")
    op.create_check_constraint(
        "ck_credit_entry_type", "photographer_credit_entry",
        "entry_type IN ('owner_grant', 'grant_revocation', 'purchase', "
        "'upload_consumption', 'purchase_reversal', 'correction')",
    )
    op.create_check_constraint(
        "ck_credit_entry_delta", "photographer_credit_entry",
        "(entry_type IN ('owner_grant', 'purchase') AND delta > 0) OR "
        "(entry_type IN ('grant_revocation', 'upload_consumption', 'purchase_reversal') AND delta < 0) OR "
        "(entry_type = 'correction' AND delta <> 0)",
    )
    op.drop_constraint(
        "uq_media_archive_operation_id_cycle_tenant", "media_archive_operation", type_="unique",
    )
    op.drop_constraint("ck_platform_admin_action", "platform_admin_event", type_="check")
    op.create_check_constraint(
        "ck_platform_admin_action", "platform_admin_event",
        "action IN ('tenant.activate','tenant.suspend','console.access_denied','tenant.status_denied',"
        "'photographer.totp_revoked','photographer.totp_revoke_denied','tenant.host_ready',"
        "'tenant.host_activation_denied')",
    )
