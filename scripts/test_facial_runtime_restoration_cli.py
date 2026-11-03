"""CLI de escopo fixo; testes usam host e fases simulados em memória."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facial_runtime_restoration_cli as cli


class FakeHost:
    def __init__(self):
        self.calls = []

    def inventory(self):
        self.calls.append("inventory")
        return {
            "schema": "20261026_0090",
            "architecture": "arm64",
            "services": {"api": {"status": "healthy", "health": "healthy", "image_id": "sha256:abc"}},
            "environment": {"TOKEN": "secret-sentinel"},
            "raw": "secret-sentinel",
        }

    def candidate_manifest(self):
        self.calls.append("candidate_manifest")
        return {"format": 1}


def test_inventory_output_redacts_raw_environment_and_identifiers():
    host = FakeHost()
    output, errors = io.StringIO(), io.StringIO()
    code = cli.main(
        ["inventory", "--support-sha", "a" * 40],
        host_factory=lambda _sha: host,
        stdout=output,
        stderr=errors,
    )
    assert code == 0
    assert "secret-sentinel" not in output.getvalue()
    result = json.loads(output.getvalue())
    assert result["status"] == "inventoried"
    assert result["services"]["api"]["health"] == "healthy"
    assert not errors.getvalue()


def test_unlisted_host_or_docker_arguments_are_rejected_before_host_access():
    calls = []
    with pytest.raises(SystemExit):
        cli.main(
            ["execute", "--support-sha", "a" * 40, "--operation", "local-test",
             "--phase", "dark", "--fingerprint", "b" * 64, "--host", "other"],
            host_factory=lambda _sha: calls.append("host"),
        )
    assert calls == []


def test_prepare_requires_phase_bound_interactive_confirmation():
    host = FakeHost()
    output, errors = io.StringIO(), io.StringIO()
    code = cli.main(
        ["prepare", "--support-sha", "a" * 40, "--operation", "local-test"],
        host_factory=lambda _sha: host,
        input_fn=lambda _prompt: "CONFIRMO ACTIVATE local-test",
        stdout=output,
        stderr=errors,
    )
    assert code == 2
    assert host.calls == []
    assert "confirmacao_divergente" in errors.getvalue()


def test_phase_requires_matching_confirmation_before_execute(monkeypatch):
    host = FakeHost()
    called = []
    monkeypatch.setattr(cli, "execute", lambda *_args: called.append("execute") or {"status": "dark_verified"})
    output, errors = io.StringIO(), io.StringIO()
    code = cli.main(
        ["execute", "--support-sha", "a" * 40, "--operation", "local-test", "--phase", "dark",
         "--fingerprint", "b" * 64],
        host_factory=lambda _sha: host,
        input_fn=lambda _prompt: "CONFIRMO RECOVER local-test",
        stdout=output,
        stderr=errors,
    )
    assert code == 2
    assert called == []
    assert "confirmacao_divergente" in errors.getvalue()


def test_matching_confirmation_invokes_only_the_requested_phase(monkeypatch):
    host = FakeHost()
    calls = []
    monkeypatch.setattr(cli, "execute", lambda _host, operation, phase, approval: calls.append((operation, phase, approval.stage)) or {"status": "dark_verified"})
    output = io.StringIO()
    code = cli.main(
        ["execute", "--support-sha", "a" * 40, "--operation", "local-test", "--phase", "dark",
         "--fingerprint", "b" * 64],
        host_factory=lambda _sha: host,
        input_fn=lambda _prompt: "CONFIRMO DARK local-test",
        stdout=output,
        stderr=io.StringIO(),
    )
    assert code == 0
    assert calls == [("local-test", "dark", "canary")]
