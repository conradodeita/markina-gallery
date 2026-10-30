import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.facial.crypto import (
    FacialCryptoContext,
    FacialCryptoContextPair,
    FacialScope,
)
from app.facial.environment_backup import (
    EncryptedBiometricBackup,
    FacialBackupError,
    create_encrypted_biometric_backup,
    restore_encrypted_biometric_backup,
)
from app.facial.environment_eligibility import BiometricEligibilityEvidence
from app.facial.environment_migration import BiometricCiphertextRecord

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
SOURCE = FacialCryptoContext.from_keyring(
    environment="staging",
    active_key_id="synthetic-source",
    keys={"synthetic-source": b"s" * 32},
)
DESTINATION = FacialCryptoContext.from_keyring(
    environment="production",
    active_key_id="synthetic-target",
    keys={"synthetic-target": b"t" * 32},
)
CONTEXTS = FacialCryptoContextPair(source=SOURCE, destination=DESTINATION)
BACKUP_KEY = b"b" * 32
BACKUP_KEY_ID = "synthetic-backup"


def _record() -> BiometricCiphertextRecord:
    tenant_id = uuid4()
    gallery_id = uuid4()
    client_id = uuid4()
    object_id = uuid4()
    scope = FacialScope(
        environment="staging",
        gallery_id=gallery_id,
        object_kind="request",
        object_id=object_id,
        purpose="reference_image",
        model_version="synthetic-model-v1",
        data_version="synthetic-consent-v1",
    )
    envelope = SOURCE.cipher.encrypt(b"synthetic biometric payload", scope=scope)
    evidence = BiometricEligibilityEvidence(
        category="reference_file",
        source_environment="staging",
        target_environment="production",
        purpose="reference_image",
        source_context_confirmed=True,
        privacy_scope_approved=True,
        target_authorized=True,
        tenant_context_valid=True,
        payload_present=True,
        authorization_method="explicit_consent",
        reference_source="upload",
        consent_version="synthetic-consent-v1",
        subject_declaration="conditional",
        object_status="ready",
        request_status="ready",
        expires_at=NOW + timedelta(days=1),
    )
    return BiometricCiphertextRecord(
        tenant_id=tenant_id,
        gallery_id=gallery_id,
        client_id=client_id,
        object_id=object_id,
        scope=scope,
        envelope=envelope,
        evidence=evidence,
        created_at=NOW - timedelta(minutes=1),
        updated_at=NOW,
    )


def _backup(record, **overrides):
    values = {
        "records": (record,),
        "contexts": CONTEXTS,
        "key_id": BACKUP_KEY_ID,
        "backup_key": BACKUP_KEY,
    }
    values.update(overrides)
    return create_encrypted_biometric_backup(**values)


def test_backup_payload_roundtrips_encrypted_snapshot_without_exposing_fields(tmp_path):
    record = _record()
    backup = _backup(record)
    path = tmp_path / "synthetic-encrypted-backup.json"
    path.write_text(json.dumps(backup.payload()), encoding="utf-8")
    stored_payload = path.read_text(encoding="utf-8")

    reopened = EncryptedBiometricBackup.from_payload(json.loads(stored_payload))
    restored = restore_encrypted_biometric_backup(
        reopened,
        contexts=CONTEXTS,
        key_id=BACKUP_KEY_ID,
        backup_key=BACKUP_KEY,
    )

    assert restored == (record,)
    assert str(record.tenant_id) not in stored_payload
    assert str(record.gallery_id) not in stored_payload
    assert str(record.client_id) not in stored_payload
    assert str(record.object_id) not in stored_payload
    assert "synthetic biometric payload" not in stored_payload
    assert record.envelope.ciphertext.hex() not in stored_payload
    assert repr(backup) == "EncryptedBiometricBackup(<redacted>)"


def test_corrupted_backup_fails_before_any_restore_artifact_is_written(tmp_path):
    record = _record()
    backup = _backup(record)
    corrupt = replace(backup, ciphertext=backup.ciphertext[:-1] + b"x")
    restore_path = tmp_path / "must-not-exist"

    with pytest.raises(FacialBackupError) as error:
        restored = restore_encrypted_biometric_backup(
            corrupt,
            contexts=CONTEXTS,
            key_id=BACKUP_KEY_ID,
            backup_key=BACKUP_KEY,
        )
        restore_path.write_text(repr(restored), encoding="utf-8")

    assert str(error.value) == "Backup biométrico indisponível ou inválido."
    assert not restore_path.exists()


@pytest.mark.parametrize(
    ("key_id", "backup_key"),
    [
        ("synthetic-backup", b"b" * 31),
        ("bad key", b"b" * 32),
    ],
)
def test_backup_rejects_invalid_key_material_before_creating_a_backup(key_id, backup_key):
    with pytest.raises(FacialBackupError, match="Backup biométrico indisponível"):
        _backup(_record(), key_id=key_id, backup_key=backup_key)


def test_backup_authentication_binds_environment_pair_and_key_identifier():
    backup = _backup(_record())
    other_contexts = FacialCryptoContextPair(
        source=SOURCE,
        destination=FacialCryptoContext.from_keyring(
            environment="development",
            active_key_id="synthetic-target",
            keys={"synthetic-target": b"t" * 32},
        ),
    )

    with pytest.raises(FacialBackupError):
        restore_encrypted_biometric_backup(
            backup,
            contexts=other_contexts,
            key_id=BACKUP_KEY_ID,
            backup_key=BACKUP_KEY,
        )
    with pytest.raises(FacialBackupError):
        restore_encrypted_biometric_backup(
            backup,
            contexts=CONTEXTS,
            key_id="other-backup",
            backup_key=BACKUP_KEY,
        )


def test_backup_rejects_unreviewed_payload_fields():
    payload = _backup(_record()).payload()
    payload["object_id"] = str(uuid4())

    with pytest.raises(FacialBackupError):
        EncryptedBiometricBackup.from_payload(payload)
