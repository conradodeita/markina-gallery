"""Somente bytes/chaves sintéticos; nenhuma conexão de banco ou provedor."""

import hashlib
import io
import struct
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup import archive


@pytest.fixture
def context():
    return archive.BackupContext(
        uuid4(), uuid4(), "20261105_0106", "test", datetime.now(UTC)
    )


@pytest.fixture
def key():
    return bytes(range(32))


def sealed(content, context, key):
    result = io.BytesIO()
    receipt = archive.seal_archive(io.BytesIO(content), result, key=key, context=context)
    return result.getvalue(), receipt


class PartialReader(io.BytesIO):
    def __init__(self, value):
        super().__init__(value)
        self.requests = []

    def read(self, count=-1):
        assert 0 < count <= archive.CHUNK_SIZE
        self.requests.append(count)
        return super().read(min(count, 127))


def test_streaming_roundtrip_receipt_and_closed_staging(context, key):
    clear = b"private-synthetic-config-and-dump\x00" * 70000
    source = PartialReader(clear)
    output = io.BytesIO()
    receipt = archive.seal_archive(source, output, key=key, context=context)
    encrypted = output.getvalue()
    assert clear[:200] not in encrypted
    assert key not in encrypted
    assert receipt.sha256 == hashlib.sha256(encrypted).hexdigest()
    assert receipt.size_bytes == len(encrypted)
    assert receipt.backup_id == context.backup_id
    with archive.open_archive(PartialReader(encrypted), key=key, expected=context) as reopened:
        handle = reopened.stream
        assert reopened.size_bytes == len(clear)
        assert handle.read() == clear
        assert "private-synthetic" not in repr(reopened)
    assert handle.closed


@pytest.mark.parametrize("part", ["magic", "length", "header", "nonce", "ciphertext", "tag"])
def test_tampered_archive_never_yields_plaintext(context, key, part):
    encrypted, _ = sealed(b"synthetic-personal-financial-data", context, key)
    header_size = struct.unpack(">I", encrypted[len(archive.MAGIC):len(archive.MAGIC) + 4])[0]
    nonce_start = len(archive.MAGIC) + 4 + header_size
    positions = {
        "magic": 0,
        "length": len(archive.MAGIC),
        "header": len(archive.MAGIC) + 4 + 2,
        "nonce": nonce_start,
        "ciphertext": nonce_start + 12,
        "tag": len(encrypted) - 1,
    }
    changed = bytearray(encrypted)
    changed[positions[part]] ^= 1
    entered = False
    with (
        pytest.raises(archive.BackupArchiveError),
        archive.open_archive(io.BytesIO(changed), key=key, expected=context),
    ):
        entered = True
    assert not entered


@pytest.mark.parametrize("mutation", ["cut_header", "cut_body", "cut_tag", "append"])
def test_truncated_or_extended_archive_is_refused(context, key, mutation):
    encrypted, _ = sealed(b"synthetic-dump", context, key)
    changed = {
        "cut_header": encrypted[:12],
        "cut_body": encrypted[:-20],
        "cut_tag": encrypted[:-1],
        "append": encrypted + b"untrusted-trailing-data",
    }[mutation]
    with (
        pytest.raises(archive.BackupArchiveError),
        archive.open_archive(io.BytesIO(changed), key=key, expected=context),
    ):
        pytest.fail("Restaurador recebeu arquivo inválido")


@pytest.mark.parametrize("field", ["instance_id", "backup_id", "schema_revision", "environment", "created_at"])
def test_foreign_context_is_refused_before_staging(context, key, field, monkeypatch):
    encrypted, _ = sealed(b"synthetic-global-dump", context, key)
    changes = {
        "instance_id": uuid4(),
        "backup_id": uuid4(),
        "schema_revision": "20261103_0097",
        "environment": "development",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    expected = replace(context, **{field: changes[field]})

    def forbidden(*args, **kwargs):
        pytest.fail("Contexto divergente chegou ao staging")

    monkeypatch.setattr(archive.tempfile, "TemporaryFile", forbidden)
    with (
        pytest.raises(archive.BackupArchiveError),
        archive.open_archive(io.BytesIO(encrypted), key=key, expected=expected),
    ):
        pytest.fail("Contexto divergente foi aceito")


def test_wrong_key_closes_private_staging_without_yield(context, key, monkeypatch):
    encrypted, _ = sealed(b"synthetic-sensitive-config", context, key)
    original = archive.tempfile.TemporaryFile
    handles = []

    def temporary(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(archive.tempfile, "TemporaryFile", temporary)
    with (
        pytest.raises(archive.BackupArchiveError),
        archive.open_archive(io.BytesIO(encrypted), key=b"x" * 32, expected=context),
    ):
        pytest.fail("Chave errada liberou plaintext")
    assert handles and all(handle.closed for handle in handles)


def test_production_is_refused_before_read_or_write(context, key, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    class Forbidden:
        def __getattr__(self, name):
            pytest.fail("Ambiente protegido acessou IO")

    with pytest.raises(archive.BackupArchiveError, match="somente no ensaio local"):
        archive.seal_archive(Forbidden(), Forbidden(), key=key, context=context)
    with (
        pytest.raises(archive.BackupArchiveError, match="somente no ensaio local"),
        archive.open_archive(Forbidden(), key=key, expected=context),
    ):
        pytest.fail("Ambiente protegido aceito")


@pytest.mark.parametrize("bad_key", [b"", b"x" * 16, b"x" * 31, b"x" * 33, None])
def test_missing_or_wrong_size_key_is_refused(context, bad_key):
    with pytest.raises(archive.BackupArchiveError, match="Chave de backup"):
        archive.seal_archive(io.BytesIO(b"data"), io.BytesIO(), key=bad_key, context=context)


def test_source_read_error_does_not_expose_secret_or_path(context, key):
    class Broken:
        def read(self, count):
            raise OSError("credential=/private/source;secret=never-log-this")

    with pytest.raises(archive.BackupArchiveError) as caught:
        archive.seal_archive(Broken(), io.BytesIO(), key=key, context=context)
    assert "credential" not in str(caught.value)
    assert "never-log" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_nonce_is_fresh_and_limits_are_enforced(context, key, monkeypatch):
    left, _ = sealed(b"data", context, key)
    right, _ = sealed(b"data", context, key)
    assert left != right
    monkeypatch.setattr(archive, "MAX_PLAINTEXT_BYTES", 3)
    with pytest.raises(archive.BackupArchiveError):
        sealed(b"data", context, key)
    with (
        pytest.raises(archive.BackupArchiveError),
        archive.open_archive(io.BytesIO(left), key=key, expected=context),
    ):
        pytest.fail("Limite excedido foi aceito")


@pytest.mark.parametrize("content", [b"", "not-bytes", None])
def test_invalid_stream_content_is_refused(context, key, content):
    class BadStream:
        def read(self, count):
            return content

    with pytest.raises(archive.BackupArchiveError):
        archive.seal_archive(BadStream(), io.BytesIO(), key=key, context=context)
