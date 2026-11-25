"""Provas sintéticas do vínculo owner-only do destino de backup."""

import base64
import io
import json
import os
import stat
import subprocess
import sys
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.platform_backup import production_cli as cli
from app.platform_backup import runtime_config as config_module
from app.platform_backup import runtime_source as source_module
from app.platform_backup.filesystem import BackupStorageError


def _inert_systemctl(argv, **_kwargs):
    assert "--value" not in argv
    unit = argv[-1]
    assert unit in {"pyp-platform-backup.service", "pyp-platform-backup.timer"}
    enabled = "static" if unit.endswith(".service") else "disabled"
    return subprocess.CompletedProcess(
        argv, 0, f"LoadState=loaded\nActiveState=inactive\nUnitFileState={enabled}\n", "",
    )


def test_inert_systemd_check_accepts_named_properties_in_host_order(monkeypatch):
    monkeypatch.setattr(cli.subprocess, "run", _inert_systemctl)
    cli._assert_backup_units_inert()


@pytest.mark.parametrize("bad_timer", [
    "LoadState=loaded\nActiveState=active\nUnitFileState=disabled\n",
    "LoadState=loaded\nActiveState=inactive\nUnitFileState=static\n",
    "LoadState=loaded\nActiveState=inactive\nUnitFileState=enabled\n",
    "LoadState=loaded\nActiveState=inactive\nActiveState=inactive\nUnitFileState=disabled\n",
    "LoadState=loaded\nUnitFileState=disabled\n",
])
def test_inert_systemd_check_rejects_unsafe_or_incomplete_properties(monkeypatch, bad_timer):
    def systemctl(argv, **kwargs):
        if argv[-1].endswith(".timer"):
            return subprocess.CompletedProcess(argv, 0, bad_timer, "")
        return _inert_systemctl(argv, **kwargs)

    monkeypatch.setattr(cli.subprocess, "run", systemctl)
    with pytest.raises(BackupStorageError, match="unsafe"):
        cli._assert_backup_units_inert()


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


@pytest.fixture
def private_backup_root(monkeypatch):
    if os.name != "posix" or os.geteuid() != 0:
        pytest.skip("O fluxo com filesystem real exige Linux root isolado")
    monkeypatch.setenv("APP_ENV", "production")
    with TemporaryDirectory(dir="/root") as temporary:
        root = Path(temporary)
        monkeypatch.setattr(cli, "CONFIG_ROOT", root)
        monkeypatch.setattr(config_module, "CONFIG_ROOT", root)
        monkeypatch.setattr(source_module, "CONFIG_ROOT", root)
        monkeypatch.setattr(cli, "prepare_source_config", partial(source_module.prepare_source_config, root=root))
        monkeypatch.setattr(cli, "bind_folder_id", partial(config_module.bind_selected_destination, root=root))
        yield root


@pytest.fixture
def synthetic_source_witness(monkeypatch):
    witness = {"api": {"id": "a" * 64, "image": "sha256:" + "b" * 64},
               "db": {"id": "c" * 64, "image": "sha256:" + "d" * 64},
               "schema_revision": "20261113_0126"}
    postgres = "synthetic_db|on|170011|1000000000000000000|20261113_0126"
    proof = {"release": "e" * 40, "witness": postgres}
    project = {"api": "markina-gallery-app-" + "f" * 32, "db": "markina-gallery"}

    def docker(*args):
        if args[:2] == ("container", "inspect"):
            for role in ("api", "db"):
                item = witness[role]
                if args[-1] == item["id"]:
                    name = f"/{project[role]}-{role}-1"
                    return f'{item["id"]}|{item["image"]}|{name}|true|{project[role]}|{role}'.encode()
        if args[0] == "exec" and args[-1] == source_module._SOURCE_QUERY and witness["db"]["id"] in args:
            assert "default_transaction_read_only=on" in args[2]
            return postgres.encode()
        if args[:2] == ("exec", witness["api"]["id"]) and source_module._API_SOURCE_PROVIDER in args:
            assert args[-1] == source_module._SOURCE_QUERY
            assert "SET TRANSACTION READ ONLY" in source_module._API_SOURCE_PROVIDER
            return json.dumps(proof).encode()
        pytest.fail("Comando fora das consultas sintéticas esperadas")

    monkeypatch.setattr(source_module, "_docker", docker)
    return witness, proof, project


