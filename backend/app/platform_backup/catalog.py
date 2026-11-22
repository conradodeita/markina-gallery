"""Eventos HMAC append-only; catálogo independente do PostgreSQL protegido."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import filesystem as fs
from .archive import BackupContext

_LIMIT = 1024 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_EVENTS = {"prepared", "copy_started", "uploaded", "verified", "restore_verified", "failed", "deletion_planned", "deleted"}
_FIELDS = {"destination_id", "artifact_sha256", "size_bytes", "code", "restore_target_id", "schema_revision", "survivor_destination_id"}


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _identifier(value: UUID) -> str:
    if not isinstance(value, UUID):
        raise fs.BackupStorageError("catalog")
    return str(value)


def _payload(event: str, at: datetime, values: dict) -> dict:
    if (event not in _EVENTS or not isinstance(at, datetime)
            or at.utcoffset() != timedelta(0) or not set(values) <= _FIELDS):
        raise fs.BackupStorageError("catalog")
    if "destination_id" in values:
        _identifier(values["destination_id"])
    if "restore_target_id" in values:
        _identifier(values["restore_target_id"])
    if "survivor_destination_id" in values:
        _identifier(values["survivor_destination_id"])
    if "schema_revision" in values and (not isinstance(values["schema_revision"], str)
            or not re.fullmatch(r"[A-Za-z0-9_]{1,64}", values["schema_revision"])):
        raise fs.BackupStorageError("catalog")
    if "artifact_sha256" in values and (not isinstance(values["artifact_sha256"], str)
            or not _DIGEST.fullmatch(values["artifact_sha256"])):
        raise fs.BackupStorageError("catalog")
    if "size_bytes" in values and (type(values["size_bytes"]) is not int or values["size_bytes"] < 0):
        raise fs.BackupStorageError("catalog")
    if "code" in values and values["code"] not in {"io", "quota", "authorization", "conflict", "checksum", "interrupted", "catalog", "unsafe"}:
        raise fs.BackupStorageError("catalog")
    clean = {key: str(value) if isinstance(value, UUID) else value for key, value in values.items()}
    return {"event": event, "at": at.isoformat(), "data": clean}


@dataclass(frozen=True, repr=False)
class BackupCatalog:
    root: Path = field(repr=False)
    key: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or len(self.key) != 32:
            raise fs.BackupStorageError("catalog")
        derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                       info=b"pyp-platform-backup-catalog-v1").derive(self.key)
        object.__setattr__(self, "key", derived)

    def __repr__(self) -> str:
        return "BackupCatalog(<redacted>)"

    def _directory(self):
        return fs.directory(self.root)

    def _context(self, instance_id: UUID, backup_id: UUID, schema_revision: str,
                 environment: str, at: datetime) -> BackupContext:
        return BackupContext(instance_id, backup_id, schema_revision, environment, at)

    def daily_context(self, instance_id: UUID, schema_revision: str,
                      environment: str, at: datetime) -> BackupContext:
        candidate = self._context(instance_id, uuid4(), schema_revision, environment, at)
        name = "day-" + at.date().isoformat() + ".json"
        with self._directory() as directory_fd, fs.lock(directory_fd, name + ".lock"):
            try:
                fd = fs.open_file(directory_fd, name, os.O_RDONLY)
            except FileNotFoundError:
                header = json.loads(candidate.header())
                record = {"context": header, "signature": hmac.new(
                    self.key, b"day:" + candidate.header(), hashlib.sha256).hexdigest()}
                fd = fs.open_file(directory_fd, name, os.O_WRONLY | os.O_EXCL, create=True)
                try:
                    fs.write_all(fd, _json(record))
                    os.fsync(fd)
                    os.fsync(directory_fd)
                finally:
                    os.close(fd)
                return candidate
            try:
                data = os.read(fd, 8193)
            finally:
                os.close(fd)
            try:
                value = json.loads(data)
                if (len(data) > 8192 or set(value) != {"context", "signature"}
                        or _json(value) != data or not isinstance(value["signature"], str)
                        or not hmac.compare_digest(value["signature"], hmac.new(
                            self.key, b"day:" + _json(value["context"]), hashlib.sha256).hexdigest())):
                    raise ValueError
                fields = value["context"]
                result = self._context(UUID(fields["instance_id"]), UUID(fields["backup_id"]),
                                       fields["schema_revision"], fields["environment"],
                                       datetime.fromisoformat(fields["created_at"]))
                if (json.loads(result.header()) != fields or result.instance_id != instance_id
                        or result.schema_revision != schema_revision or result.environment != environment
                        or result.created_at.date() != at.date()):
                    raise ValueError
                return result
            except (ValueError, TypeError, KeyError):
                raise fs.BackupStorageError("catalog") from None

    def _load(self, fd: int, backup_id: UUID) -> list[dict]:
        os.lseek(fd, 0, os.SEEK_SET)
        content = bytearray()
        while len(content) <= _LIMIT:
            part = os.read(fd, min(65536, _LIMIT + 1 - len(content)))
            if not part:
                break
            content.extend(part)
        if len(content) > _LIMIT or (content and not content.endswith(b"\n")):
            raise fs.BackupStorageError("catalog")
        records, previous = [], "0" * 64
        try:
            for sequence, line in enumerate(content.splitlines(), 1):
                record = json.loads(line)
                if not isinstance(record, dict) or set(record) != {"backup_id", "sequence", "previous", "payload", "signature"}:
                    raise ValueError
                signature = record["signature"]
                unsigned = {key: value for key, value in record.items() if key != "signature"}
                expected = hmac.new(self.key, _json(unsigned), hashlib.sha256).hexdigest()
                if (record["backup_id"] != str(backup_id) or type(record["sequence"]) is not int
                        or record["sequence"] != sequence or record["previous"] != previous
                        or not isinstance(signature, str) or not hmac.compare_digest(signature, expected)
                        or _json(record) != line):
                    raise ValueError
                payload = record["payload"]
                if not isinstance(payload, dict) or set(payload) != {"event", "at", "data"}:
                    raise ValueError
                records.append(record)
                previous = signature
        except (ValueError, TypeError, KeyError):
            raise fs.BackupStorageError("catalog") from None
        return records

    def events(self, backup_id: UUID) -> list[dict]:
        name = _identifier(backup_id) + ".events"
        with self._directory() as directory_fd, fs.lock(directory_fd, name + ".lock"):
            try:
                fd = fs.open_file(directory_fd, name, os.O_RDONLY)
            except FileNotFoundError:
                return []
            try:
                return self._load(fd, backup_id)
            finally:
                os.close(fd)

    def append(self, backup_id: UUID, event: str, *, at: datetime, **values) -> dict:
        name = _identifier(backup_id) + ".events"
        payload = _payload(event, at, values)
        with self._directory() as directory_fd, fs.lock(directory_fd, name + ".lock"):
            fd = fs.open_file(directory_fd, name, os.O_RDWR, create=True)
            try:
                existing = self._load(fd, backup_id)
                record = {"backup_id": str(backup_id), "sequence": len(existing) + 1,
                          "previous": existing[-1]["signature"] if existing else "0" * 64,
                          "payload": payload}
                record["signature"] = hmac.new(self.key, _json(record), hashlib.sha256).hexdigest()
                content = _json(record) + b"\n"
                if os.fstat(fd).st_size + len(content) > _LIMIT:
                    raise fs.BackupStorageError("catalog")
                os.lseek(fd, 0, os.SEEK_END)
                fs.write_all(fd, content)
                os.fsync(fd)
                os.fsync(directory_fd)
                return record
            finally:
                os.close(fd)
