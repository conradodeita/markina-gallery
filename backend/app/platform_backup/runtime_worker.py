"""Ponto interno para executar um backup cifrado e conferir as duas cópias."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx

from . import filesystem as fs
from .archive import (
    ArchiveReceipt,
    _describe_ciphertext,
    _open_archive,
    _ProductionContext,
    _seal_archive,
)
from .catalog import BackupCatalog
from .payload import _build_payload, _open_payload
from .remote_copy import _copy_workspace_backup
from .runtime_config import DESTINATION_MARKER, RuntimeConfig, load_runtime_config
from .worker import GlobalSnapshot
from .workspace_store import FILES_ENDPOINT, WorkspaceDriveBackupStore

WORK_ROOT = Path("/var/lib/pyp-backup")


@dataclass(frozen=True, repr=False)
class _RuntimeCatalog(BackupCatalog):
    key_id: str = field(repr=False)

    def _directory(self):
        return fs._directory(self.root)

    def _context(self, instance_id: UUID, backup_id: UUID, schema_revision: str,
                 environment: str, at: datetime) -> _ProductionContext:
        return _ProductionContext(instance_id, backup_id, schema_revision, environment, at, self.key_id)


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    backup_id: UUID | None = None
    artifact_sha256: str | None = None
    size_bytes: int | None = None
    key_id: str | None = None
    error: str | None = None


def _attest_destination(config: RuntimeConfig, store: WorkspaceDriveBackupStore) -> None:
    if (not isinstance(store, WorkspaceDriveBackupStore) or store.destination_id != config.destination_id
            or store.parent_folder_id != config.parent_folder_id or store.shared_drive_id is not None
            or store.transport is None):
        raise fs.BackupStorageError("authorization")
    try:
        url = FILES_ENDPOINT + "/" + config.parent_folder_id
        headers = store._headers()
        folder = store.transport.get(url, headers=headers, params={
            "supportsAllDrives": "true",
            "fields": "id,mimeType,trashed,driveId,ownedByMe,isAppAuthorized,appProperties,capabilities(canAddChildren)",
        })
        if folder.status_code != 200:
            raise fs.BackupStorageError("authorization")
        data = folder.json()
        if (not isinstance(data, dict) or data.get("id") != config.parent_folder_id
                or data.get("mimeType") != "application/vnd.google-apps.folder"
                or data.get("trashed") is not False or data.get("driveId")
                or data.get("ownedByMe") is not True or data.get("isAppAuthorized") is not True
                or data.get("appProperties") != DESTINATION_MARKER
                or data.get("capabilities", {}).get("canAddChildren") is not True):
            raise fs.BackupStorageError("authorization")
        permissions = store.transport.get(url + "/permissions", headers=headers, params={
            "supportsAllDrives": "true", "fields": "nextPageToken,permissions(type,role)",
        })
        if permissions.status_code != 200 or permissions.json() != {"permissions": [{"type": "user", "role": "owner"}]}:
            raise fs.BackupStorageError("authorization")
    except (httpx.HTTPError, AttributeError, TypeError, ValueError):
        raise fs.BackupStorageError("authorization") from None


def _artifact(directory: int, context: _ProductionContext, key: bytes, catalog: BackupCatalog,
              snapshot: Callable[[str], AbstractContextManager[GlobalSnapshot]]) -> ArchiveReceipt:
    final = str(context.backup_id) + ".pypb"
    partial = str(context.backup_id) + ".building"
    prepared = [e["payload"]["data"] for e in catalog.events(context.backup_id)
                if e["payload"]["event"] == "prepared"]
    try:
        descriptor = fs.open_file(directory, final, os.O_RDONLY)
    except FileNotFoundError:
        if prepared:
            raise fs.BackupStorageError("conflict") from None
        descriptor = fs.open_file(directory, partial, os.O_RDWR | os.O_EXCL, create=True)
        try:
            with os.fdopen(descriptor, "w+b") as encrypted, tempfile.TemporaryFile(mode="w+b") as package:
                with snapshot(context.schema_revision) as origin:
                    _build_payload(origin.dump, origin.configuration, package, context=context)
                package.seek(0)
                _seal_archive(package, encrypted, key=key, context=context)
                encrypted.flush()
                os.fsync(encrypted.fileno())
            os.link(partial, final, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        finally:
            os.unlink(partial, dir_fd=directory)
            os.fsync(directory)
        descriptor = fs.open_file(directory, final, os.O_RDONLY)
    with os.fdopen(descriptor, "rb") as encrypted:
        receipt = _describe_ciphertext(encrypted, context.backup_id)
        with _open_archive(encrypted, key=key, expected=context) as clear, _open_payload(clear.stream, expected=context):
            pass
    expected = {"artifact_sha256": receipt.sha256, "size_bytes": receipt.size_bytes}
    if prepared:
        if prepared != [expected]:
            raise fs.BackupStorageError("conflict")
    else:
        catalog.append(context.backup_id, "prepared", at=context.created_at, **expected)
    return receipt


def run_due(*, schema_revision: str, at: datetime,
            snapshot: Callable[[str], AbstractContextManager[GlobalSnapshot]],
            workspace: Callable[[RuntimeConfig], WorkspaceDriveBackupStore]) -> RuntimeResult:
    """Entrada comum para agenda e operação manual. Desativada até configuração aprovada."""
    context = None
    try:
        if not isinstance(at, datetime) or at.utcoffset() != timedelta(0):
            raise fs.BackupStorageError("unsafe")
        config = load_runtime_config()
        if not config.enabled:
            return RuntimeResult("disabled")
        key_id = config.keyring.active_key_id
        key = config.keyring.key_for(key_id)
        catalog = _RuntimeCatalog(WORK_ROOT / "catalog", key, key_id)
        with fs._directory(WORK_ROOT) as root, fs.lock(root, "service.lock"):
            store = workspace(config)
            _attest_destination(config, store)
            context = catalog.daily_context(config.keyring.installation_id, schema_revision, "production", at)
            with fs._directory(WORK_ROOT / "artifacts") as artifact_dir:
                receipt = _artifact(artifact_dir, context, key, catalog, snapshot)
                descriptor = fs.open_file(artifact_dir, str(context.backup_id) + ".pypb", os.O_RDONLY)
                with os.fdopen(descriptor, "rb") as encrypted:
                    _copy_workspace_backup(encrypted, receipt=receipt, context=context, key=key,
                                           store=store, catalog=catalog, at=at)
        return RuntimeResult("copies_verified", context.backup_id, receipt.sha256, receipt.size_bytes, key_id)
    except fs.BackupStorageError as error:
        return RuntimeResult("failed", context.backup_id if context else None, error=error.code)
    except Exception:  # noqa: BLE001 -- a saída do serviço não reflete mensagens do banco, arquivos ou Google.
        return RuntimeResult("failed", context.backup_id if context else None, error="io")
