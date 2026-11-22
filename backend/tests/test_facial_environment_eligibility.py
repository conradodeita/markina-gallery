from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta

import pytest

from app.facial.environment_eligibility import (
    BiometricEligibilityEvidence,
    classify_biometric_evidence,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def _reference_evidence(**overrides) -> BiometricEligibilityEvidence:
    values = {
        "category": "reference_file",
        "source_environment": "staging",
        "target_environment": "production",
        "purpose": "reference_image",
        "source_context_confirmed": True,
        "privacy_scope_approved": True,
        "target_authorized": True,
        "tenant_context_valid": True,
        "payload_present": True,
        "authorization_method": "explicit_consent",
        "reference_source": "upload",
        "consent_version": "synthetic-consent-v1",
        "subject_declaration": "conditional",
        "object_status": "ready",
        "request_status": "ready",
        "expires_at": NOW + timedelta(days=1),
    }
    values.update(overrides)
    return BiometricEligibilityEvidence(**values)


def _notification_evidence(**overrides) -> BiometricEligibilityEvidence:
    values = {
        "category": "search_notification",
        "source_environment": "staging",
        "target_environment": "production",
        "purpose": "notification",
        "source_context_confirmed": True,
        "privacy_scope_approved": True,
        "target_authorized": True,
        "tenant_context_valid": True,
        "payload_present": True,
        "authorization_method": "explicit_consent",
        "reference_source": "upload",
        "consent_version": "synthetic-consent-v1",
        "subject_declaration": "conditional",
        "object_status": "queued",
        "request_status": "ready",
        "expires_at": NOW + timedelta(days=1),
    }
    values.update(overrides)
    return BiometricEligibilityEvidence(**values)


def _embedding_evidence(**overrides) -> BiometricEligibilityEvidence:
    values = {
        "category": "photo_embedding",
        "source_environment": "staging",
        "target_environment": "production",
        "purpose": "embedding",
        "source_context_confirmed": True,
        "privacy_scope_approved": True,
        "target_authorized": True,
        "tenant_context_valid": True,
        "payload_present": True,
    }
    values.update(overrides)
    return BiometricEligibilityEvidence(**values)


def test_explicitly_authorized_reference_is_eligible_without_mutation():
    evidence = _reference_evidence()

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is True
    assert decision.reason_code == "eligible"
    assert evidence == _reference_evidence()
    with pytest.raises(FrozenInstanceError):
        evidence.target_environment = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({}, "eligible"),
        ({"record_authorization_verified": False}, "record_authorization_unverified"),
        ({"record_retention_verified": False}, "retention_unverified"),
        ({"legal_notice_version": None}, "legal_notice_missing"),
        ({"reference_source": "unknown"}, "reference_source_unverified"),
        ({"object_status": "revoked"}, "request_not_active"),
        ({"expires_at": NOW}, "retention_expired"),
    ],
)
def test_operational_gallery_requires_verified_scope_and_retention(changes, reason):
    evidence = _embedding_evidence(
        **({
            "authorization_method": "operational_gallery",
            "reference_source": "gallery_asset",
            "record_authorization_verified": True,
            "record_retention_verified": True,
            "legal_notice_version": "synthetic-notice-v1",
            "object_status": "active",
        } | changes)
    )
    decision = classify_biometric_evidence(evidence, now=NOW)
    assert decision.reason_code == reason
    assert decision.eligible is (reason == "eligible")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"source_context_confirmed": False}, "environment_context_unverified"),
        ({"source_environment": "production"}, "environment_not_distinct"),
        ({"target_environment": "STAGING"}, "environment_not_distinct"),
        ({"target_authorized": False}, "destination_not_authorized"),
        ({"privacy_scope_approved": False}, "privacy_scope_unapproved"),
        ({"tenant_context_valid": False}, "tenant_context_mismatch"),
        ({"purpose": None}, "purpose_unverified"),
        ({"purpose": "embedding"}, "purpose_mismatch"),
        ({"payload_present": False}, "ciphertext_absent"),
        ({"authorization_method": "legacy"}, "authorization_unverified"),
        ({"reference_source": "legacy_unknown"}, "reference_source_unverified"),
        ({"consent_version": None}, "consent_missing"),
        ({"subject_declaration": None}, "subject_declaration_unverified"),
        ({"reference_deleted_at": NOW}, "reference_deleted_or_revoked"),
        ({"request_status": "cancelled"}, "request_not_active"),
        ({"request_status": "unknown"}, "request_not_active"),
        ({"expires_at": NOW}, "retention_expired"),
        ({"expires_at": None}, "retention_unverified"),
    ],
)
def test_reference_with_missing_or_invalid_proof_stays_blocked(changes, reason):
    before = _reference_evidence(**changes)

    decision = classify_biometric_evidence(before, now=NOW)

    assert decision.eligible is False
    assert decision.reason_code == reason
    assert before == _reference_evidence(**changes)


