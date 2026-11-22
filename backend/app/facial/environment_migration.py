"""Operações puras de re-cifragem biométrica para validação sintética local."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from uuid import UUID

from app.facial.crypto import (
    FacialCryptoContextPair,
    FacialCryptoError,
    FacialEnvelope,
    FacialScope,
)
from app.facial.environment_eligibility import (
    ELIGIBILITY_BLOCKER_CODES,
    BiometricEligibilityEvidence,
    classify_biometric_evidence,
)

_MIGRATION_FAILURE_CODES = ELIGIBILITY_BLOCKER_CODES | frozenset(
    {"source_scope_mismatch", "crypto_failure", "invalid_record"}
)
_OBJECT_KINDS = {
    "photo_embedding": "photo",
    "reference_file": "request",
    "reference_locator": "request",
    "search_notification": "request",
}


class FacialMigrationError(RuntimeError):
    """Erro sanitizado; somente um código allowlisted pode ser exposto."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = (
            reason_code if reason_code in _MIGRATION_FAILURE_CODES else "invalid_record"
        )
        super().__init__("Re-cifragem biométrica bloqueada.")


@dataclass(frozen=True, slots=True, repr=False)
class BiometricCiphertextRecord:
    """Snapshot imutável da unidade; `repr` não revela IDs nem ciphertext."""

    tenant_id: UUID
    gallery_id: UUID
    client_id: UUID | None
    object_id: UUID
    scope: FacialScope = field(repr=False)
    envelope: FacialEnvelope = field(repr=False)
    evidence: BiometricEligibilityEvidence = field(repr=False)
    created_at: datetime = field(repr=False)
    updated_at: datetime = field(repr=False)

    def __repr__(self) -> str:
        return "BiometricCiphertextRecord(<redacted>)"


def reencrypt_eligible_record(
    record: BiometricCiphertextRecord,
    *,
    contexts: FacialCryptoContextPair,
    now: datetime,
) -> BiometricCiphertextRecord:
    """Retorna outro snapshot com o envelope no destino, sem persistir nada."""

    if not isinstance(record, BiometricCiphertextRecord) or not isinstance(
        contexts, FacialCryptoContextPair
    ):
        raise FacialMigrationError("invalid_record")
    if (
        not isinstance(record.tenant_id, UUID)
        or not isinstance(record.gallery_id, UUID)
        or (record.client_id is not None and not isinstance(record.client_id, UUID))
        or not isinstance(record.object_id, UUID)
        or not isinstance(record.scope, FacialScope)
        or not isinstance(record.envelope, FacialEnvelope)
    ):
        raise FacialMigrationError("invalid_record")

    decision = classify_biometric_evidence(record.evidence, now=now)
    if not decision.eligible:
        raise FacialMigrationError(decision.reason_code)

    expected_kind = _OBJECT_KINDS.get(record.evidence.category)
    if (
        expected_kind is None
        or record.evidence.source_environment != contexts.source.environment
        or record.evidence.target_environment != contexts.destination.environment
        or record.scope.environment != contexts.source.environment
        or record.scope.gallery_id != record.gallery_id
        or record.scope.object_id != record.object_id
        or record.scope.object_kind != expected_kind
        or record.scope.purpose != record.evidence.purpose
    ):
        raise FacialMigrationError("source_scope_mismatch")

    source_scope = record.scope
    destination_scope = replace(
        source_scope, environment=contexts.destination.environment
    )
    try:
        source_scope.additional_authenticated_data(
            envelope_version=record.envelope.version
        )
        destination_scope.additional_authenticated_data(
            envelope_version=record.envelope.version
        )
        plaintext = contexts.source.cipher.decrypt(
            record.envelope, scope=source_scope
        )
        destination_envelope = contexts.destination.cipher.encrypt(
            plaintext, scope=destination_scope
        )
    except (FacialCryptoError, TypeError, ValueError, AttributeError):
        raise FacialMigrationError("crypto_failure") from None

    return replace(
        record,
        scope=destination_scope,
        envelope=destination_envelope,
    )
