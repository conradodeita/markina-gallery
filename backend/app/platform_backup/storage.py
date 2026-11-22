"""Store POSIX de ensaio, com parcial retomável e publicação imutável."""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from . import filesystem as fs
from .archive import CHUNK_SIZE, MAX_HEADER_BYTES, MAX_PLAINTEXT_BYTES, ArchiveReceipt


@dataclass(frozen=True)
class CopyReceipt:
    destination_id: UUID
    backup_id: UUID
    size_bytes: int
    sha256: str


def _matches(stream: BinaryIO, receipt: ArchiveReceipt) -> bool:
    digest, size = hashlib.sha256(), 0
    while part := stream.read(CHUNK_SIZE):
        size += len(part)
        if size > receipt.size_bytes:
            return False
        digest.update(part)
    return size == receipt.size_bytes and digest.hexdigest() == receipt.sha256


@dataclass(frozen=True, repr=False)
class LocalBackupStore:
    root: Path = field(repr=False)
    destination_id: UUID
    failure_domain: str

    def __post_init__(self) -> None:
        if not isinstance(self.destination_id, UUID) or not re.fullmatch(r"[a-z0-9-]{1,64}", self.failure_domain):
            raise fs.BackupStorageError("unsafe")

    def __repr__(self) -> str:
        return "LocalBackupStore(<redacted>)"

    @contextmanager
    def open(self, backup_id: UUID):
        if not isinstance(backup_id, UUID):
            raise fs.BackupStorageError("unsafe")
        with fs.directory(self.root) as directory_fd:
            fd = fs.open_file(directory_fd, str(backup_id) + ".pypb", os.O_RDONLY)
            with os.fdopen(fd, "rb") as stream:
                yield stream

    def upload(self, source: BinaryIO, receipt: ArchiveReceipt) -> CopyReceipt:
        if (not isinstance(receipt, ArchiveReceipt) or not isinstance(receipt.backup_id, UUID)
                or type(receipt.size_bytes) is not int
                or not 0 < receipt.size_bytes <= MAX_PLAINTEXT_BYTES + MAX_HEADER_BYTES + 64
                or not re.fullmatch(r"[0-9a-f]{64}", receipt.sha256)):
            raise fs.BackupStorageError("checksum")
        name = str(receipt.backup_id)
        with fs.directory(self.root) as directory_fd, fs.lock(directory_fd, name + ".lock"):
            try:
                final_fd = fs.open_file(directory_fd, name + ".pypb", os.O_RDONLY)
            except FileNotFoundError:
                final_fd = None
            if final_fd is not None:
                with os.fdopen(final_fd, "rb") as existing:
                    if not _matches(existing, receipt):
                        raise fs.BackupStorageError("conflict")
            else:
                fd = fs.open_file(directory_fd, name + ".partial", os.O_RDWR, create=True)
                with os.fdopen(fd, "r+b") as partial:
                    source.seek(0)
                    offset = os.fstat(partial.fileno()).st_size
                    if offset > receipt.size_bytes:
                        raise fs.BackupStorageError("conflict")
                    remaining = offset
                    while remaining:
                        expected = partial.read(min(CHUNK_SIZE, remaining))
                        if not expected or source.read(len(expected)) != expected:
                            raise fs.BackupStorageError("conflict")
                        remaining -= len(expected)
                    partial.seek(0, os.SEEK_END)
                    remaining = receipt.size_bytes - offset
                    while remaining:
                        part = source.read(min(CHUNK_SIZE, remaining))
                        if not isinstance(part, bytes) or not part or len(part) > remaining:
                            raise fs.BackupStorageError("checksum")
                        fs.write_all(partial.fileno(), part)
                        remaining -= len(part)
                    if source.read(1) != b"":
                        raise fs.BackupStorageError("checksum")
                    partial.flush()
                    os.fsync(partial.fileno())
                    partial.seek(0)
                    if not _matches(partial, receipt):
                        raise fs.BackupStorageError("checksum")
                try:
                    os.link(name + ".partial", name + ".pypb", src_dir_fd=directory_fd,
                            dst_dir_fd=directory_fd, follow_symlinks=False)
                except FileExistsError:
                    raise fs.BackupStorageError("conflict") from None
                os.unlink(name + ".partial", dir_fd=directory_fd)
                os.fsync(directory_fd)
        return CopyReceipt(self.destination_id, receipt.backup_id, receipt.size_bytes, receipt.sha256)
