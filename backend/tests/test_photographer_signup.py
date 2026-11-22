"""Prova HTTP/DB real do cadastro; somente anti-bot e e-mail são simulados."""

import base64
import hashlib
import json
import secrets
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import auth, platform_console
from app import photographer_onboarding as onboarding
from app import photographer_signup as signup
from app import photographer_terms as terms
from app.admin_security import decrypt_sensitive_payload
from app.auth import (
    AdminUser,
    Client,
    EmailDelivery,
    PhotographerCreditEntry,
    PhotographerSignup,
    PhotographerTermsVersion,
    Role,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    now,
)
from app.email_delivery import EmailConfigurationError
from app.main import protect_credential_validation_input
from app.photographer_cpf import (
    LEGACY_KEY_VERSION,
    PhotographerCpfFingerprintError,
    active_cpf_fingerprint,
    cpf_matches_tenant,
)
from app.system_monitor.models import MonitorGrant, PlatformOwner
from app.worker import validate_email_origin
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
ROOT = "/api/auth/photographer-signup"
PASSWORD = "IsolatedFlow!47Alpha"
ADDRESS = {
    "zip_code": "01311-000", "street_name": "Avenida Paulista", "street_number": "1000",
    "neighborhood": "Bela Vista", "city": "São Paulo", "state": "SP", "complement": "",
}


