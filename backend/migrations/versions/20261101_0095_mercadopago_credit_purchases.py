"""Compras de créditos Orders e revisão financeira tenant-wide."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261101_0095"
down_revision = "20261031_0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Migration de compra de créditos requer PostgreSQL.")

    op.create_table(
        "mercadopago_credit_purchase",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_name", sa.String(length=120), nullable=False),
        sa.Column("credit_quantity", sa.Integer(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), server_default=sa.text("'BRL'"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("external_reference", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=24), nullable=True),
        sa.Column("state", sa.String(length=32), server_default=sa.text("'prepared'"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("provider_order_id", sa.String(length=64), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=64), nullable=True),
        sa.Column("order_status", sa.String(length=32), nullable=True),
        sa.Column("order_detail", sa.String(length=64), nullable=True),
        sa.Column("transaction_status", sa.String(length=32), nullable=True),
        sa.Column("transaction_detail", sa.String(length=64), nullable=True),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pix_copy_paste", sa.Text(), nullable=True),
        sa.Column("error_category", sa.String(length=48), nullable=True),
        sa.Column("check_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_check_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_status", sa.String(length=16), server_default=sa.text("'none'"), nullable=False),
        sa.Column("reviewed_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("credit_quantity > 0", name="ck_credit_purchase_quantity"),
        sa.CheckConstraint("total_cents > 0", name="ck_credit_purchase_total"),
        sa.CheckConstraint("currency_code = 'BRL'", name="ck_credit_purchase_currency"),
        sa.CheckConstraint(
            "method IS NULL OR method IN ('credit_card', 'pix')",
            name="ck_credit_purchase_method",
        ),
        sa.CheckConstraint(
            "state IN ('prepared', 'submitting', 'initiated', 'pending', 'processing', 'confirmed', "
            "'rejected', 'canceled', 'expired', 'refunded', 'partially_refunded', 'charged_back', "
            "'verification_required', 'abandoned')",
            name="ck_credit_purchase_state",
        ),
        sa.CheckConstraint(
            "state <> 'confirmed' OR (provider_order_id IS NOT NULL AND provider_payment_id IS NOT NULL "
            "AND confirmed_at IS NOT NULL AND ledger_entry_id IS NOT NULL)",
            name="ck_credit_purchase_confirmed",
        ),
        sa.CheckConstraint(
            "review_status IN ('none', 'pending', 'released', 'restricted')",
            name="ck_credit_purchase_review_status",
        ),
        sa.CheckConstraint(
            "(review_status IN ('none', 'pending') AND reviewed_by_admin_id IS NULL "
            "AND reviewed_at IS NULL AND review_note IS NULL) OR "
            "(review_status IN ('released', 'restricted') AND reviewed_by_admin_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL AND review_note IS NOT NULL)",
            name="ck_credit_purchase_review_resolution",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_credit_purchase_tenant"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "buyer_admin_id"],
            ["tenant_admin.tenant_id", "tenant_admin.admin_user_id"],
            name="fk_credit_purchase_buyer_membership",
        ),
        sa.ForeignKeyConstraint(
            ["owner_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_credit_purchase_owner",
        ),
        sa.ForeignKeyConstraint(
            ["receiver_tenant_id"], ["tenant.id"],
            name="fk_credit_purchase_receiver_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["receiver_account_id", "receiver_tenant_id"],
            ["mercadopago_account.id", "mercadopago_account.tenant_id"],
            name="fk_credit_purchase_receiver_account_tenant",
        ),
        sa.ForeignKeyConstraint(["package_id"], ["photographer_credit_package.id"], name="fk_credit_purchase_package"),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id", "tenant_id"],
            ["photographer_credit_entry.id", "photographer_credit_entry.tenant_id"],
            name="fk_credit_purchase_ledger_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"], ["platform_owner.admin_user_id"],
            name="fk_credit_purchase_review_owner",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_credit_purchase_id_tenant"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_credit_purchase_idempotency"),
        sa.UniqueConstraint("receiver_account_id", "external_reference", name="uq_credit_purchase_external_reference"),
        sa.UniqueConstraint("receiver_account_id", "provider_order_id", name="uq_credit_purchase_provider_order"),
        sa.UniqueConstraint("ledger_entry_id", name="uq_credit_purchase_ledger_entry"),
        sa.PrimaryKeyConstraint("id", name="pk_mercadopago_credit_purchase"),
    )
    op.create_index(
        "ix_mercadopago_credit_purchase_tenant_id",
        "mercadopago_credit_purchase", ["tenant_id"],
    )
    op.create_index(
        "ix_credit_purchase_active", "mercadopago_credit_purchase",
        ["tenant_id", "active", "created_at"],
    )
    op.create_index(
        "ix_credit_purchase_reconcile", "mercadopago_credit_purchase",
        ["active", "next_check_at"],
    )
    op.create_index(
        "ix_credit_purchase_review_state", "mercadopago_credit_purchase",
        ["tenant_id", "review_status"],
    )

    op.create_table(
        "mercadopago_credit_purchase_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_key", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('prepared', 'submission_started', 'provider_updated', 'initiated', "
            "'pending', 'processing', 'confirmed', 'rejected', 'canceled', 'expired', 'refunded', "
            "'partially_refunded', 'charged_back', 'verification_required', 'abandoned', 'owner_reviewed')",
            name="ck_credit_purchase_event_type",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_credit_purchase_event_tenant"),
        sa.ForeignKeyConstraint(
            ["purchase_id", "tenant_id"],
            ["mercadopago_credit_purchase.id", "mercadopago_credit_purchase.tenant_id"],
            name="fk_credit_purchase_event_scope",
        ),
        sa.UniqueConstraint("id", "tenant_id", name="uq_credit_purchase_event_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "purchase_id", "event_key", name="uq_credit_purchase_event_key",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mercadopago_credit_purchase_event"),
    )
    op.create_index(
        "ix_mercadopago_credit_purchase_event_tenant_id",
        "mercadopago_credit_purchase_event", ["tenant_id"],
    )
    op.create_index(
        "ix_credit_purchase_event_history", "mercadopago_credit_purchase_event",
        ["tenant_id", "purchase_id", "occurred_at"],
    )

    op.execute(sa.text("""
        CREATE FUNCTION reject_mercadopago_credit_purchase_snapshot_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.id, NEW.tenant_id, NEW.buyer_admin_id, NEW.owner_admin_id,
                NEW.receiver_tenant_id, NEW.receiver_account_id, NEW.package_id,
                NEW.package_name, NEW.credit_quantity, NEW.total_cents, NEW.currency_code,
                NEW.idempotency_key, NEW.external_reference, NEW.created_at)
               IS DISTINCT FROM
               (OLD.id, OLD.tenant_id, OLD.buyer_admin_id, OLD.owner_admin_id,
                OLD.receiver_tenant_id, OLD.receiver_account_id, OLD.package_id,
                OLD.package_name, OLD.credit_quantity, OLD.total_cents, OLD.currency_code,
                OLD.idempotency_key, OLD.external_reference, OLD.created_at) THEN
                RAISE EXCEPTION 'Mercado Pago credit purchase snapshot is immutable';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER tr_credit_purchase_snapshot_immutable
        BEFORE UPDATE ON mercadopago_credit_purchase
        FOR EACH ROW EXECUTE FUNCTION reject_mercadopago_credit_purchase_snapshot_change();
    """))
    for operation in ("UPDATE OR DELETE", "TRUNCATE"):
        if operation == "TRUNCATE":
            op.execute(sa.text("""
                CREATE TRIGGER tr_credit_purchase_event_no_truncate
                BEFORE TRUNCATE ON mercadopago_credit_purchase_event
                FOR EACH STATEMENT EXECUTE FUNCTION reject_photographer_credit_history_change()
            """))
        else:
            op.execute(sa.text("""
                CREATE TRIGGER tr_credit_purchase_event_append_only
                BEFORE UPDATE OR DELETE ON mercadopago_credit_purchase_event
                FOR EACH ROW EXECUTE FUNCTION reject_photographer_credit_history_change()
            """))


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Downgrade de compra de créditos requer PostgreSQL.")

    tables = (
        "mercadopago_credit_purchase",
        "mercadopago_credit_purchase_event",
    )
    connection.exec_driver_sql(
        "LOCK TABLE " + ", ".join(tables) + " IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    for table_name in tables:
        if connection.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")):
            raise RuntimeError(
                "Preserve as compras de créditos: há compras ou eventos financeiros que seriam perdidos."
            )

    op.execute(sa.text("DROP TRIGGER IF EXISTS tr_credit_purchase_event_no_truncate ON mercadopago_credit_purchase_event"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS tr_credit_purchase_event_append_only ON mercadopago_credit_purchase_event"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS tr_credit_purchase_snapshot_immutable ON mercadopago_credit_purchase"))
    op.drop_table("mercadopago_credit_purchase_event")
    op.drop_table("mercadopago_credit_purchase")
    op.execute(sa.text("DROP FUNCTION IF EXISTS reject_mercadopago_credit_purchase_snapshot_change()"))
