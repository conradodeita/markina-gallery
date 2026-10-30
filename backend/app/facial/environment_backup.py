"""Backup autenticado de snapshots cifrados; não acessa storage operacional."""

from __future__ import annotations

import base64
import json
import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.facial.crypto import (
    FacialCryptoContextPair,
    FacialCryptoError,
    FacialEnvelope,
    FacialScope,
)
from app.facial.environment_eligibility import BiometricEligibilityEvidence
from app.facial.environment_migration import BiometricCiphertextRecord

_KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,48}\Z")
_BACKUP_ERROR = "Backup biométrico indisponível ou inválido."
_EVIDENCE_FIELDS = {item.name for item in fields(BiometricEligibilityEvidence)}
_SCOPE_FIELDS = {
    "environment",
    "gallery_id",
    "object_kind",
    "object_id",
    "purpose",
    "model_version",
    "data_version",
}


class FacialBackupError(RuntimeError):
    """Falha de backup sem expor chave, ciphertext ou metadado de cliente."""


@dataclass(frozen=True, slots=True, repr=False)
class EncryptedBiometricBackup:
    version: int
    key_id: str
    record_count: int
    nonce: bytes
    ciphertext: bytes

    def __repr__(self) -> str:
        return "EncryptedBiometricBackup(<redacted>)"

    def payload(self) -> dict[str, Any]:
        """Retorna envelope cifrado e contagem agregada, sem identificadores."""

        return {
            "version": self.version,
            "key_id": self.key_id,
            "record_count": self.record_count,
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
        }

    @classmethod
    def from_payload(cls, value: Any) -> EncryptedBiometricBackup:
        try:
            if not isinstance(value, dict) or set(value) != {
                "version",
                "key_id",
                "record_count",
                "nonce",
                "ciphertext",
            }:
                raise ValueError
            if (
                value["version"] != 1
                or type(value["record_count"]) is not int
                or value["record_count"] < 0
                or not isinstance(value["key_id"], str)
                or not _KEY_ID.fullmatch(value["key_id"])
                or not isinstance(value["nonce"], str)
                or not isinstance(value["ciphertext"], str)
            ):
                raise ValueError
            nonce = base64.b64decode(value["nonce"], validate=True)
            ciphertext = base64.b64decode(value["ciphertext"], validate=True)
            if len(nonce) != 12 or not ciphertext:
                raise ValueError
            return cls(1, value["key_id"], value["record_count"], nonce, ciphertext)
        except (ValueError, TypeError, KeyError):
            raise FacialBackupError(_BACKUP_ERROR) from None


