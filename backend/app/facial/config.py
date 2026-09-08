"""Configuração fail-closed do subsistema facial isolado."""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType

from app.facial.model_assets import load_manifest, verify_models

DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "facial-assets" / "model-manifest.json"
)
PRIVATE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class FacialConfigurationError(RuntimeError):
    """Configuração facial ausente, divergente ou insegura."""


def _boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default).lower()).strip().lower()
    if value not in {"true", "false"}:
        raise FacialConfigurationError(f"{name} deve ser true ou false.")
    return value == "true"


def _integer(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise FacialConfigurationError(f"{name} deve ser um número inteiro.") from exc
    if not minimum <= value <= maximum:
        raise FacialConfigurationError(
            f"{name} deve estar entre {minimum} e {maximum}."
        )
    return value


def _text(name: str) -> str:
    return os.getenv(name, "").strip()


def _utc_datetime(name: str) -> datetime | None:
    raw = _text(name)
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise FacialConfigurationError(f"{name} deve ser um instante ISO-8601 UTC.") from exc
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise FacialConfigurationError(f"{name} deve ser um instante ISO-8601 UTC.")
    return value.astimezone(UTC)


def _keys() -> Mapping[str, bytes]:
    raw = _text("FACIAL_AEAD_KEYS_JSON")
    if not raw:
        return MappingProxyType({})
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FacialConfigurationError("O chaveiro AEAD facial é inválido.") from exc
    if not isinstance(payload, dict) or not payload:
        raise FacialConfigurationError("O chaveiro AEAD facial é inválido.")
    decoded: dict[str, bytes] = {}
    for key_id, encoded in payload.items():
        if (
            not isinstance(key_id, str)
            or not key_id.strip()
            or len(key_id) > 80
            or not isinstance(encoded, str)
        ):
            raise FacialConfigurationError("O chaveiro AEAD facial é inválido.")
        try:
            key = base64.b64decode(encoded, altchars=b"-_", validate=True)
        except (ValueError, binascii.Error, UnicodeEncodeError) as exc:
            raise FacialConfigurationError("O chaveiro AEAD facial é inválido.") from exc
        if len(key) != 32:
            raise FacialConfigurationError(
                "Cada chave AEAD facial deve possuir exatamente 32 bytes."
            )
        decoded[key_id.strip()] = key
    return MappingProxyType(decoded)


@dataclass(frozen=True)
class FacialSettings:
    enabled: bool
    environment: str
    credential_environment: str
    manifest_path: Path
    model_root: Path
    reference_root: Path
    model_version: str
    quality_version: str
    calibration_version: str
    legal_notice_version: str
    consent_version: str
    legal_basis_reference: str
    retention_policy_version: str
    minor_policy_version: str
    minor_search_enabled: bool
    similarity_threshold_milli: int
    active_key_id: str
    aead_keys: Mapping[str, bytes] = field(repr=False)
    reference_retention_seconds: int
    candidate_retention_seconds: int
    queue_name: str
    worker_concurrency: int
    max_jobs_per_process: int
    model_idle_seconds: int
    job_lease_seconds: int
    queue_block_seconds: int
    max_reference_bytes: int
    max_reference_pixels: int
    private_homologation_enabled: bool = False
    homolog_batch_id: str = ""
    homolog_origin_ref: str = ""
    homolog_authorization_ref: str = ""
    homolog_operator_ref: str = ""
    homolog_expected_count: int = 0
    homolog_retention_hours: int = 0
    homolog_contains_minors: bool = False
    homolog_window_expires_at: datetime | None = None

    @property
    def active_key(self) -> bytes:
        try:
            return self.aead_keys[self.active_key_id]
        except KeyError as exc:
            raise FacialConfigurationError(
                "A chave AEAD facial ativa não está disponível."
            ) from exc

    @property
    def private_homologation_active(self) -> bool:
        expiry = self.homolog_window_expires_at
        references = (
            self.homolog_batch_id,
            self.homolog_origin_ref,
            self.homolog_authorization_ref,
            self.homolog_operator_ref,
        )
        return bool(
            self.private_homologation_enabled
            and self.environment in {"homolog", "staging"}
            and all(PRIVATE_REFERENCE_RE.fullmatch(value) for value in references)
            and 500 <= self.homolog_expected_count <= 1000
            and 1 <= self.homolog_retention_hours <= 72
            and expiry is not None
            and expiry > datetime.now(UTC)
        )


def facial_settings_from_environment(
    *, verify_runtime_assets: bool = True
) -> FacialSettings:
    """Carrega a configuração sem permitir ativação parcial ou entre ambientes."""

    settings = FacialSettings(
        enabled=_boolean("FACIAL_PROCESSING_ENABLED"),
        environment=os.getenv("APP_ENV", "development").strip().lower(),
        credential_environment=_text("FACIAL_CREDENTIAL_ENV").lower(),
        manifest_path=Path(
            os.getenv("FACIAL_MODEL_MANIFEST_PATH", str(DEFAULT_MANIFEST_PATH))
        ).resolve(),
        model_root=Path(os.getenv("FACIAL_MODEL_ROOT", "./facial-models")).resolve(),
        reference_root=Path(
            os.getenv("FACIAL_REFERENCE_ROOT", "./media/facial-references")
        ).resolve(),
        model_version=_text("FACIAL_MODEL_VERSION"),
        quality_version=_text("FACIAL_QUALITY_VERSION"),
        calibration_version=_text("FACIAL_CALIBRATION_VERSION"),
        legal_notice_version=_text("FACIAL_LEGAL_NOTICE_VERSION"),
        consent_version=_text("FACIAL_CONSENT_VERSION"),
        legal_basis_reference=_text("FACIAL_LEGAL_BASIS_REFERENCE"),
        retention_policy_version=_text("FACIAL_RETENTION_POLICY_VERSION"),
        minor_policy_version=_text("FACIAL_MINOR_POLICY_VERSION"),
        minor_search_enabled=_boolean("FACIAL_MINOR_SEARCH_ENABLED"),
        similarity_threshold_milli=_integer(
            "FACIAL_SIMILARITY_THRESHOLD_MILLI", 750, minimum=0, maximum=1000
        ),
        active_key_id=_text("FACIAL_AEAD_ACTIVE_KEY_ID"),
        aead_keys=_keys(),
        reference_retention_seconds=_integer(
            "FACIAL_REFERENCE_RETENTION_SECONDS", 900, minimum=60, maximum=900
        ),
        candidate_retention_seconds=_integer(
            "FACIAL_CANDIDATE_RETENTION_SECONDS", 86400, minimum=60, maximum=86400
        ),
        queue_name=os.getenv("FACIAL_QUEUE_NAME", "markina:facial:jobs").strip(),
        worker_concurrency=_integer(
            "FACIAL_WORKER_CONCURRENCY", 1, minimum=1, maximum=2
        ),
        max_jobs_per_process=_integer(
            "FACIAL_MAX_JOBS_PER_PROCESS", 100, minimum=1, maximum=1000
        ),
        model_idle_seconds=_integer(
            "FACIAL_MODEL_IDLE_SECONDS", 300, minimum=30, maximum=3600
        ),
        job_lease_seconds=_integer(
            "FACIAL_JOB_LEASE_SECONDS", 120, minimum=30, maximum=900
        ),
        queue_block_seconds=_integer(
            "FACIAL_QUEUE_BLOCK_SECONDS", 10, minimum=1, maximum=60
        ),
        max_reference_bytes=_integer(
            "FACIAL_MAX_REFERENCE_BYTES", 10_485_760, minimum=65_536, maximum=20_971_520
        ),
        max_reference_pixels=_integer(
            "FACIAL_MAX_REFERENCE_PIXELS", 25_000_000, minimum=1_000_000, maximum=40_000_000
        ),
        private_homologation_enabled=_boolean("FACIAL_HOMOLOG_PRIVATE_MODE"),
        homolog_batch_id=_text("FACIAL_HOMOLOG_BATCH_ID"),
        homolog_origin_ref=_text("FACIAL_HOMOLOG_ORIGIN_REF"),
        homolog_authorization_ref=_text("FACIAL_HOMOLOG_AUTHORIZATION_REF"),
        homolog_operator_ref=_text("FACIAL_HOMOLOG_OPERATOR_REF"),
        homolog_expected_count=_integer(
            "FACIAL_HOMOLOG_EXPECTED_COUNT", 0, minimum=0, maximum=1000
        ),
        homolog_retention_hours=_integer(
            "FACIAL_HOMOLOG_RETENTION_HOURS", 0, minimum=0, maximum=72
        ),
        homolog_contains_minors=_boolean("FACIAL_HOMOLOG_CONTAINS_MINORS"),
        homolog_window_expires_at=_utc_datetime("FACIAL_HOMOLOG_WINDOW_EXPIRES_AT"),
    )
    if not settings.queue_name or len(settings.queue_name) > 120:
        raise FacialConfigurationError("FACIAL_QUEUE_NAME é inválida.")
    if settings.enabled:
        _validate_enabled(settings, verify_runtime_assets=verify_runtime_assets)
    return settings


def _validate_enabled(
    settings: FacialSettings, *, verify_runtime_assets: bool
) -> None:
    if not settings.environment or settings.credential_environment != settings.environment:
        raise FacialConfigurationError(
            "A configuração facial não pertence ao APP_ENV atual."
        )
    required = {
        "FACIAL_MODEL_VERSION": settings.model_version,
        "FACIAL_QUALITY_VERSION": settings.quality_version,
        "FACIAL_CALIBRATION_VERSION": settings.calibration_version,
        "FACIAL_LEGAL_NOTICE_VERSION": settings.legal_notice_version,
        "FACIAL_CONSENT_VERSION": settings.consent_version,
        "FACIAL_LEGAL_BASIS_REFERENCE": settings.legal_basis_reference,
        "FACIAL_RETENTION_POLICY_VERSION": settings.retention_policy_version,
        "FACIAL_MINOR_POLICY_VERSION": settings.minor_policy_version,
        "FACIAL_AEAD_ACTIVE_KEY_ID": settings.active_key_id,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise FacialConfigurationError(
            "A configuração facial obrigatória está incompleta."
        )
    manifest = load_manifest(settings.manifest_path)
    if settings.model_version != manifest["model_version"]:
        raise FacialConfigurationError(
            "A versão configurada dos modelos faciais diverge do manifesto."
        )
    if settings.private_homologation_enabled and not settings.private_homologation_active:
        raise FacialConfigurationError(
            "A autorização privada de homologação está incompleta, divergente ou expirada."
        )
    if settings.minor_search_enabled and (
        not settings.private_homologation_active
        or not settings.homolog_contains_minors
    ):
        raise FacialConfigurationError(
            "A busca facial infantil da cliente exige homologação privada autorizada, "
            "vigente e declarada com menores."
        )
    _ = settings.active_key
    if verify_runtime_assets:
        verify_models(settings.manifest_path, settings.model_root)