def test_prepare_bind_and_rehearse_runs_the_real_local_guards(
    private_backup_root, synthetic_source_witness, monkeypatch, capsys,
):
    root = private_backup_root
    witness, _, _ = synthetic_source_witness
    install_id = str(uuid4())
    destination_id = str(uuid4())
    files = {
        "keyring.json": {"version": 1, "installation_id": install_id, "active_key_id": "backup-f123456789ab",
                         "keys": {"backup-f123456789ab": base64.b64encode(bytes(32)).decode()}},
        "destination.json": {"version": 1, "installation_id": install_id, "destination_id": destination_id,
                             "environment": "production", "scope": "drive.file", "provider": "google-workspace",
                             "parent_folder_id": "old-folder", "marker": dict(config_module.DESTINATION_MARKER),
                             "enabled": False},
    }
    for name, document in files.items():
        path = root / name
        path.write_text(json.dumps(document), encoding="utf-8")
        path.chmod(0o400)
    monkeypatch.setattr(cli.subprocess, "run", _inert_systemctl)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(witness).encode())))
    monkeypatch.setattr(cli, "_attest_database", lambda *_: pytest.fail("ensaio não faz snapshot"))
    store = SyntheticRehearsalStore()

    def picker_selection(*args):
        assert cli._SELECTED_FOLDER_PROVIDER in args and args[1] == witness["api"]["id"]
        assert args[-1] == "e" * 40
        return b'{"folder_id":"selected-global-folder"}'

    def drive_workspace(source, config):
        assert source.api_container == witness["api"]["id"]
        assert config.parent_folder_id == "selected-global-folder" and not config.enabled
        return store

    monkeypatch.setattr(cli, "_docker", picker_selection)
    monkeypatch.setattr(cli, "_workspace", drive_workspace)
    monkeypatch.setattr(cli, "_attest_destination", lambda _, actual: actual is store or pytest.fail())
    # Cada entrada passa pelo dispatcher usado pelo wrapper. Apenas Docker, systemd e Drive são simulados.
    for mode, status in (("--prepare-source", "source_prepared"),
                         ("--bind-selected-destination", "destination_bound"),
                         ("--synthetic-destination-rehearsal", "destination_synthetic_verified")):
        monkeypatch.setattr(sys, "argv", ["production_cli.py", mode])
        assert cli.main() == 0
        captured = capsys.readouterr().out
        assert json.loads(captured)["status"] == status
        assert witness["api"]["id"] not in captured and store.found_id not in captured

    source_path = root / "source.json"
    assert stat.S_IMODE(source_path.stat().st_mode) == 0o400
    assert source_module.load_source_config().max_dump_bytes == 1024 ** 3
    assert config_module.load_runtime_config().parent_folder_id == "selected-global-folder"
    assert config_module.load_runtime_config().enabled is False
    assert len(store.uploaded) == 1
    assert store.deleted == [(store.found_id, store.uploaded[0][0])]
    assert {p.name for p in root.iterdir()} == {*files, "source.json"}


def test_source_preparation_preserves_existing_file_and_rejects_drift(
    private_backup_root, synthetic_source_witness,
):
    root = private_backup_root
    witness, proof, project = synthetic_source_witness
    path = root / "source.json"
    matching = proof["witness"]
    proof["witness"] += "|different"
    with pytest.raises(BackupStorageError, match="unsafe"):
        source_module.prepare_source_config(witness, root=root)
    assert not path.exists()
    proof["witness"] = matching

    other = project["api"]
    project["api"] = "third-party"
    with pytest.raises(BackupStorageError, match="unsafe"):
        source_module.prepare_source_config(witness, root=root)
    assert not path.exists()
    project["api"] = other

    source_module.prepare_source_config(witness, root=root)
    inode = path.stat().st_ino
    original = path.read_bytes()
    source_module.prepare_source_config(witness, root=root)
    assert path.stat().st_ino == inode
    proof["release"] = "1" * 40
    with pytest.raises(BackupStorageError, match="conflict"):
        source_module.prepare_source_config(witness, root=root)
    assert path.read_bytes() == original
    path.chmod(0o600)
    with pytest.raises(BackupStorageError, match="unsafe"):
        source_module.prepare_source_config(witness, root=root)
    assert {item.name for item in root.iterdir()} == {"source.json"}


def test_backup_work_directories_prepare_only_fixed_children(private_backup_root, monkeypatch):
    monkeypatch.setattr(cli, "WORK_ROOT", private_backup_root)
    foreign = private_backup_root / "foreign"
    foreign.mkdir(mode=0o700)
    artifacts = private_backup_root / "artifacts"
    artifacts.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(BackupStorageError, match="unsafe"):
        cli._prepare_work_directories()
    assert not (private_backup_root / "catalog").exists()
    artifacts.unlink()
    cli._prepare_work_directories()
    cli._prepare_work_directories()
    assert {p.name for p in private_backup_root.iterdir()} == {"catalog", "artifacts", "foreign"}
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o700 for p in private_backup_root.iterdir())


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
