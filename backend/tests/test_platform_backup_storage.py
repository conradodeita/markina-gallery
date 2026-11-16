"""IO POSIX somente em diretórios sintéticos criados pelo pytest."""

import errno
import hashlib
import io
import os
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup import filesystem as fs
from app.platform_backup.archive import CHUNK_SIZE, ArchiveReceipt, BackupArchiveError
from app.platform_backup.catalog import BackupCatalog
from app.platform_backup.storage import LocalBackupStore

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Contrato de storage POSIX")


@pytest.fixture
def root(tmp_path):
    result = tmp_path / "private"
    result.mkdir(mode=0o700)
    return result


@pytest.fixture
def catalog(root):
    return BackupCatalog(root, bytes(range(32)))


@pytest.fixture
def store(root):
    return LocalBackupStore(root, uuid4(), "synthetic-store-a")


def artifact(data):
    return ArchiveReceipt(uuid4(), len(data), hashlib.sha256(data).hexdigest())


def test_catalog_survives_reopen_without_overwriting_previous_event(catalog, root):
    backup_id, destination_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    first = catalog.append(backup_id, "prepared", at=now, artifact_sha256="a" * 64,
                           size_bytes=10)
    before = (root / f"{backup_id}.events").read_bytes()
    reopened = BackupCatalog(root, bytes(range(32)))
    second = reopened.append(backup_id, "uploaded", at=now, destination_id=destination_id)
    assert (root / f"{backup_id}.events").read_bytes().startswith(before)
    assert second["sequence"] == 2
    assert second["previous"] == first["signature"]
    assert reopened.events(backup_id) == [first, second]
    assert bytes(range(32)) not in before
    assert (root / f"{backup_id}.events").stat().st_mode & 0o777 == 0o600
    assert str(root) not in repr(reopened)


@pytest.mark.parametrize("mutation", ["truncate", "alter", "reorder", "wrong_key"])
def test_catalog_integrity_refuses_resume_and_preserves_evidence(catalog, root, mutation):
    identifier = uuid4()
    for event in ("prepared", "uploaded"):
        catalog.append(identifier, event, at=datetime.now(UTC))
    path = root / f"{identifier}.events"
    data = path.read_bytes()
    if mutation == "truncate":
        path.write_bytes(data[:-1])
    elif mutation == "alter":
        path.write_bytes(data.replace(b"prepared", b"verified", 1))
    elif mutation == "reorder":
        path.write_bytes(b"\n".join(reversed(data.splitlines())) + b"\n")
    else:
        catalog = BackupCatalog(root, b"x" * 32)
    before = path.read_bytes()
    with pytest.raises(fs.BackupStorageError, match="catalog"):
        catalog.append(identifier, "verified", at=datetime.now(UTC))
    assert path.read_bytes() == before


def test_catalog_rejects_secret_payload_and_busy_concurrent_writer(catalog, root):
    identifier = uuid4()
    with pytest.raises(fs.BackupStorageError, match="catalog"):
        catalog.append(identifier, "failed", at=datetime.now(UTC), secret="never-log")
    with (
        fs.directory(root) as directory_fd,
        fs.lock(directory_fd, f"{identifier}.events.lock"),
        pytest.raises(fs.BackupStorageError, match="busy"),
    ):
        catalog.append(identifier, "prepared", at=datetime.now(UTC))
    assert catalog.events(identifier) == []
    assert catalog.append(identifier, "prepared", at=datetime.now(UTC))["sequence"] == 1


def test_upload_is_reopened_idempotent_and_immutable(store, root):
    data = b"synthetic-ciphertext" * 1000
    receipt = artifact(data)
    first = store.upload(io.BytesIO(data), receipt)
    assert store.upload(io.BytesIO(data), receipt) == first
    with store.open(receipt.backup_id) as source:
        assert source.read() == data
    with pytest.raises(fs.BackupStorageError, match="conflict"):
        store.upload(io.BytesIO(b"changed"), replace(receipt, sha256="a" * 64))
    assert (root / f"{receipt.backup_id}.pypb").read_bytes() == data
    assert (root / f"{receipt.backup_id}.pypb").stat().st_mode & 0o777 == 0o600
    assert not (root / f"{receipt.backup_id}.partial").exists()


