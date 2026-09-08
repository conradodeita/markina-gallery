"""Configuração segura e desligada por padrão do subsistema facial."""

import base64
from pathlib import Path

import pytest

from app.facial.config import FacialConfigurationError, facial_settings_from_environment


def _clear_facial_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "FACIAL_PROCESSING_ENABLED",
        "FACIAL_CREDENTIAL_ENV",
        "FACIAL_MODEL_MANIFEST_PATH",
        "FACIAL_MODEL_ROOT",
        "FACIAL_REFERENCE_ROOT",
        "FACIAL_MODEL_VERSION",
        "FACIAL_QUALITY_VERSION",
        "FACIAL_CALIBRATION_VERSION",
        "FACIAL_LEGAL_NOTICE_VERSION",
        "FACIAL_CONSENT_VERSION",
        "FACIAL_LEGAL_BASIS_REFERENCE",
        "FACIAL_RETENTION_POLICY_VERSION",
        "FACIAL_MINOR_POLICY_VERSION",
        "FACIAL_MINOR_SEARCH_ENABLED",
        "FACIAL_SIMILARITY_THRESHOLD_MILLI",
        "FACIAL_AEAD_ACTIVE_KEY_ID",
        "FACIAL_AEAD_KEYS_JSON",
        "FACIAL_REFERENCE_RETENTION_SECONDS",
        "FACIAL_CANDIDATE_RETENTION_SECONDS",
        "FACIAL_QUEUE_NAME",
        "FACIAL_WORKER_CONCURRENCY",
        "FACIAL_MAX_JOBS_PER_PROCESS",
        "FACIAL_MODEL_IDLE_SECONDS",
        "FACIAL_JOB_LEASE_SECONDS",
        "FACIAL_QUEUE_BLOCK_SECONDS",
        "FACIAL_MAX_REFERENCE_BYTES",
        "FACIAL_MAX_REFERENCE_PIXELS",
    ):
        monkeypatch.delenv(name, raising=False)


def _valid_enabled_environment(monkeypatch: pytest.MonkeyPatch) -> bytes:
    key = bytes(range(32))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("FACIAL_PROCESSING_ENABLED", "true")
    monkeypatch.setenv("FACIAL_CREDENTIAL_ENV", "test")
    monkeypatch.setenv("FACIAL_MODEL_VERSION", "yunet-2023mar+sface-2021dec")
    monkeypatch.setenv("FACIAL_QUALITY_VERSION", "opencv-technical-v1")
    monkeypatch.setenv("FACIAL_CALIBRATION_VERSION", "synthetic-v1")
    monkeypatch.setenv("FACIAL_LEGAL_NOTICE_VERSION", "synthetic-notice-v1")
    monkeypatch.setenv("FACIAL_CONSENT_VERSION", "synthetic-consent-v1")
    monkeypatch.setenv("FACIAL_LEGAL_BASIS_REFERENCE", "synthetic-only")
    monkeypatch.setenv("FACIAL_RETENTION_POLICY_VERSION", "short-v1")
    monkeypatch.setenv("FACIAL_MINOR_POLICY_VERSION", "minor-disabled-v1")
    monkeypatch.setenv("FACIAL_AEAD_ACTIVE_KEY_ID", "test-2026-09")
    encoded = base64.urlsafe_b64encode(key).decode("ascii")
    monkeypatch.setenv(
        "FACIAL_AEAD_KEYS_JSON", f'{{"test-2026-09":"{encoded}"}}'
    )
    return key


def test_facial_configuration_is_disabled_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_facial_environment(monkeypatch)
    settings = facial_settings_from_environment()
    assert settings.enabled is False
    assert settings.aead_keys == {}
    assert settings.reference_retention_seconds == 900
    assert settings.candidate_retention_seconds == 86400


def test_enabled_facial_configuration_fails_closed_when_incomplete_or_cross_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_facial_environment(monkeypatch)
    monkeypatch.setenv("FACIAL_PROCESSING_ENABLED", "true")
    with pytest.raises(FacialConfigurationError, match="APP_ENV"):
        facial_settings_from_environment()

    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("FACIAL_CREDENTIAL_ENV", "production")
    with pytest.raises(FacialConfigurationError, match="APP_ENV"):
        facial_settings_from_environment()

    monkeypatch.setenv("FACIAL_CREDENTIAL_ENV", "homolog")
    with pytest.raises(FacialConfigurationError, match="incompleta"):
        facial_settings_from_environment()


def test_enabled_facial_configuration_validates_manifest_models_and_secret_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_facial_environment(monkeypatch)
    key = _valid_enabled_environment(monkeypatch)
    verified: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        "app.facial.config.verify_models",
        lambda manifest, root: verified.append((manifest, root)),
    )

    settings = facial_settings_from_environment()

    assert settings.enabled is True
    assert settings.active_key == key
    assert len(verified) == 1
    assert base64.urlsafe_b64encode(key).decode("ascii") not in repr(settings)
    assert str(key) not in repr(settings)


def test_enabled_facial_configuration_rejects_unsafe_retention_and_ignores_legacy_minor_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_facial_environment(monkeypatch)
    _valid_enabled_environment(monkeypatch)
    monkeypatch.setenv("FACIAL_REFERENCE_RETENTION_SECONDS", "901")
    with pytest.raises(FacialConfigurationError, match="RETENTION"):
        facial_settings_from_environment()

    monkeypatch.setenv("FACIAL_REFERENCE_RETENTION_SECONDS", "900")
    monkeypatch.setenv("FACIAL_MINOR_SEARCH_ENABLED", "true")
    settings = facial_settings_from_environment(verify_runtime_assets=False)
    assert not hasattr(settings, "minor_search_enabled")


def test_removed_minor_flag_is_absent_from_runtime_configuration() -> None:
    config_path = Path(__file__).resolve().parents[1] / "app" / "facial" / "config.py"
    assert "FACIAL_MINOR_SEARCH_ENABLED" not in config_path.read_text(encoding="utf-8")
