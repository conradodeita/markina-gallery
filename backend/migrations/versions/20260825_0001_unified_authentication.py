"""Cria a persistência da autenticação unificada.

Revision ID: 20260825_0001
Revises:
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa

revision = "20260825_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "admin_user",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("totp_secret", sa.String(128), nullable=False),
    )
    op.create_index("ix_admin_user_email", "admin_user", ["email"])
    op.create_table(
        "client",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("phone_e164", sa.String(16), nullable=False, unique=True),
    )
    op.create_index("ix_client_phone_e164", "client", ["phone_e164"])
    op.create_table(
        "gallery_access",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("client_id", uuid, sa.ForeignKey("client.id"), nullable=False),
        sa.Column("gallery_id", uuid, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_gallery_access_client_id", "gallery_access", ["client_id"])
    op.create_index("ix_gallery_access_gallery_id", "gallery_access", ["gallery_id"])
    op.create_table(
        "auth_challenge",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(320), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("resend_count", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_challenge_kind", "auth_challenge", ["kind"])
    op.create_index("ix_auth_challenge_subject", "auth_challenge", ["subject"])
    op.create_table(
        "auth_session",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("subject_id", uuid, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_session_token_hash", "auth_session", ["token_hash"])
    op.create_index("ix_auth_session_role", "auth_session", ["role"])
    op.create_index("ix_auth_session_subject_id", "auth_session", ["subject_id"])
    op.create_table(
        "audit_event",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("event", sa.String(80), nullable=False),
        sa.Column("subject", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_event_event", "audit_event", ["event"])


def downgrade() -> None:
    for table in (
        "audit_event",
        "auth_session",
        "auth_challenge",
        "gallery_access",
        "client",
        "admin_user",
    ):
        op.drop_table(table)