def test_direct_region_notification_uses_legal_notice_not_upload_consent():
    evidence = _notification_evidence(
        authorization_method="direct_region",
        reference_source="indexed_region",
        consent_version=None,
        subject_declaration=None,
        legal_notice_version="synthetic-legal-v1",
        request_status="no_candidates",
    )

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is True
    assert decision.reason_code == "eligible"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"request_status": None}, "request_not_active"),
        ({"request_status": "cancelled"}, "request_not_active"),
        ({"request_status": "expired"}, "request_not_active"),
        ({"request_status": "unexpected"}, "request_not_active"),
        ({"object_status": "sent"}, "ciphertext_absent"),
        ({"authorization_method": "legacy"}, "authorization_unverified"),
        ({"reference_source": "indexed_region"}, "reference_source_unverified"),
        ({"expires_at": NOW - timedelta(seconds=1)}, "retention_expired"),
    ],
)
def test_notification_unknown_or_expired_context_stays_blocked(changes, reason):
    evidence = _notification_evidence(**changes)

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is False
    assert decision.reason_code == reason


def test_direct_region_notification_without_legal_notice_is_blocked():
    evidence = _notification_evidence(
        authorization_method="direct_region",
        reference_source="indexed_region",
        consent_version=None,
        subject_declaration=None,
        legal_notice_version=None,
    )

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is False
    assert decision.reason_code == "legal_notice_missing"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({}, "record_authorization_unverified"),
        ({"record_authorization_verified": True}, "retention_unverified"),
        (
            {
                "record_authorization_verified": True,
                "record_retention_verified": True,
                "expires_at": NOW,
            },
            "retention_expired",
        ),
    ],
)
def test_photo_embedding_without_per_record_authorization_and_retention_is_blocked(
    changes, reason
):
    decision = classify_biometric_evidence(
        _embedding_evidence(**changes), now=NOW
    )

    assert decision.eligible is False
    assert decision.reason_code == reason


def test_synthetic_embedding_proof_can_be_classified_without_claiming_live_eligibility():
    evidence = _embedding_evidence(
        record_authorization_verified=True,
        record_retention_verified=True,
        expires_at=NOW + timedelta(days=1),
    )

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is True
    assert decision.reason_code == "eligible"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"source_context_confirmed": False}, "environment_context_unverified"),
        ({"target_authorized": False}, "destination_not_authorized"),
        ({"tenant_context_valid": False}, "tenant_context_mismatch"),
        ({"privacy_scope_approved": False}, "privacy_scope_unapproved"),
    ],
)
def test_reference_locator_obeys_the_same_scope_and_authorization_gates(changes, reason):
    evidence = _reference_evidence(
        category="reference_locator",
        purpose="reference_locator",
        **changes,
    )

    decision = classify_biometric_evidence(evidence, now=NOW)

    assert decision.eligible is False
    assert decision.reason_code == reason


def test_evidence_contract_contains_no_payload_or_direct_identifier_fields():
    names = {item.name for item in fields(BiometricEligibilityEvidence)}

    assert "payload_present" in names
    assert not names.intersection(
        {"payload", "ciphertext", "tenant_id", "gallery_id", "client_id", "photo_id", "request_id"}
    )


def test_invalid_metadata_fails_closed_with_allowlisted_reason():
    decision = classify_biometric_evidence(
        replace(_reference_evidence(), category="unknown"), now=NOW
    )

    assert decision.eligible is False
    assert decision.reason_code == "unsupported_category"
