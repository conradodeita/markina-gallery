"""Revisão explícita do perfil sem apagar identidade mínima, crédito ou mídia."""

import base64
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import photographer_onboarding as onboarding
from app import platform_console as console
from app.auth import (
    AdminUser,
    MediaArchiveCycle,
    MediaArchiveObject,
    PhotoCreditOperation,
    PhotographerBusinessProfile,
    PhotographerSignup,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureMediaDeletionBatch,
    TenantClosureRequest,
    now,
    password_hasher,
)
from app.media_archive_executor import execute_delete_operation
from app.photographer_cpf import active_cpf_fingerprint, cpf_matches_tenant
from app.private_fields import encrypt_private_document, encrypt_private_field
from app.tenant_profile_retention import (
    CONFIRMATION,
    profile_reduction_plan,
    profile_retention_payload,
    reduce_closed_profile,
)
from tests.test_photographer_credits import create_accounts, create_photo
from tests.test_platform_console_media_deletion import media_deletion_http as _media_deletion_http
from tests.test_tenant_client_isolation import client_db as _client_db
from tests.test_tenant_media_deletion import (
    _closed_archive_fixture,
    _request_deletion,
    _start_delete,
)

client_db = _client_db
media_deletion_http = _media_deletion_http
CPF = "52998224725"
ADDRESS = {"zip_code": "01310100", "street_name": "Rua de teste", "street_number": "123",
           "neighborhood": "Bairro de teste", "city": "São Paulo", "state": "SP"}


def _closed_profile(db, monkeypatch, tenant_id, photographer_id):
    monkeypatch.setenv("ADMIN_PRIVATE_FIELD_KEY", base64.urlsafe_b64encode(b"p" * 32).decode())
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-retention-fingerprint-key")
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", raising=False)
    version, fingerprint, duplicate = active_cpf_fingerprint(db, CPF)
    assert not duplicate
    db.get(Tenant, tenant_id).lifecycle = "closed"
    closed_at = now() - timedelta(days=4000)
    closure = TenantClosureRequest(
        tenant_id=tenant_id, request_id=uuid4(), requested_by=photographer_id,
        state="closed", requested_at=closed_at, closed_at=closed_at,
        terms_version="synthetic", terms_sha256="a" * 64, balance_snapshot=0, balance_acknowledged=True,
    )
    profile = PhotographerBusinessProfile(
        tenant_id=tenant_id, admin_user_id=photographer_id, full_name="Fotógrafa sintética",
        cpf_envelope=encrypt_private_field(CPF, tenant_id=tenant_id, field="photographer-cpf"),
        address_envelope=encrypt_private_document("synthetic address", tenant_id=tenant_id, field="photographer-address"),
        cpf_fingerprint=fingerprint, cpf_fingerprint_key_version=version,
    )
    db.add_all([closure, profile])
    db.commit()
    return profile, closure


@pytest.fixture
def retention_context(client_db, monkeypatch):
    _, tenant, owner, photographer = create_accounts(client_db)
    profile, closure = _closed_profile(client_db, monkeypatch, tenant.id, photographer.id)
    return tenant, owner, photographer, profile, closure


def test_reduction_requires_review_then_removes_only_reversible_profile_fields(client_db, retention_context):
    tenant, owner, photographer, profile, closure = retention_context
    original = (profile.full_name, photographer.email, profile.cpf_fingerprint, profile.cpf_fingerprint_key_version)
    assert profile_reduction_plan(client_db, tenant_id=tenant.id).blocker is None
    # Consultar o aniversário não executa a redução.
    assert profile.cpf_envelope and profile.address_envelope
    result = reduce_closed_profile(client_db, owner_id=owner.id, tenant_id=tenant.id,
                                  confirmation=CONFIRMATION, confirm_review=True)
    assert result == closure.id
    assert profile.cpf_envelope is None and profile.address_envelope is None
    assert (profile.full_name, photographer.email, profile.cpf_fingerprint,
            profile.cpf_fingerprint_key_version) == original
    assert cpf_matches_tenant(client_db, tenant.id, CPF)
    assert profile_retention_payload(client_db, tenant_id=tenant.id)["state"] == "reduced"
    assert CPF not in str(profile_retention_payload(client_db, tenant_id=tenant.id))


