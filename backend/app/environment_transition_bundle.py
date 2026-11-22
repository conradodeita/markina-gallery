"""Pacote conjunto do corte SQL; segredos e snapshots só existem dentro de AES-GCM."""

import base64
import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.app_env_transition import (
    EncryptedTransitionBackup,
    MercadoPagoTransitionPlan,
    _account_fingerprint,
    _load_accounts,
    create_encrypted_transition_backup,
    create_mercadopago_transition_plan,
)
from app.auth import (
    FacialJob,
    FacialSearchNotificationOutbox,
    FacialSearchRequest,
    PhotoFaceEmbedding,
)
from app.combined_environment_transition import (
    apply_combined_transition,
    read_channel_snapshot,
    recover_combined_transition,
)
from app.facial.environment_migration_guard import BiometricWritePreflight
from app.facial.environment_package_store import persist_encrypted_package, reopen_package
from app.facial.environment_sql import EmbeddingSnapshot, prepare_embedding_destination
from app.facial.environment_sql_backup import (
    SqlTransitionArchive,
    _decode,
    _encode,
    inspect_sql_destination,
    open_sql_transition,
    seal_sql_transition,
)


class CutoverBundleError(RuntimeError):
    pass


FINANCIAL_TABLES = (
    "sale_order", "sale_order_item", "payment_group", "provider_payment",
    "provider_payment_attempt", "provider_payment_receipt", "provider_payment_correction",
    "payment_confirmation_correction", "payment_communication", "global_pix_settings",
    "mercadopago_account", "mercadopago_payment", "mercadopago_webhook", "payment_preferences",
)


def financial_snapshot(connection: Connection) -> dict:
    """Prova privada no pacote cifrado; consulta agregada sem emitir registros financeiros."""
    result = {}
    for table in FINANCIAL_TABLES:
        # Somente nomes da allowlist constante; hashes ficam dentro do pacote cifrado.
        row = connection.execute(text(
            "SELECT count(*) AS count, md5(coalesce(string_agg(value::text, ',' ORDER BY value::text), '')) AS digest "
            "FROM (SELECT to_jsonb(t) - 'access_token_envelope' - 'webhook_secret_envelope' AS value "
            f'FROM "{table}" t) records'
        )).mappings().one()
        result[table] = dict(row)
    return result


