"""Primitivas POSIX sem dependências criptográficas, para bootstrap seguro."""

from __future__ import annotations

import os
import stat
from pathlib import Path


class CredentialError(RuntimeError):
    """A fronteira pública só emite códigos, nunca valores ou erros de terceiros."""


def _directory(path: Path) -> int:
    """Abre todos os componentes via dirfd; nenhum symlink é seguido."""
    if os.name != "posix" or not path.is_absolute() or ".." in path.parts:
        raise CredentialError("unsafe_directory")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = next_fd
            info = os.fstat(descriptor)
            # /tmp root-owned e sticky é permitido; a raiz privada abaixo é obrigatória.
            sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            if info.st_uid not in {0, os.getuid()} or (
                info.st_mode & 0o022 and not sticky_root
            ):
                raise CredentialError("unsafe_directory")
        return descriptor
    except (OSError, CredentialError):
        os.close(descriptor)
        raise CredentialError("unsafe_directory") from None


def _private_directory(path: Path) -> int:
    fd = _directory(path)
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise CredentialError("unsafe_directory")
    return fd


def _read(
    directory: int,
    name: str,
    limit: int,
    *,
    credential=False,
    public=False,
    allow_empty=False,
) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        mode = stat.S_IMODE(info.st_mode)
        allowed_mode = (
            bool(mode & 0o400) and not mode & 0o7022
            if public
            else mode in ({0o400, 0o600} if credential else {0o600})
        )
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.getuid()
            or not allowed_mode
            or (info.st_size == 0 and not allow_empty)
            or info.st_size < 0
            or info.st_size > limit
        ):
            raise CredentialError("credential_unavailable")
        value = os.read(fd, limit + 1)
        if len(value) > limit:
            raise CredentialError("credential_unavailable")
        return value
    finally:
        os.close(fd)


def _write(directory: int, name: str, payload: bytes):
    fd = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(directory)
