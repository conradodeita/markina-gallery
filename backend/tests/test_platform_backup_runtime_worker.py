"""Execução operacional isolada. O provider Workspace é completamente sintético."""

from __future__ import annotations

import io
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.platform_backup.runtime_config import DESTINATION_MARKER, BackupKeyring, RuntimeConfig
from app.platform_backup.runtime_worker import run_due
from app.platform_backup.worker import GlobalSnapshot
from app.platform_backup.workspace_store import FILES_ENDPOINT, WorkspaceDriveBackupStore
from tests.test_platform_backup_workspace_store import SyntheticDrive

DATE = datetime(2026, 11, 17, 8, 30, tzinfo=UTC)
KEY_ID = "backup-123456789abc"
FICTITIOUS_DATA = b"PGDMP-fictitious-tenant-snapshot"

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Runtime usa armazenamento POSIX")


class Destination(SyntheticDrive):
    def __init__(self):
        super().__init__()
        self.private = True

    def get(self, url, **kwargs):
        if url == FILES_ENDPOINT + "/" + self.folder_id:
            return httpx.Response(200, json={
                "id": self.folder_id, "ownedByMe": True, "isAppAuthorized": True, "trashed": False,
                "mimeType": "application/vnd.google-apps.folder", "appProperties": dict(DESTINATION_MARKER),
                "capabilities": {"canAddChildren": True},
            })
        if url == FILES_ENDPOINT + "/" + self.folder_id + "/permissions":
            roles = [{"type": "user", "role": "owner"}]
            if not self.private:
                roles.append({"type": "anyone", "role": "reader"})
            return httpx.Response(200, json={"permissions": roles})
        return super().get(url, **kwargs)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = tmp_path / "backup"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    (root / "catalog").mkdir(mode=0o700)
    drive = Destination()
    keyring = BackupKeyring(uuid4(), KEY_ID, MappingProxyType({KEY_ID: bytes(range(32))}))
    config = RuntimeConfig(keyring, uuid4(), drive.folder_id, True)
    monkeypatch.setattr("app.platform_backup.runtime_worker.WORK_ROOT", root)
    monkeypatch.setattr("app.platform_backup.runtime_worker.load_runtime_config", lambda: config)
    monkeypatch.setenv("APP_ENV", "production")
    snapshots = []

    @contextmanager
    def snapshot(schema_revision):
        snapshots.append(schema_revision)
        yield GlobalSnapshot(io.BytesIO(FICTITIOUS_DATA), {"MARKER": "synthetic-no-secret"})

    def store(current):
        return WorkspaceDriveBackupStore(
            current.destination_id, current.parent_folder_id, SecretStr(drive.token), transport=drive,
        )

    def tick():
        return run_due(schema_revision="20261113_0126", at=DATE, snapshot=snapshot, workspace=store)

    return tick, drive, snapshots, root


def test_daily_retry_preserves_snapshot_and_remote_identity(runtime):
    run, drive, snapshots, root = runtime
    first = run()
    second = run()
    assert first.status == "copies_verified"
    assert first == second
    assert snapshots == ["20261113_0126"]
    assert drive.upload_starts == 1
    local = (root / "artifacts" / f"{first.backup_id}.pypb").read_bytes()
    assert local == drive.bodies["synthetic_file_1"]
    assert FICTITIOUS_DATA not in local and b"synthetic-no-secret" not in local
    events = (root / "catalog" / f"{first.backup_id}.events").read_text()
    assert '"event":"verified"' in events
    assert '"event":"restore_verified"' not in events


def test_destination_change_aborts_before_snapshot_or_upload(runtime):
    run, drive, snapshots, _ = runtime
    drive.private = False
    result = run()
    assert result.status == "failed" and result.error == "authorization"
    assert not snapshots and drive.upload_starts == 0


def test_quota_failure_preserves_local_ciphertext_and_recovers_without_new_dump(runtime):
    run, drive, snapshots, root = runtime
    drive.list_status = 429
    first = run()
    assert first.status == "failed" and first.error == "quota"
    local = root / "artifacts" / f"{first.backup_id}.pypb"
    ciphertext = local.read_bytes()
    drive.list_status = 200
    second = run()
    assert second.status == "copies_verified" and second.backup_id == first.backup_id
    assert snapshots == ["20261113_0126"]
    assert ciphertext == local.read_bytes() == drive.bodies["synthetic_file_1"]
