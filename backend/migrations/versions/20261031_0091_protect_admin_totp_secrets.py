"""Protege segredos TOTP e registra o último passo consumido."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.totp_crypto import TotpSecretCipher
from app.totp_migration import encrypt_existing_totp, restore_legacy_totp

revision = "20261031_0091"
down_revision = "20261026_0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("admin_user") as batch_op:
        batch_op.alter_column(
            "totp_secret", existing_type=sa.String(128), existing_nullable=False,
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("totp_secret_envelope", sa.String(768), nullable=True)
        )
        batch_op.add_column(
            sa.Column("totp_last_used_step", sa.Integer(), nullable=True)
        )
    cipher = TotpSecretCipher.from_environment()
    encrypt_existing_totp(bind, cipher)


def downgrade() -> None:
    bind = op.get_bind()
    cipher = TotpSecretCipher.from_environment()
    restore_legacy_totp(bind, cipher)
    with op.batch_alter_table("admin_user") as batch_op:
        batch_op.drop_column("totp_last_used_step")
        batch_op.drop_column("totp_secret_envelope")
        batch_op.alter_column(
            "totp_secret", existing_type=sa.String(128), existing_nullable=True,
            nullable=False,
        )
