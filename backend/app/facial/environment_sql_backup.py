"""Pacote SQL autenticado; nenhuma rotina de persistência operacional ou CLI."""

import base64
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.auth import PhotoFaceEmbedding
from app.facial.crypto import FacialCryptoError, FacialEnvelope, FacialScope
from app.facial.environment_migration_guard import (
    BiometricWritePreflight,
    authorize_biometric_migration_write,
)
from app.facial.environment_sql import EmbeddingSnapshot, replace_embedding_envelopes

_FIELDS = set(PhotoFaceEmbedding.__table__.c.keys())
_ENVELOPES = {"payload_ciphertext", "payload_nonce", "key_id"}
_FP = re.compile(r"[0-9a-f]{64}\Z")


class SqlBackupError(RuntimeError):
    """É seguro registrar apenas a mensagem constante deste erro."""


@dataclass(frozen=True, repr=False)
class SqlTransitionArchive:
    nonce: bytes
    ciphertext: bytes

    def __repr__(self):
        return "SqlTransitionArchive(<redacted>)"

    def payload(self) -> dict:
        return {"version": 1, "nonce": base64.b64encode(self.nonce).decode("ascii"),
                "ciphertext": base64.b64encode(self.ciphertext).decode("ascii")}

    @classmethod
    def from_payload(cls, value):
        try:
            if (not isinstance(value, dict) or set(value) != {"version", "nonce", "ciphertext"}
                    or type(value["version"]) is not int or value["version"] != 1):
                raise ValueError
            nonce = base64.b64decode(value["nonce"], validate=True)
            ciphertext = base64.b64decode(value["ciphertext"], validate=True)
            if len(nonce) != 12 or len(ciphertext) < 17:
                raise ValueError
            return cls(nonce, ciphertext)
        except (ValueError, TypeError, KeyError):
            raise SqlBackupError("Pacote SQL inválido.") from None


def _aad(preflight: BiometricWritePreflight) -> bytes:
    inventory = preflight.current_inventory_fingerprint
    plan = preflight.operation_plan_fingerprint
    if not isinstance(inventory, str) or not _FP.fullmatch(inventory):
        raise SqlBackupError("Pacote SQL inválido.")
    if not isinstance(plan, str) or not _FP.fullmatch(plan):
        raise SqlBackupError("Pacote SQL inválido.")
    return json.dumps({"domain": "biometric-sql-preservation-v1", "inventory": inventory,
        "plan": plan, "source": preflight.contexts.source.environment,
        "target": preflight.contexts.destination.environment}, sort_keys=True).encode()


def _encode(value):
    if value is None or type(value) in {str, int, float, bool}:
        return ["scalar", value]
    if isinstance(value, UUID):
        return ["uuid", str(value)]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, bytes):
        return ["bytes", base64.b64encode(value).decode("ascii")]
    raise ValueError


def _decode(item):
    if not isinstance(item, list) or len(item) != 2:
        raise ValueError
    kind, value = item
    if kind == "scalar" and (value is None or type(value) in {str, int, float, bool}):
        return value
    if not isinstance(value, str):
        raise TypeError
    if kind == "uuid":
        return UUID(value)
    if kind == "datetime":
        return datetime.fromisoformat(value)
    if kind == "bytes":
        return base64.b64decode(value, validate=True)
    raise ValueError


def _validate_pair(source, target, preflight):
    before = {row.values["id"]: row for row in source}
    after = {row.values["id"]: row for row in target}
    if (len(before) != len(source) or len(after) != len(target)
            or before.keys() != after.keys()):
        raise ValueError
    for identifier, snapshot in before.items():
        left, right = snapshot.values, after[identifier].values
        if set(left) != _FIELDS or set(right) != _FIELDS:
            raise ValueError
        if any(left[k] != right[k] for k in _FIELDS - _ENVELOPES):
            raise ValueError
        clear = []
        for row, context in ((left, preflight.contexts.source),
                             (right, preflight.contexts.destination)):
            scope = FacialScope(context.environment, row["parent_gallery_id"], "photo",
                row["photo_asset_id"], "embedding", row["model_version"], row["quality_version"])
            clear.append(context.cipher.decrypt(FacialEnvelope(
                row["payload_ciphertext"], row["payload_nonce"], row["key_id"]), scope=scope))
        if clear[0] != clear[1]:
            raise ValueError
        del clear


