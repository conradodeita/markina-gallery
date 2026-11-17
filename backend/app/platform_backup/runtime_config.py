"""Custódia e destino de um backup de produção, sem ativar a rotina."""

from __future__ import annotations

import base64
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from uuid import UUID

from .filesystem import BackupStorageError

CONFIG_ROOT = Path("/etc/pyp-backup")
_LIMIT = 16_384
_KEY_ID = re.compile(r"backup-[0-9a-f]{12}\Z")
_FOLDER_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
DESTINATION_MARKER = MappingProxyType({
    "pypBackupInstallation": "markina-gallery",
    "pypBackupDestination": "global-database",
})


@dataclass(frozen=True, repr=False)
class BackupKeyring:
    installation_id: UUID
    active_key_id: str
    keys: Mapping[str, bytes] = field(repr=False)

    def key_for(self, key_id: str) -> bytes:
        try:
            return self.keys[key_id]
        except (KeyError, TypeError):
            raise BackupStorageError("authorization") from None


@dataclass(frozen=True, repr=False)
class RuntimeConfig:
    keyring: BackupKeyring
    destination_id: UUID
    parent_folder_id: str
    enabled: bool


def _unique(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _object(raw: bytes, fields: set[str]) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _LIMIT:
        raise ValueError
    value = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(value, dict) or set(value) != fields or type(value["version"]) is not int or value["version"] != 1:
        raise ValueError
    return value


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise TypeError
    result = UUID(value)
    if value != str(result) or not result.int:
        raise ValueError
    return result


def parse_recovery_keyring(raw: bytes) -> BackupKeyring:
    """Forma portátil da cópia offline. O chamador controla a mídia e a leitura."""
    try:
        item = _object(raw, {"version", "installation_id", "active_key_id", "keys"})
        keys = item["keys"]
        active = item["active_key_id"]
        if (not isinstance(active, str) or not _KEY_ID.fullmatch(active)
                or not isinstance(keys, dict) or not 1 <= len(keys) <= 16 or active not in keys):
            raise ValueError
        decoded = {}
        for name, value in keys.items():
            if not _KEY_ID.fullmatch(name) or not isinstance(value, str) or len(value) != 44:
                raise ValueError
            key = base64.b64decode(value, validate=True)
            if len(key) != 32 or base64.b64encode(key).decode("ascii") != value:
                raise ValueError
            decoded[name] = key
        return BackupKeyring(_uuid(item["installation_id"]), active, MappingProxyType(decoded))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise BackupStorageError("authorization") from None


def _binding(raw: bytes, keyring: BackupKeyring) -> RuntimeConfig:
    try:
        item = _object(raw, {"version", "installation_id", "destination_id", "provider", "scope",
                             "parent_folder_id", "environment", "enabled", "marker"})
        folder = item["parent_folder_id"]
        if (_uuid(item["installation_id"]) != keyring.installation_id
                or item["provider"] != "google-workspace" or item["scope"] != "drive.file"
                or item["environment"] != "production" or type(item["enabled"]) is not bool
                or item["marker"] != DESTINATION_MARKER
                or not isinstance(folder, str) or not _FOLDER_ID.fullmatch(folder)):
            raise ValueError
        return RuntimeConfig(keyring, _uuid(item["destination_id"]), folder, item["enabled"])
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise BackupStorageError("unsafe") from None


def _private_root(root: Path) -> int:
    if (os.name != "posix" or os.geteuid() != 0 or not root.is_absolute()
            or ".." in root.parts):
        raise BackupStorageError("unsafe")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            info = os.fstat(descriptor)
            if info.st_uid != 0 or info.st_gid != 0 or info.st_mode & 0o022:
                raise BackupStorageError("unsafe")
        if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o700:
            raise BackupStorageError("unsafe")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read(directory: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_gid != 0
                or stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1
                or not 0 < info.st_size <= _LIMIT):
            raise BackupStorageError("unsafe")
        raw = stream.read(_LIMIT + 1)
        if len(raw) != info.st_size:
            raise BackupStorageError("unsafe")
        return raw


def load_runtime_config() -> RuntimeConfig:
    """Carrega somente a configuração fixa do serviço em produção."""
    if os.getenv("APP_ENV") != "production":
        raise BackupStorageError("unsafe")
    try:
        descriptor = _private_root(CONFIG_ROOT)
        try:
            keyring = parse_recovery_keyring(_read(descriptor, "keyring.json"))
            return _binding(_read(descriptor, "destination.json"), keyring)
        finally:
            os.close(descriptor)
    except OSError:
        raise BackupStorageError("unsafe") from None
