"""Configuração versionada, cofre e fronteira administrativa de Orders."""
# ruff: noqa: F811

import base64
import json
from uuid import uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    MercadoPagoAccount,
    PaymentPreferences,
    Role,
    SessionLocal,
    Tenant,
    TenantAdmin,
    create_session,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope
from app.main import app
from app.mercadopago_api import SettingsInput
from app.mercadopago_settings import (
    account_for,
    apply_proposal,
    credential_provider,
    prepare_proposal,
    settings_payload,
)
from app.payment_availability import payment_methods
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_global_pix import clean_database, client  # noqa: F401

TOKEN = "APP_USR-synthetic-access-token"
SIGNATURE = "synthetic-webhook-signature-for-tests"


@pytest.fixture(autouse=True)
def config_environment(monkeypatch, clean_database):
    monkeypatch.setenv("INTEGRATION_SECRET_ENV", "development")
    monkeypatch.setenv("INTEGRATION_SECRET_ACTIVE_KEY_ID", "test")
    monkeypatch.setenv("INTEGRATION_SECRET_KEYS", json.dumps(
        {"test": base64.b64encode(b"x" * 32).decode()}))
    monkeypatch.setattr("app.mercadopago_settings.OrdersProvider.identity", lambda _: {
        "id": 123456, "site_id": "MLB", "tags": ["test_user"]})


def payload(**changes):
    return {
        "current_password": "Senha-atual-2026", "expected_version": 0,
        "pix_enabled": True, "mercadopago_enabled": True,
        "access_token": TOKEN, "public_key": "APP_USR-synthetic-public",
        "webhook_secret": SIGNATURE, **changes,
    }


def test_cifra_contextual_e_configuracao_nao_vaza_segredos(client):
    with SessionLocal() as db:
        target = prepare_proposal(db, FIXTURE_TENANT_ID, SettingsInput(**payload()))
        assert TOKEN not in target and SIGNATURE not in target
        result = apply_proposal(db, FIXTURE_TENANT_ID, target)
        db.commit()
        assert result["mercadopago_available"] and result["version"] == 1
        assert result["account"]["webhook_path"].startswith("/api/mercadopago/webhooks/")
        account = db.scalar(select(MercadoPagoAccount))
        assert TOKEN not in json.dumps(account.access_token_envelope)
        assert credential_provider(account).sdk is not None
        with pytest.raises(IntegrationSecretError):
            IntegrationCipher().decrypt(
                SecretEnvelope.from_payload(account.access_token_envelope),
                tenant_id=uuid4(), credential_id=account.id)
        assert account_for(db, account.id, uuid4()) is None
        assert settings_payload(db, FIXTURE_TENANT_ID) == result
        with pytest.raises(CheckoutError, match="mudou"):
            apply_proposal(db, FIXTURE_TENANT_ID, target)
    response = client.get("/admin/settings/payment-providers")
    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    assert TOKEN not in response.text and SIGNATURE not in response.text


def test_senha_otp_finalidade_sessao_e_versao(client, monkeypatch):
    monkeypatch.setattr("app.mercadopago_api.create_security_challenge", _challenge)
    response = client.post("/admin/settings/payment-providers/challenge", json=payload())
    assert response.status_code == 202, response.text
    assert TOKEN not in response.text
    challenge_id = response.json()["challenge_id"]
    assert client.post("/admin/settings/payment-providers/confirm", json={
        "challenge_id": challenge_id, "code": "000000"}).status_code == 401
    response = client.post("/admin/settings/payment-providers/confirm", json={
        "challenge_id": challenge_id, "code": "123456"})
    assert response.status_code == 200, response.text
    assert response.json()["mercadopago_available"]
    assert client.post("/admin/settings/payment-providers/confirm", json={
        "challenge_id": challenge_id, "code": "123456"}).status_code == 401
    assert client.post("/admin/settings/payment-providers/challenge", json=payload(
        current_password="wrong")).status_code == 401


def _challenge(db, **kwargs):
    from datetime import timedelta

    from app.admin_security import encrypt_sensitive_payload
    from app.auth import now, pii_fingerprint, token_hash
    item = AdminSecurityChallenge(
        id=uuid4(), tenant_id=kwargs["tenant_id"], admin_id=kwargs["admin"].id,
        session_id=kwargs["session_id"], purpose=kwargs["purpose"],
        subject_fingerprint=kwargs["subject_fingerprint"],
        target_fingerprint=pii_fingerprint(kwargs["target"].strip().casefold()),
        secret_hash=token_hash("123456"), expires_at=now() + timedelta(minutes=10))
    item.encrypted_target = encrypt_sensitive_payload(
        {"target": kwargs["target"]}, context=f"admin-challenge:{item.id}:{item.purpose}")
    db.add(item)
    db.commit()
    return item, "123456", True


