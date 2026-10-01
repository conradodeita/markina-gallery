"""Permissão técnica explícita, vazia por padrão e sem concessão automática."""

import sqlalchemy as sa
from alembic import op

revision = "20261001_0071"
down_revision = "20260930_0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installation_operator",
        sa.Column("admin_user_id", sa.Uuid(), sa.ForeignKey("admin_user.id"), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("authorization_reference", sa.String(120), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(authorization_reference) BETWEEN 1 AND 120", name="ck_operator_reference"),
        sa.CheckConstraint("NOT active OR revoked_at IS NULL", name="ck_operator_active_revocation"),
    )


def downgrade() -> None:
    raise RuntimeError("Downgrade recusado: preserve permissões e auditoria da instalação.")