def test_interrupted_upload_resumes_only_matching_prefix(store, root):
    data = b"a" * CHUNK_SIZE + b"b" * 1000
    receipt = artifact(data)

    class Interrupted(io.BytesIO):
        def read(self, count=-1):
            if self.tell() >= CHUNK_SIZE:
                raise OSError(errno.ETIMEDOUT, "secret=https://private/token")
            return super().read(count)

    with pytest.raises(fs.BackupStorageError) as caught:
        store.upload(Interrupted(data), receipt)
    assert "private" not in str(caught.value)
    partial = root / f"{receipt.backup_id}.partial"
    assert partial.stat().st_size == CHUNK_SIZE
    assert not (root / f"{receipt.backup_id}.pypb").exists()
    resumed = store.upload(io.BytesIO(data), receipt)
    assert resumed.sha256 == receipt.sha256
    assert (root / f"{receipt.backup_id}.pypb").read_bytes() == data


@pytest.mark.parametrize("failure,expected", [(errno.ENOSPC, "quota"), (errno.EACCES, "authorization")])
def test_quota_and_access_errors_are_sanitized_and_partial_is_preserved(store, root, monkeypatch,
                                                                      failure, expected):
    data = b"ciphertext"
    receipt = artifact(data)

    def fail(*args):
        raise OSError(failure, "token=never-log-this;private-path")

    with monkeypatch.context() as patch:
        patch.setattr(fs, "write_all", fail)
        with pytest.raises(fs.BackupStorageError) as caught:
            store.upload(io.BytesIO(data), receipt)
    assert caught.value.code == expected
    assert "never-log" not in str(caught.value)
    assert (root / f"{receipt.backup_id}.partial").exists()
    assert not (root / f"{receipt.backup_id}.pypb").exists()
    store.upload(io.BytesIO(data), receipt)


def test_partial_conflict_and_wrong_checksum_never_publish(store, root):
    data = b"right-ciphertext"
    receipt = artifact(data)
    partial = root / f"{receipt.backup_id}.partial"
    partial.write_bytes(b"wrong-prefix")
    partial.chmod(0o600)
    with pytest.raises(fs.BackupStorageError, match="conflict"):
        store.upload(io.BytesIO(data), receipt)
    assert partial.read_bytes() == b"wrong-prefix"
    assert not (root / f"{receipt.backup_id}.pypb").exists()
    second = artifact(data)
    with pytest.raises(fs.BackupStorageError, match="checksum"):
        store.upload(io.BytesIO(data), replace(second, sha256="0" * 64))
    assert not (root / f"{second.backup_id}.pypb").exists()
    assert (root / f"{second.backup_id}.partial").read_bytes() == data


@pytest.mark.parametrize("unsafe", ["root_mode", "root_symlink", "file_symlink", "file_hardlink"])
def test_unsafe_storage_is_refused_without_touching_peer(store, root, tmp_path, unsafe):
    data = b"opaque-artifact"
    receipt = artifact(data)
    peer = tmp_path / "peer"
    peer.write_bytes(b"peer-must-survive")
    peer.chmod(0o600)
    if unsafe == "root_mode":
        root.chmod(0o755)
    elif unsafe == "root_symlink":
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)
        store = LocalBackupStore(link, uuid4(), "synthetic-b")
    elif unsafe == "file_symlink":
        (root / f"{receipt.backup_id}.partial").symlink_to(peer)
    else:
        os.link(peer, root / f"{receipt.backup_id}.partial")
    with pytest.raises(fs.BackupStorageError):
        store.upload(io.BytesIO(data), receipt)
    assert peer.read_bytes() == b"peer-must-survive"


def test_production_storage_refuses_before_creating_files(store, root, catalog, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    before = list(root.iterdir())
    with pytest.raises(BackupArchiveError):
        store.upload(io.BytesIO(b"data"), artifact(b"data"))
    with pytest.raises(BackupArchiveError):
        catalog.append(uuid4(), "prepared", at=datetime.now(UTC))
    assert list(root.iterdir()) == before
