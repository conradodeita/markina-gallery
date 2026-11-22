"""Limpa a coluna legada após reconciliar os consumidores TOTP."""

from __future__ import annotations

from alembic import op

from app.totp_crypto import TotpSecretCipher
from app.totp_migration import contract_legacy_totp, restore_legacy_totp

revision = "20261031_0093"
down_revision = "20261031_0092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    contract_legacy_totp(op.get_bind(), TotpSecretCipher.from_environment())


def downgrade() -> None:
    restore_legacy_totp(op.get_bind(), TotpSecretCipher.from_environment())
