"""Configuração operacional e recuperação portátil sem segredos reais."""

from __future__ import annotations

import base64
import io
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.platform_backup.archive import (
    BackupArchiveError,
    BackupContext,
    _ProductionContext,
    _seal_archive,
)
from app.platform_backup.filesystem import BackupStorageError
from app.platform_backup.offline_recovery import restore_saved_archive
from app.platform_backup.payload import _build_payload
from app.platform_backup.restore import BackupRestoreError, RestoreTargetState
from app.platform_backup.runtime_config import (
    DESTINATION_MARKER,
    _binding,
    load_runtime_config,
    parse_recovery_keyring,
)

KEY_ID = "backup-f123456789ab"
KEY = bytes(range(32))
DATE = datetime(2026, 11, 17, tzinfo=UTC)


def dump(obj):
    return json.dumps(obj).encode()


@pytest.fixture
def documents():
    installation = uuid4()
    keyring = {"version": 1, "installation_id": str(installation), "active_key_id": KEY_ID,
               "keys": {KEY_ID: base64.b64encode(KEY).decode()}}
    destination = {"version": 1, "installation_id": str(installation), "destination_id": str(uuid4()),
                   "provider": "google-workspace", "scope": "drive.file", "marker": dict(DESTINATION_MARKER),
                   "parent_folder_id": "synthetic-folder-id", "environment": "production", "enabled": False}
    return keyring, destination


def test_portable_keyring_and_disabled_binding(documents):
    keyring, binding = documents
    parsed = parse_recovery_keyring(dump(keyring))
    config = _binding(dump(binding), parsed)
    assert not config.enabled
    assert config.parent_folder_id == "synthetic-folder-id"
    assert parsed.key_for(KEY_ID) == KEY
    assert repr(parsed).startswith("<app.platform_backup.runtime_config.")
    with pytest.raises(BackupStorageError, match="authorization"):
        parsed.key_for("unknown")


@pytest.mark.parametrize("edit", [
    {"scope": "drive"}, {"parent_folder_id": "folder/other"}, {"environment": "test"},
    {"installation_id": str(uuid4())}, {"enabled": 1}, {"marker": {}},
])
def test_binding_rejects_drift(documents, edit):
    keyring, binding = documents
    with pytest.raises(BackupStorageError, match="unsafe"):
        _binding(dump({**binding, **edit}), parse_recovery_keyring(dump(keyring)))


def test_rejects_duplicate_fields_and_incorrect_key(documents):
    ring, _ = documents
    with pytest.raises(BackupStorageError, match="authorization"):
        parse_recovery_keyring(dump({**ring, "keys": {KEY_ID: "YQ=="}}))
    with pytest.raises(BackupStorageError, match="authorization"):
        parse_recovery_keyring(dump(ring)[:-1] + b', "version": 1}')


def test_rejects_missing_config_and_nonproduction(monkeypatch, tmp_path):
    monkeypatch.setattr("app.platform_backup.runtime_config.CONFIG_ROOT", tmp_path / "missing")
    for env in ("test", "production"):
        monkeypatch.setenv("APP_ENV", env)
        with pytest.raises(BackupStorageError, match="unsafe"):
            load_runtime_config()


@pytest.mark.skipif(os.name != "posix" or getattr(os, "geteuid", lambda: -1)() != 0,
                    reason="Permissões root do leitor são ensaiadas em Linux isolado")
def test_secure_files_reject_mode_symlink_and_hardlink(documents, monkeypatch):
    from pathlib import Path
    from tempfile import TemporaryDirectory

    ring, binding = documents
    monkeypatch.setenv("APP_ENV", "production")
    # /root permanece root-owned mesmo quando TMPDIR aponta para /tmp.
    with TemporaryDirectory(dir="/root") as root:
        root = Path(root)
        monkeypatch.setattr("app.platform_backup.runtime_config.CONFIG_ROOT", root)
        key_path = root / "keyring.json"
        dest_path = root / "destination.json"
        for path, raw in ((key_path, ring), (dest_path, binding)):
            path.write_bytes(dump(raw))
            path.chmod(0o400)
        assert load_runtime_config().keyring.key_for(KEY_ID) == KEY
        key_path.chmod(0o444)
        with pytest.raises(BackupStorageError, match="unsafe"):
            load_runtime_config()
        key_path.chmod(0o400)
        (root / "linked-key").hardlink_to(key_path)
        with pytest.raises(BackupStorageError, match="unsafe"):
            load_runtime_config()
        key_path.unlink()
        key_path.symlink_to(root / "linked-key")
        with pytest.raises(BackupStorageError, match="unsafe"):
            load_runtime_config()


class EmptyTarget:
    def __init__(self):
        self.data = None
        self.instance = uuid4()

    def inspect(self):
        return RestoreTargetState(self.instance, "test", True, self.data is None, True)

    def restore(self, stream):
        self.data = stream.read()

    def verify(self, schema_revision):
        return self.data == b"PGDMP-fictional" and schema_revision == "schema_test"


def test_recovery_reads_production_archive_offline_and_rejects_tamper(documents, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    ring = parse_recovery_keyring(dump(documents[0]))
    with pytest.raises(BackupArchiveError):
        BackupContext(ring.installation_id, uuid4(), "schema_test", "production", DATE)
    context = _ProductionContext(ring.installation_id, uuid4(), "schema_test", "production", DATE, KEY_ID)
    package, encrypted = io.BytesIO(), io.BytesIO()
    _build_payload(io.BytesIO(b"PGDMP-fictional"), {"CONFIG": "fake"}, package, context=context)
    package.seek(0)
    receipt = _seal_archive(package, encrypted, key=KEY, context=context)
    new_target = EmptyTarget()
    report = restore_saved_archive(encrypted, keyring=ring, artifact=receipt, expected_schema="schema_test",
                                   target=new_target, at=DATE)
    assert new_target.data == b"PGDMP-fictional"
    assert report.configuration_items_checked == 1
    mismatch = EmptyTarget()
    with pytest.raises(BackupRestoreError):
        restore_saved_archive(encrypted, keyring=ring, artifact=receipt, expected_schema="other",
                              target=mismatch, at=DATE)
    altered = bytearray(encrypted.getvalue())
    altered[-1] ^= 1
    with pytest.raises(BackupRestoreError):
        restore_saved_archive(io.BytesIO(altered), keyring=ring, artifact=receipt, expected_schema="schema_test",
                              target=mismatch, at=DATE)
    assert mismatch.data is None
