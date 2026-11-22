"""Cadastro automatizado aditivo, sem ativação ou alteração de conta legada."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103_0097"
down_revision = "20261103_0096"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Cadastro de fotógrafo requer PostgreSQL.")
    op.add_column("tenant", sa.Column("photographer_name", sa.String(120), nullable=True))
    op.create_table(
        "photographer_signup",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_request_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("photographer_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("otp_digest", sa.String(64), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("reserved_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reserved_tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setup_digest", sa.String(64), unique=True, nullable=True),
        sa.Column("setup_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("totp_envelope", sa.String(512), nullable=True),
        sa.Column("activated_tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('email_pending','credentials_pending','active','expired','cancelled')", name="ck_photographer_signup_state"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 5", name="ck_photographer_signup_attempts"),
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Cadastro de fotógrafo requer PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE photographer_signup, tenant IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM photographer_signup LIMIT 1)")):
        raise RuntimeError("Preserve os cadastros: rollback com histórico recusado.")
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM tenant WHERE photographer_name IS NOT NULL LIMIT 1)")):
        raise RuntimeError("Preserve nomes de fotógrafos: rollback recusado.")
    op.drop_table("photographer_signup")
    op.drop_column("tenant", "photographer_name")