def seal_sql_transition(source, target, *, preflight, backup_key: bytes) -> SqlTransitionArchive:
    try:
        if not isinstance(backup_key, bytes) or len(backup_key) != 32:
            raise ValueError
        _validate_pair(source, target, preflight)
        payload = {name: [{key: _encode(value) for key, value in row.values.items()}
                         for row in rows] for name, rows in (("source", source), ("target", target))}
        nonce = secrets.token_bytes(12)
        encrypted = AESGCM(backup_key).encrypt(nonce, json.dumps(
            payload, sort_keys=True, allow_nan=False).encode(), _aad(preflight))
        return SqlTransitionArchive(nonce, encrypted)
    except (ValueError, TypeError, KeyError, AttributeError, FacialCryptoError):
        raise SqlBackupError("Pacote SQL inválido.") from None


def _open_sql_archive(archive, *, preflight, backup_key: bytes):
    try:
        if not isinstance(backup_key, bytes) or len(backup_key) != 32:
            raise ValueError
        payload = json.loads(AESGCM(backup_key).decrypt(
            archive.nonce, archive.ciphertext, _aad(preflight)))
        if not isinstance(payload, dict) or set(payload) != {"source", "target"}:
            raise ValueError
        batches = []
        for name in ("source", "target"):
            if not isinstance(payload[name], list):
                raise TypeError
            rows = []
            for row in payload[name]:
                if not isinstance(row, dict) or set(row) != _FIELDS:
                    raise ValueError
                rows.append(EmbeddingSnapshot({key: _decode(value) for key, value in row.items()}))
            batches.append(tuple(rows))
        return tuple(batches)
    except (ValueError, TypeError, KeyError, AttributeError, FacialCryptoError, InvalidTag):
        raise SqlBackupError("Pacote SQL inválido.") from None


def open_sql_transition(archive, *, preflight, backup_key: bytes):
    batches = _open_sql_archive(archive, preflight=preflight, backup_key=backup_key)
    try:
        _validate_pair(*batches, preflight)
    except (ValueError, TypeError, KeyError, AttributeError, FacialCryptoError):
        raise SqlBackupError("Pacote SQL inválido.") from None
    return batches


def inspect_sql_destination(connection: Connection, archive, *, preflight,
                            backup_key: bytes) -> dict[str, int | bool]:
    """Compara snapshots com pacote autenticado sem decifrar o payload biométrico.

    O caller deve usar uma transação READ ONLY consistente. Não libera a troca global de ambiente.
    Autenticidade do pacote e igualdade completa das linhas são ambas obrigatórias.
    """
    if not connection.in_transaction():
        raise SqlBackupError("Transação explícita obrigatória.")
    source, target = _open_sql_archive(archive, preflight=preflight, backup_key=backup_key)
    try:
        before = {row.values["id"]: dict(row.values) for row in source}
        after = {row.values["id"]: dict(row.values) for row in target}
        if (len(before) != len(source) or len(after) != len(target)
                or before.keys() != after.keys()
                or len(after) != preflight.expected_record_count):
            raise ValueError
        if any(set(row) != _FIELDS for row in (*before.values(), *after.values())):
            raise ValueError
        if any(before[k][f] != after[k][f] for k in before for f in _FIELDS - _ENVELOPES):
            raise ValueError
        current = {row["id"]: dict(row) for row in connection.execute(
            select(PhotoFaceEmbedding.__table__)).mappings()}
    except (ValueError, TypeError, KeyError, AttributeError):
        raise SqlBackupError("Prova do conjunto inválida.") from None
    return {"record_count": len(current), "destination_verified": current == after,
            "source_verified": current == before}


def apply_sql_transition(connection: Connection, archive: SqlTransitionArchive, *,
                         preflight: BiometricWritePreflight, backup_key: bytes,
                         persisted_archive_reopened: bool, recovery: bool = False) -> int:
    """Não confirma transação nem altera configuração; exige guarda e pacote válido."""
    authorize_biometric_migration_write(preflight)
    if persisted_archive_reopened is not True or type(recovery) is not bool:
        raise SqlBackupError("Pacote persistido não verificado.")
    source, target = open_sql_transition(archive, preflight=preflight, backup_key=backup_key)
    if len(source) != preflight.expected_record_count:
        raise SqlBackupError("Contagem do pacote divergente.")
    return replace_embedding_envelopes(connection, expected=target if recovery else source,
                                      replacement=source if recovery else target)
