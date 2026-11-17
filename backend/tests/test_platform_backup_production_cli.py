"""Provas sintéticas do vínculo owner-only do destino de backup."""

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
