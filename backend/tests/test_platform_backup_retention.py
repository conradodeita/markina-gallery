"""Política global pura e remoção somente de cópias sintéticas redundantes."""

import io
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.platform_backup import filesystem as fs
from app.platform_backup.archive import ArchiveReceipt, BackupArchiveError, BackupContext
from app.platform_backup.catalog import BackupCatalog
from app.platform_backup.restore import RestoreTargetState, record_restore, restore_global
from app.platform_backup.retention import (
    monthly_restore_due,
    plan_retention,
    remove_redundant_local_copy,
)
from app.platform_backup.storage import LocalBackupStore
from app.platform_backup.worker import GlobalSnapshot, LocalBackupWorker

NOW = datetime(2026, 11, 6, 23, 59, tzinfo=UTC)


def history(instance=None):
    instance = instance or uuid4()
    return tuple(BackupContext(instance, uuid4(), "20261105_0106", "test", NOW - timedelta(days=i))
                 for i in range(98))


def test_global_7_4_3_uses_union_of_utc_periods_without_duplicate_tiers():
    points = history()
    plan = plan_retention(points, restored_ids=frozenset(), as_of=NOW)
    dates = {point.created_at.strftime("%m-%d") for point in points if point.backup_id in plan.retained}
    assert dates == {"11-06", "11-05", "11-04", "11-03", "11-02", "11-01", "10-31",
                     "10-25", "10-18", "09-30"}
    assert plan.retained.isdisjoint(plan.expired)
    assert len(plan.retained | plan.expired) == len(points)


def test_latest_recoverable_is_kept_even_when_outside_retention_periods():
    points = history()
    oldest = points[-1]
    plan = plan_retention(points, restored_ids=frozenset({oldest.backup_id}), as_of=NOW)
    assert oldest.backup_id in plan.retained
    assert oldest.backup_id not in plan.expired
    sparse = (points[0], oldest)
    assert not plan_retention(sparse, restored_ids=frozenset(), as_of=NOW).expired


@pytest.mark.parametrize("invalid", ["future", "foreign", "duplicate", "unknown_restore"])
def test_invalid_retention_history_is_refused(invalid):
    points = history()
    restored = frozenset()
    if invalid == "future":
        points = (replace(points[0], created_at=NOW + timedelta(days=1)), *points[1:])
    elif invalid == "foreign":
        points = (replace(points[0], instance_id=uuid4()), *points[1:])
    elif invalid == "duplicate":
        points = (*points, points[0])
    else:
        restored = frozenset({uuid4()})
    with pytest.raises(fs.BackupStorageError):
        plan_retention(points, restored_ids=restored, as_of=NOW)


def test_monthly_restore_due_is_utc_calendar_based_and_rejects_future():
    assert monthly_restore_due(None, now=NOW)
    assert monthly_restore_due(datetime(2026, 10, 31, tzinfo=UTC), now=NOW)
    assert not monthly_restore_due(datetime(2026, 11, 1, tzinfo=UTC), now=NOW)
    with pytest.raises(fs.BackupStorageError):
        monthly_restore_due(NOW + timedelta(seconds=1), now=NOW)


@pytest.fixture
def copies(tmp_path):
    if os.name != "posix":
        pytest.skip("Remoção local usa contrato POSIX")
    roots = []
    for name in ("work", "catalog", "a", "b"):
        root = tmp_path / name
        root.mkdir(mode=0o700)
        roots.append(root)
    key, instance = bytes(range(32)), uuid4()

    @contextmanager
    def snapshot(context):
        yield GlobalSnapshot(io.BytesIO(b"PGDMP-synthetic-retention-dump"), {"KEY": "synthetic"})

    catalog = BackupCatalog(roots[1], key)
    stores = (LocalBackupStore(roots[2], uuid4(), "synthetic-a"),
              LocalBackupStore(roots[3], uuid4(), "synthetic-b"))
    worker = LocalBackupWorker(instance, "20261105_0106", "test", key, roots[0],
                                catalog, stores, snapshot)
    old_time = NOW - timedelta(days=200)
    report = worker.run_due(old_time)
    assert report.status == "copies_verified"
    context = catalog.daily_context(instance, worker.schema_revision, "test", old_time)
    prepared = next(event["payload"]["data"] for event in catalog.events(context.backup_id)
                    if event["payload"]["event"] == "prepared")
    artifact = ArchiveReceipt(context.backup_id, prepared["size_bytes"], prepared["artifact_sha256"])

    class Target:
        def inspect(self):
            return RestoreTargetState(uuid4(), "test", True, True, True)

        def restore(self, dump):
            assert dump.read().startswith(b"PGDMP")

        def verify(self, schema):
            return schema == context.schema_revision

    with stores[1].open(context.backup_id) as source:
        restored = restore_global(source, key=key, expected=context, artifact=artifact,
                                  target=Target(), at=NOW)
    # História hipotética dos demais dias; somente a prova do conjunto candidato
    # autoriza esta remoção de cópia, sendo revalidada separadamente no catálogo.
    points = (*history(instance), context)
    plan = plan_retention(points, restored_ids=frozenset({points[0].backup_id, context.backup_id}),
                          as_of=NOW)
    assert context.backup_id in plan.expired
    return {"context": context, "artifact": artifact, "plan": plan, "candidate": stores[0],
            "survivor": stores[1], "catalog": catalog, "key": key,
            "confirmation": f"DELETE_LOCAL_BACKUP_COPY:{context.backup_id}:{stores[0].destination_id}"}, restored


