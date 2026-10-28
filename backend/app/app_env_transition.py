"""Re-cifragem transacional dos envelopes do Mercado Pago entre ambientes."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import MercadoPagoAccount
from app.environment_transition_inventory import environment_category, render_environment_inventory
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope

_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_ERROR = "Transição de ambiente indisponível; confira o inventário e o plano aprovado."
APP_ENV_CONSUMER_SERVICES = frozenset({
    "api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker",
})


class EnvironmentTransitionError(RuntimeError):
    """Falha sanitizada que nunca inclui IDs, envelopes ou texto claro."""


@dataclass(frozen=True)
class MercadoPagoTransitionPlan:
    account_count: int
    fingerprint: str
    source_category: str
    target_category: str
    _source_environment: str = field(repr=False)
    _target_environment: str = field(repr=False)


@dataclass(frozen=True)
class MercadoPagoTransitionResult:
    account_count: int
    source_category: str
    target_category: str
    before_fingerprint: str
    after_fingerprint: str


@dataclass(frozen=True)
class MercadoPagoRecoveryResult:
    account_count: int
    source_category: str
    restored_fingerprint: str
    configuration_context: RecoveredConfigurationContext = field(repr=False)


@dataclass(frozen=True)
class RecoveredConfigurationContext:
    app_environment: str = field(repr=False)
    integration_secret_environment: str = field(repr=False)
    active_key_id: str = field(repr=False)


@dataclass(frozen=True)
class EncryptedTransitionBackup:
    version: int
    key_id: str
    account_count: int
    fingerprint: str
    source_category: str
    target_category: str
    nonce: bytes = field(repr=False)
    ciphertext: bytes = field(repr=False)

    def payload(self) -> dict[str, Any]:
        """Serializa somente a cópia cifrada e metadados sanitizados."""
        return {
            "version": self.version,
            "key_id": self.key_id,
            "account_count": self.account_count,
            "fingerprint": self.fingerprint,
            "source_category": self.source_category,
            "target_category": self.target_category,
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
        }

    @classmethod
    def from_payload(cls, value: Any) -> EncryptedTransitionBackup:
        try:
            expected = {
                "version", "key_id", "account_count", "fingerprint", "source_category",
                "target_category", "nonce", "ciphertext",
            }
            if not isinstance(value, dict) or set(value) != expected:
                raise ValueError()
            if (value["version"] != 1 or type(value["account_count"]) is not int
                    or value["account_count"] < 0
                    or not isinstance(value["key_id"], str)
                    or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", value["key_id"])
                    or not isinstance(value["fingerprint"], str)
                    or not _FINGERPRINT.fullmatch(value["fingerprint"])
                    or value["source_category"] != "outro_ambiente_conhecido"
                    or value["target_category"] != "production"):
                raise ValueError()
            nonce = base64.b64decode(value["nonce"], validate=True)
            ciphertext = base64.b64decode(value["ciphertext"], validate=True)
            if len(nonce) != 12 or not ciphertext:
                raise ValueError()
            return cls(
                version=1,
                key_id=value["key_id"],
                account_count=value["account_count"],
                fingerprint=value["fingerprint"],
                source_category=value["source_category"],
                target_category=value["target_category"],
                nonce=nonce,
                ciphertext=ciphertext,
            )
        except (ValueError, TypeError, KeyError):
            raise EnvironmentTransitionError(_ERROR) from None


def _validate_contexts(source: IntegrationCipher, target: IntegrationCipher) -> None:
    source_category = environment_category(source.environment)
    target_category = environment_category(target.environment)
    if (source_category != "outro_ambiente_conhecido"
            or target_category != "production"
            or source.environment == target.environment
            or source.active_key_id != target.active_key_id
            or dict(source._keys) != dict(target._keys)):
        raise EnvironmentTransitionError(_ERROR)


def _canonical_envelope(value: Any) -> tuple[SecretEnvelope, str]:
    if not isinstance(value, dict):
        raise EnvironmentTransitionError(_ERROR)
    envelope = SecretEnvelope.from_payload(value)
    serialized = json.dumps(envelope.payload(), sort_keys=True, separators=(",", ":"))
    return envelope, hashlib.sha256(serialized.encode()).hexdigest()


def _account_metadata(account: MercadoPagoAccount) -> dict[str, Any]:
    created_at = account.created_at
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "account": str(account.id),
        "tenant": str(account.tenant_id),
        "seller": account.seller_id,
        "public_key": account.public_key,
        "test_account": account.test_account,
        "status": account.status,
        "created_at": created_at,
    }


def _fingerprint_snapshot(snapshot: list[dict[str, Any]]) -> str:
    snapshot.sort(key=lambda item: item["account"])
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _account_fingerprint(rows: list[MercadoPagoAccount]) -> str:
    snapshot = []
    for account in rows:
        _, access_digest = _canonical_envelope(account.access_token_envelope)
        _, webhook_digest = _canonical_envelope(account.webhook_secret_envelope)
        snapshot.append({
            **_account_metadata(account),
            "access_envelope_sha256": access_digest,
            "webhook_envelope_sha256": webhook_digest,
        })
    return _fingerprint_snapshot(snapshot)


def _backup_key(cipher: IntegrationCipher, key_id: str) -> bytes:
    key = cipher._keys.get(key_id)
    if key is None:
        raise EnvironmentTransitionError(_ERROR)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"markina-gallery-app-env-transition-v1",
        info=f"encrypted-backup:{key_id}".encode(),
    ).derive(key)


def _backup_aad(
    *, source_environment: str, target_environment: str, fingerprint: str,
    key_id: str, account_count: int,
) -> bytes:
    return json.dumps({
        "format": "app-env-transition-backup-v1",
        "source_environment": source_environment,
        "target_environment": target_environment,
        "fingerprint": fingerprint,
        "key_id": key_id,
        "account_count": account_count,
    }, sort_keys=True, separators=(",", ":")).encode()


def _validate_plan_contexts(
    plan: MercadoPagoTransitionPlan, source: IntegrationCipher, target: IntegrationCipher,
) -> None:
    if (not isinstance(plan, MercadoPagoTransitionPlan)
            or type(plan.account_count) is not int or plan.account_count < 0
            or not isinstance(plan.fingerprint, str) or not _FINGERPRINT.fullmatch(plan.fingerprint)
            or plan._source_environment != source.environment
            or plan._target_environment != target.environment):
        raise EnvironmentTransitionError(_ERROR)
    _validate_contexts(source, target)


def create_encrypted_transition_backup(
    session: Session,
    plan: MercadoPagoTransitionPlan,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
) -> EncryptedTransitionBackup:
    """Cria backup autenticado e cifrado, sem persistir conteúdo em claro."""
    if session.in_transaction():
        raise EnvironmentTransitionError(_ERROR)
    _validate_plan_contexts(plan, source, target)
    try:
        with session.begin():
            rows = _load_accounts(session, lock=False)
            _verify_envelopes(rows, source)
            if len(rows) != plan.account_count or _account_fingerprint(rows) != plan.fingerprint:
                raise EnvironmentTransitionError(_ERROR)
            accounts = []
            for account in rows:
                accounts.append({
                    "metadata": _account_metadata(account),
                    "access_token_envelope": account.access_token_envelope,
                    "webhook_secret_envelope": account.webhook_secret_envelope,
                })
            clear_archive = json.dumps({
                "version": 1,
                "fingerprint": plan.fingerprint,
                "source_environment": source.environment,
                "target_environment": target.environment,
                "configuration_context": {
                    "app_environment": source.environment,
                    "integration_secret_environment": source.environment,
                    "active_key_id": source.active_key_id,
                },
                "accounts": accounts,
            }, sort_keys=True, separators=(",", ":")).encode()
            key_id = source.active_key_id
            nonce = secrets.token_bytes(12)
            ciphertext = AESGCM(_backup_key(source, key_id)).encrypt(
                nonce, clear_archive, _backup_aad(
                    source_environment=source.environment,
                    target_environment=target.environment,
                    fingerprint=plan.fingerprint,
                    key_id=key_id,
                    account_count=plan.account_count,
                ),
            )
    except EnvironmentTransitionError:
        raise
    except (SQLAlchemyError, IntegrationSecretError, AttributeError, TypeError, ValueError, KeyError):
        raise EnvironmentTransitionError(_ERROR) from None
    return EncryptedTransitionBackup(
        version=1,
        key_id=key_id,
        account_count=plan.account_count,
        fingerprint=plan.fingerprint,
        source_category=plan.source_category,
        target_category=plan.target_category,
        nonce=nonce,
        ciphertext=ciphertext,
    )


def _open_transition_backup(
    backup: EncryptedTransitionBackup,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
 ) -> tuple[list[dict[str, Any]], RecoveredConfigurationContext]:
    backup = EncryptedTransitionBackup.from_payload(backup.payload())
    _validate_contexts(source, target)
    try:
        if (backup.source_category != environment_category(source.environment)
                or backup.target_category != environment_category(target.environment)):
            raise ValueError()
        aad = _backup_aad(
            source_environment=source.environment,
            target_environment=target.environment,
            fingerprint=backup.fingerprint,
            key_id=backup.key_id,
            account_count=backup.account_count,
        )
        clear_archive = AESGCM(_backup_key(source, backup.key_id)).decrypt(
            backup.nonce, backup.ciphertext, aad)
        archive = json.loads(clear_archive)
        if (not isinstance(archive, dict)
                or set(archive) != {"version", "fingerprint", "source_environment",
                                    "target_environment", "configuration_context", "accounts"}
                or archive["version"] != 1
                or archive["fingerprint"] != backup.fingerprint
                or archive["source_environment"] != source.environment
                or archive["target_environment"] != target.environment
                or not isinstance(archive["configuration_context"], dict)
                or set(archive["configuration_context"]) != {
                    "app_environment", "integration_secret_environment", "active_key_id"}
                or archive["configuration_context"]["app_environment"] != source.environment
                or archive["configuration_context"]["integration_secret_environment"] != source.environment
                or archive["configuration_context"]["active_key_id"] != backup.key_id
                or not isinstance(archive["accounts"], list)
                or len(archive["accounts"]) != backup.account_count):
            raise ValueError()
        accounts = archive["accounts"]
        expected_snapshot = []
        seen_ids: set[str] = set()
        for item in accounts:
            if (not isinstance(item, dict)
                    or set(item) != {"metadata", "access_token_envelope", "webhook_secret_envelope"}
                    or not isinstance(item["metadata"], dict)
                    or set(item["metadata"]) != {"account", "tenant", "seller", "public_key",
                                                  "test_account", "status", "created_at"}):
                raise ValueError()
            metadata = item["metadata"]
            account_id = UUID(metadata["account"])
            tenant_id = UUID(metadata["tenant"])
            if str(account_id) in seen_ids:
                raise ValueError()
            seen_ids.add(str(account_id))
            access, access_digest = _canonical_envelope(item["access_token_envelope"])
            webhook, webhook_digest = _canonical_envelope(item["webhook_secret_envelope"])
            source.decrypt(access, tenant_id=tenant_id, credential_id=account_id)
            source.decrypt(webhook, tenant_id=tenant_id, credential_id=account_id)
            expected_snapshot.append({
                **metadata,
                "access_envelope_sha256": access_digest,
                "webhook_envelope_sha256": webhook_digest,
            })
        if _fingerprint_snapshot(expected_snapshot) != backup.fingerprint:
            raise ValueError()
        return accounts, RecoveredConfigurationContext(
            app_environment=archive["configuration_context"]["app_environment"],
            integration_secret_environment=archive["configuration_context"][
                "integration_secret_environment"],
            active_key_id=archive["configuration_context"]["active_key_id"],
        )
    except (InvalidTag, IntegrationSecretError, EnvironmentTransitionError,
            KeyError, TypeError, ValueError, AttributeError):
        raise EnvironmentTransitionError(_ERROR) from None


def _load_accounts(session: Session, *, lock: bool) -> list[MercadoPagoAccount]:
    if lock and session.bind is not None and session.bind.dialect.name == "postgresql":
        # Also blocks concurrent inserts, which row locks alone do not prevent.
        dialect = session.bind.dialect
        schema_map = session.bind.get_execution_options().get("schema_translate_map", {})
        schema = schema_map.get(None) if isinstance(schema_map, Mapping) else None
        table_name = dialect.identifier_preparer.quote(MercadoPagoAccount.__tablename__)
        if schema is not None:
            if not isinstance(schema, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema):
                raise EnvironmentTransitionError(_ERROR)
            table_name = f"{dialect.identifier_preparer.quote_schema(schema)}.{table_name}"
        session.execute(text(f"LOCK TABLE {table_name} IN SHARE ROW EXCLUSIVE MODE"))
    statement = select(MercadoPagoAccount).order_by(MercadoPagoAccount.id)
    if lock:
        statement = statement.with_for_update()
    return list(session.scalars(statement.execution_options(populate_existing=True)).all())


def _verify_envelopes(rows: list[MercadoPagoAccount], cipher: IntegrationCipher) -> None:
    try:
        for account in rows:
            access, _ = _canonical_envelope(account.access_token_envelope)
            webhook, _ = _canonical_envelope(account.webhook_secret_envelope)
            cipher.decrypt(access, tenant_id=account.tenant_id, credential_id=account.id)
            cipher.decrypt(webhook, tenant_id=account.tenant_id, credential_id=account.id)
    except (EnvironmentTransitionError, IntegrationSecretError, AttributeError, TypeError, ValueError):
        raise EnvironmentTransitionError(_ERROR) from None


def create_mercadopago_transition_plan(
    session: Session,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
) -> MercadoPagoTransitionPlan:
    """Produz fingerprint de envelopes válidos, sem persistir texto claro."""
    if session.in_transaction():
        raise EnvironmentTransitionError(_ERROR)
    _validate_contexts(source, target)
    try:
        with session.begin():
            rows = _load_accounts(session, lock=False)
            _verify_envelopes(rows, source)
            fingerprint = _account_fingerprint(rows)
            count = len(rows)
    except EnvironmentTransitionError:
        raise
    except (SQLAlchemyError, IntegrationSecretError, AttributeError, TypeError, ValueError, KeyError):
        raise EnvironmentTransitionError(_ERROR) from None
    return MercadoPagoTransitionPlan(
        account_count=count,
        fingerprint=fingerprint,
        source_category=environment_category(source.environment),
        target_category=environment_category(target.environment),
        _source_environment=source.environment,
        _target_environment=target.environment,
    )


def _execute_mercadopago_transition(
    session: Session,
    plan: MercadoPagoTransitionPlan,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
) -> MercadoPagoTransitionResult:
    """Aplica os dois envelopes por conta numa transação indivisível."""
    if (session.in_transaction()
            or not isinstance(plan, MercadoPagoTransitionPlan)
            or type(plan.account_count) is not int or plan.account_count < 0
            or not isinstance(plan.fingerprint, str) or not _FINGERPRINT.fullmatch(plan.fingerprint)
            or plan._source_environment != source.environment
            or plan._target_environment != target.environment):
        raise EnvironmentTransitionError(_ERROR)
    _validate_contexts(source, target)

    try:
        with session.begin():
            rows = _load_accounts(session, lock=True)
            _verify_envelopes(rows, source)
            current_fingerprint = _account_fingerprint(rows)
            if len(rows) != plan.account_count or current_fingerprint != plan.fingerprint:
                raise EnvironmentTransitionError(_ERROR)

            for account in rows:
                access, _ = _canonical_envelope(account.access_token_envelope)
                webhook, _ = _canonical_envelope(account.webhook_secret_envelope)
                access_value = source.decrypt(
                    access, tenant_id=account.tenant_id, credential_id=account.id)
                webhook_value = source.decrypt(
                    webhook, tenant_id=account.tenant_id, credential_id=account.id)
                new_access = target.encrypt(
                    access_value, tenant_id=account.tenant_id, credential_id=account.id)
                new_webhook = target.encrypt(
                    webhook_value, tenant_id=account.tenant_id, credential_id=account.id)
                if (target.decrypt(new_access, tenant_id=account.tenant_id,
                                   credential_id=account.id) != access_value
                        or target.decrypt(new_webhook, tenant_id=account.tenant_id,
                                          credential_id=account.id) != webhook_value):
                    raise EnvironmentTransitionError(_ERROR)
                result = session.execute(
                    update(MercadoPagoAccount)
                    .where(MercadoPagoAccount.id == account.id,
                           MercadoPagoAccount.tenant_id == account.tenant_id)
                    .values(
                        access_token_envelope=new_access.payload(),
                        webhook_secret_envelope=new_webhook.payload(),
                    )
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != 1:
                    raise EnvironmentTransitionError(_ERROR)

            session.flush()
            updated = _load_accounts(session, lock=False)
            _verify_envelopes(updated, target)
            after_fingerprint = _account_fingerprint(updated)
            if len(updated) != plan.account_count:
                raise EnvironmentTransitionError(_ERROR)
    except EnvironmentTransitionError:
        raise
    except (SQLAlchemyError, IntegrationSecretError, AttributeError, TypeError, ValueError, KeyError):
        raise EnvironmentTransitionError(_ERROR) from None

    return MercadoPagoTransitionResult(
        account_count=plan.account_count,
        source_category=plan.source_category,
        target_category=plan.target_category,
        before_fingerprint=plan.fingerprint,
        after_fingerprint=after_fingerprint,
    )


def execute_approved_mercadopago_transition(
    session: Session,
    plan: MercadoPagoTransitionPlan,
    backup: EncryptedTransitionBackup,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
    inventory: dict[str, Any],
    approved_inventory_fingerprint: str,
    operator_confirmation: str,
    paused_consumers: set[str] | frozenset[str],
    backup_storage_verified: bool,
) -> MercadoPagoTransitionResult:
    """Gate operacional: inventory, backup e confirmações antes da mutação."""
    try:
        if session.in_transaction():
            raise EnvironmentTransitionError(_ERROR)
        _validate_plan_contexts(plan, source, target)
        serialized_inventory = render_environment_inventory(inventory)
        parsed_inventory = json.loads(serialized_inventory)
        inventory_fingerprint = parsed_inventory["approval_fingerprint"]
        if (not isinstance(approved_inventory_fingerprint, str)
                or not _FINGERPRINT.fullmatch(approved_inventory_fingerprint)
                or inventory_fingerprint != approved_inventory_fingerprint
                or parsed_inventory["blockers"]
                or parsed_inventory["target_environment_category"] != "production"
                or parsed_inventory["live_payment_gate_closed"] is not True
                or any(value != 0 for value in parsed_inventory["biometric_counts"].values())
                or any(value == "nao_classificado"
                       for value in parsed_inventory["integration_states"].values())
                or parsed_inventory["credential_counts"]["mercadopago_access_token"]
                != plan.account_count
                or parsed_inventory["credential_counts"]["mercadopago_webhook_secret"]
                != plan.account_count
                or paused_consumers != APP_ENV_CONSUMER_SERVICES
                or backup_storage_verified is not True
                or not isinstance(operator_confirmation, str)
                or operator_confirmation != (
                    f"APLICAR_TRANSICAO_APP_ENV:{inventory_fingerprint}:{plan.fingerprint}")):
            raise EnvironmentTransitionError(_ERROR)
        _open_transition_backup(backup, source=source, target=target)
        if backup.fingerprint != plan.fingerprint or backup.account_count != plan.account_count:
            raise EnvironmentTransitionError(_ERROR)
        return _execute_mercadopago_transition(session, plan, source=source, target=target)
    except (EnvironmentTransitionError, SQLAlchemyError, TypeError, ValueError, KeyError):
        raise EnvironmentTransitionError(_ERROR) from None


def restore_mercadopago_transition_backup(
    session: Session,
    backup: EncryptedTransitionBackup,
    *,
    source: IntegrationCipher,
    target: IntegrationCipher,
) -> MercadoPagoRecoveryResult:
    """Restaura envelopes de origem do backup autenticado em uma transação única.

    A configuração dos processos e os consumidores externos continuam
    sendo recuperada pelo procedimento operacional; esta função não altera env.
    """
    if session.in_transaction():
        raise EnvironmentTransitionError(_ERROR)
    accounts, configuration_context = _open_transition_backup(
        backup, source=source, target=target)
    saved = {item["metadata"]["account"]: item for item in accounts}
    try:
        with session.begin():
            current = _load_accounts(session, lock=True)
            if len(current) != backup.account_count:
                raise EnvironmentTransitionError(_ERROR)
            current_by_id = {str(account.id): account for account in current}
            if set(current_by_id) != set(saved):
                raise EnvironmentTransitionError(_ERROR)
            for account_id, account in current_by_id.items():
                if _account_metadata(account) != saved[account_id]["metadata"]:
                    raise EnvironmentTransitionError(_ERROR)
            for account_id, account in current_by_id.items():
                item = saved[account_id]
                result = session.execute(
                    update(MercadoPagoAccount)
                    .where(MercadoPagoAccount.id == account.id,
                           MercadoPagoAccount.tenant_id == account.tenant_id)
                    .values(
                        access_token_envelope=item["access_token_envelope"],
                        webhook_secret_envelope=item["webhook_secret_envelope"],
                    )
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != 1:
                    raise EnvironmentTransitionError(_ERROR)
            session.flush()
            restored = _load_accounts(session, lock=False)
            _verify_envelopes(restored, source)
            restored_fingerprint = _account_fingerprint(restored)
            if (len(restored) != backup.account_count
                    or restored_fingerprint != backup.fingerprint):
                raise EnvironmentTransitionError(_ERROR)
    except EnvironmentTransitionError:
        raise
    except (SQLAlchemyError, IntegrationSecretError, AttributeError, TypeError, ValueError, KeyError):
        raise EnvironmentTransitionError(_ERROR) from None
    return MercadoPagoRecoveryResult(
        account_count=backup.account_count,
        source_category=backup.source_category,
        restored_fingerprint=restored_fingerprint,
        configuration_context=configuration_context,
    )
