"""Arquivo GCM em streaming; plaintext só é liberado após autenticação integral."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import struct
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import BinaryIO
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"PYPBACK1"
CHUNK_SIZE = 1024 * 1024
MAX_PLAINTEXT_BYTES = 32 * 1024**3
MAX_HEADER_BYTES = 8192
_NONCE_SIZE = 12
_TAG_SIZE = 16
_SCHEMA = re.compile(r"[a-zA-Z0-9_]{1,64}\Z")


class BackupArchiveError(ValueError):
    """Mensagem constante, sem paths, dados ou segredo da exceção original."""


def _local_runtime() -> None:
    if os.getenv("APP_ENV", "development") not in {"development", "test"}:
        raise BackupArchiveError("Operação de backup disponível somente no ensaio local.")


@dataclass(frozen=True)
class BackupContext:
    instance_id: UUID
    backup_id: UUID
    schema_revision: str
    environment: str
    created_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.instance_id, UUID)
            or not isinstance(self.backup_id, UUID)
            or not isinstance(self.schema_revision, str)
            or not _SCHEMA.fullmatch(self.schema_revision)
            or not self._valid_environment()
            or not isinstance(self.created_at, datetime)
            or self.created_at.utcoffset() != timedelta(0)
        ):
            raise BackupArchiveError("Contexto de backup inválido.")

    def _valid_environment(self) -> bool:
        return self.environment in {"development", "test"}

    def header(self) -> bytes:
        return json.dumps(
            {
                "version": 1,
                "scope": "global-database-config",
                "instance_id": str(self.instance_id),
                "backup_id": str(self.backup_id),
                "schema_revision": self.schema_revision,
                "environment": self.environment,
                "created_at": self.created_at.astimezone(timezone.utc).isoformat(),  # noqa: UP017 -- host Python 3.10
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")


@dataclass(frozen=True)
class ArchiveReceipt:
    backup_id: UUID
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _ProductionContext(BackupContext):
    """Contexto interno autenticado, vinculado à versão da chave operacional."""

    key_id: str

    def _valid_environment(self) -> bool:
        return (self.environment == "production" and isinstance(self.key_id, str)
                and re.fullmatch(r"backup-[0-9a-f]{12}", self.key_id) is not None)

    def header(self) -> bytes:
        base = json.loads(super().header())
        base.update(version=2, key_id=self.key_id)
        return json.dumps(base, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def describe_ciphertext(source: BinaryIO, backup_id: UUID) -> ArchiveReceipt:
    """Checksum limitado do ciphertext; não autentica nem qualifica restore."""
    _local_runtime()
    return _describe_ciphertext(source, backup_id)


def _describe_ciphertext(source: BinaryIO, backup_id: UUID) -> ArchiveReceipt:
    if not isinstance(backup_id, UUID):
        raise BackupArchiveError("Identidade de backup inválida.")
    try:
        source.seek(0)
        size, digest = 0, hashlib.sha256()
        while chunk := source.read(CHUNK_SIZE):
            if not isinstance(chunk, bytes) or len(chunk) > CHUNK_SIZE:
                raise ValueError
            size += len(chunk)
            if size > MAX_PLAINTEXT_BYTES + MAX_HEADER_BYTES + 64:
                raise ValueError
            digest.update(chunk)
        if size == 0 or not isinstance(chunk, bytes):
            raise ValueError
        source.seek(0)
        return ArchiveReceipt(backup_id, size, digest.hexdigest())
    except (OSError, ValueError, TypeError, AttributeError):
        raise BackupArchiveError("Checksum do arquivo indisponível.") from None


def verify_ciphertext(source: BinaryIO, receipt: ArchiveReceipt) -> None:
    _local_runtime()
    _verify_ciphertext(source, receipt)


def _verify_ciphertext(source: BinaryIO, receipt: ArchiveReceipt) -> None:
    if (not isinstance(receipt, ArchiveReceipt) or not isinstance(receipt.backup_id, UUID)
            or type(receipt.size_bytes) is not int
            or not 0 < receipt.size_bytes <= MAX_PLAINTEXT_BYTES + MAX_HEADER_BYTES + 64
            or not isinstance(receipt.sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt.sha256)):
        raise BackupArchiveError("Recibo de arquivo inválido.")
    if _describe_ciphertext(source, receipt.backup_id) != receipt:
        raise BackupArchiveError("Checksum do arquivo divergente.")


@dataclass(frozen=True, repr=False)
class AuthenticatedContent:
    stream: BinaryIO = field(repr=False)
    size_bytes: int

    def __repr__(self) -> str:
        return "AuthenticatedContent(<redacted>)"


def _key(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise BackupArchiveError("Chave de backup indisponível.")
    return value


def _write_all(stream: BinaryIO, value: bytes) -> None:
    pending = memoryview(value)
    while pending:
        count = stream.write(pending)
        if type(count) is not int or not 0 < count <= len(pending):
            raise ValueError
        pending = pending[count:]


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        part = stream.read(count - len(result))
        if not isinstance(part, bytes) or not part or len(part) > count - len(result):
            raise ValueError
        result.extend(part)
    return bytes(result)


def seal_archive(
    source: BinaryIO, destination: BinaryIO, *, key: bytes, context: BackupContext
) -> ArchiveReceipt:
    """O caller publica o ciphertext somente após receber o receipt completo."""
    _local_runtime()
    return _seal_archive(source, destination, key=key, context=context)


def _seal_archive(
    source: BinaryIO, destination: BinaryIO, *, key: bytes, context: BackupContext
) -> ArchiveReceipt:
    key = _key(key)
    if not isinstance(context, BackupContext):
        raise BackupArchiveError("Contexto de backup inválido.")
    try:
        header = context.header()
        if not 0 < len(header) <= MAX_HEADER_BYTES:
            raise ValueError
        first = source.read(CHUNK_SIZE)
        if not isinstance(first, bytes) or not 0 < len(first) <= CHUNK_SIZE:
            raise ValueError
        nonce = secrets.token_bytes(_NONCE_SIZE)
        prefix = MAGIC + struct.pack(">I", len(header)) + header
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(prefix)
        digest = hashlib.sha256()
        size = 0

        def emit(value: bytes) -> None:
            nonlocal size
            _write_all(destination, value)
            digest.update(value)
            size += len(value)

        emit(prefix + nonce)
        part, clear_size = first, 0
        while part:
            if not isinstance(part, bytes) or len(part) > CHUNK_SIZE:
                raise ValueError
            clear_size += len(part)
            if clear_size > MAX_PLAINTEXT_BYTES:
                raise ValueError
            emit(encryptor.update(part))
            part = source.read(CHUNK_SIZE)
        if not isinstance(part, bytes):
            raise TypeError
        emit(encryptor.finalize())
        emit(encryptor.tag)
        destination.flush()
        return ArchiveReceipt(context.backup_id, size, digest.hexdigest())
    except (OSError, ValueError, TypeError, AttributeError):
        raise BackupArchiveError("Não foi possível produzir o arquivo cifrado.") from None


@contextmanager
def open_archive(
    source: BinaryIO, *, key: bytes, expected: BackupContext
) -> Iterator[AuthenticatedContent]:
    """Staging anônimo privado; nenhum handle é entregue antes de GCM.finalize()."""
    _local_runtime()
    with _open_archive(source, key=key, expected=expected) as content:
        yield content


@contextmanager
def _open_archive(
    source: BinaryIO, *, key: bytes, expected: BackupContext
) -> Iterator[AuthenticatedContent]:
    key = _key(key)
    if not isinstance(expected, BackupContext):
        raise BackupArchiveError("Contexto de backup inválido.")
    staged = None
    try:
        if not source.seekable():
            raise ValueError
        source.seek(0, os.SEEK_END)
        total_size = source.tell()
        if type(total_size) is not int or total_size <= len(MAGIC) + 4 + _NONCE_SIZE + _TAG_SIZE:
            raise ValueError
        source.seek(0)
        if _read_exact(source, len(MAGIC)) != MAGIC:
            raise ValueError
        encoded_length = _read_exact(source, 4)
        header_size = struct.unpack(">I", encoded_length)[0]
        if not 0 < header_size <= MAX_HEADER_BYTES:
            raise ValueError
        header = _read_exact(source, header_size)
        if header != expected.header():
            raise ValueError
        nonce = _read_exact(source, _NONCE_SIZE)
        ciphertext_start = source.tell()
        remaining = total_size - ciphertext_start - _TAG_SIZE
        if not 0 < remaining <= MAX_PLAINTEXT_BYTES:
            raise ValueError
        source.seek(total_size - _TAG_SIZE)
        tag = _read_exact(source, _TAG_SIZE)
        source.seek(ciphertext_start)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        decryptor.authenticate_additional_data(MAGIC + encoded_length + header)
        # Fechado tanto em falha de autenticação quanto no fim do contexto cedido.
        staged = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115
        clear_size = 0
        while remaining:
            chunk = _read_exact(source, min(CHUNK_SIZE, remaining))
            clear = decryptor.update(chunk)
            _write_all(staged, clear)
            clear_size += len(clear)
            remaining -= len(chunk)
        if _read_exact(source, _TAG_SIZE) != tag or source.read(1) != b"":
            raise ValueError
        _write_all(staged, decryptor.finalize())
        staged.flush()
        staged.seek(0)
    except (OSError, ValueError, TypeError, AttributeError, InvalidTag):
        if staged is not None:
            staged.close()
        raise BackupArchiveError("Arquivo de backup não autenticado ou incompatível.") from None
    try:
        yield AuthenticatedContent(staged, clear_size)
    finally:
        staged.close()