def authorize(parameters, receipt):
    record_restore(parameters["catalog"], receipt, context=parameters["context"],
                   destination_id=parameters["survivor"].destination_id)


def path(store, context):
    return store.root / f"{context.backup_id}.pypb"


def test_only_expired_redundant_copy_is_removed_with_audit(copies):
    parameters, receipt = copies
    authorize(parameters, receipt)
    candidate = path(parameters["candidate"], parameters["context"])
    survivor = path(parameters["survivor"], parameters["context"])
    before = survivor.read_bytes()
    remove_redundant_local_copy(**parameters)
    assert not candidate.exists()
    assert survivor.read_bytes() == before
    events = parameters["catalog"].events(parameters["context"].backup_id)
    assert [event["payload"]["event"] for event in events[-2:]] == ["deletion_planned", "deleted"]
    assert events[-1]["payload"]["data"]["survivor_destination_id"] == str(parameters["survivor"].destination_id)


@pytest.mark.parametrize("missing", ["proof", "confirmation", "independence", "root", "retained", "key"])
def test_missing_gate_never_removes_last_copy(copies, missing):
    parameters, receipt = copies
    if missing != "proof":
        authorize(parameters, receipt)
    original_candidate = path(parameters["candidate"], parameters["context"])
    before = original_candidate.read_bytes()
    if missing == "confirmation":
        parameters["confirmation"] = ""
    elif missing == "independence":
        parameters["survivor"] = replace(parameters["survivor"],
                                           failure_domain=parameters["candidate"].failure_domain)
    elif missing == "root":
        parameters["survivor"] = replace(parameters["survivor"], root=parameters["candidate"].root)
    elif missing == "retained":
        parameters["plan"] = plan_retention((parameters["context"],),
                                              restored_ids=frozenset({parameters["context"].backup_id}),
                                              as_of=NOW)
    elif missing == "key":
        parameters["key"] = b"z" * 32
    with pytest.raises((fs.BackupStorageError, BackupArchiveError)):
        remove_redundant_local_copy(**parameters)
    assert original_candidate.read_bytes() == before


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_invalid_survivor_does_not_authorize_removal(copies, damage):
    parameters, receipt = copies
    authorize(parameters, receipt)
    candidate = path(parameters["candidate"], parameters["context"])
    survivor = path(parameters["survivor"], parameters["context"])
    before = candidate.read_bytes()
    if damage == "missing":
        survivor.unlink()
    else:
        survivor.write_bytes(b"corrupt")
    with pytest.raises((fs.BackupStorageError, BackupArchiveError)):
        remove_redundant_local_copy(**parameters)
    assert candidate.read_bytes() == before


def test_concurrent_copy_lock_blocks_disposal(copies):
    parameters, receipt = copies
    authorize(parameters, receipt)
    survivor = parameters["survivor"]
    with (
        fs.directory(survivor.root) as directory_fd,
        fs.lock(directory_fd, str(parameters["context"].backup_id) + ".lock"),
        pytest.raises(fs.BackupStorageError, match="busy"),
    ):
        remove_redundant_local_copy(**parameters)
    assert path(parameters["candidate"], parameters["context"]).exists()
