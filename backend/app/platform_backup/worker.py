"""Agenda diária global local; produção e integração real permanecem sem caller."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from . import filesystem as fs
from .archive import (
    ArchiveReceipt,
    BackupArchiveError,
    BackupContext,
    _key,
    _local_runtime,
    describe_ciphertext,
    open_archive,
    seal_archive,
    verify_ciphertext,
)
from .catalog import BackupCatalog
from .payload import BackupPayloadError, build_payload, open_payload
from .storage import LocalBackupStore


@dataclass(frozen=True, repr=False)
class GlobalSnapshot:
    dump: BinaryIO = field(repr=False)
    configuration: dict[str, str] = field(repr=False)

    def __repr__(self) -> str:
        return "GlobalSnapshot(<redacted>)"


@dataclass(frozen=True)
class BackupRunReport:
    backup_id: UUID | None
    status: str
    uploaded_count: int
    verified_count: int
    errors: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class LocalBackupWorker:
    instance_id: UUID
    schema_revision: str
    environment: str
    key: bytes = field(repr=False)
    workspace: Path = field(repr=False)
    catalog: BackupCatalog = field(repr=False)
    stores: tuple[LocalBackupStore, ...] = field(repr=False)
    snapshot: Callable[[BackupContext], AbstractContextManager[GlobalSnapshot]] = field(repr=False)

    def __repr__(self) -> str:
        return "LocalBackupWorker(<redacted>)"

    def _validate_roots(self) -> None:
        if (not self.stores or len({store.destination_id for store in self.stores}) != len(self.stores)
                or len({store.failure_domain for store in self.stores}) != len(self.stores)):
            raise fs.BackupStorageError("unsafe")
        roots = [self.workspace, self.catalog.root, *(store.root for store in self.stores)]
        identities = []
        for root in roots:
            with fs.directory(root) as directory_fd:
                info = os.fstat(directory_fd)
                identities.append((info.st_dev, info.st_ino))
        if len(set(identities)) != len(identities):
            raise fs.BackupStorageError("unsafe")

    def _artifact(self, context: BackupContext, directory_fd: int) -> ArchiveReceipt:
        name = str(context.backup_id)
        prepared = [event for event in self.catalog.events(context.backup_id)
                    if event["payload"]["event"] == "prepared"]
        try:
            fd = fs.open_file(directory_fd, name + ".pypb", os.O_RDONLY)
        except FileNotFoundError:
            if prepared:
                raise fs.BackupStorageError("conflict") from None
            try:
                fd = fs.open_file(directory_fd, name + ".building", os.O_RDWR | os.O_EXCL,
                                  create=True)
            except FileExistsError:
                raise fs.BackupStorageError("conflict") from None
            with os.fdopen(fd, "w+b") as target, tempfile.TemporaryFile(mode="w+b") as package:
                with self.snapshot(context) as source:
                    build_payload(source.dump, source.configuration, package, context=context)
                package.seek(0)
                seal_archive(package, target, key=self.key, context=context)
                target.flush()
                os.fsync(target.fileno())
            os.link(name + ".building", name + ".pypb", src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd, follow_symlinks=False)
            os.unlink(name + ".building", dir_fd=directory_fd)
            os.fsync(directory_fd)
            fd = fs.open_file(directory_fd, name + ".pypb", os.O_RDONLY)
        with os.fdopen(fd, "rb") as stream:
            receipt = describe_ciphertext(stream, context.backup_id)
            with (
                open_archive(stream, key=self.key, expected=context) as clear,
                open_payload(clear.stream, expected=context),
            ):
                pass
        if prepared:
            expected = prepared[-1]["payload"]["data"]
            if (expected.get("artifact_sha256") != receipt.sha256
                    or expected.get("size_bytes") != receipt.size_bytes):
                raise fs.BackupStorageError("conflict")
        else:
            self.catalog.append(context.backup_id, "prepared", at=context.created_at,
                                artifact_sha256=receipt.sha256, size_bytes=receipt.size_bytes)
        return receipt

    def _record_once(self, context: BackupContext, event: str, destination: UUID,
                     at: datetime, receipt: ArchiveReceipt) -> None:
        events = self.catalog.events(context.backup_id)
        if not any(item["payload"]["event"] == event
                   and item["payload"]["data"].get("destination_id") == str(destination)
                   for item in events):
            self.catalog.append(context.backup_id, event, at=at, destination_id=destination,
                                artifact_sha256=receipt.sha256, size_bytes=receipt.size_bytes)

    def run_due(self, at: datetime) -> BackupRunReport:
        """Um tick idempotente por dia UTC; o chamador local fornece o relógio."""
        _local_runtime()
        _key(self.key)
        context, uploaded, verified, errors = None, 0, 0, []
        try:
            self._validate_roots()
            context = self.catalog.daily_context(self.instance_id, self.schema_revision,
                                                 self.environment, at)
            with fs.directory(self.workspace) as directory_fd, fs.lock(
                    directory_fd, str(context.backup_id) + ".run.lock"):
                receipt = self._artifact(context, directory_fd)
                for store in self.stores:
                    try:
                        self._record_once(context, "copy_started", store.destination_id, at, receipt)
                        fd = fs.open_file(directory_fd, str(context.backup_id) + ".pypb", os.O_RDONLY)
                        with os.fdopen(fd, "rb") as source:
                            store.upload(source, receipt)
                        uploaded += 1
                        self._record_once(context, "uploaded", store.destination_id, at, receipt)
                        with store.open(context.backup_id) as source:
                            verify_ciphertext(source, receipt)
                            with (
                                open_archive(source, key=self.key, expected=context) as clear,
                                open_payload(clear.stream, expected=context),
                            ):
                                pass
                        verified += 1
                        self._record_once(context, "verified", store.destination_id, at, receipt)
                    except (fs.BackupStorageError, BackupArchiveError, BackupPayloadError) as error:
                        code = error.code if isinstance(error, fs.BackupStorageError) else "checksum"
                        errors.append(code)
                        self.catalog.append(context.backup_id, "failed", at=at,
                                            destination_id=store.destination_id, code=code)
            status = "copies_verified" if verified == len(self.stores) else "partial" if verified else "failed"
            return BackupRunReport(context.backup_id, status, uploaded, verified, tuple(errors))
        except Exception as error:  # noqa: BLE001 -- fronteira de producer injetado; erro sanitizado.
            code = error.code if isinstance(error, fs.BackupStorageError) else "io"
            if context is not None:
                try:
                    self.catalog.append(context.backup_id, "failed", at=at, code=code)
                except Exception:  # noqa: BLE001 -- falha do catálogo não pode expor erro original.
                    code = "catalog"
            return BackupRunReport(context.backup_id if context else None, "failed", uploaded,
                                   verified, (*errors, code))