@pytest.fixture
def proof(client_db, monkeypatch):
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED", "true")
    monkeypatch.setenv("PHOTOGRAPHER_TEST_TERMS_ENABLED", "true")
    monkeypatch.setenv("ADMIN_PRIVATE_FIELD_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    messages = []

    class Services:
        def verify_bot(self, proof, _address):
            return proof == "synthetic-proof"

        def send_code(self, _db, signup_row, code):
            messages.append((signup_row.email, code))

    app = FastAPI()
    app.include_router(signup.router, prefix="/api")
    app.include_router(onboarding.router, prefix="/api")
    app.include_router(platform_console.router, prefix="/api")
    app.add_exception_handler(RequestValidationError, protect_credential_validation_input)
    app.dependency_overrides[signup.signup_services] = Services
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(signup, "SessionLocal", factory)
    monkeypatch.setattr(onboarding, "SessionLocal", factory)
    monkeypatch.setattr(platform_console, "SessionLocal", factory)

    @app.get("/api/probe-admin")
    def probe_admin(request: Request):
        session = auth.current_session(request, Role.ADMIN)
        return {"tenant_id": str(session.tenant_id), "subject_id": str(session.subject_id)}

    return TestClient(app), messages


def test_progressive_profile_terms_and_checkout_identity_are_tenant_scoped(proof, client_db, monkeypatch):
    client, messages = proof
    account = verify(client, messages, start(client))
    assert finish(client, account).status_code == 200
    status = client.get("/api/admin/onboarding")
    assert status.status_code == 200
    assert status.json()["exploratory"] and not status.json()["can_buy_credits"]
    signup_row = client_db.scalar(select(PhotographerSignup).where(PhotographerSignup.state == "active"))
    admin_id = signup_row.reserved_admin_id
    tenant_id = signup_row.activated_tenant_id
    client_db.commit()
    monkeypatch.setattr(onboarding, "channel_settings", lambda *_args, **_kwargs: SimpleNamespace(status="sandbox"))
    monkeypatch.setenv("APP_ENV", "production")
    production_state = onboarding.onboarding_status(
        client_db, admin=client_db.get(AdminUser, admin_id), tenant_id=tenant_id, signup=signup_row,
    )
    assert not production_state["whatsapp_configured"]
    monkeypatch.setenv("APP_ENV", "development")
    with pytest.raises(HTTPException) as purchase_blocked:
        onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    assert purchase_blocked.value.status_code == 409
    client_db.rollback()
    with pytest.raises(HTTPException) as upload_blocked:
        onboarding.require_upload_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    assert upload_blocked.value.status_code == 409
    client_db.rollback()
    saved = client.put("/api/admin/onboarding/profile", json={"cpf": "529.982.247-25", "address": ADDRESS})
    assert saved.status_code == 200
    before_acceptance = client.get("/api/admin/onboarding").json()
    assert before_acceptance["can_buy_credits"] and not before_acceptance["terms_accepted"]
    onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    assert "52998224725" not in saved.text
    profile = client_db.scalar(select(onboarding.PhotographerBusinessProfile))
    assert profile.full_name == "Fotógrafa sintética"
    assert "52998224725" not in profile.cpf_envelope
    assert profile.cpf_fingerprint != "52998224725"
    assert profile.cpf_fingerprint_key_version == LEGACY_KEY_VERSION
    assert profile.cpf_fingerprint == auth.pii_fingerprint("photographer-cpf:52998224725")
    assert "Paulista" not in profile.address_envelope
    identity = client.get("/api/admin/onboarding/checkout-identity")
    assert identity.json() == {
        "name": "Fotógrafa sintética", "email": "signup@example.test",
        "identification_number": "52998224725",
        "address": {**ADDRESS, "zip_code": "01311000"},
    }
    assert client.post("/api/admin/onboarding/terms/test-acceptance", json={"accepted": True}).status_code == 200
    assert client.post("/api/admin/onboarding/terms/test-acceptance", json={"accepted": True}).status_code == 200
    updated = client.get("/api/admin/onboarding")
    assert updated.json()["profile_complete"] and updated.json()["terms_accepted"]
    assert updated.json()["can_buy_credits"]
    assert "52998224725" not in updated.text
    assert "no-store" in identity.headers["cache-control"]
    admin = client_db.get(AdminUser, admin_id)
    admin.email_verified = False
    client_db.commit()
    with pytest.raises(HTTPException) as email_blocked:
        onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    assert email_blocked.value.status_code == 409
    admin.email_verified = True
    client_db.commit()
    monkeypatch.setenv("APP_ENV", "production")
    production_state = onboarding.onboarding_status(
        client_db, admin=client_db.get(AdminUser, admin_id), tenant_id=tenant_id, signup=signup_row,
    )
    assert not production_state["terms_available"] and production_state["can_buy_credits"]
    assert not production_state["can_upload"]
    onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    client_db.rollback()
    monkeypatch.setenv("APP_ENV", "development")
    onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    client_db.commit()
    with pytest.raises(HTTPException) as upload_still_blocked:
        onboarding.require_upload_ready(client_db, tenant_id=tenant_id, admin_id=admin_id)
    assert upload_still_blocked.value.status_code == 409
    client_db.rollback()


def test_profile_validation_does_not_echo_cpf_or_accept_injected_tenant(proof):
    client, messages = proof
    assert finish(client, verify(client, messages, start(client))).status_code == 200
    denied = client.put("/api/admin/onboarding/profile", json={
        "cpf": "52998224725", "address": ADDRESS, "tenant_id": "other-tenant",
    })
    assert denied.status_code == 422
    assert "52998224725" not in denied.text and "other-tenant" not in denied.text


def test_published_terms_render_per_photographer_and_acceptance_keeps_immutable_snapshot(proof, client_db, monkeypatch):
    from app import photographer_credits

    monkeypatch.setattr(onboarding, "global_pix_settings", lambda *_args, **_kwargs: SimpleNamespace(status="active"))
    monkeypatch.setattr(onboarding, "channel_settings", lambda *_args, **_kwargs: SimpleNamespace(status="ready"))
    monkeypatch.setattr(photographer_credits, "wallet_snapshot", lambda *_args, **_kwargs: {"available_credits": 10})
    client, messages = proof
    setup = verify(client, messages, start(client, name="Fotógrafa do tenant"))
    assert finish(client, setup).status_code == 200
    admin = client_db.scalar(select(AdminUser).where(AdminUser.email == "signup@example.test"))
    template = terms.DEFAULT_TEMPLATE.read_text(encoding="utf-8-sig")
    version = PhotographerTermsVersion(
        version_number=1, terms_version="v1", template_text=template,
        template_sha256=hashlib.sha256(template.encode("utf-8")).hexdigest(),
        provider_legal_name="Provedor sintético", provider_contact_email="support@example.test",
        published_by_admin_id=admin.id, published_at=now(),
    )
    client_db.add(version)
    client_db.commit()

    profile = client.put("/api/admin/onboarding/profile", json={"cpf": "52998224725", "address": ADDRESS})
    assert profile.status_code == 200
    signup_row = client_db.scalar(select(PhotographerSignup).where(PhotographerSignup.state == "active"))
    tenant_id = signup_row.activated_tenant_id
    pending = client.get("/api/admin/onboarding").json()
    assert all(pending[key] for key in ("email_verified", "profile_complete", "pix_configured", "whatsapp_configured", "credits_available"))
    assert pending["can_buy_credits"] and not pending["terms_accepted"] and not pending["can_upload"]
    onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin.id)
    with pytest.raises(HTTPException) as terms_blocked:
        onboarding.require_upload_ready(client_db, tenant_id=tenant_id, admin_id=admin.id)
    assert terms_blocked.value.status_code == 409
    assert terms_blocked.value.detail["terms_accepted"] is False
    # require_upload_ready serializes against tenant closure with FOR UPDATE.
    # Release that expected-failure transaction before the HTTP acceptance flow.
    client_db.rollback()
    terms_response = client.get("/api/admin/onboarding/terms")
    assert terms_response.status_code == 200 and terms_response.json()["test_only"] is False
    assert terms_response.json()["version"] == "v1"
    rendered = terms_response.json()["text"]
    assert "Provedor sintético" in rendered and "support@example.test" in rendered
    assert "Fotógrafa do tenant" in rendered and "signup@example.test" in rendered
    assert "### 12. Suspensão e encerramento da conta" in rendered
    assert "### 14. Aviso de Privacidade do serviço" in rendered
    assert "referência protegida e versionada do CPF" in rendered
    assert "Google Drive" not in rendered

    unchecked = client.post("/api/admin/onboarding/terms/accept", json={"version": "v1", "accepted": False})
    assert unchecked.status_code == 422
    assert client_db.scalar(select(func.count()).select_from(onboarding.PhotographerTermsAcceptance)) == 0
    stale = client.post("/api/admin/onboarding/terms/accept", json={"version": "old", "accepted": True})
    assert stale.status_code == 409
    accepted = client.post("/api/admin/onboarding/terms/accept", json={"version": "v1", "accepted": True})
    assert accepted.status_code == 200 and accepted.json()["version"] == "v1"
    assert client.get("/api/admin/onboarding").json()["can_upload"] is True
    onboarding.require_upload_ready(client_db, tenant_id=tenant_id, admin_id=admin.id)
    record = client_db.scalar(select(onboarding.PhotographerTermsAcceptance))
    assert record.terms_text == terms_response.json()["text"]
    assert record.terms_sha256 == hashlib.sha256(record.terms_text.encode("utf-8")).hexdigest()
    assert "support@example.test" in record.provider_identity
    assert "Fotógrafa do tenant" in record.photographer_identity
    acceptances = client.get("/api/admin/onboarding/terms/acceptances")
    assert acceptances.status_code == 200 and len(acceptances.json()["items"]) == 1
    acceptance_id = acceptances.json()["items"][0]["id"]
    copy = client.get(f"/api/admin/onboarding/terms/acceptances/{acceptance_id}/copy")
    assert copy.status_code == 200 and "support@example.test" in copy.text
    assert record.terms_sha256 in copy.text and record.terms_text in copy.text
    accepted_text = record.terms_text
    accepted_hash = record.terms_sha256
    assert "attachment; filename=\"termos-pick-your-pic-v1.txt\"" in copy.headers["content-disposition"]
    assert client.post("/api/admin/onboarding/terms/accept", json={"version": "v1", "accepted": True}).status_code == 200
    next_template = template + " · versão futura"
    client_db.add(PhotographerTermsVersion(
        version_number=2, terms_version="v2", template_text=next_template,
        template_sha256=hashlib.sha256(next_template.encode("utf-8")).hexdigest(),
        provider_legal_name="Provedor sintético", provider_contact_email="support@example.test",
        published_by_admin_id=admin.id, published_at=now(),
    ))
    client_db.commit()
    outdated = client.get("/api/admin/onboarding").json()
    assert outdated["terms_accepted"] is False and outdated["can_upload"] is False
    assert outdated["can_buy_credits"] is True
    onboarding.require_credit_purchase_ready(client_db, tenant_id=tenant_id, admin_id=admin.id)
    with pytest.raises(HTTPException) as outdated_terms:
        onboarding.require_upload_ready(client_db, tenant_id=tenant_id, admin_id=admin.id)
    assert outdated_terms.value.status_code == 409
    assert outdated_terms.value.detail["terms_accepted"] is False
    preserved_copy = client.get(f"/api/admin/onboarding/terms/acceptances/{acceptance_id}/copy")
    assert preserved_copy.status_code == 200
    assert accepted_text in preserved_copy.text and accepted_hash in preserved_copy.text
    assert "versão futura" not in preserved_copy.text


