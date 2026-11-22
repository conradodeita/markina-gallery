"""Primitivas transacionais de preservação; sem CLI, conexão ou commit próprios."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.auth import PhotoFaceEmbedding
from app.facial.crypto import (
    FacialCryptoContextPair,
    FacialCryptoError,
    FacialEnvelope,
    FacialScope,
)

_TABLE = PhotoFaceEmbedding.__table__
_ENVELOPE_FIELDS = frozenset({"payload_ciphertext", "payload_nonce", "key_id"})


class BiometricSqlError(RuntimeError):
    """Mensagem constante; o coordenador deve descartar a transação após falha."""


@dataclass(frozen=True, repr=False)
class EmbeddingSnapshot:
    values: Mapping = field(repr=False)

    def __post_init__(self):
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def __repr__(self):
        return "EmbeddingSnapshot(<redacted>)"


def _require_transaction(connection: Connection) -> None:
    if not connection.in_transaction() or connection.dialect.name != "postgresql":
        raise BiometricSqlError("Transação PostgreSQL explícita obrigatória.")


def lock_embedding_snapshot(connection: Connection) -> tuple[EmbeddingSnapshot, ...]:
    """Bloqueia inserts/updates concorrentes; não abre payload nem emite IDs."""
    _require_transaction(connection)
    connection.execute(text("SET LOCAL lock_timeout='5s'"))
    connection.execute(text("LOCK TABLE photo_face_embedding IN EXCLUSIVE MODE"))
    return tuple(EmbeddingSnapshot(row) for row in connection.execute(
        select(_TABLE).order_by(_TABLE.c.id)
    ).mappings())


def prepare_embedding_destination(
    source: tuple[EmbeddingSnapshot, ...], *, contexts: FacialCryptoContextPair,
) -> tuple[EmbeddingSnapshot, ...]:
    """Prepara em memória; requer aprovação/backup no coordenador antes de persistir."""
    result = []
    seen = set()
    try:
        for snapshot in source:
            row = snapshot.values
            if set(row) != set(_TABLE.c.keys()) or row["id"] in seen:
                raise ValueError
            for name in ("id", "tenant_id", "parent_gallery_id", "photo_asset_id"):
                if not isinstance(row[name], UUID):
                    raise TypeError
            seen.add(row["id"])
            scope = FacialScope(
                environment=contexts.source.environment, gallery_id=row["parent_gallery_id"],
                object_kind="photo", object_id=row["photo_asset_id"], purpose="embedding",
                model_version=row["model_version"], data_version=row["quality_version"],
            )
            envelope = FacialEnvelope(row["payload_ciphertext"], row["payload_nonce"], row["key_id"])
            plaintext = contexts.source.cipher.decrypt(envelope, scope=scope)
            destination_scope = replace(scope, environment=contexts.destination.environment)
            target = contexts.destination.cipher.encrypt(plaintext, scope=destination_scope)
            if contexts.destination.cipher.decrypt(target, scope=destination_scope) != plaintext:
                raise ValueError
            del plaintext
            result.append(EmbeddingSnapshot({**row, "payload_ciphertext": target.ciphertext,
                "payload_nonce": target.nonce, "key_id": target.key_id}))
    except (FacialCryptoError, ValueError, TypeError, KeyError, AttributeError):
        raise BiometricSqlError("Preparação de envelopes indisponível.") from None
    return tuple(result)


def replace_embedding_envelopes(
    connection: Connection, *, expected: tuple[EmbeddingSnapshot, ...],
    replacement: tuple[EmbeddingSnapshot, ...],
) -> int:
    """Primitiva interna, sem autorização implícita; funciona também para recovery.

    O caller deve usar uma transação própria e abandonar toda a transação em erro.
    Não conectar a CLI/rota antes de implementar backup e aprovação do conjunto.
    """
    _require_transaction(connection)
    current = lock_embedding_snapshot(connection)
    try:
        before = {row.values["id"]: dict(row.values) for row in expected}
        after = {row.values["id"]: dict(row.values) for row in replacement}
        observed = {row.values["id"]: dict(row.values) for row in current}
        if len(before) != len(expected) or len(after) != len(replacement):
            raise ValueError
        if before != observed or before.keys() != after.keys():
            raise ValueError
        for identifier, source in before.items():
            target = after[identifier]
            if set(source) != set(target) or any(
                source[key] != target[key] for key in source.keys() - _ENVELOPE_FIELDS
            ):
                raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError):
        raise BiometricSqlError("Snapshot divergente; transição bloqueada.") from None
    # Savepoint reverte inclusive falha no meio do lote, sem confirmar a transação externa.
    try:
        with connection.begin_nested():
            for identifier, target in after.items():
                count = connection.execute(update(_TABLE).where(_TABLE.c.id == identifier).values(
                    **{key: target[key] for key in _ENVELOPE_FIELDS},
                    updated_at=target["updated_at"],
                )).rowcount
                if count != 1:
                    raise ValueError
    except (SQLAlchemyError, ValueError):
        raise BiometricSqlError("Escrita revertida; transição bloqueada.") from None
    return len(after)
