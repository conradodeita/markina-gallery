"""Adiciona hashes de códigos de recuperação TOTP de uso único."""

import sqlalchemy as sa
from alembic import op

revision = "20261031_0092"
down_revision = "20261031_0091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_totp_recovery_code",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_user_id", sa.Uuid(), nullable=False),
        sa.Column("code_selector", sa.String(length=4), nullable=False),
        sa.Column("code_hash", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admin_user_id", "code_selector", name="uq_admin_totp_recovery_selector"),
    )
    op.create_index(
        "ix_admin_totp_recovery_active",
        "admin_totp_recovery_code",
        ["admin_user_id", "used_at", "revoked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_totp_recovery_active", table_name="admin_totp_recovery_code")
    op.drop_table("admin_totp_recovery_code")