def test_cpf_is_globally_unique_without_exposing_or_reassigning_another_profile(proof, client_db):
    client, messages = proof
    assert finish(client, verify(client, messages, start(client, name="Primeira conta"))).status_code == 200
    assert client.put("/api/admin/onboarding/profile", json={"cpf": "529.982.247-25", "address": ADDRESS}).status_code == 200
    first = client_db.scalar(select(onboarding.PhotographerBusinessProfile))
    first_id, first_tenant, first_envelope = first.id, first.tenant_id, first.cpf_envelope
    client_db.commit()
    assert finish(client, verify(client, messages, start(client, name="Segunda conta", email="another-profile@example.test"))).status_code == 200
    assert client.get("/api/admin/onboarding/checkout-identity").status_code == 409
    duplicate = client.put("/api/admin/onboarding/profile", json={"cpf": "52998224725", "address": ADDRESS})
    assert duplicate.status_code == 409
    assert "Primeira conta" not in duplicate.text and "signup@example.test" not in duplicate.text
    assert "52998224725" not in duplicate.text
    assert not client.get("/api/admin/onboarding").json()["can_buy_credits"]
    distinct = client.put("/api/admin/onboarding/profile", json={"cpf": "11144477735", "address": ADDRESS})
    assert distinct.status_code == 200
    identity = client.get("/api/admin/onboarding/checkout-identity").json()
    assert identity["name"] == "Segunda conta" and identity["identification_number"] == "11144477735"
    client_db.expire_all()
    first = client_db.get(onboarding.PhotographerBusinessProfile, first_id)
    assert first.tenant_id == first_tenant and first.full_name == "Primeira conta" and first.cpf_envelope == first_envelope