def seal_payload(payload: dict, key: bytes, operation: str) -> dict:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(nonce, json.dumps(payload, sort_keys=True,
        allow_nan=False).encode(), ("environment-cutover-v1:" + operation).encode())
    return {"version": 1, "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode()}


def open_payload(payload: dict, key: bytes, operation: str) -> dict:
    try:
        if set(payload) != {"version", "nonce", "ciphertext"} or type(payload["version"]) is not int or payload["version"] != 1:
            raise ValueError
        result = json.loads(AESGCM(key).decrypt(base64.b64decode(payload["nonce"], validate=True),
            base64.b64decode(payload["ciphertext"], validate=True),
            ("environment-cutover-v1:" + operation).encode()))
        if not isinstance(result, dict):
            raise TypeError
        return result
    except (ValueError, TypeError, KeyError, InvalidTag):
        raise CutoverBundleError("Pacote de corte inválido.") from None


def assert_sql_only_idle(connection: Connection) -> None:
    if (connection.scalar(select(func.count()).select_from(FacialJob).where(
            FacialJob.status.in_(("queued", "processing"))))
        or connection.scalar(select(func.count()).select_from(FacialSearchRequest).where(
            FacialSearchRequest.reference_locator_ciphertext.is_not(None)))
        or connection.scalar(select(func.count()).select_from(FacialSearchNotificationOutbox).where(
            func.length(FacialSearchNotificationOutbox.payload_ciphertext) > 0))):
        raise CutoverBundleError("Armazenamento fora do plano ou jobs ativos.")


def persist_profile(connection, *, package_root, key_root, operation, continuity, inventory, plan):
    assert_sql_only_idle(connection)
    key = secrets.token_bytes(32)
    content = {"inventory": inventory, "plan": plan, "continuity": continuity}
    name = operation + "-profile"
    saved = persist_encrypted_package(package_root, key_root, name,
        encrypted_payload=seal_payload(content, key, name), backup_key=key)
    if open_payload(saved.payload, saved.key, name) != content:
        raise CutoverBundleError("Perfil de continuidade divergente.")
    return {"channels_verified": True,
            "embedding_count": connection.scalar(select(func.count()).select_from(PhotoFaceEmbedding))}


def make_preflight(contexts, *, inventory: str, plan: str, count: int,
                   app_environment: str) -> BiometricWritePreflight:
    return BiometricWritePreflight(
        contexts, inventory, inventory, inventory, True, True, count, count,
        plan, plan, True, f"APPLY_BIOMETRIC_CONTEXT:{inventory}:{plan}",
        frozenset({"api", "worker", "face-index-worker", "face-search-worker", "face-maintenance-worker"}),
        0, False, False, app_environment, app_environment, 0, 0, 0, 0,
    )


def prepare_bundle(connection: Connection, *, contexts, source_cipher, target_cipher,
                   inventory: str, plan: str, operation: str,
                   package_root: Path, key_root: Path, continuity: dict) -> dict[str, int]:
    """Requer transação externa READ ONLY e autorização operacional do conjunto."""
    if not connection.in_transaction() or connection.dialect.name != "postgresql":
        raise CutoverBundleError("Transação explícita obrigatória.")
    assert_sql_only_idle(connection)
    profile, _ = load_bundle(package_root, key_root, operation + "-profile")
    if profile != {"inventory": inventory, "plan": plan, "continuity": continuity}:
        raise CutoverBundleError("Continuidade mudou antes da preparação.")
    source = tuple(EmbeddingSnapshot(row) for row in connection.execute(
        select(PhotoFaceEmbedding.__table__).order_by(PhotoFaceEmbedding.id)).mappings())
    preflight = make_preflight(contexts, inventory=inventory, plan=plan, count=len(source),
                              app_environment=source_cipher.environment)
    destination = prepare_embedding_destination(source, contexts=contexts)
    key = secrets.token_bytes(32)
    archive = seal_sql_transition(source, destination, preflight=preflight, backup_key=key)
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        account_plan = create_mercadopago_transition_plan(session, source=source_cipher, target=target_cipher)
        account_backup = create_encrypted_transition_backup(session, account_plan,
            source=source_cipher, target=target_cipher)
    channels = read_channel_snapshot(connection)
    if any(row["environment"] != source_cipher.environment for row in channels):
        raise CutoverBundleError("Ambiente de canal fora do plano.")
    content = {"version": 1, "inventory": inventory, "plan": plan,
        "source_environment": contexts.source.environment,
        "target_environment": contexts.destination.environment,
        "count": len(source), "biometric_archive": archive.payload(),
        "account_plan": asdict(account_plan), "account_backup": account_backup.payload(),
        "channels": [{k: _encode(v) for k,v in row.items()} for row in channels],
        "prepared_at": datetime.now(UTC).isoformat(), "continuity": continuity,
        "financial_baseline": financial_snapshot(connection)}
    reopened = persist_encrypted_package(package_root, key_root, operation,
        encrypted_payload=seal_payload(content, key, operation), backup_key=key)
    if open_payload(reopened.payload, reopened.key, operation) != content:
        raise CutoverBundleError("Reabertura do pacote divergente.")
    open_sql_transition(archive, preflight=preflight, backup_key=reopened.key)
    return {"embedding_count": len(source), "account_count": account_plan.account_count,
            "channel_count": len(channels)}


def load_bundle(package_root, key_root, operation):
    reopened = reopen_package(package_root, key_root, operation)
    return open_payload(reopened.payload, reopened.key, operation), reopened.key


def bundle_arguments(content, key, *, contexts, source_cipher, target_cipher, app_environment):
    if (content["source_environment"] != contexts.source.environment
            or content["target_environment"] != contexts.destination.environment
            or source_cipher.environment != contexts.source.environment
            or target_cipher.environment != contexts.destination.environment):
        raise CutoverBundleError("Contextos do pacote divergentes.")
    return {
        "biometric_archive": SqlTransitionArchive.from_payload(content["biometric_archive"]),
        "biometric_preflight": make_preflight(contexts, inventory=content["inventory"], plan=content["plan"],
            count=content["count"], app_environment=app_environment),
        "biometric_backup_key": key, "account_plan": MercadoPagoTransitionPlan(**content["account_plan"]),
        "account_backup": EncryptedTransitionBackup.from_payload(content["account_backup"]),
        "source_cipher": source_cipher, "target_cipher": target_cipher,
        "persisted_backups_reopened": True,
        "channel_source": tuple({k: _decode(v) for k,v in row.items()} for row in content["channels"]),
    }


def apply_bundle(connection: Connection, *, package_root, key_root, operation,
                 contexts, source_cipher, target_cipher, app_environment):
    content, key = load_bundle(package_root, key_root, operation)
    assert_sql_only_idle(connection)
    arguments = bundle_arguments(content, key, contexts=contexts, source_cipher=source_cipher,
                                 target_cipher=target_cipher, app_environment=app_environment)
    with connection.begin_nested():
        if financial_snapshot(connection) != content["financial_baseline"]:
            raise CutoverBundleError("Estado financeiro mudou antes da operação.")
        result = apply_combined_transition(connection, **arguments)
        if financial_snapshot(connection) != content["financial_baseline"]:
            raise CutoverBundleError("Preservação financeira não comprovada.")
        state = {"inventory": content["inventory"], "plan": content["plan"], "result": result}
        reopened = persist_encrypted_package(package_root, key_root, operation + "-applied",
            encrypted_payload=seal_payload(state, key, operation + "-applied"), backup_key=key)
        if open_payload(reopened.payload, reopened.key, operation + "-applied") != state:
            raise CutoverBundleError("Recibo de destino inválido.")
    return {k:v for k,v in result.items() if k.endswith("_count")}


def inspect_bundle(connection: Connection, *, package_root, key_root, operation,
                   contexts, source_cipher, target_cipher, app_environment):
    content, key = load_bundle(package_root, key_root, operation)
    arguments = bundle_arguments(content, key, contexts=contexts, source_cipher=source_cipher,
                                 target_cipher=target_cipher, app_environment=app_environment)
    biometric = inspect_sql_destination(connection, arguments["biometric_archive"],
        preflight=arguments["biometric_preflight"], backup_key=key)
    with (Session(bind=connection, join_transaction_mode="create_savepoint") as session,
          session.begin()):
        current_accounts = _account_fingerprint(_load_accounts(session, lock=False))
    channels = read_channel_snapshot(connection)
    source_channels = arguments["channel_source"]
    target_channels = tuple({**row, "environment": target_cipher.environment} for row in source_channels)
    source_matches = (biometric["source_verified"] and current_accounts == arguments["account_plan"].fingerprint
                      and channels == source_channels)
    destination_matches = False
    if biometric["destination_verified"] and channels == target_channels:
        receipt, _ = load_bundle(package_root, key_root, operation + "-applied")
        if receipt["inventory"] != content["inventory"] or receipt["plan"] != content["plan"]:
            raise CutoverBundleError("Recibo não pertence ao plano.")
        destination_matches = current_accounts == receipt["result"]["account_fingerprint"]
    return {"source_verified": bool(source_matches), "destination_verified": bool(destination_matches),
            "embedding_count": biometric["record_count"]}


def recover_bundle(connection: Connection, *, package_root, key_root, operation,
                   contexts, source_cipher, target_cipher, app_environment):
    status = inspect_bundle(connection, package_root=package_root, key_root=key_root, operation=operation,
        contexts=contexts, source_cipher=source_cipher, target_cipher=target_cipher, app_environment=app_environment)
    if status["source_verified"]:
        return {"source_verified": True, "already_recovered": True}
    if not status["destination_verified"]:
        raise CutoverBundleError("Estado misto ou desconhecido; recuperação bloqueada.")
    content, key = load_bundle(package_root, key_root, operation)
    receipt, _ = load_bundle(package_root, key_root, operation + "-applied")
    arguments = bundle_arguments(content, key, contexts=contexts, source_cipher=source_cipher,
                                 target_cipher=target_cipher, app_environment=app_environment)
    arguments.pop("account_plan")
    if financial_snapshot(connection) != content["financial_baseline"]:
        raise CutoverBundleError("Estado financeiro divergente; recuperação bloqueada.")
    with connection.begin_nested():
        result = recover_combined_transition(connection, **arguments,
            account_destination_fingerprint=receipt["result"]["account_fingerprint"])
        if financial_snapshot(connection) != content["financial_baseline"]:
            raise CutoverBundleError("Preservação financeira não comprovada.")
        return result
