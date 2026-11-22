"""Cópia remota verificada em ensaios locais, sem ativar runtime de produção."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import BinaryIO

from .archive import (
    ArchiveReceipt,
    BackupArchiveError,
    BackupContext,
    _key,
    _local_runtime,
    _open_archive,
    _verify_ciphertext,
)
from .catalog import BackupCatalog
from .filesystem import BackupStorageError
from .payload import BackupPayloadError, _open_payload
from .restore import (
    BackupRestoreError,
    RestoreReceipt,
    RestoreTarget,
    record_restore,
    restore_global,
)
from .storage import CopyReceipt
from .workspace_store import WorkspaceDriveBackupStore


def _record_once(catalog: BackupCatalog, backup_id, event: str, *, at: datetime,
                 destination_id, receipt: ArchiveReceipt) -> None:
    for item in catalog.events(backup_id):
        data = item["payload"]["data"]
        if (item["payload"]["event"] == event
                and data.get("destination_id") == str(destination_id)):
            if (data.get("artifact_sha256") != receipt.sha256
                    or data.get("size_bytes") != receipt.size_bytes):
                raise BackupStorageError("conflict")
            return
    catalog.append(backup_id, event, at=at, destination_id=destination_id,
                   artifact_sha256=receipt.sha256, size_bytes=receipt.size_bytes)


def copy_workspace_backup(source: BinaryIO, *, receipt: ArchiveReceipt,
                          context: BackupContext, key: bytes,
                          store: WorkspaceDriveBackupStore, catalog: BackupCatalog,
                          at: datetime) -> CopyReceipt:
    """Envia e lê de volta o mesmo ciphertext antes de registrar `verified`.

    Esta função permanece sob o runtime local/teste. Nenhuma chamada Drive real é
    feita sem que o chamador forneça explicitamente um transporte configurado.
    """
    _local_runtime()
    return _copy_workspace_backup(source, receipt=receipt, context=context, key=key,
                                  store=store, catalog=catalog, at=at)


def _copy_workspace_backup(source: BinaryIO, *, receipt: ArchiveReceipt,
                           context: BackupContext, key: bytes,
                           store: WorkspaceDriveBackupStore, catalog: BackupCatalog,
                           at: datetime) -> CopyReceipt:
    _key(key)
    if (
        not isinstance(receipt, ArchiveReceipt)
        or not isinstance(context, BackupContext)
        or not isinstance(store, WorkspaceDriveBackupStore)
        or not isinstance(catalog, BackupCatalog)
        or not isinstance(at, datetime)
        or at.utcoffset() != timedelta(0)
        or receipt.backup_id != context.backup_id
    ):
        raise BackupStorageError("unsafe")

    _record_once(catalog, context.backup_id, "copy_started", at=at,
                 destination_id=store.destination_id, receipt=receipt)
    try:
        copy = store.upload(source, receipt)
        if (copy.destination_id != store.destination_id
                or copy.backup_id != receipt.backup_id
                or copy.size_bytes != receipt.size_bytes
                or copy.sha256 != receipt.sha256):
            raise BackupStorageError("conflict")
        _record_once(catalog, context.backup_id, "uploaded", at=at,
                     destination_id=store.destination_id, receipt=receipt)
        with store.open(context.backup_id) as remote:
            _verify_ciphertext(remote, receipt)
            with (
                _open_archive(remote, key=key, expected=context) as clear,
                _open_payload(clear.stream, expected=context),
            ):
                pass
        _record_once(catalog, context.backup_id, "verified", at=at,
                     destination_id=store.destination_id, receipt=receipt)
        return copy
    except BackupStorageError as error:
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code=error.code)
        raise
    except (BackupArchiveError, BackupPayloadError):
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code="checksum")
        raise BackupStorageError("checksum") from None
    except Exception:  # noqa: BLE001 -- erros de provider/stream devem ser sanitizados.
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code="io")
        raise BackupStorageError("io") from None


def restore_workspace_backup(*, receipt: ArchiveReceipt, context: BackupContext,
                              key: bytes, store: WorkspaceDriveBackupStore,
                              catalog: BackupCatalog, target: RestoreTarget,
                              at: datetime) -> RestoreReceipt:
    """Restaura a cópia Workspace somente em alvo isolado validado pelo fluxo comum."""
    _local_runtime()
    _key(key)
    if (not isinstance(receipt, ArchiveReceipt)
            or not isinstance(context, BackupContext)
            or not isinstance(store, WorkspaceDriveBackupStore)
            or not isinstance(catalog, BackupCatalog)
            or receipt.backup_id != context.backup_id
            or not isinstance(at, datetime)
            or at.utcoffset() != timedelta(0)):
        raise BackupStorageError("unsafe")
    verified = any(
        item["payload"]["event"] == "verified"
        and item["payload"]["data"].get("destination_id") == str(store.destination_id)
        and item["payload"]["data"].get("artifact_sha256") == receipt.sha256
        and item["payload"]["data"].get("size_bytes") == receipt.size_bytes
        for item in catalog.events(context.backup_id)
    )
    if not verified:
        raise BackupStorageError("unsafe")
    try:
        with store.open(context.backup_id) as remote:
            restored = restore_global(remote, key=key, expected=context,
                                      artifact=receipt, target=target, at=at)
        record_restore(catalog, restored, context=context,
                       destination_id=store.destination_id)
        return restored
    except BackupStorageError as error:
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code=error.code)
        raise
    except BackupRestoreError:
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code="io")
        raise
    except Exception:  # noqa: BLE001 -- evento e provider não expõem detalhes externos.
        catalog.append(context.backup_id, "failed", at=at,
                       destination_id=store.destination_id, code="io")
        raise BackupStorageError("io") from None