def test_versioned_cpf_fingerprint_survives_rotation_and_stays_tenant_scoped(proof, client_db, monkeypatch):
    client, messages = proof
    key_v1 = base64.b64encode(b"\x11" * 32).decode("ascii")
    key_v2 = base64.b64encode(b"\x22" * 32).decode("ascii")
    monkeypatch.setenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", json.dumps({"v1": key_v1}))
    monkeypatch.setenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", "v1")

    assert finish(client, verify(client, messages, start(client, name="Primeira versão"))).status_code == 200
    assert client.put("/api/admin/onboarding/profile", json={
        "cpf": "529.982.247-25", "address": ADDRESS,
    }).status_code == 200
    first = client_db.scalar(select(onboarding.PhotographerBusinessProfile))
    first_tenant = first.tenant_id
    assert first.cpf_fingerprint_key_version == "v1"
    assert cpf_matches_tenant(client_db, first_tenant, "52998224725")

    assert finish(client, verify(client, messages, start(
        client, name="Outra conta", email="another-version@example.test",
    ))).status_code == 200
    second_signup = client_db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.email == "another-version@example.test",
    ))
    assert second_signup and not cpf_matches_tenant(
        client_db, second_signup.activated_tenant_id, "52998224725",
    )

    monkeypatch.setenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", json.dumps({
        "v1": key_v1, "v2": key_v2,
    }))
    monkeypatch.setenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", "v2")
    assert cpf_matches_tenant(client_db, first_tenant, "52998224725")
    version, _candidate, duplicate = active_cpf_fingerprint(client_db, "52998224725")
    assert version == "v2" and duplicate
    # A conferência direta abre lock transacional no PostgreSQL; a próxima
    # requisição HTTP usa outra conexão e deve começar após essa transação.
    client_db.commit()
    duplicate_response = client.put("/api/admin/onboarding/profile", json={
        "cpf": "52998224725", "address": ADDRESS,
    })
    assert duplicate_response.status_code == 409
    assert "52998224725" not in duplicate_response.text
    assert "Primeira versão" not in duplicate_response.text

    # Uma versão referenciada sem chave disponível bloqueia a gravação de forma genérica.
    monkeypatch.setenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", json.dumps({"v2": key_v2}))
    unavailable = client.put("/api/admin/onboarding/profile", json={
        "cpf": "11144477735", "address": ADDRESS,
    })
    assert unavailable.status_code == 503
    assert "11144477735" not in unavailable.text


def test_legacy_cpf_fingerprint_fails_closed_when_secret_is_missing(proof, client_db, monkeypatch):
    client, messages = proof
    assert finish(client, verify(client, messages, start(client))).status_code == 200
    assert client.put("/api/admin/onboarding/profile", json={
        "cpf": "52998224725", "address": ADDRESS,
    }).status_code == 200
    profile = client_db.scalar(select(onboarding.PhotographerBusinessProfile))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_PII_FINGERPRINT_SALT", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON", raising=False)
    monkeypatch.delenv("PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION", raising=False)

    with pytest.raises(PhotographerCpfFingerprintError):
        cpf_matches_tenant(client_db, profile.tenant_id, "52998224725")
    unavailable = client.put("/api/admin/onboarding/profile", json={
        "cpf": "52998224725", "address": ADDRESS,
    })
    assert unavailable.status_code == 503
    assert "52998224725" not in unavailable.text


def start(client, *, name="Fotógrafa sintética", email="signup@example.test"):
    response = client.post(ROOT, json={"photographer_name": name, "email": email,
                                      "adult_attested": True, "anti_bot_proof": "synthetic-proof"})
    assert response.status_code == 202
    assert set(response.json()) == {"request_id", "message"}
    return response.json()["request_id"]


def verify(client, messages, request_id):
    response = client.post(ROOT + "/verify-email", json={"request_id": request_id, "code": messages[-1][1]})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    setup = client.get(ROOT + "/setup")
    assert setup.status_code == 200
    return setup.json()


def finish(client, setup):
    return client.post(ROOT + "/complete", json={"password": PASSWORD})


def test_adult_attestation_is_required_before_persisting_candidate_or_sending_email(proof, client_db):
    client, messages = proof
    payload = {"photographer_name": "Candidato sintético", "email": "minor-photographer@example.test",
               "anti_bot_proof": "synthetic-proof"}
    missing = client.post(ROOT, json=payload)
    assert missing.status_code == 422
    declined = client.post(ROOT, json={**payload, "adult_attested": False})
    assert declined.status_code == 400
    assert client_db.scalar(select(func.count()).select_from(PhotographerSignup)) == 0
    assert messages == []


