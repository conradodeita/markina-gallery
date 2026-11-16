"""Enrollment voluntário com material temporário cifrado e escopo de sessão."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261104_0100"
down_revision = "20261104_0099"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_totp_enrollment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_user.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret_envelope", sa.String(768), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 5"),
        sa.UniqueConstraint("id", "tenant_id"),
        sa.UniqueConstraint("tenant_id", "admin_user_id"),
        sa.ForeignKeyConstraint(["admin_user_id", "tenant_id"], ["tenant_admin.admin_user_id", "tenant_admin.tenant_id"]),
        sa.ForeignKeyConstraint(["session_id", "tenant_id"], ["auth_session.id", "auth_session.tenant_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_admin_totp_enrollment_tenant_id", "admin_totp_enrollment", ["tenant_id"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Enrollment TOTP requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE admin_totp_enrollment IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM admin_totp_enrollment)")):
        raise RuntimeError("Preserve tentativas de autenticador: rollback recusado.")
    op.drop_table("admin_totp_enrollment")
