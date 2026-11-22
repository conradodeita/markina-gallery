"""Provas sintéticas do vínculo owner-only do destino de backup."""

import json
import os
import stat
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.platform_backup import production_cli as cli
from app.platform_backup.filesystem import BackupStorageError


def _config(folder_id: str, *, enabled: bool = False):
    return SimpleNamespace(
        keyring=SimpleNamespace(installation_id=uuid4()),
        destination_id=uuid4(),
        parent_folder_id=folder_id,
        enabled=enabled,
    )


def _source():
    return SimpleNamespace(
        api_container="markina-gallery-api-1",
        api_image="sha256:synthetic-api-image",
        configuration={"APP_RELEASE": "synthetic-release"},
    )


def _prepare(monkeypatch, provider_reply: bytes):
    current = _config("old-folder")
    updated = SimpleNamespace(
        keyring=current.keyring,
        destination_id=current.destination_id,
        parent_folder_id="selected-global-folder",
        enabled=False,
    )
    source = _source()
    calls = {"attest_container": [], "docker": [], "workspace": [], "destination": [], "bind": []}
    monkeypatch.setattr(cli, "load_source_config", lambda: source)
    monkeypatch.setattr(cli, "attest_container", lambda *args, **kwargs:
                        calls["attest_container"].append((args, kwargs)))
    monkeypatch.setattr(cli, "_docker", lambda *args:
                        calls["docker"].append(args) or provider_reply)

    def workspace(candidate_source, candidate):
        calls["workspace"].append((candidate_source, candidate))
        return "synthetic-drive-store"

    monkeypatch.setattr(cli, "_workspace", workspace)
    monkeypatch.setattr(cli, "_attest_destination", lambda candidate, store:
                        calls["destination"].append((candidate, store)))
    monkeypatch.setattr(cli, "bind_folder_id", lambda folder_id:
                        calls["bind"].append(folder_id))
    configs = iter((current, updated))
    monkeypatch.setattr(cli, "load_runtime_config", lambda: next(configs))
    monkeypatch.setattr(cli, "_assert_backup_units_inert", lambda: None)
    return current, source, calls


def test_bind_selected_destination_revalidates_then_updates_only_disabled_destination(monkeypatch):
    current, source, calls = _prepare(monkeypatch, b'{"folder_id":"selected-global-folder"}')

    result = cli._bind_selected_destination()

    assert result.status == "destination_bound"
    assert len(calls["attest_container"]) == 1
    assert len(calls["docker"]) == 1
    assert cli._SELECTED_FOLDER_PROVIDER in calls["docker"][0]
    assert calls["docker"][0][-1] == source.configuration["APP_RELEASE"]
    candidate_source, candidate = calls["workspace"][0]
    assert candidate_source is source
    assert candidate.parent_folder_id == "selected-global-folder"
    assert candidate.destination_id == current.destination_id
    assert candidate.keyring is current.keyring
    assert candidate.enabled is False
    assert calls["destination"] == [(candidate, "synthetic-drive-store")]
    assert calls["bind"] == ["selected-global-folder"]


def test_bind_selected_destination_rejects_missing_or_malformed_selection_before_drive_write(monkeypatch):
    _current, _source_config, calls = _prepare(monkeypatch, b'{"folder_id":"../wrong"}')

    with pytest.raises(BackupStorageError, match="authorization"):
        cli._bind_selected_destination()

    assert calls["workspace"] == []
    assert calls["destination"] == []
    assert calls["bind"] == []


def test_bind_selected_destination_refuses_enabled_runtime_before_source_or_drive_access(monkeypatch):
    enabled = _config("old-folder", enabled=True)
    monkeypatch.setattr(cli, "load_runtime_config", lambda: enabled)
    monkeypatch.setattr(cli, "load_source_config", lambda: pytest.fail("não deveria carregar source"))
    monkeypatch.setattr(cli, "attest_container", lambda *_args, **_kwargs:
                        pytest.fail("não deveria inspecionar container"))

    with pytest.raises(BackupStorageError, match="unsafe"):
        cli._bind_selected_destination()


class SyntheticRehearsalStore:
    def __init__(self, *, delete_ok=True, read_content=None):
        self.delete_ok = delete_ok
        self.read_content = read_content
        self.uploaded = []
        self.deleted = []
        self.found_id = "synthetic-drive-object-id"

    def upload_rehearsal_item(self, *, name, content):
        self.uploaded.append((name, content))
        return SimpleNamespace(file_id=self.found_id)

    def read_rehearsal_item(self, *, file_id, name):
        assert file_id == self.found_id
        assert name == self.uploaded[0][0]
        return self.read_content if self.read_content is not None else self.uploaded[0][1]

    def delete_rehearsal_item(self, *, file_id, name):
        self.deleted.append((file_id, name))
        return self.delete_ok

    def find_rehearsal_item(self, *, name):
        return self.found_id if self.uploaded and name == self.uploaded[0][0] else None