def test_automatic_signup_creates_finite_tenant_and_real_admin_session_without_owner_approval(proof, client_db):
    client, messages = proof
    tenants_before = client_db.scalar(select(func.count()).select_from(Tenant))
    request_id = start(client, name="  Fotógrafa   Local  ", email="SIGNUP@example.test")
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == tenants_before
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0
    row = client_db.scalar(select(PhotographerSignup))
    assert row.adult_attested_at is not None
    assert row.otp_digest != messages[-1][1] and row.state == "email_pending"
    setup = verify(client, messages, request_id)
    assert client.get("/api/probe-admin").status_code == 403
    client_db.expire_all()
    assert client_db.get(PhotographerSignup, row.id).totp_envelope is None
    response = finish(client, setup)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "active"
    assert "totp" not in response.text and PASSWORD not in response.text
    session = client.get("/api/probe-admin")
    assert session.status_code == 200
    tenant = client_db.get(Tenant, UUID(session.json()["tenant_id"]))
    assert tenant.photographer_name == "Fotógrafa Local" and tenant.status == "active"
    assert client_db.get(TenantCreditWallet, tenant.id).mode == "finite"
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry)) == 0
    assert client_db.scalar(select(func.count()).select_from(PlatformOwner)) == 0
    assert client_db.scalar(select(func.count()).select_from(MonitorGrant)) == 0
    client_db.expire_all()
    row = client_db.get(PhotographerSignup, row.id)
    assert row.state == "active" and row.totp_envelope is None and row.setup_digest is None
    assert client_db.scalar(select(AdminUser.__table__.c.totp_secret)) is None
    assert finish(client, setup).status_code == 400
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == tenants_before + 1


def test_resend_rotates_public_identity_and_old_otp_and_existing_account_is_neutral(proof, client_db):
    client, messages = proof
    first = start(client)
    old_code = messages[-1][1]
    second = start(client)
    assert first != second
    assert client.post(ROOT + "/verify-email", json={"request_id": first, "code": old_code}).status_code == 400
    setup = verify(client, messages, second)
    assert finish(client, setup).status_code == 200
    count = len(messages)
    decoy = start(client)
    assert decoy not in {first, second} and len(messages) == count


def test_two_website_accounts_have_independent_identity_and_no_global_role(proof, client_db):
    client, messages = proof
    identities = []
    for suffix in ("a", "b"):
        request_id = start(client, name=f"Fotógrafo {suffix}", email=f"signup-{suffix}@example.test")
        setup = verify(client, messages, request_id)
        assert finish(client, setup).status_code == 200
        identities.append(client.get("/api/probe-admin").json())
        assert client.get("/api/admin/platform/console/tenants?mode=all").status_code == 403
    assert identities[0]["tenant_id"] != identities[1]["tenant_id"]
    assert identities[0]["subject_id"] != identities[1]["subject_id"]
    for identity in identities:
        membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == UUID(identity["subject_id"])))
        assert str(membership.tenant_id) == identity["tenant_id"]
    tenants = [client_db.get(Tenant, UUID(identity["tenant_id"])) for identity in identities]
    assert [tenant.photographer_name for tenant in tenants] == ["Fotógrafo a", "Fotógrafo b"]
    shared_phone = "+5511999999999"
    client_db.add_all([
        Client(tenant_id=tenant.id, full_name=f"Cliente {suffix}", phone_e164=shared_phone)
        for tenant, suffix in zip(tenants, ("a", "b"), strict=True)
    ])
    client_db.commit()
    assert len(list(client_db.scalars(select(Client).where(Client.phone_e164 == shared_phone)))) == 2
    for suffix, tenant in zip(("a", "b"), tenants, strict=True):
        by_name = platform_console.tenant_directory(client_db, query=f"Fotógrafo {suffix}", mode="all")
        by_email = platform_console.tenant_directory(client_db, query=f"signup-{suffix}@example.test", mode="all")
        assert [item["tenant_id"] for item in by_name["items"]] == [str(tenant.id)]
        assert [item["tenant_id"] for item in by_email["items"]] == [str(tenant.id)]
        assert by_name["items"][0]["admin_email"] == f"signup-{suffix}@example.test"
    pending_request = start(client, name="Candidatura descartável", email="pending@example.test")
    pending = client_db.scalar(select(PhotographerSignup).where(PhotographerSignup.public_request_id == UUID(pending_request)))
    pending.otp_expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    assert signup.process_signup_expiry(session_factory=factory)
    client_db.expire_all()
    assert client_db.get(PhotographerSignup, pending.id).state == "expired"
    assert [client_db.get(Tenant, tenant.id).status for tenant in tenants] == ["active", "active"]


