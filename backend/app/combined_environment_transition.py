"""Composição local das transações; não expõe CLI, rota ou commit operacional."""

from sqlalchemy import select, text, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.app_env_transition import (
    EnvironmentTransitionError,
    _account_fingerprint,
    _execute_mercadopago_transition,
    _load_accounts,
    _open_transition_backup,
    restore_mercadopago_transition_backup,
)
from app.auth import WhatsAppChannelSettings
from app.facial.environment_migration_guard import authorize_biometric_migration_write
from app.facial.environment_sql import BiometricSqlError
from app.facial.environment_sql_backup import (
    SqlBackupError,
    apply_sql_transition,
    open_sql_transition,
)


class CombinedTransitionError(RuntimeError):
    """Falha constante; nenhuma entrada ou saída de provedor é exposta."""


def apply_combined_transition(connection: Connection, *, biometric_archive,
    biometric_preflight, biometric_backup_key: bytes, account_plan, account_backup,
    source_cipher, target_cipher, persisted_backups_reopened: bool,
    channel_source: tuple[dict, ...]) -> dict[str, int | str]:
    """Executa somente envelopes em transação externa já aprovada pelo coordenador.

    Esta primitiva não valida configuração/integrações externas e não substitui o
    gate do release. Não conectar a comando operacional sem o preflight completo.
    """
    if (not connection.in_transaction() or connection.dialect.name != "postgresql"
            or persisted_backups_reopened is not True):
        raise CombinedTransitionError("Transição conjunta bloqueada.")
    authorize_biometric_migration_write(biometric_preflight)
    try:
        if (source_cipher.environment != biometric_preflight.contexts.source.environment
                or target_cipher.environment != biometric_preflight.contexts.destination.environment
                or account_plan.fingerprint != account_backup.fingerprint
                or account_plan.account_count != account_backup.account_count):
            raise ValueError
        # Autenticar todos os pacotes antes da primeira atualização SQL.
        source, _ = open_sql_transition(biometric_archive,
            preflight=biometric_preflight, backup_key=biometric_backup_key)
        if len(source) != biometric_preflight.expected_record_count:
            raise ValueError
        _open_transition_backup(account_backup, source=source_cipher, target=target_cipher)
        with connection.begin_nested():
            channel_count = replace_channel_environment(connection, channel_source,
                source_environment=source_cipher.environment, target_environment=target_cipher.environment)
            embeddings = apply_sql_transition(connection, biometric_archive,
                preflight=biometric_preflight, backup_key=biometric_backup_key,
                persisted_archive_reopened=True)
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                financial = _execute_mercadopago_transition(session, account_plan,
                    source=source_cipher, target=target_cipher)
        return {"embedding_count": embeddings, "account_count": financial.account_count,
                "channel_count": channel_count, "account_fingerprint": financial.after_fingerprint}
    except (SQLAlchemyError, EnvironmentTransitionError, BiometricSqlError, SqlBackupError,
            ValueError, TypeError, KeyError, AttributeError):
        raise CombinedTransitionError("Transição conjunta revertida.") from None


def read_channel_snapshot(connection: Connection, *, lock: bool = False) -> tuple[dict, ...]:
    if lock:
        if connection.dialect.name != "postgresql" or not connection.in_transaction():
            raise CombinedTransitionError("Transação PostgreSQL explícita obrigatória.")
        connection.execute(text("LOCK TABLE whatsapp_channel_settings IN EXCLUSIVE MODE"))
    return tuple(dict(row) for row in connection.execute(select(
        WhatsAppChannelSettings.__table__).order_by(WhatsAppChannelSettings.id)).mappings())


def replace_channel_environment(connection: Connection, original: tuple[dict, ...], *,
                                source_environment: str, target_environment: str,
                                recovery: bool = False) -> int:
    """Muda somente o binding ambiental de linhas inteiramente inventariadas."""
    table = WhatsAppChannelSettings.__table__
    if any(set(row) != set(table.c.keys()) or row["environment"] != source_environment
           for row in original):
        raise CombinedTransitionError("Snapshot de canal divergente.")
    target = tuple({**row, "environment": target_environment} for row in original)
    expected, replacement = (target, original) if recovery else (original, target)
    if read_channel_snapshot(connection, lock=True) != expected:
        raise CombinedTransitionError("Snapshot de canal divergente.")
    for row in replacement:
        count = connection.execute(update(table).where(table.c.id == row["id"]).values(
            environment=row["environment"], updated_at=row["updated_at"])).rowcount
        if count != 1:
            raise CombinedTransitionError("Snapshot de canal divergente.")
    return len(original)


def recover_combined_transition(connection: Connection, *, biometric_archive,
    biometric_preflight, biometric_backup_key: bytes, account_backup, source_cipher,
    target_cipher, account_destination_fingerprint: str, channel_source: tuple[dict, ...],
    persisted_backups_reopened: bool) -> dict[str, int]:
    """Recupera os três conjuntos, exigindo o fingerprint financeiro autenticado do pós-write."""
    if (not connection.in_transaction() or connection.dialect.name != "postgresql"
            or persisted_backups_reopened is not True):
        raise CombinedTransitionError("Recuperação conjunta bloqueada.")
    authorize_biometric_migration_write(biometric_preflight)
    try:
        if (source_cipher.environment != biometric_preflight.contexts.source.environment
                or target_cipher.environment != biometric_preflight.contexts.destination.environment):
            raise ValueError
        _open_transition_backup(account_backup, source=source_cipher, target=target_cipher)
        with connection.begin_nested():
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                with session.begin():
                    rows = _load_accounts(session, lock=True)
                    if _account_fingerprint(rows) != account_destination_fingerprint:
                        raise ValueError
                embeddings = apply_sql_transition(connection, biometric_archive,
                    preflight=biometric_preflight, backup_key=biometric_backup_key,
                    persisted_archive_reopened=True, recovery=True)
                financial = restore_mercadopago_transition_backup(session, account_backup,
                    source=source_cipher, target=target_cipher)
            channels = replace_channel_environment(connection, channel_source,
                source_environment=source_cipher.environment, target_environment=target_cipher.environment,
                recovery=True)
        return {"embedding_count": embeddings, "account_count": financial.account_count,
                "channel_count": channels}
    except (SQLAlchemyError, EnvironmentTransitionError, BiometricSqlError, SqlBackupError,
            ValueError, TypeError, KeyError, AttributeError):
        raise CombinedTransitionError("Recuperação conjunta revertida.") from None
