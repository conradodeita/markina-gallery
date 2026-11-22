"""Persistência aditiva para OAuth privado Google Drive."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103_0098"
down_revision = "20261103_0097"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Conexão Google Drive requer PostgreSQL.")
    op.create_table(
        "google_drive_oauth_attempt",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("auth_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth_session.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("state_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("verifier_envelope", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_google_drive_oauth_attempt_actor_admin_id", "google_drive_oauth_attempt", ["actor_admin_id"])
    op.create_index("ix_google_drive_oauth_attempt_auth_session_id", "google_drive_oauth_attempt", ["auth_session_id"])
    op.create_index("ix_google_drive_oauth_attempt_tenant_id", "google_drive_oauth_attempt", ["tenant_id"])
    op.create_table(
        "google_drive_connection",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False, unique=True),
        sa.Column("connected_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("refresh_token_envelope", sa.JSON(), nullable=False),
        sa.Column("scopes", sa.String(256), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quota_limit", sa.String(40), nullable=True),
        sa.Column("quota_usage", sa.String(40), nullable=True),
        sa.Column("quota_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('connected','revoked','reauthorization_required')", name="ck_google_drive_connection_state"),
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Conexão Google Drive requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE google_drive_connection, google_drive_oauth_attempt "
        "IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM google_drive_connection LIMIT 1)")):
        raise RuntimeError("Preserve a conexão Drive; rollback com credencial recusado.")
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM google_drive_oauth_attempt LIMIT 1)")):
        raise RuntimeError("Preserve o histórico OAuth; rollback com tentativas recusado.")
    op.drop_table("google_drive_connection")
    op.drop_index("ix_google_drive_oauth_attempt_auth_session_id", table_name="google_drive_oauth_attempt")
    op.drop_index("ix_google_drive_oauth_attempt_tenant_id", table_name="google_drive_oauth_attempt")
    op.drop_index("ix_google_drive_oauth_attempt_actor_admin_id", table_name="google_drive_oauth_attempt")
    op.drop_table("google_drive_oauth_attempt")
