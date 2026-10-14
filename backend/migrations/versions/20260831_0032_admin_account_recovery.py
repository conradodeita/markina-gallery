"""Adiciona recuperação e segurança da conta administrativa.

Revision ID: 20260831_0032
Revises: 20260831_0031
"""

import sqlalchemy as sa
from alembic import op

revision = "20260831_0032"
down_revision = "20260831_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_security_challenge",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("subject_fingerprint", sa.String(64), nullable=False),
        sa.Column("target_fingerprint", sa.String(64), nullable=True),
        sa.Column("encrypted_target", sa.Text(), nullable=True),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("resend_count", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('password_recovery_otp', 'change_password_otp', 'change_email_otp')"
        ),
        sa.CheckConstraint("attempts >= 0"),
        sa.CheckConstraint("resend_count >= 0"),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("purpose", "admin_id", "session_id", "subject_fingerprint", "target_fingerprint", "expires_at"):
        op.create_index(f"ix_admin_security_challenge_{column}", "admin_security_challenge", [column])

    op.create_table(
        "admin_action_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("target_fingerprint", sa.String(64), nullable=True),
        sa.Column("encrypted_target", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purpose IN ('password_reset', 'verify_admin_email')"),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    for column in ("admin_id", "purpose", "token_hash", "target_fingerprint", "expires_at"):
        op.create_index(f"ix_admin_action_token_{column}", "admin_action_token", [column])

    op.create_table(
        "email_delivery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("recipient_fingerprint", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("external_message_id", sa.String(192), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('password_recovery', 'email_verification', 'security_notice')"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'accepted', 'failed', 'unknown', 'expired')"),
        sa.CheckConstraint("attempts >= 0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_message_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in ("kind", "source_type", "source_id", "recipient_fingerprint", "status", "next_attempt_at", "expires_at"):
        op.create_index(f"ix_email_delivery_{column}", "email_delivery", [column])

    op.create_table(
        "email_delivery_attempt",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("external_message_id", sa.String(192), nullable=True),
        sa.Column("error_category", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("result IN ('accepted', 'transient_failure', 'permanent_failure', 'unknown')"),
        sa.CheckConstraint("attempt_number >= 1"),
        sa.ForeignKeyConstraint(["delivery_id"], ["email_delivery.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_delivery_attempt_delivery_id", "email_delivery_attempt", ["delivery_id"])


def downgrade() -> None:
    op.drop_index("ix_email_delivery_attempt_delivery_id", table_name="email_delivery_attempt")
    op.drop_table("email_delivery_attempt")
    for column in ("expires_at", "next_attempt_at", "status", "recipient_fingerprint", "source_id", "source_type", "kind"):
        op.drop_index(f"ix_email_delivery_{column}", table_name="email_delivery")
    op.drop_table("email_delivery")
    for column in ("expires_at", "target_fingerprint", "token_hash", "purpose", "admin_id"):
        op.drop_index(f"ix_admin_action_token_{column}", table_name="admin_action_token")
    op.drop_table("admin_action_token")
    for column in ("expires_at", "target_fingerprint", "subject_fingerprint", "session_id", "admin_id", "purpose"):
        op.drop_index(f"ix_admin_security_challenge_{column}", table_name="admin_security_challenge")
    op.drop_table("admin_security_challenge")
