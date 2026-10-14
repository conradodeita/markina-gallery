"""Adiciona transporte WhatsApp genérico e estado operacional.

Revision ID: 20260830_0016
Revises: 20260829_0015
"""

import sqlalchemy as sa
from alembic import op


revision = "20260830_0016"
down_revision = "20260829_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "whatsapp_channel_settings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("environment", sa.String(32), nullable=False, unique=True),
        sa.Column("expected_phone_e164", sa.String(16), nullable=True),
        sa.Column("connected_phone_e164", sa.String(16), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("last_error", sa.String(240), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('sandbox', 'pending_pairing', 'connecting', 'ready', "
            "'mismatch', 'disconnected', 'error')"
        ),
    )
    op.create_index(
        "ix_whatsapp_channel_settings_environment",
        "whatsapp_channel_settings",
        ["environment"],
    )
    op.create_index(
        "ix_whatsapp_channel_settings_status", "whatsapp_channel_settings", ["status"]
    )
    op.create_table(
        "whatsapp_delivery",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("recipient_phone", sa.String(16), nullable=False),
        sa.Column("template_kind", sa.String(48), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True),
        sa.Column("encrypted_payload", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("external_message_id", sa.String(192), nullable=True, unique=True),
        sa.Column("provider_status", sa.String(48), nullable=True),
        sa.Column("last_error", sa.String(240), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('otp', 'payment')"),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'accepted', 'delivered', 'read', "
            "'failed', 'unknown', 'expired')"
        ),
        sa.CheckConstraint("attempts >= 0"),
    )
    for name in ("kind", "source_type", "source_id", "expires_at", "status", "next_attempt_at"):
        op.create_index(f"ix_whatsapp_delivery_{name}", "whatsapp_delivery", [name])
    op.create_table(
        "whatsapp_delivery_attempt",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "delivery_id",
            uuid,
            sa.ForeignKey("whatsapp_delivery.id"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("external_message_id", sa.String(192), nullable=True),
        sa.Column("error_category", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "result IN ('accepted', 'transient_failure', 'permanent_failure', 'unknown')"
        ),
        sa.CheckConstraint("attempt_number >= 1"),
    )
    op.create_index(
        "ix_whatsapp_delivery_attempt_delivery_id",
        "whatsapp_delivery_attempt",
        ["delivery_id"],
    )
    op.create_table(
        "whatsapp_webhook_receipt",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("external_message_id", sa.String(192), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_webhook_receipt")
    op.drop_index(
        "ix_whatsapp_delivery_attempt_delivery_id",
        table_name="whatsapp_delivery_attempt",
    )
    op.drop_table("whatsapp_delivery_attempt")
    for name in reversed(
        ("kind", "source_type", "source_id", "expires_at", "status", "next_attempt_at")
    ):
        op.drop_index(f"ix_whatsapp_delivery_{name}", table_name="whatsapp_delivery")
    op.drop_table("whatsapp_delivery")
    op.drop_index(
        "ix_whatsapp_channel_settings_status", table_name="whatsapp_channel_settings"
    )
    op.drop_index(
        "ix_whatsapp_channel_settings_environment",
        table_name="whatsapp_channel_settings",
    )
    op.drop_table("whatsapp_channel_settings")