def _prepare_synthetic_rehearsal(monkeypatch, store, *, pending=None):
    config = _config("synthetic-global-folder")
    source = _source()
    journals = {}
    calls = {"attest": [], "units": 0, "persist": [], "remove": []}
    monkeypatch.setattr(cli, "load_runtime_config", lambda: config)
    monkeypatch.setattr(cli, "_assert_backup_units_inert", lambda: calls.__setitem__("units", 1))
    monkeypatch.setattr(cli, "_attest_database", lambda *_args, **_kwargs:
                        pytest.fail("ensaio sintético não deve ler origem ou validar snapshot"))
    monkeypatch.setattr(cli, "load_source_config", lambda: source)
    monkeypatch.setattr(cli, "_workspace", lambda candidate_source, candidate:
                        (candidate_source is source and candidate is config and store) or pytest.fail("config/source divergiu"))
    monkeypatch.setattr(cli, "_attest_destination", lambda candidate, candidate_store:
                        calls["attest"].append((candidate, candidate_store)))
    monkeypatch.setattr(cli, "_pending_rehearsal_journals", lambda: pending or [])
    monkeypatch.setattr(cli.secrets, "token_hex", lambda _size: "d" * 32)

    def save(document, *, create):
        name = f"synthetic-rehearsal-{document['marker']}.json"
        calls["persist"].append((document.copy(), create))
        journals[name] = document.copy()
        return name

    def remove(name, marker):
        assert journals[name]["marker"] == marker
        calls["remove"].append(name)
        journals.pop(name)

    monkeypatch.setattr(cli, "_save_rehearsal_journal", save)
    monkeypatch.setattr(cli, "_remove_rehearsal_journal", remove)
    return config, source, journals, calls


def test_synthetic_rehearsal_uploads_reads_hashes_and_deletes_only_its_item(monkeypatch):
    store = SyntheticRehearsalStore()
    config, _source, journals, calls = _prepare_synthetic_rehearsal(monkeypatch, store)

    result = cli._run_synthetic_destination_rehearsal()

    name, content = store.uploaded[0]
    assert result.status == "destination_synthetic_verified"
    assert result.size_bytes == len(content)
    assert result.artifact_sha256 == __import__("hashlib").sha256(content).hexdigest()
    assert "synthetic-drive-object-id" not in json.dumps(result.__dict__)
    assert name == "pyp-backup-rehearsal-" + "d" * 32 + ".txt"
    assert b"Pick-your-Pic synthetic destination rehearsal" in content
    assert store.deleted == [(store.found_id, name)]
    assert journals == {}
    assert calls["units"] == 1
    assert calls["attest"] == [(config, store)]


def test_synthetic_cleanup_failure_records_id_only_in_root_journal(monkeypatch):
    store = SyntheticRehearsalStore(delete_ok=False)
    _config_value, _source_value, journals, _calls = _prepare_synthetic_rehearsal(monkeypatch, store)

    result = cli._run_synthetic_destination_rehearsal()

    journal = next(iter(journals.values()))
    assert result.status == "failed"
    assert result.error == "cleanup"
    assert journal["state"] == "cleanup_pending"
    assert journal["file_id"] == store.found_id
    assert store.found_id not in json.dumps(result.__dict__)


def test_upload_response_loss_keeps_marker_journal_for_exact_reconciliation(monkeypatch):
    class LostUpload(SyntheticRehearsalStore):
        def upload_rehearsal_item(self, *, name, content):
            self.uploaded.append((name, content))
            raise BackupStorageError("io")

    store = LostUpload()
    _config_value, _source_value, journals, _calls = _prepare_synthetic_rehearsal(monkeypatch, store)

    result = cli._run_synthetic_destination_rehearsal()

    journal = next(iter(journals.values()))
    assert result.error == "io"
    assert journal["state"] == "upload_pending"
    assert "file_id" not in journal
    assert store.deleted == []


def test_new_synthetic_rehearsal_stops_when_prior_cleanup_needs_reconciliation(monkeypatch):
    store = SyntheticRehearsalStore()
    _prepare_synthetic_rehearsal(monkeypatch, store, pending=["synthetic-rehearsal-" + "1" * 32 + ".json"])
    monkeypatch.setattr(cli, "load_source_config", lambda: pytest.fail("não deve obter credencial OAuth"))

    with pytest.raises(BackupStorageError, match="conflict"):
        cli._run_synthetic_destination_rehearsal()

    assert store.uploaded == []
    assert store.deleted == []


def test_synthetic_reconciliation_finds_content_then_deletes_exact_id(monkeypatch):
    marker = "e" * 32
    content = cli._synthetic_payload(marker)
    name = f"synthetic-rehearsal-{marker}.json"
    journal = cli._journal_document(marker, state="upload_pending", content=content)
    store = SyntheticRehearsalStore()
    store.uploaded.append((journal["name"], content))
    _config_value, _source_value, _journals, calls = _prepare_synthetic_rehearsal(monkeypatch, store, pending=[name])
    monkeypatch.setattr(cli, "_read_rehearsal_journal", lambda _name: journal)
    monkeypatch.setattr(cli, "_pending_rehearsal_journals", lambda: [name])

    result = cli._reconcile_synthetic_destination()

    assert result.status == "destination_synthetic_reconciled"
    assert store.deleted == [(store.found_id, journal["name"])]
    assert calls["remove"] == [name]
    assert calls["persist"][-1][0]["file_id"] == store.found_id


@pytest.mark.skipif(os.name != "posix", reason="journal filesystem contract requires POSIX")
def test_synthetic_journal_uses_private_atomic_root_only_file(tmp_path, monkeypatch):
    config_root = tmp_path / "pyp-backup-config"
    config_root.mkdir(mode=0o700)
    config_root.chmod(0o700)
    monkeypatch.setattr(cli, "CONFIG_ROOT", config_root)
    marker = "f" * 32
    content = cli._synthetic_payload(marker)
    document = cli._journal_document(marker, state="created", content=content,
                                     file_id="synthetic-private-drive-id")

    name = cli._save_rehearsal_journal(document, create=True)
    path = config_root / name
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cli._read_rehearsal_journal(name) == document
    updated = cli._journal_document(marker, state="cleanup_pending", content=content,
                                    file_id="synthetic-private-drive-id")
    cli._save_rehearsal_journal(updated, create=False)
    assert cli._read_rehearsal_journal(name)["state"] == "cleanup_pending"
    cli._remove_rehearsal_journal(name, marker)
    assert not path.exists()
