"""Worker local com dump opaco sintético e stores temporários distintos."""

import io
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.platform_backup.archive import ArchiveReceipt, BackupArchiveError
from app.platform_backup.catalog import BackupCatalog
from app.platform_backup.filesystem import BackupStorageError
from app.platform_backup.restore import (
    BackupRestoreError,
    RestoreTargetState,
    record_restore,
    restore_global,
)
from app.platform_backup.storage import LocalBackupStore
from app.platform_backup.worker import GlobalSnapshot, LocalBackupWorker

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Coordenador usa storage POSIX")
NOW = datetime(2026, 11, 6, 12, tzinfo=UTC)


@pytest.fixture
def setup(tmp_path):
    roots = []
    for name in ("work", "catalog", "copy-a", "copy-b"):
        root = tmp_path / name
        root.mkdir(mode=0o700)
        roots.append(root)
    calls = []

    @contextmanager
    def snapshot(context):
        calls.append(context.backup_id)
        yield GlobalSnapshot(io.BytesIO(b"PGDMP-synthetic-global-data"),
                             {"SYNTHETIC_SECRET": "must-stay-encrypted"})

    key = bytes(range(32))
    worker = LocalBackupWorker(
        uuid4(), "20261105_0106", "test", key, roots[0], BackupCatalog(roots[1], key),
        (LocalBackupStore(roots[2], uuid4(), "synthetic-a"),
         LocalBackupStore(roots[3], uuid4(), "synthetic-b")), snapshot)
    return worker, calls


def test_daily_global_schedule_is_idempotent_and_never_claims_restore(setup):
    worker, calls = setup
    first = worker.run_due(NOW)
    assert first.status == "copies_verified"
    assert first.uploaded_count == first.verified_count == 2
    assert not first.errors
    events = worker.catalog.events(first.backup_id)
    assert not any(event["payload"]["event"] == "restore_verified" for event in events)
    second = worker.run_due(NOW + timedelta(hours=2))
    assert second.backup_id == first.backup_id
    assert len(calls) == 1
    assert worker.catalog.events(first.backup_id) == events
    encrypted = (worker.workspace / f"{first.backup_id}.pypb").read_bytes()
    assert b"must-stay-encrypted" not in encrypted
    assert b"synthetic-global-data" not in encrypted
    assert b"must-stay-encrypted" not in b"".join(
        file.read_bytes() for file in worker.catalog.root.iterdir())
    third = worker.run_due(NOW + timedelta(days=1))
    assert third.status == "copies_verified"
    assert third.backup_id != first.backup_id
    assert len(calls) == 2


@pytest.mark.parametrize("failure_kind", ["quota", "expired_credential"])
def test_retry_keeps_same_snapshot_and_successful_copy(setup, monkeypatch, failure_kind):
    worker, calls = setup
    original = LocalBackupStore.upload
    blocked = worker.stores[1].destination_id
    failures = []

    def upload(self, source, receipt):
        if self.destination_id == blocked and not failures:
            failures.append(True)
            raise BackupStorageError("authorization" if failure_kind == "expired_credential" else "quota")
        return original(self, source, receipt)

    monkeypatch.setattr(LocalBackupStore, "upload", upload)
    first = worker.run_due(NOW)
    assert first.status == "partial"
    assert first.verified_count == 1
    assert first.errors == (("authorization",) if failure_kind == "expired_credential" else ("quota",))
    second = worker.run_due(NOW + timedelta(minutes=1))
    assert second.status == "copies_verified"
    assert second.backup_id == first.backup_id
    assert len(calls) == 1
    assert any(event["payload"]["event"] == "failed"
               for event in worker.catalog.events(first.backup_id))