def create_encrypted_biometric_backup(
    records: Sequence[BiometricCiphertextRecord],
    *,
    contexts: FacialCryptoContextPair,
    key_id: str,
    backup_key: bytes,
) -> EncryptedBiometricBackup:
    """Cifra snapshots de origem; não grava arquivos nem abre ciphertexts internos."""

    if (
        not isinstance(contexts, FacialCryptoContextPair)
        or not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or not isinstance(key_id, str)
        or not _KEY_ID.fullmatch(key_id)
        or not isinstance(backup_key, bytes)
        or len(backup_key) != 32
    ):
        raise FacialBackupError(_BACKUP_ERROR)
    try:
        snapshots = []
        for record in records:
            if (
                not isinstance(record, BiometricCiphertextRecord)
                or record.scope.environment != contexts.source.environment
            ):
                raise ValueError
            _validate_record(record, contexts.source.environment)
            snapshots.append(_record_payload(record))
        archive = {
            "version": 1,
            "source_environment": contexts.source.environment,
            "target_environment": contexts.destination.environment,
            "records": snapshots,
        }
        clear_archive = json.dumps(
            archive, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(backup_key).encrypt(
            nonce,
            clear_archive,
            _aad(
                source_environment=contexts.source.environment,
                target_environment=contexts.destination.environment,
                key_id=key_id,
                record_count=len(snapshots),
            ),
        )
    except (FacialCryptoError, TypeError, ValueError, AttributeError):
        raise FacialBackupError(_BACKUP_ERROR) from None
    return EncryptedBiometricBackup(
        version=1,
        key_id=key_id,
        record_count=len(snapshots),
        nonce=nonce,
        ciphertext=ciphertext,
    )


def restore_encrypted_biometric_backup(
    backup: EncryptedBiometricBackup,
    *,
    contexts: FacialCryptoContextPair,
    key_id: str,
    backup_key: bytes,
) -> tuple[BiometricCiphertextRecord, ...]:
    """Autentica e reconstrói todos os snapshots em memória antes de qualquer caller gravar."""

    try:
        if (
            not isinstance(backup, EncryptedBiometricBackup)
            or not isinstance(contexts, FacialCryptoContextPair)
            or type(backup.version) is not int
            or backup.version != 1
            or backup.key_id != key_id
            or not isinstance(key_id, str)
            or not _KEY_ID.fullmatch(key_id)
            or type(backup.record_count) is not int
            or backup.record_count < 0
            or not isinstance(backup_key, bytes)
            or len(backup_key) != 32
            or len(backup.nonce) != 12
            or not backup.ciphertext
        ):
            raise ValueError
        clear_archive = AESGCM(backup_key).decrypt(
            backup.nonce,
            backup.ciphertext,
            _aad(
                source_environment=contexts.source.environment,
                target_environment=contexts.destination.environment,
                key_id=key_id,
                record_count=backup.record_count,
            ),
        )
        archive = json.loads(clear_archive)
        if (
            not isinstance(archive, dict)
            or set(archive)
            != {"version", "source_environment", "target_environment", "records"}
            or archive["version"] != 1
            or archive["source_environment"] != contexts.source.environment
            or archive["target_environment"] != contexts.destination.environment
            or not isinstance(archive["records"], list)
            or len(archive["records"]) != backup.record_count
        ):
            raise ValueError
        records = tuple(_record_from_payload(item) for item in archive["records"])
        for record in records:
            _validate_record(record, contexts.source.environment)
        return records
    except (
        FacialCryptoError,
        InvalidTag,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        UnicodeError,
    ):
        raise FacialBackupError(_BACKUP_ERROR) from None


def _aad(
    *, source_environment: str, target_environment: str, key_id: str, record_count: int
) -> bytes:
    return json.dumps(
        {
            "format": "biometric-transition-backup-v1",
            "source_environment": source_environment,
            "target_environment": target_environment,
            "key_id": key_id,
            "record_count": record_count,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _record_payload(record: BiometricCiphertextRecord) -> dict[str, Any]:
    return {
        "tenant_id": str(record.tenant_id),
        "gallery_id": str(record.gallery_id),
        "client_id": str(record.client_id) if record.client_id else None,
        "object_id": str(record.object_id),
        "scope": {
            "environment": record.scope.environment,
            "gallery_id": str(record.scope.gallery_id),
            "object_kind": record.scope.object_kind,
            "object_id": str(record.scope.object_id),
            "purpose": record.scope.purpose,
            "model_version": record.scope.model_version,
            "data_version": record.scope.data_version,
        },
        "envelope": {
            "ciphertext": base64.b64encode(record.envelope.ciphertext).decode("ascii"),
            "nonce": base64.b64encode(record.envelope.nonce).decode("ascii"),
            "key_id": record.envelope.key_id,
            "version": record.envelope.version,
        },
        "evidence": {
            item.name: _json_value(getattr(record.evidence, item.name))
            for item in fields(BiometricEligibilityEvidence)
        },
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if value is None or type(value) in {bool, str}:
        return value
    raise ValueError


def _record_from_payload(value: Any) -> BiometricCiphertextRecord:
    if not isinstance(value, dict) or set(value) != {
        "tenant_id",
        "gallery_id",
        "client_id",
        "object_id",
        "scope",
        "envelope",
        "evidence",
        "created_at",
        "updated_at",
    }:
        raise ValueError
    scope = value["scope"]
    envelope = value["envelope"]
    evidence = value["evidence"]
    if (
        not isinstance(scope, dict)
        or set(scope) != _SCOPE_FIELDS
        or not isinstance(envelope, dict)
        or set(envelope) != {"ciphertext", "nonce", "key_id", "version"}
        or not isinstance(evidence, dict)
        or set(evidence) != _EVIDENCE_FIELDS
    ):
        raise ValueError

    evidence_values = {
        name: _from_json_value(name, item) for name, item in evidence.items()
    }
    scope_object = FacialScope(
        environment=_string(scope["environment"]),
        gallery_id=UUID(_string(scope["gallery_id"])),
        object_kind=_string(scope["object_kind"]),
        object_id=UUID(_string(scope["object_id"])),
        purpose=_string(scope["purpose"]),
        model_version=_string(scope["model_version"]),
        data_version=_string(scope["data_version"]),
    )
    encoded_ciphertext = base64.b64decode(_string(envelope["ciphertext"]), validate=True)
    encoded_nonce = base64.b64decode(_string(envelope["nonce"]), validate=True)
    if not encoded_ciphertext or len(encoded_nonce) != 12:
        raise ValueError
    envelope_object = FacialEnvelope(
        ciphertext=encoded_ciphertext,
        nonce=encoded_nonce,
        key_id=_string(envelope["key_id"]),
        version=envelope["version"],
    )
    return BiometricCiphertextRecord(
        tenant_id=UUID(_string(value["tenant_id"])),
        gallery_id=UUID(_string(value["gallery_id"])),
        client_id=UUID(_string(value["client_id"])) if value["client_id"] else None,
        object_id=UUID(_string(value["object_id"])),
        scope=scope_object,
        envelope=envelope_object,
        evidence=BiometricEligibilityEvidence(**evidence_values),
        created_at=datetime.fromisoformat(_string(value["created_at"])),
        updated_at=datetime.fromisoformat(_string(value["updated_at"])),
    )


def _from_json_value(name: str, value: Any) -> Any:
    if name in {"expires_at", "reference_deleted_at"}:
        if value is None:
            return None
        if not isinstance(value, dict) or set(value) != {"datetime"}:
            raise ValueError
        return datetime.fromisoformat(_string(value["datetime"]))
    if value is None or type(value) in {bool, str}:
        return value
    raise ValueError


def _string(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError
    return value


def _validate_record(record: BiometricCiphertextRecord, source_environment: str) -> None:
    if (
        not isinstance(record.tenant_id, UUID)
        or not isinstance(record.gallery_id, UUID)
        or (record.client_id is not None and not isinstance(record.client_id, UUID))
        or not isinstance(record.object_id, UUID)
        or not isinstance(record.scope, FacialScope)
        or not isinstance(record.envelope, FacialEnvelope)
        or not isinstance(record.evidence, BiometricEligibilityEvidence)
        or not isinstance(record.created_at, datetime)
        or not isinstance(record.updated_at, datetime)
        or record.scope.environment != source_environment
        or record.scope.gallery_id != record.gallery_id
        or record.scope.object_id != record.object_id
        or not isinstance(record.envelope.ciphertext, bytes)
        or not record.envelope.ciphertext
        or not isinstance(record.envelope.nonce, bytes)
        or len(record.envelope.nonce) != 12
        or type(record.envelope.version) is not int
        or not isinstance(record.envelope.key_id, str)
        or not record.envelope.key_id
        or record.scope.object_kind not in {"photo", "request"}
        or record.scope.purpose
        not in {"embedding", "reference_image", "reference_locator", "notification"}
    ):
        raise ValueError
    for item in fields(BiometricEligibilityEvidence):
        evidence_value = getattr(record.evidence, item.name)
        if item.name in {
            "source_context_confirmed",
            "privacy_scope_approved",
            "target_authorized",
            "tenant_context_valid",
            "payload_present",
            "record_authorization_verified",
            "record_retention_verified",
        }:
            if type(evidence_value) is not bool:
                raise ValueError
        elif item.name in {"expires_at", "reference_deleted_at"}:
            if evidence_value is not None and not isinstance(evidence_value, datetime):
                raise ValueError
        elif evidence_value is not None and not isinstance(evidence_value, str):
            raise ValueError
    record.scope.additional_authenticated_data(
        envelope_version=record.envelope.version
    )