@pytest.mark.parametrize("reason", ["recent", "open", "missing_key", "mismatched_cpf", "pending_obligation"])
def test_failed_preflight_preserves_both_envelopes(client_db, retention_context, monkeypatch, reason):
    tenant, owner, _, profile, closure = retention_context
    original = (profile.cpf_envelope, profile.address_envelope, profile.cpf_fingerprint)
    if reason == "recent":
        closure.closed_at = now() - timedelta(days=30)
    elif reason == "open":
        tenant.lifecycle = "open"
    elif reason == "missing_key":
        monkeypatch.delenv("ADMIN_PRIVATE_FIELD_KEY")
    elif reason == "mismatched_cpf":
        profile.cpf_fingerprint = "f" * 64
        original = (profile.cpf_envelope, profile.address_envelope, profile.cpf_fingerprint)
    else:
        monkeypatch.setattr("app.tenant_profile_retention.operational_obligation_blockers",
                            lambda *_args: ["financial_review"])
    client_db.flush()
    with pytest.raises(HTTPException) as failure:
        reduce_closed_profile(client_db, owner_id=owner.id, tenant_id=tenant.id,
                              confirmation=CONFIRMATION, confirm_review=True)
    assert failure.value.status_code == 409
    assert (profile.cpf_envelope, profile.address_envelope, profile.cpf_fingerprint) == original


def test_actor_and_explicit_confirmations_cannot_be_bypassed(client_db, retention_context):
    tenant, owner, photographer, profile, _ = retention_context
    for actor, phrase, review, status in (
        (photographer.id, CONFIRMATION, True, 403),
        (owner.id, "wrong", True, 422), (owner.id, CONFIRMATION, False, 422),
    ):
        with pytest.raises(HTTPException) as failure:
            reduce_closed_profile(client_db, owner_id=actor, tenant_id=tenant.id,
                                  confirmation=phrase, confirm_review=review)
        assert failure.value.status_code == status
    assert profile.cpf_envelope and profile.address_envelope


def test_reopened_profile_requires_same_cpf_and_address_before_checkout(
    client_db, retention_context, monkeypatch,
):
    from app import main

    tenant, owner, photographer, profile, _ = retention_context
    reduce_closed_profile(client_db, owner_id=owner.id, tenant_id=tenant.id,
                          confirmation=CONFIRMATION, confirm_review=True)
    tenant.lifecycle = "open"
    signup = PhotographerSignup(
        photographer_name=profile.full_name, email=photographer.email, state="active",
        otp_expires_at=now(), reserved_admin_id=photographer.id, reserved_tenant_id=tenant.id,
        activated_tenant_id=tenant.id, adult_attested_at=now(), activated_at=now(),
    )
    client_db.add(signup)
    client_db.commit()
    session = SimpleNamespace(subject_id=photographer.id, tenant_id=tenant.id)
    monkeypatch.setattr(onboarding, "_context", lambda *_args: (session, photographer, signup))
    monkeypatch.setattr(main, "require_same_origin", lambda *_args: None)
    with pytest.raises(HTTPException) as incomplete:
        onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant.id, admin_id=photographer.id)
    assert incomplete.value.status_code == 409
    assert incomplete.value.detail["profile_complete"] is False
    with pytest.raises(HTTPException) as checkout:
        onboarding.checkout_identity(None, client_db)
    assert checkout.value.status_code == 409
    wrong = onboarding.ProfileInput(cpf=SecretStr("11144477735"), address=ADDRESS)
    with pytest.raises(HTTPException) as mismatch:
        onboarding.save_profile(wrong, None, client_db)
    assert mismatch.value.status_code == 409 and profile.cpf_envelope is None
    valid = onboarding.ProfileInput(cpf=SecretStr(CPF), address=ADDRESS)
    assert onboarding.save_profile(valid, None, client_db)["profile_complete"] is True
    identity = onboarding.checkout_identity(None, client_db)
    assert identity["identification_number"] == CPF and identity["address"]["zip_code"] == "01310100"


def test_http_reduction_reauthenticates_and_audits_idempotent_request(
    media_deletion_http, client_db, monkeypatch,
):
    from app import main

    client, tenant_id, owner_id = media_deletion_http
    photographer_id = client_db.scalar(select(TenantAdmin.admin_user_id).where(TenantAdmin.tenant_id == tenant_id))
    profile, closure = _closed_profile(client_db, monkeypatch, tenant_id, photographer_id)
    profile_id, closure_id = profile.id, closure.id
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda *_args: None)
    actions = []
    monkeypatch.setattr(console, "enforce_rate_limit", lambda _db, action, *_args, **_kwargs: actions.append(action))
    request_id = uuid4()
    payload = {"request_id": str(request_id), "confirm_phrase": CONFIRMATION, "confirm_review": True,
               "current_password": "wrong", "totp_code": pyotp.TOTP(owner.totp_secret).now()}
    path = f"/admin/platform/console/tenants/{tenant_id}/closure/profile-reduction"
    assert client.post(path, json=payload).status_code == 403
    assert client_db.scalar(select(PhotographerBusinessProfile.cpf_envelope).where(
        PhotographerBusinessProfile.id == profile_id,
    )) is not None
    payload["current_password"] = "SyntheticOwnerPassword!2026"
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "reduced" and response.json()["replayed"] is False
    assert CPF not in response.text and "fingerprint" not in response.text
    replay = client.post(path, json={**payload, "current_password": "not-used-for-replay"})
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    events = list(client_db.scalars(select(PlatformAdminEvent).where(PlatformAdminEvent.action == "tenant.profile_reduced")))
    assert len(events) == 1 and events[0].object_id == closure_id
    assert events[0].previous_status == "retained" and events[0].next_status == "reduced"
    assert actions == ["platform_tenant_profile_reduction"] * 2


