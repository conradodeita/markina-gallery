"""Pacote interno global allowlisted; nunca extrai caminhos fornecidos pelo arquivo."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import BinaryIO

from .archive import (
    CHUNK_SIZE,
    MAX_PLAINTEXT_BYTES,
    BackupContext,
    _local_runtime,
    _read_exact,
    _write_all,
)

_CONFIG_LIMIT = 1024 * 1024
_MANIFEST_LIMIT = 65536
_MEMBERS = {"database.dump", "runtime-config.json", "manifest.json"}


class BackupPayloadError(ValueError):
    pass


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _configuration(value: dict) -> bytes:
    if (not isinstance(value, dict) or len(value) > 256
            or any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", key)
                   or not isinstance(item, str) for key, item in value.items())):
        raise ValueError
    result = _json(value)
    if len(result) > _CONFIG_LIMIT:
        raise ValueError
    return result


def build_payload(dump: BinaryIO, configuration: dict, destination: BinaryIO,
                  *, context: BackupContext) -> None:
    _local_runtime()
    _build_payload(dump, configuration, destination, context=context)


def _build_payload(dump: BinaryIO, configuration: dict, destination: BinaryIO,
                   *, context: BackupContext) -> None:
    if not isinstance(context, BackupContext):
        raise BackupPayloadError("Contexto de backup inválido.")
    try:
        config = _configuration(configuration)
        first = _read_exact(dump, 5)
        if first != b"PGDMP":
            raise ValueError
        digest, size = hashlib.sha256(), 0
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED,
                             allowZip64=True) as package:
            with package.open("database.dump", "w", force_zip64=True) as target:
                part = first
                while part:
                    if not isinstance(part, bytes) or len(part) > CHUNK_SIZE:
                        raise ValueError
                    size += len(part)
                    if size > MAX_PLAINTEXT_BYTES - _CONFIG_LIMIT - _MANIFEST_LIMIT:
                        raise ValueError
                    _write_all(target, part)
                    digest.update(part)
                    part = dump.read(CHUNK_SIZE)
                if not isinstance(part, bytes):
                    raise TypeError
            package.writestr("runtime-config.json", config)
            manifest = {
                "version": 1,
                "context": json.loads(context.header()),
                "members": {
                    "database.dump": {"size_bytes": size, "sha256": digest.hexdigest()},
                    "runtime-config.json": {"size_bytes": len(config),
                                            "sha256": hashlib.sha256(config).hexdigest()},
                },
            }
            package.writestr("manifest.json", _json(manifest))
    except (OSError, ValueError, TypeError, AttributeError, zipfile.BadZipFile):
        raise BackupPayloadError("Não foi possível preparar o pacote global.") from None


@dataclass(frozen=True, repr=False)
class GlobalPayload:
    dump: BinaryIO = field(repr=False)
    configuration: MappingProxyType = field(repr=False)

    def __repr__(self) -> str:
        return "GlobalPayload(<redacted>)"


def _member(package: zipfile.ZipFile, name: str, limit: int) -> bytes:
    info = package.getinfo(name)
    if not 0 <= info.file_size <= limit:
        raise ValueError
    value = package.read(name)
    if len(value) != info.file_size:
        raise ValueError
    return value


@contextmanager
def open_payload(source: BinaryIO, *, expected: BackupContext):
    """Recebe stream autenticado; valida todos os membros antes de ceder o dump."""
    _local_runtime()
    with _open_payload(source, expected=expected) as payload:
        yield payload


@contextmanager
def _open_payload(source: BinaryIO, *, expected: BackupContext):
    if not isinstance(expected, BackupContext):
        raise BackupPayloadError("Contexto de backup inválido.")
    package, dump = None, None
    try:
        package = zipfile.ZipFile(source, "r")
        members = package.infolist()
        if len(members) != len(_MEMBERS) or {member.filename for member in members} != _MEMBERS:
            raise ValueError
        for member in members:
            mode = member.external_attr >> 16
            if (member.is_dir() or member.compress_type != zipfile.ZIP_STORED
                    or member.flag_bits & 1 or member.file_size != member.compress_size
                    or stat.S_IFMT(mode) not in {0, stat.S_IFREG}
                    or not 0 <= member.file_size <= MAX_PLAINTEXT_BYTES):
                raise ValueError
        raw_manifest = _member(package, "manifest.json", _MANIFEST_LIMIT)
        manifest = json.loads(raw_manifest)
        if (not isinstance(manifest, dict) or set(manifest) != {"version", "context", "members"}
                or type(manifest["version"]) is not int or manifest["version"] != 1
                or manifest["context"] != json.loads(expected.header())
                or _json(manifest) != raw_manifest
                or not isinstance(manifest["members"], dict)
                or set(manifest["members"]) != {"database.dump", "runtime-config.json"}):
            raise ValueError
        for name in ("database.dump", "runtime-config.json"):
            descriptor = manifest["members"][name]
            if (not isinstance(descriptor, dict) or set(descriptor) != {"size_bytes", "sha256"}
                    or type(descriptor["size_bytes"]) is not int
                    or descriptor["size_bytes"] != package.getinfo(name).file_size
                    or not isinstance(descriptor["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"])):
                raise ValueError
            digest = hashlib.sha256()
            with package.open(name) as member:
                while block := member.read(CHUNK_SIZE):
                    digest.update(block)
            if digest.hexdigest() != descriptor["sha256"]:
                raise ValueError
        raw_config = _member(package, "runtime-config.json", _CONFIG_LIMIT)
        config = json.loads(raw_config)
        if _configuration(config) != raw_config:
            raise ValueError
        dump = package.open("database.dump")
        if _read_exact(dump, 5) != b"PGDMP":
            raise ValueError
        dump.seek(0)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, zipfile.BadZipFile):
        if dump is not None:
            dump.close()
        if package is not None:
            package.close()
        raise BackupPayloadError("Pacote global não autenticado ou incompatível.") from None
    try:
        yield GlobalPayload(dump, MappingProxyType(config))
    finally:
        dump.close()
        package.close()