@pytest.mark.parametrize("damage", ["source_tamper", "source_missing", "copy_tamper"])
def test_artifact_drift_never_recreates_snapshot_or_overwrites_copies(setup, damage):
    worker, calls = setup
    first = worker.run_due(NOW)
    source = worker.workspace / f"{first.backup_id}.pypb"
    copy = worker.stores[0].root / f"{first.backup_id}.pypb"
    peer = worker.stores[1].root / f"{first.backup_id}.pypb"
    before = peer.read_bytes()
    if damage == "source_tamper":
        changed = bytearray(source.read_bytes())
        changed[-1] ^= 1
        source.write_bytes(changed)
    elif damage == "source_missing":
        source.unlink()
    else:
        copy.write_bytes(b"corrupt-existing-copy")
    result = worker.run_due(NOW + timedelta(minutes=1))
    assert result.status == ("partial" if damage == "copy_tamper" else "failed")
    assert len(calls) == 1
    assert peer.read_bytes() == before
    if damage == "copy_tamper":
        assert copy.read_bytes() == b"corrupt-existing-copy"


def test_interrupted_build_is_preserved_without_new_snapshot(setup):
    worker, calls = setup
    context = worker.catalog.daily_context(worker.instance_id, worker.schema_revision,
                                            worker.environment, NOW)
    partial = worker.workspace / f"{context.backup_id}.building"
    partial.write_bytes(b"interrupted-encrypted-artifact")
    partial.chmod(0o600)
    result = worker.run_due(NOW)
    assert result.status == "failed"
    assert "conflict" in result.errors
    assert calls == []
    assert partial.read_bytes() == b"interrupted-encrypted-artifact"


def test_foreign_daily_context_and_catalog_tamper_fail_closed(setup):
    worker, calls = setup
    worker.run_due(NOW)
    foreign = replace(worker, instance_id=uuid4())
    assert foreign.run_due(NOW).status == "failed"
    assert len(calls) == 1
    marker = worker.catalog.root / "day-2026-11-06.json"
    marker.write_bytes(b"truncated")
    assert worker.run_due(NOW).status == "failed"
    assert len(calls) == 1


def test_production_missing_key_and_duplicate_stores_are_refused(setup, monkeypatch):
    worker, calls = setup
    duplicate = replace(worker, stores=(worker.stores[0], worker.stores[0]))
    assert duplicate.run_due(NOW).status == "failed"
    assert calls == []
    with pytest.raises(BackupArchiveError):
        replace(worker, key=b"invalid").run_due(NOW)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(BackupArchiveError):
        worker.run_due(NOW)
    assert calls == []


def test_restore_receipt_requires_matching_verified_copy_and_context(setup):
    worker, _ = setup
    report = worker.run_due(NOW)
    context = worker.catalog.daily_context(worker.instance_id, worker.schema_revision,
                                            worker.environment, NOW)
    prepared = next(event["payload"]["data"] for event in worker.catalog.events(report.backup_id)
                    if event["payload"]["event"] == "prepared")
    artifact = ArchiveReceipt(context.backup_id, prepared["size_bytes"], prepared["artifact_sha256"])

    class Target:
        def inspect(self):
            return RestoreTargetState(uuid4(), "test", True, True, True)

        def restore(self, dump):
            assert dump.read() == b"PGDMP-synthetic-global-data"

        def verify(self, schema):
            return schema == worker.schema_revision

    with worker.stores[0].open(context.backup_id) as source:
        receipt = restore_global(source, key=worker.key, expected=context, artifact=artifact,
                                 target=Target(), at=NOW)
    with pytest.raises(BackupRestoreError):
        record_restore(worker.catalog, receipt, context=context, destination_id=uuid4())
    with pytest.raises(BackupRestoreError):
        record_restore(worker.catalog, replace(receipt, schema_revision="wrong_schema"),
                       context=context, destination_id=worker.stores[0].destination_id)
    record_restore(worker.catalog, receipt, context=context,
                   destination_id=worker.stores[0].destination_id)
    events = worker.catalog.events(context.backup_id)
    assert events[-1]["payload"]["event"] == "restore_verified"
    assert events[-1]["payload"]["data"]["restore_target_id"] == str(receipt.target_instance_id)
