"""A dispensa explícita nunca é interpretada como medição aprovada."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_restoration import (
    GENERAL_RESTORE_MODE,
    RestorationError,
    calibration_admission_proven,
    validate_images,
)
from facial_runtime_restoration_host import RestorationHost

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
