import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.facial.crypto import (
    FacialCryptoContext,
    FacialCryptoContextPair,
    FacialCryptoError,
    FacialScope,
)
from app.facial.environment_eligibility import BiometricEligibilityEvidence
from app.facial.environment_migration import (
    BiometricCiphertextRecord,
    FacialMigrationError,
    reencrypt_eligible_record,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
_SOURCE_CONTEXT = FacialCryptoContext.from_keyring(
    environment="staging",
    active_key_id="synthetic-source",
    keys={"synthetic-source": b"s" * 32},
)
_TARGET_CONTEXT = FacialCryptoContext.from_keyring(
    environment="production",
    active_key_id="synthetic-target",
    keys={"synthetic-target": b"t" * 32},
)
_CONTEXTS = FacialCryptoContextPair(
    source=_SOURCE_CONTEXT, destination=_TARGET_CONTEXT
)


def _approved_evidence(**overrides) -> BiometricEligibilityEvidence:
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


def _record(*, evidence=None) -> BiometricCiphertextRecord:
    evidence = evidence or _approved_evidence()
    tenant_id = uuid4()
    gallery_id = uuid4()
    object_id = uuid4()
    scope = FacialScope(
        environment="staging",
        gallery_id=gallery_id,
        object_kind="photo" if evidence.category == "photo_embedding" else "request",
        object_id=object_id,
        purpose=evidence.purpose,
        model_version="synthetic-model-v1",
        data_version="synthetic-consent-v1",
    )
    payload = b"synthetic biometric payload"
    envelope = _SOURCE_CONTEXT.cipher.encrypt(payload, scope=scope)
    return BiometricCiphertextRecord(
        tenant_id=tenant_id,
        gallery_id=gallery_id,
        client_id=uuid4(),
        object_id=object_id,
        scope=scope,
        envelope=envelope,
        evidence=evidence,
        created_at=NOW - timedelta(minutes=5),
        updated_at=NOW,
    )


def test_reencryption_preserves_identity_privacy_metadata_and_source_snapshot():
    source = _record()
    source_envelope = source.envelope
    source_scope = source.scope

    migrated = reencrypt_eligible_record(source, contexts=_CONTEXTS, now=NOW)

    assert migrated is not source
    assert migrated.tenant_id == source.tenant_id
    assert migrated.gallery_id == source.gallery_id
    assert migrated.client_id == source.client_id
    assert migrated.object_id == source.object_id
    assert migrated.created_at == source.created_at
    assert migrated.updated_at == source.updated_at
    assert migrated.evidence == source.evidence
    assert migrated.scope.environment == "production"
    assert replace(migrated.scope, environment="staging") == source_scope
    assert migrated.envelope != source_envelope
    assert _SOURCE_CONTEXT.cipher.decrypt(source_envelope, scope=source_scope) == (
        b"synthetic biometric payload"
    )
    assert _TARGET_CONTEXT.cipher.decrypt(
        migrated.envelope, scope=migrated.scope
    ) == b"synthetic biometric payload"
    with pytest.raises(FacialCryptoError):
        _TARGET_CONTEXT.cipher.decrypt(source_envelope, scope=migrated.scope)


@pytest.mark.parametrize(
    "evidence",
    [
        _approved_evidence(category="reference_locator", purpose="reference_locator"),
        _approved_evidence(
            category="search_notification",
            purpose="notification",
            object_status="queued",
        ),
        _approved_evidence(
            category="photo_embedding",
            purpose="embedding",
            record_authorization_verified=True,
            record_retention_verified=True,
            expires_at=NOW + timedelta(days=1),
        ),
    ],
)
def test_approved_synthetic_categories_can_be_reencrypted(evidence):
    source = _record(evidence=evidence)

    migrated = reencrypt_eligible_record(source, contexts=_CONTEXTS, now=NOW)

    assert migrated.scope.environment == "production"
    assert migrated.scope.purpose == evidence.purpose
    assert _TARGET_CONTEXT.cipher.decrypt(
        migrated.envelope, scope=migrated.scope
    ) == b"synthetic biometric payload"


def test_ineligible_record_is_rejected_before_source_or_target_crypto(monkeypatch):
    source = _record(evidence=_approved_evidence(consent_version=None))

    def unexpected_crypto(*args, **kwargs):
        raise AssertionError("crypto must not run for an ineligible record")

    monkeypatch.setattr(_SOURCE_CONTEXT.cipher, "decrypt", unexpected_crypto)
    monkeypatch.setattr(_TARGET_CONTEXT.cipher, "encrypt", unexpected_crypto)

    with pytest.raises(FacialMigrationError) as error:
        reencrypt_eligible_record(source, contexts=_CONTEXTS, now=NOW)

    assert error.value.reason_code == "consent_missing"
    assert source.evidence.consent_version is None


def test_context_or_scope_mismatch_is_rejected_without_mutating_snapshot():
    source = _record()
    wrong_scope = replace(source.scope, environment="development")
    mismatched = replace(source, scope=wrong_scope)

    with pytest.raises(FacialMigrationError) as error:
        reencrypt_eligible_record(mismatched, contexts=_CONTEXTS, now=NOW)

    assert error.value.reason_code == "source_scope_mismatch"
    assert source.scope.environment == "staging"
    assert mismatched.envelope == source.envelope


def test_evidence_context_must_match_the_supplied_cryptographic_contexts():
    source = _record(
        evidence=_approved_evidence(
            source_environment="homolog", target_environment="development"
        )
    )

    with pytest.raises(FacialMigrationError) as error:
        reencrypt_eligible_record(source, contexts=_CONTEXTS, now=NOW)

    assert error.value.reason_code == "source_scope_mismatch"


def test_corrupt_envelope_returns_sanitized_error_and_keeps_source_unchanged():
    source = _record()
    corrupted = replace(
        source,
        envelope=replace(source.envelope, ciphertext=b"synthetic-corruption"),
    )

    with pytest.raises(FacialMigrationError) as error:
        reencrypt_eligible_record(corrupted, contexts=_CONTEXTS, now=NOW)

    assert error.value.reason_code == "crypto_failure"
    assert str(error.value) == "Re-cifragem biométrica bloqueada."
    assert corrupted.envelope.ciphertext == b"synthetic-corruption"


def test_record_repr_does_not_include_ids_or_ciphertext():
    record = _record()

    rendered = repr(record)

    assert str(record.tenant_id) not in rendered
    assert str(record.gallery_id) not in rendered
    assert str(record.object_id) not in rendered
    assert record.envelope.ciphertext.decode("latin1") not in rendered


def test_blocked_migration_emits_no_logs_or_output_and_exception_is_allowlisted(
    caplog, capsys
):
    record = _record(evidence=_approved_evidence(consent_version=None))
    sentinels = {
        str(record.tenant_id),
        str(record.gallery_id),
        str(record.client_id),
        str(record.object_id),
        record.envelope.ciphertext.decode("latin1"),
        b"synthetic biometric payload".decode("ascii"),
    }

    with caplog.at_level(logging.DEBUG), pytest.raises(FacialMigrationError) as error:
        reencrypt_eligible_record(record, contexts=_CONTEXTS, now=NOW)

    captured = capsys.readouterr()
    rendered = " ".join(
        (str(error.value), repr(error.value), repr(record), caplog.text,
         captured.out, captured.err)
    )
    assert error.value.reason_code == "consent_missing"
    assert caplog.records == []
    assert captured.out == ""
    assert captured.err == ""
    assert all(sentinel not in rendered for sentinel in sentinels)
