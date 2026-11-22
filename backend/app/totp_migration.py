"""Conversão idempotente de valores TOTP durante upgrade/downgrade Alembic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.totp_crypto import TotpSecretCipher, TotpSecretError


def _lock_admin_totp_table(connection: Connection) -> None:
    """Serializa o snapshot e a escrita para impedir corridas com escritores antigos."""
    if connection.dialect.name == "postgresql":
        connection.execute(text("LOCK TABLE admin_user IN SHARE ROW EXCLUSIVE MODE"))


def encrypt_existing_totp(connection: Connection, cipher: TotpSecretCipher) -> int:
    """Backfill envelope sem modificar a coluna plaintext usada pelo binário antigo."""
    rows = connection.execute(text(
        "SELECT id, totp_secret, totp_secret_envelope "
        "FROM admin_user ORDER BY id"
    )).all()
    updates: list[tuple[str, str]] = []
    for row in rows:
        admin_id = UUID(str(row.id))
        legacy = row.totp_secret
        envelope = row.totp_secret_envelope
        if envelope is not None:
            current = cipher.decrypt(envelope, admin_id=admin_id)
            if legacy is None:
                continue
            if not isinstance(legacy, str) or not legacy or len(legacy) > 128:
                raise TotpSecretError()
            if current == legacy:
                continue
        if not isinstance(legacy, str) or not legacy or len(legacy) > 128:
            raise TotpSecretError()
        updates.append((cipher.encrypt(legacy, admin_id=admin_id), str(admin_id)))
    for envelope, admin_id in updates:
        connection.execute(
            text(
                "UPDATE admin_user SET totp_secret_envelope = :value "
                "WHERE id = :admin_id"
            ),
            {"value": envelope, "admin_id": admin_id},
        )
    return len(updates)


def restore_legacy_totp(connection: Connection, cipher: TotpSecretCipher) -> int:
    """Valida todo o conjunto e restaura plaintext antes de rollback legado."""
    _lock_admin_totp_table(connection)
    rows = connection.execute(text(
        "SELECT id, totp_secret, totp_secret_envelope "
        "FROM admin_user ORDER BY id"
    )).all()
    updates: list[tuple[str, str]] = []
    for row in rows:
        admin_id = UUID(str(row.id))
        legacy = row.totp_secret
        envelope = row.totp_secret_envelope
        # Durante expansão, o binário antigo ainda pode ter a escrita mais nova.
        # Preservar esse valor é essencial para que rollback não restaure ciphertext
        # antigo sobre uma alteração legítima feita pelo consumidor legado.
        if isinstance(legacy, str) and legacy and len(legacy) <= 128:
            continue
        if legacy is not None:
            raise TotpSecretError()
        if not TotpSecretCipher.is_envelope(envelope):
            raise TotpSecretError()
        plaintext = cipher.decrypt(envelope, admin_id=admin_id)
        if not plaintext or len(plaintext) > 128:
            raise TotpSecretError()
        updates.append((plaintext, str(admin_id)))
    for plaintext, admin_id in updates:
        connection.execute(
            text("UPDATE admin_user SET totp_secret = :value WHERE id = :admin_id"),
            {"value": plaintext, "admin_id": admin_id},
        )
    return len(updates)


def contract_legacy_totp(connection: Connection, cipher: TotpSecretCipher) -> int:
    """Reconcilia plaintext recente, valida tudo e só então limpa a coluna legada."""
    from app.totp_crypto import legacy_totp_dual_write_enabled

    if legacy_totp_dual_write_enabled():
        raise TotpSecretError()
    _lock_admin_totp_table(connection)
    rows = connection.execute(text(
        "SELECT id, totp_secret, totp_secret_envelope "
        "FROM admin_user ORDER BY id"
    )).all()
    admin_ids: list[str] = []
    replacements: list[tuple[str, str]] = []
    for row in rows:
        admin_id = UUID(str(row.id))
        legacy = row.totp_secret
        envelope = row.totp_secret_envelope
        if not TotpSecretCipher.is_envelope(envelope):
            raise TotpSecretError()
        current = cipher.decrypt(envelope, admin_id=admin_id)
        if legacy is not None:
            if not isinstance(legacy, str) or not legacy or len(legacy) > 128:
                raise TotpSecretError()
            if current != legacy:
                replacements.append((cipher.encrypt(legacy, admin_id=admin_id), str(admin_id)))
        admin_ids.append(str(admin_id))
    for envelope, admin_id in replacements:
        connection.execute(
            text(
                "UPDATE admin_user SET totp_secret_envelope = :value "
                "WHERE id = :admin_id"
            ),
            {"value": envelope, "admin_id": admin_id},
        )
    for admin_id in admin_ids:
        connection.execute(
            text("UPDATE admin_user SET totp_secret = NULL WHERE id = :admin_id"),
            {"admin_id": admin_id},
        )
    return len(admin_ids)


def rotate_admin_totp_envelopes(session, cipher: TotpSecretCipher, *, apply: bool) -> dict[str, int]:
    """Valida e planeja/recifra todos os envelopes sem retornar IDs ou segredos."""
    from sqlalchemy import select

    from app.auth import AdminUser

    table = AdminUser.__table__
    statement = select(
        table.c.id.label("admin_id"),
        table.c.totp_secret.label("legacy"),
        table.c.totp_secret_envelope.label("envelope"),
    ).order_by(table.c.id)
    if apply:
        statement = statement.with_for_update()
    connection = session.connection()
    rows = connection.execute(statement).all()
    counts: dict[str, int] = {}
    replacements: list[tuple[UUID, str]] = []
    for row in rows:
        admin_id = UUID(str(row.admin_id))
        envelope = row.envelope
        if not TotpSecretCipher.is_envelope(envelope):
            raise TotpSecretError()
        key_id = envelope.split(":")[2]
        current = cipher.decrypt(envelope, admin_id=admin_id)
        counts[key_id] = counts.get(key_id, 0) + 1
        source = current
        if row.legacy is not None:
            if not isinstance(row.legacy, str) or not row.legacy or len(row.legacy) > 128:
                raise TotpSecretError()
            source = row.legacy
        replacement = (
            cipher.encrypt(source, admin_id=admin_id)
            if source != current
            else cipher.rotate(envelope, admin_id=admin_id)
        )
        if replacement != envelope:
            replacements.append((admin_id, replacement))
    if apply:
        for admin_id, replacement in replacements:
            connection.execute(
                table.update().where(table.c.id == admin_id).values(
                    totp_secret_envelope=replacement
                )
            )
    counts["recifrados"] = len(replacements) if apply else 0
    counts["pendentes"] = len(replacements)
    return counts