def test_http_reduction_rejects_cross_origin_before_mutation(media_deletion_http):
    client, tenant_id, _owner_id = media_deletion_http
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/profile-reduction",
        headers={"Origin": "https://unrelated.example.test"},
        json={"request_id": str(uuid4()), "confirm_phrase": CONFIRMATION, "confirm_review": True,
              "current_password": "synthetic", "totp_code": "123456"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(("delete_media", "tamper_receipt"), [(False, False), (True, False), (True, True)])
def test_profile_reduction_preserves_media_or_requires_verified_deletion_receipt(
    tmp_path, monkeypatch, delete_media, tamper_receipt,
):
    engine, tenant_id, cycle_id, owner_id, storage = _closed_archive_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("ADMIN_PRIVATE_FIELD_KEY", base64.urlsafe_b64encode(b"p" * 32).decode())
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-retention-fingerprint-key")
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", raising=False)
    with Session(engine, expire_on_commit=False) as db:
        profile = db.scalar(select(PhotographerBusinessProfile).where(PhotographerBusinessProfile.tenant_id == tenant_id))
        profile.cpf_fingerprint_key_version = "legacy-v0"
        db.flush()
        version, fingerprint, duplicate = active_cpf_fingerprint(db, CPF, exclude_profile_id=profile.id)
        assert not duplicate
        profile.cpf_fingerprint, profile.cpf_fingerprint_key_version = fingerprint, version
        profile.cpf_envelope = encrypt_private_field(CPF, tenant_id=tenant_id, field="photographer-cpf")
        profile.address_envelope = encrypt_private_document("synthetic address", tenant_id=tenant_id, field="photographer-address")
        db.commit()
        if delete_media:
            _request_deletion(db, tenant_id=tenant_id, owner_id=owner_id)
            claim = _start_delete(db, tenant_id=tenant_id)
            assert execute_delete_operation(db, claim, storage=storage).status == "completed"
            assert profile.cpf_fingerprint is None
        if tamper_receipt:
            batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
                TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
            ))
            batch.inventory_sha256 = "b" * 64
            db.commit()
            with pytest.raises(HTTPException) as failure:
                reduce_closed_profile(db, owner_id=owner_id, tenant_id=tenant_id,
                                      confirmation=CONFIRMATION, confirm_review=True)
            assert failure.value.status_code == 409
            assert profile.cpf_envelope and profile.address_envelope
            return
        before = dict(storage.objects)
        reduce_closed_profile(db, owner_id=owner_id, tenant_id=tenant_id,
                              confirmation=CONFIRMATION, confirm_review=True)
        assert storage.objects == before
        assert profile.cpf_envelope is None and profile.address_envelope is None
        assert db.get(MediaArchiveCycle, cycle_id).state == ("deleted" if delete_media else "archived")
        if not delete_media:
            assert cpf_matches_tenant(db, tenant_id, CPF)
            assert all(row.remote_deleted_at is None for row in db.scalars(select(MediaArchiveObject)))


def test_pending_operation_blocks_only_its_own_tenant(client_db, retention_context):
    tenant, owner, _photographer, profile, _closure = retention_context
    other = Tenant()
    client_db.add(other)
    client_db.flush()
    operations = []
    for target in (other, tenant):
        photo = create_photo(client_db, target.id)
        operation = PhotoCreditOperation(
            tenant_id=target.id, photo_asset_id=photo.id, photo_asset_id_snapshot=photo.id,
            storage_key_snapshot=photo.storage_key, payload_fingerprint="c" * 64,
        )
        client_db.add(operation)
        client_db.commit()
        operations.append(operation)
        assert profile_reduction_plan(client_db, tenant_id=tenant.id).blocker == (
            "obligations_pending" if target is tenant else None
        )
    with pytest.raises(HTTPException) as failure:
        reduce_closed_profile(client_db, owner_id=owner.id, tenant_id=tenant.id,
                              confirmation=CONFIRMATION, confirm_review=True)
    assert failure.value.status_code == 409 and profile.cpf_envelope
    operations[1].status = "released"
    client_db.commit()
    assert profile_reduction_plan(client_db, tenant_id=tenant.id).blocker is None
