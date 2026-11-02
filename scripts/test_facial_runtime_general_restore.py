"""A dispensa explícita nunca é interpretada como medição aprovada."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_restoration import (
    GENERAL_RESTORE_MODE,
    RestorationError,
    calibration_admission_proven,
    validate_images,
    validate_inventory,
)
from facial_runtime_restoration_host import RestorationHost
from test_facial_runtime_restoration import fixture

MANIFEST = {"activation_policy": GENERAL_RESTORE_MODE,
            "authorization_reference": "owner-general-restore-20261102"}
PROOF = {"calibration_verified": False, "calibration_waived": True,
         "authorization_reference": MANIFEST["authorization_reference"]}


def test_general_restore_has_explicit_waiver_without_fake_approval():
    assert calibration_admission_proven(MANIFEST, PROOF, "general")


@pytest.mark.parametrize("proof,stage", [
    ({**PROOF, "calibration_verified": True}, "general"),
    ({**PROOF, "calibration_waived": False}, "general"),
    ({**PROOF, "authorization_reference": "other"}, "general"),
    (PROOF, "canary"),
])
def test_waiver_requires_exact_mode_authorization_and_general_stage(proof, stage):
    assert not calibration_admission_proven(MANIFEST, proof, stage)


def test_strict_mode_does_not_accept_a_waiver():
    assert not calibration_admission_proven({}, PROOF, "general")
    assert calibration_admission_proven({}, {"calibration_verified": True}, "canary")


def test_preserved_peers_do_not_require_executable_manifests():
    inventory, _manifest = fixture()
    for service in ("web", "nginx", "db", "redis"):
        inventory["services"][service]["compose_files"] = []
    validate_inventory(inventory)
    inventory["services"]["api"]["compose_files"] = []
    with pytest.raises(RestorationError, match="proveniencia_ausente"):
        validate_inventory(inventory)


def test_git_trust_is_limited_to_fixed_roots_per_command(monkeypatch):
    observed = []

    def run(command, **kwargs):
        observed.append((command, kwargs))
        return SimpleNamespace(stdout=b"ok")

    monkeypatch.setattr("facial_runtime_restoration_host.subprocess.run", run)
    host = RestorationHost(support_sha="a" * 40, command=lambda *_args: b"")
    assert host._command(("git", "rev-parse", "HEAD"), None, 30) == b"ok"
    command, options = observed[0]
    assert command == ["git", "-c", "safe.directory=" + str(host.root),
                       "-c", "safe.directory=" + str(host.code_root), "rev-parse", "HEAD"]
    assert "GIT_CONFIG_GLOBAL" not in options["env"]


def test_manifest_refuses_general_mode_without_authorization():
    manifest = {"format": 1, "support_sha": "a" * 40, "activation_policy": GENERAL_RESTORE_MODE}
    with pytest.raises(RestorationError, match="autorizacao_ausente"):
        validate_images({"support_sha": "a" * 40}, manifest, {})


@pytest.mark.parametrize("policy,required", [(GENERAL_RESTORE_MODE, "false"), ("strict", "true")])
def test_target_environment_changes_only_explicit_facial_gate_configuration(policy, required):
    env = ["APP_ENV=production", "MERCADOPAGO_ALLOW_LIVE_PAYMENTS=true", "PAYMENT_SENTINEL=preserve"]
    saved = {"activation_policy": policy, "containers": {
        "api": {"Config": {"Env": env}}, "worker": {"Config": {"Env": env}},
    }}
    host = RestorationHost(support_sha="a" * 40, command=lambda *_args: b"")
    actual = host._target_environment(saved, "worker", True)
    assert actual["FACIAL_REQUIRE_PRODUCTION_CALIBRATION"] == required
    assert actual["FACIAL_REQUIRE_EXPLICIT_ROLLOUT"] == required
    assert actual["MERCADOPAGO_ALLOW_LIVE_PAYMENTS"] == "true"
    assert actual["PAYMENT_SENTINEL"] == "preserve"
    assert actual["PYTHONDONTWRITEBYTECODE"] == "1"
