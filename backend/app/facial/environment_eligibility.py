"""Classificação fail-closed de metadados para uma futura transição facial."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

BiometricCategory = Literal[
    "photo_embedding",
    "reference_file",
    "reference_locator",
    "search_notification",
]

_EXPECTED_PURPOSE: dict[str, str] = {
    "photo_embedding": "embedding",
    "reference_file": "reference_image",
    "reference_locator": "reference_locator",
    "search_notification": "notification",
}
_TERMINAL_REFERENCE_STATES = frozenset(
    {"cancelled", "expired", "failed", "no_face", "multiple_faces", "low_quality",
     "index_incomplete", "no_candidates"}
)
_ALLOWED_REQUEST_STATES = frozenset(
    {"queued", "waiting_index", "validating_reference", "searching", "ranking", "ready"}
)
_KNOWN_REQUEST_STATES = _ALLOWED_REQUEST_STATES | frozenset(
    {
        "no_face",
        "multiple_faces",
        "low_quality",
        "index_incomplete",
        "no_candidates",
        "cancelled",
        "expired",
        "failed",
    }
)
ELIGIBILITY_BLOCKER_CODES = frozenset(
    {
        "authorization_unverified",
        "ciphertext_absent",
        "consent_missing",
        "destination_not_authorized",
        "environment_context_unverified",
        "environment_not_distinct",
        "invalid_metadata",
        "legal_notice_missing",
        "privacy_scope_unapproved",
        "purpose_mismatch",
        "purpose_unverified",
        "record_authorization_unverified",
        "reference_deleted_or_revoked",
        "reference_source_unverified",
        "request_not_active",
        "retention_expired",
        "retention_unverified",
        "subject_declaration_unverified",
        "tenant_context_mismatch",
        "unsupported_category",
    }
)


@dataclass(frozen=True, slots=True)
class BiometricEligibilityEvidence:
    """Metadados allowlisted; a estrutura não aceita IDs nem payloads."""

    category: str
    source_environment: str | None
    target_environment: str | None
    purpose: str | None
    source_context_confirmed: bool = False
    privacy_scope_approved: bool = False
    target_authorized: bool = False
    tenant_context_valid: bool = False
    payload_present: bool = False
    record_authorization_verified: bool = False
    record_retention_verified: bool = False
    authorization_method: str | None = None
    reference_source: str | None = None
    consent_version: str | None = None
    legal_notice_version: str | None = None
    subject_declaration: str | None = None
    object_status: str | None = None
    request_status: str | None = None
    expires_at: datetime | None = None
    reference_deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class BiometricEligibilityDecision:
    eligible: bool
    reason_code: str


def classify_biometric_evidence(
    evidence: BiometricEligibilityEvidence,
    *,
    now: datetime,
) -> BiometricEligibilityDecision:
    """Avalia apenas metadados; nunca abre ou altera o objeto biométrico."""

    if not isinstance(evidence, BiometricEligibilityEvidence) or not isinstance(now, datetime):
        return _blocked("invalid_metadata")
    expected_purpose = _EXPECTED_PURPOSE.get(evidence.category)
    if expected_purpose is None:
        return _blocked("unsupported_category")
    if evidence.payload_present is not True:
        return _blocked("ciphertext_absent")
    if not _nonempty(evidence.source_environment) or not _nonempty(evidence.target_environment):
        return _blocked("environment_context_unverified")
    if evidence.source_environment.strip().casefold() == evidence.target_environment.strip().casefold():
        return _blocked("environment_not_distinct")
    if evidence.source_context_confirmed is not True or evidence.tenant_context_valid is not True:
        return _blocked("environment_context_unverified" if evidence.source_context_confirmed is not True
                        else "tenant_context_mismatch")
    if evidence.target_authorized is not True:
        return _blocked("destination_not_authorized")
    if evidence.privacy_scope_approved is not True:
        return _blocked("privacy_scope_unapproved")
    if not _nonempty(evidence.purpose):
        return _blocked("purpose_unverified")
    if evidence.purpose.strip() != expected_purpose:
        return _blocked("purpose_mismatch")

    if evidence.category == "photo_embedding":
        # A prova pode vir do vínculo com o rollout/política operacional da galeria.
        # A declaração de origem do proprietário, isoladamente, não preenche essas flags.
        if evidence.record_authorization_verified is not True:
            return _blocked("record_authorization_unverified")
        if evidence.record_retention_verified is not True:
            return _blocked("retention_unverified")
        if evidence.authorization_method == "operational_gallery":
            if evidence.reference_source != "gallery_asset":
                return _blocked("reference_source_unverified")
            if not _nonempty(evidence.legal_notice_version):
                return _blocked("legal_notice_missing")
            if evidence.object_status != "active":
                return _blocked("request_not_active")
            # Índices podem seguir retenção por ciclo de vida da galeria, sem prazo
            # individual. Um prazo explícito, quando presente, continua obrigatório.
            if evidence.expires_at is not None and not _expires_after(evidence.expires_at, now):
                return _blocked("retention_expired")
            return _eligible()
        if not _expires_after(evidence.expires_at, now):
            return _blocked("retention_expired" if evidence.expires_at is not None
                            else "retention_unverified")
        return _eligible()

    if evidence.category in {"reference_file", "reference_locator"}:
        return _classify_reference(evidence, now=now)

    return _classify_notification(evidence, now=now)


def _classify_reference(
    evidence: BiometricEligibilityEvidence, *, now: datetime
) -> BiometricEligibilityDecision:
    if evidence.authorization_method != "explicit_consent":
        return _blocked("authorization_unverified")
    if evidence.reference_source != "upload":
        return _blocked("reference_source_unverified")
    if not _nonempty(evidence.consent_version):
        return _blocked("consent_missing")
    if evidence.subject_declaration != "conditional":
        return _blocked("subject_declaration_unverified")
    if evidence.reference_deleted_at is not None:
        return _blocked("reference_deleted_or_revoked")
    if evidence.object_status in _TERMINAL_REFERENCE_STATES:
        return _blocked("request_not_active")
    if evidence.request_status not in _ALLOWED_REQUEST_STATES:
        return _blocked("request_not_active")
    if not _expires_after(evidence.expires_at, now):
        return _blocked("retention_expired" if evidence.expires_at is not None
                        else "retention_unverified")
    return _eligible()


def _classify_notification(
    evidence: BiometricEligibilityEvidence, *, now: datetime
) -> BiometricEligibilityDecision:
    if evidence.object_status not in {"queued", "processing"}:
        return _blocked("ciphertext_absent")
    if evidence.request_status not in _KNOWN_REQUEST_STATES:
        return _blocked("request_not_active")
    if evidence.request_status in {"cancelled", "expired"}:
        return _blocked("request_not_active")
    if not _expires_after(evidence.expires_at, now):
        return _blocked("retention_expired" if evidence.expires_at is not None
                        else "retention_unverified")
    if evidence.authorization_method == "explicit_consent":
        if evidence.reference_source != "upload":
            return _blocked("reference_source_unverified")
        if not _nonempty(evidence.consent_version):
            return _blocked("consent_missing")
        if evidence.subject_declaration != "conditional":
            return _blocked("subject_declaration_unverified")
    elif evidence.authorization_method == "direct_region":
        if evidence.reference_source != "indexed_region":
            return _blocked("reference_source_unverified")
        if not _nonempty(evidence.legal_notice_version):
            return _blocked("legal_notice_missing")
    else:
        return _blocked("authorization_unverified")
    return _eligible()


def _expires_after(expires_at: datetime | None, now: datetime) -> bool:
    if not isinstance(expires_at, datetime):
        return False
    return _as_utc(expires_at) > _as_utc(now)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _nonempty(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _blocked(reason_code: str) -> BiometricEligibilityDecision:
    if reason_code not in ELIGIBILITY_BLOCKER_CODES:
        return BiometricEligibilityDecision(False, "invalid_metadata")
    return BiometricEligibilityDecision(False, reason_code)


def _eligible() -> BiometricEligibilityDecision:
    return BiometricEligibilityDecision(True, "eligible")
