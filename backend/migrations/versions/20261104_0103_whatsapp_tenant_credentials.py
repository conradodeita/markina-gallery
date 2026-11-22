"""Credenciais cifradas Evolution por tenant e ambiente."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261104_0103"
down_revision = "20261104_0102"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Credenciais WhatsApp por tenant requerem PostgreSQL.")
    op.create_table(
        "whatsapp_tenant_credential",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("instance_name", sa.String(80), nullable=False),
        sa.Column("webhook_secret_envelope", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "environment", name="uq_whatsapp_tenant_credential_scope"),
        sa.UniqueConstraint("environment", "instance_name", name="uq_whatsapp_tenant_instance"),
    )
    op.create_index(
        "ix_whatsapp_tenant_credential_tenant_id",
        "whatsapp_tenant_credential",
        ["tenant_id"],
    )
    op.create_index(
        "ix_whatsapp_tenant_credential_environment",
        "whatsapp_tenant_credential",
        ["environment"],
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("Credenciais WhatsApp por tenant requerem PostgreSQL.")
    bind.exec_driver_sql(
        "LOCK TABLE whatsapp_tenant_credential IN ACCESS EXCLUSIVE MODE NOWAIT"
    )
    if bind.scalar(sa.text(
        "SELECT EXISTS(SELECT 1 FROM whatsapp_tenant_credential LIMIT 1)"
    )):
        raise RuntimeError("Preserve credenciais WhatsApp; rollback com canais provisionados recusado.")
    op.drop_index("ix_whatsapp_tenant_credential_environment", table_name="whatsapp_tenant_credential")
    op.drop_index("ix_whatsapp_tenant_credential_tenant_id", table_name="whatsapp_tenant_credential")
    op.drop_table("whatsapp_tenant_credential")
