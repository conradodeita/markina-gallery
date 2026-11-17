"""IO privado POSIX para o catálogo e cópias sintéticas locais."""

from __future__ import annotations

import errno
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

from .archive import _local_runtime

_NAME = re.compile(r"[a-z0-9][a-z0-9.-]{0,100}\Z")


class BackupStorageError(RuntimeError):
    def __init__(self, code: str = "io") -> None:
        self.code = code if code in {"io", "quota", "authorization", "conflict", "checksum", "busy", "catalog", "unsafe"} else "io"
        super().__init__(f"Backup local indisponível ({self.code}).")


def io_error(error: OSError) -> BackupStorageError:
    if error.errno in {errno.ENOSPC, errno.EDQUOT}:
        return BackupStorageError("quota")
    if isinstance(error, PermissionError):
        return BackupStorageError("authorization")
    return BackupStorageError()


@contextmanager
def directory(root: Path):
    _local_runtime()
    with _directory(root) as descriptor:
        yield descriptor


@contextmanager
def _directory(root: Path):
    if os.name != "posix" or not root.is_absolute():
        raise BackupStorageError("unsafe")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            if part in {".", ".."}:
                raise BackupStorageError("unsafe")
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        info = os.fstat(descriptor)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise BackupStorageError("unsafe")
        yield descriptor
    except OSError as error:
        raise io_error(error) from None
    finally:
        os.close(descriptor)


def open_file(directory_fd: int, name: str, flags: int, *, create: bool = False) -> int:
    if not isinstance(name, str) or not _NAME.fullmatch(name) or name in {".", ".."}:
        raise BackupStorageError("unsafe")
    fd = os.open(name, flags | os.O_NOFOLLOW | (os.O_CREAT if create else 0), 0o600,
                 dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise BackupStorageError("unsafe")
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def lock(directory_fd: int, name: str):
    import fcntl

    fd = open_file(directory_fd, name, os.O_RDWR, create=True)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupStorageError("busy") from None
        yield
    finally:
        os.close(fd)


def write_all(fd: int, data: bytes) -> None:
    pending = memoryview(data)
    while pending:
        count = os.write(fd, pending)
        if count <= 0:
            raise BackupStorageError()
        pending = pending[count:]
