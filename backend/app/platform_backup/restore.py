"""Recuperação global autenticada; configuração recuperada não é aplicada."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import BinaryIO, Protocol
from uuid import UUID

from .archive import (
    ArchiveReceipt,
    BackupContext,
    _key,
    _local_runtime,
    _open_archive,
    _verify_ciphertext,
)
from .catalog import BackupCatalog
from .payload import _open_payload


class BackupRestoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class RestoreTargetState:
    instance_id: UUID
    environment: str
    disposable: bool
    empty: bool
    atomic: bool


class RestoreTarget(Protocol):
    def inspect(self) -> RestoreTargetState: ...
    def restore(self, dump: BinaryIO) -> None: ...
    def verify(self, schema_revision: str) -> bool: ...


@dataclass(frozen=True)
class RestoreReceipt:
    backup_id: UUID
    source_instance_id: UUID
    target_instance_id: UUID
    schema_revision: str
    artifact_sha256: str
    restored_at: datetime
    elapsed_seconds: float
    configuration_items_checked: int


def restore_global(source: BinaryIO, *, key: bytes, expected: BackupContext,
                   artifact: ArchiveReceipt, target: RestoreTarget,
                   at: datetime) -> RestoreReceipt:
    _local_runtime()
    return _restore_global(source, key=key, expected=expected, artifact=artifact, target=target, at=at)


def _restore_global(source: BinaryIO, *, key: bytes, expected: BackupContext,
                    artifact: ArchiveReceipt, target: RestoreTarget,
                    at: datetime) -> RestoreReceipt:
    _key(key)
    start = time.monotonic()
    try:
        if (not isinstance(expected, BackupContext) or not isinstance(artifact, ArchiveReceipt)
                or artifact.backup_id != expected.backup_id or not isinstance(at, datetime)
                or at.utcoffset() != timedelta(0)):
            raise ValueError
        _verify_ciphertext(source, artifact)
        with (
            _open_archive(source, key=key, expected=expected) as clear,
            _open_payload(clear.stream, expected=expected) as payload,
        ):
            state = target.inspect()
            if (not isinstance(state, RestoreTargetState) or not isinstance(state.instance_id, UUID)
                    or state.instance_id == expected.instance_id
                    or state.environment not in {"development", "test"}
                    or state.disposable is not True or state.empty is not True
                    or state.atomic is not True):
                raise ValueError
            target.restore(payload.dump)
            if target.verify(expected.schema_revision) is not True:
                raise ValueError
            count = len(payload.configuration)
        return RestoreReceipt(expected.backup_id, expected.instance_id, state.instance_id,
                              expected.schema_revision, artifact.sha256, at,
                              time.monotonic() - start, count)
    except Exception:  # noqa: BLE001 -- adapters não podem expor SQL, dump ou credenciais.
        raise BackupRestoreError("Recuperação global não comprovada no destino isolado.") from None


def record_restore(catalog: BackupCatalog, receipt: RestoreReceipt, *, context: BackupContext,
                   destination_id: UUID) -> None:
    _local_runtime()
    if (not isinstance(receipt, RestoreReceipt) or not isinstance(destination_id, UUID)
            or not isinstance(context, BackupContext) or receipt.backup_id != context.backup_id
            or receipt.source_instance_id != context.instance_id
            or receipt.schema_revision != context.schema_revision
            or not isinstance(receipt.target_instance_id, UUID)
            or receipt.target_instance_id == context.instance_id):
        raise BackupRestoreError("Recibo de recuperação inválido.")
    events = catalog.events(receipt.backup_id)
    if not any(event["payload"]["event"] == "verified"
               and event["payload"]["data"].get("destination_id") == str(destination_id)
               and event["payload"]["data"].get("artifact_sha256") == receipt.artifact_sha256
               for event in events):
        raise BackupRestoreError("Cópia sem verificação correspondente.")
    catalog.append(receipt.backup_id, "restore_verified", at=receipt.restored_at,
                   destination_id=destination_id, artifact_sha256=receipt.artifact_sha256,
                   restore_target_id=receipt.target_instance_id,
                   schema_revision=receipt.schema_revision)