def test_invalid_expired_replayed_otp_and_password_never_provision_access(proof, client_db):
    client, messages = proof
    request_id = start(client)
    assert client.post(ROOT + "/verify-email", json={"request_id": request_id, "code": "bad"}).status_code == 400
    setup = verify(client, messages, request_id)
    assert client.post(ROOT + "/verify-email", json={"request_id": request_id, "code": messages[-1][1]}).status_code == 400
    assert client.post(ROOT + "/complete", json={"password": "weak"}).status_code == 400
    row = client_db.scalar(select(PhotographerSignup))
    row.setup_expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    assert finish(client, setup).status_code == 400
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0


def test_atomic_failure_rolls_back_tenant_user_wallet_and_session(proof, client_db, monkeypatch):
    client, messages = proof
    setup = verify(client, messages, start(client))
    before = client_db.scalar(select(func.count()).select_from(Tenant))
    original = signup.create_session

    def fail(*_, **__):
        raise IntegrityError("synthetic failure", {}, Exception("synthetic"))

    monkeypatch.setattr(signup, "create_session", fail)
    assert finish(client, setup).status_code == 400
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == before
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0
    assert client.get("/api/probe-admin").status_code == 403
    monkeypatch.setattr(signup, "create_session", original)
    assert finish(client, setup).status_code == 200


def test_default_gate_production_gate_antibot_and_sensitive_validation(proof, monkeypatch):
    client, _messages = proof
    monkeypatch.delenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED")
    assert client.post(ROOT, json={}).status_code == 404
    assert client.post(ROOT + "/recovery/email-link", json={"email": "unknown@example.test"}).status_code == 404
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    assert client.post(ROOT, json={}).status_code == 404
    assert client.post(ROOT + "/recovery/email-link", json={"email": "unknown@example.test"}).status_code == 404
    monkeypatch.setenv("APP_ENV", "development")
    response = client.post(ROOT, json={"photographer_name": "Fake", "email": "fake@example.test", "adult_attested": True, "anti_bot_proof": "invalid"})
    assert response.status_code == 400
    response = client.post(ROOT + "/complete", json={"password": PASSWORD, "unexpected": PASSWORD})
    assert response.status_code == 422 and PASSWORD not in response.text


def test_expired_otp_attempt_limit_cancellation_and_invalid_password_do_not_create_account(proof, client_db):
    client, messages = proof
    identity = start(client)
    row = client_db.scalar(select(PhotographerSignup))
    row.otp_expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    assert client.post(ROOT + "/verify-email", json={"request_id": identity, "code": messages[-1][1]}).status_code == 400
    client_db.expire_all()
    assert client_db.get(PhotographerSignup, row.id).state == "expired"
    setup = verify(client, messages, start(client))
    assert client.post(ROOT + "/complete", json={"password": "weak"}).status_code == 400
    assert client.post(ROOT + "/cancel").status_code == 200
    assert finish(client, setup).status_code == 400
    assert client.get(ROOT + "/setup").status_code == 400
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0
    client_db.expire_all()
    row = client_db.get(PhotographerSignup, row.id)
    assert row.state == "cancelled" and row.totp_envelope is None and row.setup_digest is None


def test_otp_bruteforce_is_limited_and_never_activates(proof, client_db):
    client, _messages = proof
    identity = start(client)
    for _ in range(5):
        assert client.post(ROOT + "/verify-email", json={"request_id": identity, "code": "invalid"}).status_code == 400
    assert client.post(ROOT + "/verify-email", json={"request_id": identity, "code": "invalid"}).status_code == 429
    assert client_db.scalar(select(PhotographerSignup.attempts)) == 5
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0


def test_mail_failure_and_missing_adapter_are_sanitized_and_rollback(proof, client_db):
    client, _messages = proof

    class FailedServices:
        def verify_bot(self, *_): return True
        def send_code(self, *_): raise signup.SignupServiceError("synthetic-private-provider-detail")

    client.app.dependency_overrides[signup.signup_services] = FailedServices
    response = client.post(ROOT, json={"photographer_name": "Local", "email": "local@example.test", "adult_attested": True, "anti_bot_proof": "synthetic-proof"})
    assert response.status_code == 503 and "provider-detail" not in response.text
    assert client_db.scalar(select(func.count()).select_from(PhotographerSignup)) == 0
    client.app.dependency_overrides.pop(signup.signup_services)
    assert client.post(ROOT, json={"photographer_name": "Local", "email": "local@example.test", "adult_attested": True, "anti_bot_proof": "synthetic-proof"}).status_code == 503