def test_flags_independentes_sem_remover_pix_ou_conta(client):
    with SessionLocal() as db:
        target = prepare_proposal(db, FIXTURE_TENANT_ID, SettingsInput(**payload()))
        apply_proposal(db, FIXTURE_TENANT_ID, target)
        db.commit()
        pref = db.scalar(select(PaymentPreferences))
        old_account = pref.account_id
        pref.pix_enabled = False
        db.commit()
        assert payment_methods(db, tenant_id=FIXTURE_TENANT_ID)["card_available"]
        assert not payment_methods(db, tenant_id=FIXTURE_TENANT_ID)["pix_available"]
        pref.mercadopago_enabled = False
        db.commit()
        assert not payment_methods(db, tenant_id=FIXTURE_TENANT_ID)["available"]
        assert pref.account_id == old_account


def test_credencial_real_nao_habilita_cobranca_e_entrada_invalida_nao_vaza(client, monkeypatch):
    monkeypatch.setattr("app.mercadopago_settings.OrdersProvider.identity", lambda _: {
        "id": 123456, "site_id": "MLB", "tags": []})
    response = client.post("/admin/settings/payment-providers/challenge", json=payload())
    assert response.status_code == 409
    response = client.post("/admin/settings/payment-providers/challenge", json=payload(
        expected_version="invalid", tenant_id=str(uuid4())))
    assert response.status_code == 422
    assert TOKEN not in response.text and SIGNATURE not in response.text
    assert client.post("/admin/settings/payment-providers/challenge", content="x" * 32769,
                       headers={"content-type": "application/json"}).status_code == 413
    assert client.post("/admin/settings/payment-providers/challenge", json=payload(),
                       headers={"origin": "https://foreign.test"}).status_code == 403


def test_cada_fotografo_configura_propria_conta_e_nao_confirma_desafio_alheio(client, monkeypatch):
    monkeypatch.setattr("app.mercadopago_api.create_security_challenge", _challenge)
    with SessionLocal() as db:
        apply_proposal(db, FIXTURE_TENANT_ID, prepare_proposal(
            db, FIXTURE_TENANT_ID, SettingsInput(**payload())))
        second = Tenant()
        db.add(second)
        db.flush()
        first_admin = db.scalar(select(AdminUser))
        admin = AdminUser(email="second@photographer.test", email_verified=True,
                          password_hash=first_admin.password_hash, totp_secret="JBSWY3DPEHPK3PXP")
        admin.tenant_memberships.append(TenantAdmin(tenant_id=second.id))
        db.add(admin)
        db.flush()
        cookie = create_session(db, Response(), Role.ADMIN, admin.id, tenant_id=second.id)
        monkeypatch.setattr("app.mercadopago_settings.OrdersProvider.identity", lambda _: {
            "id": 987654, "site_id": "MLB", "tags": ["test_user"]})
        apply_proposal(db, second.id, prepare_proposal(db, second.id, SettingsInput(**payload(
            access_token="APP_USR-second-synthetic-token", public_key="APP_USR-second-public-key",
            webhook_secret="second-synthetic-webhook-secret", pix_enabled=False))))
        db.commit()
    first = client.get("/admin/settings/payment-providers").json()
    with TestClient(app) as other:
        other.cookies.set("markina_session", cookie)
        second = other.get("/admin/settings/payment-providers").json()
        assert first["account"]["seller_id"] == "123456"
        assert second["account"]["seller_id"] == "987654"
        assert first["account"]["webhook_path"] != second["account"]["webhook_path"]
        assert first["pix_enabled"] is True and second["pix_enabled"] is False
        challenge = other.post("/admin/settings/payment-providers/challenge", json=payload(
            expected_version=1, access_token=None, public_key=None, webhook_secret=None,
            pix_enabled=True)).json()
        confirm = {"challenge_id": challenge["challenge_id"], "code": "123456"}
        assert client.post("/admin/settings/payment-providers/confirm", json=confirm).status_code == 401
        assert other.post("/admin/settings/payment-providers/confirm", json=confirm).status_code == 200
        assert client.get("/admin/settings/payment-providers").json() == first
        assert other.get("/admin/settings/payment-providers").json()["version"] == 2
