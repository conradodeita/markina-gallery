"""Schema aditivo para carteira, ledger e recuperação de uploads."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261031_0094"
down_revision = "20261031_0093"
branch_labels = None
depends_on = None


def _resolve_existing_wallets(connection) -> tuple[list[object], object | None]:
    """Fail closed antes do DDL se uma base existente não identificar o owner."""
    connection.exec_driver_sql(
        "LOCK TABLE tenant, tenant_admin, platform_owner IN SHARE ROW EXCLUSIVE MODE"
    )
    tenants = list(connection.scalars(sa.text("SELECT id FROM tenant ORDER BY id")))
    owners = list(connection.execute(sa.text(
        "SELECT singleton, admin_user_id FROM platform_owner ORDER BY singleton"
    )))
    if not tenants and not owners:
        return tenants, None
    if len(owners) != 1 or owners[0].singleton != 1:
        raise RuntimeError(
            "Migration de créditos recusada: proprietário persistente ausente ou ambíguo."
        )

    memberships = list(connection.scalars(sa.text(
        "SELECT tenant_id FROM tenant_admin "
        "WHERE admin_user_id = :admin_id AND active IS TRUE ORDER BY tenant_id LIMIT 2"
    ), {"admin_id": owners[0].admin_user_id}))
    if len(memberships) != 1:
        raise RuntimeError(
            "Migration de créditos recusada: vínculo ativo do proprietário ausente ou ambíguo."
        )
    status = connection.scalar(sa.text(
        "SELECT status FROM tenant WHERE id = :tenant_id"
    ), {"tenant_id": memberships[0]})
    if status != "active":
        raise RuntimeError(
            "Migration de créditos recusada: tenant do proprietário indisponível."
        )
    return tenants, memberships[0]


def _create_history_guard(table_name: str) -> None:
    op.execute(sa.text(f"""
        CREATE TRIGGER tr_{table_name}_append_only
        BEFORE UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION reject_photographer_credit_history_change()
    """))
    op.execute(sa.text(f"""
        CREATE TRIGGER tr_{table_name}_no_truncate
        BEFORE TRUNCATE ON {table_name}
        FOR EACH STATEMENT EXECUTE FUNCTION reject_photographer_credit_history_change()
    """))


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Migration da carteira requer PostgreSQL.")

    # O lock mantém estável a associação consultada durante o backfill. A única
    # base sem owner aceita é uma instalação realmente sem tenant e sem PlatformOwner.
    tenant_ids, owner_tenant_id = _resolve_existing_wallets(connection)

    op.create_table(
        "tenant_credit_wallet",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(length=16), server_default=sa.text("'finite'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("mode IN ('finite', 'unmetered')", name="ck_tenant_credit_wallet_mode"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_tenant_credit_wallet_tenant"),
        sa.PrimaryKeyConstraint("tenant_id", name="pk_tenant_credit_wallet"),
    )
    op.create_index(
        "uq_tenant_credit_wallet_single_unmetered", "tenant_credit_wallet", ["mode"],
        unique=True, postgresql_where=sa.text("mode = 'unmetered'"),
    )

    op.create_table(
        "photographer_credit_package",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("credit_quantity", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 120", name="ck_credit_package_name"),
        sa.CheckConstraint("credit_quantity > 0", name="ck_credit_package_quantity"),
        sa.CheckConstraint(
            "(price_cents IS NULL AND currency_code IS NULL) OR "
            "(price_cents > 0 AND currency_code IS NOT NULL "
            "AND length(currency_code) = 3 AND currency_code = upper(currency_code))",
            name="ck_credit_package_price_currency",
        ),
        sa.CheckConstraint(
            "active = false OR (price_cents IS NOT NULL AND currency_code IS NOT NULL)",
            name="ck_credit_package_active_price",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_credit_package_created_by_owner",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_credit_package_updated_by_owner",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_photographer_credit_package"),
    )

    op.create_table(
        "photo_credit_operation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("photo_asset_id_snapshot", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key_snapshot", sa.String(length=1024), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'reserved'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(payload_fingerprint) = 64", name="ck_credit_operation_fingerprint"),
        sa.CheckConstraint("quantity = 1", name="ck_credit_operation_quantity"),
        sa.CheckConstraint(
            "photo_asset_id IS NULL OR photo_asset_id = photo_asset_id_snapshot",
            name="ck_credit_operation_photo_snapshot",
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'consumed', 'released', 'reconciliation_required')",
            name="ck_credit_operation_status",
        ),
        sa.ForeignKeyConstraint(
            ["photo_asset_id", "tenant_id"], ["photo_asset.id", "photo_asset.tenant_id"],
            name="fk_credit_operation_photo_tenant",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_credit_operation_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "photo_asset_id_snapshot", name="uq_credit_operation_asset_snapshot",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_owner_photo_credit_operation_id_tenant_id"),
        sa.PrimaryKeyConstraint("id", name="pk_photo_credit_operation"),
    )
    op.create_index("ix_photo_credit_operation_status", "photo_credit_operation", ["status"])
    op.create_index("ix_photo_credit_operation_tenant_id", "photo_credit_operation", ["tenant_id"])
    op.create_index(
        "ix_credit_operation_reconcile", "photo_credit_operation", ["tenant_id", "status", "updated_at"],
    )

    op.create_table(
        "photographer_credit_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("global_owner_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_reference", sa.String(length=240), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('owner_grant', 'grant_revocation', 'purchase', "
            "'upload_consumption', 'purchase_reversal', 'correction')",
            name="ck_credit_entry_type",
        ),
        sa.CheckConstraint(
            "(entry_type IN ('owner_grant', 'purchase') AND delta > 0) OR "
            "(entry_type IN ('grant_revocation', 'upload_consumption', 'purchase_reversal') AND delta < 0) OR "
            "(entry_type = 'correction' AND delta <> 0)",
            name="ck_credit_entry_delta",
        ),
        sa.CheckConstraint(
            "entry_type <> 'upload_consumption' OR (operation_id IS NOT NULL AND delta = -1)",
            name="ck_credit_entry_upload_operation",
        ),
        sa.CheckConstraint(
            "entry_type <> 'purchase' OR package_id IS NOT NULL",
            name="ck_credit_entry_purchase_package",
        ),
        sa.CheckConstraint(
            "entry_type NOT IN ('grant_revocation', 'purchase_reversal', 'upload_consumption') "
            "OR source_entry_id IS NOT NULL",
            name="ck_credit_entry_source_required",
        ),
        sa.CheckConstraint(
            "entry_type NOT IN ('owner_grant', 'grant_revocation') "
            "OR global_owner_admin_id IS NOT NULL",
            name="ck_credit_entry_owner_authority",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_entry_operation_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_entry_source_tenant",
        ),
        sa.ForeignKeyConstraint(["package_id"], ["photographer_credit_package.id"], name="fk_credit_entry_package"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admin_user.id"], name="fk_credit_entry_actor_admin"),
        sa.ForeignKeyConstraint(
            ["global_owner_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_credit_entry_global_owner",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_credit_entry_tenant"),
        sa.ForeignKeyConstraint(
            ["actor_admin_id", "tenant_id"], ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"],
            name="fk_owner_photographer_credit_entry_actor_admin_id_tena_2b27af5a",
        ),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_entry_idempotency"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_owner_photographer_credit_entry_id_tenant_id"),
        sa.PrimaryKeyConstraint("id", name="pk_photographer_credit_entry"),
    )
    op.create_index("ix_photographer_credit_entry_tenant_id", "photographer_credit_entry", ["tenant_id"])
    op.create_index("ix_credit_entry_tenant_created", "photographer_credit_entry", ["tenant_id", "created_at"])
    op.create_index(
        "uq_credit_entry_operation_consumption", "photographer_credit_entry", ["tenant_id", "operation_id"],
        unique=True,
        postgresql_where=sa.text("entry_type = 'upload_consumption' AND operation_id IS NOT NULL"),
    )

    op.create_table(
        "photographer_credit_allocation_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credit_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('reserved', 'consumed', 'released', 'revoked')",
            name="ck_credit_allocation_event_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_credit_allocation_quantity"),
        sa.CheckConstraint(
            "(event_type IN ('reserved', 'released') AND operation_id IS NOT NULL AND credit_entry_id IS NULL) OR "
            "(event_type = 'consumed' AND operation_id IS NOT NULL AND credit_entry_id IS NOT NULL) OR "
            "(event_type = 'revoked' AND operation_id IS NULL AND credit_entry_id IS NOT NULL)",
            name="ck_credit_allocation_event_context",
        ),
        sa.ForeignKeyConstraint(
            ["source_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_allocation_source_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_allocation_operation_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["credit_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_allocation_entry_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.id"], name="fk_credit_allocation_tenant",
        ),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_allocation_idempotency"),
        sa.UniqueConstraint(
            "id", "tenant_id", name="uq_owner_photographer_credit_allocation_event_id_tenant_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_photographer_credit_allocation_event"),
    )
    op.create_index(
        "ix_photographer_credit_allocation_event_tenant_id",
        "photographer_credit_allocation_event", ["tenant_id"],
    )
    op.create_index(
        "ix_credit_allocation_source_history", "photographer_credit_allocation_event",
        ["tenant_id", "source_entry_id", "occurred_at"],
    )
    op.create_index(
        "ix_credit_allocation_operation_history", "photographer_credit_allocation_event",
        ["tenant_id", "operation_id", "occurred_at"],
    )

    op.create_table(
        "photo_credit_operation_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('reserved', 'upload_attempted', 'source_durable', 'consumed', "
            "'released', 'reconciliation_required', 'reconciled_consumed', 'reconciled_released')",
            name="ck_credit_operation_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id", "tenant_id"],
            ["photo_credit_operation.id", "photo_credit_operation.tenant_id"],
            name="fk_credit_operation_event_scope",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_credit_operation_event_tenant"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admin_user.id"], name="fk_credit_operation_event_actor_admin"),
        sa.ForeignKeyConstraint(
            ["actor_admin_id", "tenant_id"], ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"],
            name="fk_owner_photo_credit_operation_event_actor_admin_id_t_2ffe933d",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_owner_photo_credit_operation_event_id_tenant_id"),
        sa.PrimaryKeyConstraint("id", name="pk_photo_credit_operation_event"),
    )
    op.create_index("ix_photo_credit_operation_event_tenant_id", "photo_credit_operation_event", ["tenant_id"])
    op.create_index(
        "ix_credit_operation_event_history", "photo_credit_operation_event",
        ["tenant_id", "operation_id", "occurred_at"],
    )

    op.execute(sa.text("""
        CREATE FUNCTION reject_photographer_credit_history_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'photographer credit history is append-only'
                USING ERRCODE = '55000';
        END;
        $$
    """))
    for table_name in (
        "photographer_credit_entry", "photographer_credit_allocation_event",
        "photo_credit_operation_event",
    ):
        _create_history_guard(table_name)

    op.execute(sa.text("""
        CREATE FUNCTION protect_photo_credit_operation_identity()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
                OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
                OR NEW.photo_asset_id_snapshot IS DISTINCT FROM OLD.photo_asset_id_snapshot
                OR NEW.storage_key_snapshot IS DISTINCT FROM OLD.storage_key_snapshot
                OR NEW.payload_fingerprint IS DISTINCT FROM OLD.payload_fingerprint
                OR NEW.quantity IS DISTINCT FROM OLD.quantity
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
                OR (NEW.photo_asset_id IS DISTINCT FROM OLD.photo_asset_id
                    AND NEW.photo_asset_id IS NOT NULL)
            THEN
                RAISE EXCEPTION 'photo credit operation identity is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER tr_photo_credit_operation_identity
        BEFORE UPDATE ON photo_credit_operation
        FOR EACH ROW EXECUTE FUNCTION protect_photo_credit_operation_identity()
    """))

    if tenant_ids:
        values = [
            {
                "tenant_id": tenant_id,
                "mode": "unmetered" if tenant_id == owner_tenant_id else "finite",
            }
            for tenant_id in tenant_ids
        ]
        connection.execute(sa.text(
            "INSERT INTO tenant_credit_wallet (tenant_id, mode) "
            "VALUES (:tenant_id, :mode)"
        ), values)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Downgrade da carteira requer PostgreSQL.")
    tables = (
        "photo_credit_operation_event", "photographer_credit_allocation_event",
        "photographer_credit_entry", "photo_credit_operation",
        "photographer_credit_package", "tenant_credit_wallet",
    )
    connection.exec_driver_sql(
        "LOCK TABLE " + ", ".join(tables) + " IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    for table_name in tables:
        if connection.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")):
            raise RuntimeError(
                "Preserve o schema da carteira: há configuração, saldo ou histórico que seria perdido."
            )

    for table_name in tables:
        op.drop_table(table_name)
    op.execute(sa.text("DROP FUNCTION reject_photographer_credit_history_change()"))
    op.execute(sa.text("DROP FUNCTION protect_photo_credit_operation_identity()"))
