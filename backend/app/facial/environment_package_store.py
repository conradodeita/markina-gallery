"""Armazenamento POSIX restrito; raiz e chave nunca aparecem em exceções."""

import hmac
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")


class PackageStorageError(RuntimeError):
    pass


@dataclass(frozen=True, repr=False)
class ReopenedPackage:
    payload: dict = field(repr=False)
    key: bytes = field(repr=False)

    def __repr__(self):
        return "ReopenedPackage(<redacted>)"


def _directory(path: Path):
    if os.name != "posix" or not path.is_absolute():
        raise PackageStorageError("Storage POSIX indisponível.")
    # Resolver componente por componente via descritor evita seguir symlinks
    # inclusive em diretórios ancestrais e durante a abertura do arquivo final.
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if part in {".", ".."}:
                raise ValueError
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        info = os.fstat(descriptor)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError
        return descriptor
    except (OSError, ValueError):
        os.close(descriptor)
        raise PackageStorageError("Diretório de pacote inseguro.") from None


def _read(directory, name, limit):
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or info.st_size > limit):
            raise ValueError
        result = stream.read(limit + 1)
        if len(result) > limit:
            raise ValueError
        return result


def _write(directory, name, content):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(directory)


def reopen_package(package_root: Path, key_root: Path, operation: str) -> ReopenedPackage:
    if not isinstance(operation, str) or not _NAME.fullmatch(operation):
        raise PackageStorageError("Identificador de pacote inválido.")
    directories = []
    try:
        if package_root == key_root:
            raise ValueError
        for root in (package_root, key_root):
            directories.append(_directory(root))
        payload = json.loads(_read(directories[0], operation + ".json", 256_000_000))
        key = _read(directories[1], operation + ".key", 32)
        if not isinstance(payload, dict) or len(key) != 32:
            raise ValueError
        return ReopenedPackage(payload, key)
    except (OSError, ValueError, TypeError):
        raise PackageStorageError("Pacote persistido indisponível.") from None
    finally:
        for descriptor in directories:
            os.close(descriptor)


def persist_encrypted_package(package_root: Path, key_root: Path, operation: str, *,
                              encrypted_payload: dict, backup_key: bytes) -> ReopenedPackage:
    """Recebe somente envelope já cifrado; caller deve autenticar após reabertura."""
    if not isinstance(operation, str) or not _NAME.fullmatch(operation):
        raise PackageStorageError("Identificador de pacote inválido.")
    if (not isinstance(backup_key, bytes) or len(backup_key) != 32
            or not isinstance(encrypted_payload, dict)
            or set(encrypted_payload) != {"version", "nonce", "ciphertext"}):
        raise PackageStorageError("Envelope de pacote inválido.")
    directories = []
    try:
        if package_root == key_root:
            raise ValueError
        content = json.dumps(encrypted_payload, sort_keys=True, allow_nan=False).encode()
        if len(content) > 256_000_000:
            raise ValueError
        for root in (package_root, key_root):
            directories.append(_directory(root))
        _write(directories[1], operation + ".key", backup_key)
        _write(directories[0], operation + ".json", content)
        if not hmac.compare_digest(_read(directories[1], operation + ".key", 32), backup_key):
            raise ValueError
        if _read(directories[0], operation + ".json", 256_000_000) != content:
            raise ValueError
    except (OSError, ValueError, TypeError):
        # Nunca apagar nem sobrescrever automaticamente um pacote parcial.
        raise PackageStorageError("Persistência de pacote bloqueada.") from None
    finally:
        for descriptor in directories:
            os.close(descriptor)
    return reopen_package(package_root, key_root, operation)