def test_turnstile_and_email_flags_fail_closed_and_public_config_has_no_secret(proof, client_db, monkeypatch):
    client, _messages = proof
    for key in (
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED",
        "PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_SITE_KEY",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    config = client.get(ROOT + "/config")
    assert config.status_code == 200
    assert config.json() == {"turnstile_enabled": False, "turnstile_site_key": None}
    client.app.dependency_overrides.pop(signup.signup_services)
    response = client.post(ROOT, json={
        "photographer_name": "Local", "email": "local@example.test", "adult_attested": True, "anti_bot_proof": "synthetic-token",
    })
    assert response.status_code == 503
    assert client_db.scalar(select(func.count()).select_from(PhotographerSignup)) == 0
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 0


def test_turnstile_verified_signup_queues_encrypted_otp_and_rejects_stale_delivery(
    proof, client_db, monkeypatch
):
    client, _messages = proof
    for key, value in {
        "APP_ENV": "development",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED": "true",
        "PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED": "true",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_SITE_KEY": "synthetic-public-site-key",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY": "synthetic-secret-key",
        "PHOTOGRAPHER_SIGNUP_TURNSTILE_HOSTNAME": "pickyourpic.com.br",
        "EMAIL_PROVIDER": "smtp",
        "EMAIL_CREDENTIAL_ENV": "development",
        "SMTP_HOST": "smtp.example.test",
        "SMTP_USER": "synthetic-user",
        "SMTP_PASSWORD": "synthetic-password",
        "SMTP_FROM_ADDRESS": "no-reply@pickyourpic.com.br",
        "PUBLIC_APP_ORIGIN": "https://pickyourpic.com.br",
    }.items():
        monkeypatch.setenv(key, value)

    class SyntheticVerifier:
        def verify(self, proof):
            return proof == "synthetic-valid-token"

    monkeypatch.setattr(signup, "TurnstileVerifier", lambda _settings: SyntheticVerifier())
    client.app.dependency_overrides.pop(signup.signup_services)

    config = client.get(ROOT + "/config")
    assert config.status_code == 200
    assert config.json() == {
        "turnstile_enabled": True,
        "turnstile_site_key": "synthetic-public-site-key",
    }
    assert "synthetic-secret-key" not in config.text

    rejected = client.post(ROOT, json={
        "photographer_name": "Local", "email": "local@example.test", "adult_attested": True, "anti_bot_proof": "synthetic-invalid-token",
    })
    assert rejected.status_code == 400
    assert client_db.scalar(select(func.count()).select_from(PhotographerSignup)) == 0
    assert client_db.scalar(select(func.count()).select_from(EmailDelivery)) == 0

    accepted = client.post(ROOT, json={
        "photographer_name": "Local", "email": "local@example.test", "adult_attested": True, "anti_bot_proof": "synthetic-valid-token",
    })
    assert accepted.status_code == 202
    signup_row = client_db.scalar(select(PhotographerSignup).where(PhotographerSignup.email == "local@example.test"))
    delivery = client_db.scalar(select(EmailDelivery))
    assert signup_row and delivery
    assert delivery.kind == "email_verification"
    assert delivery.status == "queued"
    assert delivery.recipient_fingerprint == signup.pii_fingerprint(signup_row.email)
    assert "synthetic-valid-token" not in delivery.encrypted_payload
    payload = decrypt_sensitive_payload(
        delivery.encrypted_payload,
        context=f"email-delivery:{delivery.id}:{delivery.idempotency_key}",
    )
    assert signup_row.otp_digest not in payload["text_body"]
    validate_email_origin(client_db, delivery, payload=payload)

    signup_row.public_request_id = UUID("a0ea0ce4-24c7-48a0-8cb3-6328d3bde85b")
    client_db.commit()
    with pytest.raises(EmailConfigurationError):
        validate_email_origin(client_db, delivery, payload=payload)


def test_signup_password_setup_does_not_require_or_return_totp_material(proof, client_db, monkeypatch):
    client, messages = proof
    verify(client, messages, start(client))
    client.app.dependency_overrides.pop(signup.database, None)
    monkeypatch.setattr(signup, "SessionLocal", sessionmaker(bind=client_db.get_bind(), expire_on_commit=False))
    monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "unavailable-synthetic")
    response = client.get(ROOT + "/setup")
    assert response.status_code == 200
    assert set(response.json()) == {"photographer_name", "email"}
    assert "totp" not in response.text.lower() and "envelope" not in response.text


def test_concurrent_email_verification_consumes_otp_once_without_admin_access(proof, client_db):
    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Concorrência de cadastro exige PostgreSQL isolado")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    client, messages = proof
    request_id = start(client)
    code = messages[-1][1]
    before = client_db.scalar(select(func.count()).select_from(Tenant))
    client_db.commit()
    barrier = Barrier(2)

    def verify_once(_):
        with TestClient(client.app) as parallel:
            barrier.wait(timeout=10)
            response = parallel.post(ROOT + "/verify-email", json={"request_id": request_id, "code": code})
            assert parallel.get("/api/probe-admin").status_code == 403
            if response.status_code == 400:
                assert signup.SETUP_COOKIE not in response.cookies
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(verify_once, range(2))) == [200, 400]
    client_db.expire_all()
    row = client_db.scalar(select(PhotographerSignup))
    assert row.state == "credentials_pending" and row.otp_digest is None
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == before
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0


def test_concurrent_completion_creates_exactly_one_tenant(proof, client_db):
    if client_db.bind.dialect.name != "postgresql":
        pytest.skip("Concorrência de cadastro exige PostgreSQL isolado")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    client, messages = proof
    verify(client, messages, start(client))
    cookie = client.cookies.get(signup.SETUP_COOKIE)
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)

    def database():
        with factory() as db: yield db

    client.app.dependency_overrides[signup.database] = database
    before = client_db.scalar(select(func.count()).select_from(Tenant))
    client_db.commit()
    barrier = Barrier(2)

    def activate(_):
        with TestClient(client.app) as parallel:
            barrier.wait(timeout=10)
            return parallel.post(ROOT + "/complete", headers={"Cookie": f"{signup.SETUP_COOKIE}={cookie}"},
                json={"password": PASSWORD}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(activate, range(2))) == [200, 400]
    client_db.expire_all()
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == before + 1
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 1


def test_expiry_scrubs_temporary_factors_preserves_profile_and_is_off_by_default(proof, client_db, monkeypatch):
    client, messages = proof
    verify(client, messages, start(client))
    row = client_db.scalar(select(PhotographerSignup))
    identity, name, email = row.id, row.photographer_name, row.email
    row.setup_expires_at = now() - timedelta(seconds=1)
    client_db.commit()
    assert signup.expire_signup_material(client_db)
    client_db.commit()
    row = client_db.get(PhotographerSignup, identity)
    assert (row.state, row.photographer_name, row.email) == ("expired", name, email)
    assert row.totp_envelope is None and row.otp_digest is None and row.setup_digest is None
    assert not signup.expire_signup_material(client_db)
    assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 0
    from app.auth import AuditEvent
    from app.homolog_cleanup import admin_security_audit_criteria
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        admin_security_audit_criteria(), AuditEvent.event.like("photographer_signup.%"),
    )) == 3
    monkeypatch.delenv("PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED")

    def never_connect():
        pytest.fail("Feature fechada não pode acessar banco ou fatores.")

    assert signup.process_signup_expiry(session_factory=never_connect) is False


def test_retention_erases_only_unverified_signup_and_scrubs_its_email_outbox(proof, client_db):
    client, messages = proof
    from app.auth import AuditEvent

    unverified_request = start(client, name="Nome a expurgar", email="unverified-retention@example.test")
    unverified = client_db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.public_request_id == UUID(unverified_request),
    ))
    unverified_id = unverified.id
    unverified.created_at = now() - timedelta(days=31)
    delivery = EmailDelivery(
        kind="email_verification", source_type="photographer_signup", source_id=str(unverified.id),
        recipient_fingerprint="a" * 64, idempotency_key=f"signup-retention:{unverified.id}",
        encrypted_payload="encrypted-recipient-and-code", status="queued", attempts=0,
        expires_at=now() + timedelta(minutes=10),
    )
    client_db.add(delivery)

    verified_request = start(client, name="Nome a preservar", email="verified-retention@example.test")
    verify(client, messages, verified_request)
    verified = client_db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.public_request_id == UUID(verified_request),
    ))
    verified_id = verified.id
    verified.created_at = now() - timedelta(days=31)
    verified.setup_expires_at = now() - timedelta(seconds=1)
    client_db.commit()

    assert signup.expire_signup_material(client_db)
    client_db.commit()
    assert client_db.get(PhotographerSignup, unverified_id) is None
    assert client_db.get(PhotographerSignup, verified_id).state == "expired"
    assert client_db.get(PhotographerSignup, verified_id).photographer_name == "Nome a preservar"
    client_db.refresh(delivery)
    assert delivery.encrypted_payload is None
    assert delivery.recipient_fingerprint == "0" * 64
    assert delivery.status == "expired"
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == "photographer_signup.pii_expired",
        AuditEvent.subject == "count:1",
    )) == 1


def test_signup_retention_can_run_only_when_explicitly_enabled_in_production(proof, client_db, monkeypatch):
    client, _messages = proof
    request_id = start(client, name="Candidatura vencida", email="retention-enabled@example.test")
    row = client_db.scalar(select(PhotographerSignup).where(
        PhotographerSignup.public_request_id == UUID(request_id),
    ))
    row_id = row.id
    row.created_at = now() - timedelta(days=31)
    client_db.commit()
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_RETENTION_ENABLED", "true")
    assert signup.process_signup_expiry(session_factory=factory) is True
    assert client_db.get(PhotographerSignup, row_id) is None

    def never_connect():
        pytest.fail("Retenção desligada não pode acessar o banco.")

    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_RETENTION_ENABLED", "false")
    assert signup.process_signup_expiry(session_factory=never_connect) is False
