"""Regressões do PIX global e da confirmação administrativa sensível."""

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminSecurityChallenge,
    AdminUser,
    AuditEvent,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    GlobalPixSettings,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    PriceRule,
    Role,
    SaleOrder,
    SessionLocal,
    WhatsAppChannelSettings,
    create_session,
    engine,
    now,
    password_hasher,
    token_hash,
)
from app.checkout import CheckoutError, create_pending_checkout
from app.global_pix import apply_configuration, canonical_proposal, normalize_configuration
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin = AdminUser(
                email="pix@markina.test",
                email_verified=True,
                password_hash=password_hasher.hash("Senha-atual-2026"),
                totp_secret="JBSWY3DPEHPK3PXP",
            )
            db.add(admin)
            db.flush()
            cookie = create_session(db, Response(), Role.ADMIN, admin.id)
            db.add(
                WhatsAppChannelSettings(
                    environment="development",
                    status="sandbox",
                    expected_phone_e164="+5511999999999",
                )
            )
            db.commit()
        client.cookies.set("markina_session", cookie)
        yield client


def test_pix_is_global_and_requires_password_and_otp(client):
    response = client.get("/admin/settings/pix")
    assert response.status_code == 200
    assert response.json()["status"] == "unconfigured"
    config = {
        "copy_paste": "financeiro@example.test",
        "receiver_name": "MARKINA",
        "receiver_city": "SAO PAULO",
        "instructions": "Confirmação manual.",
    }
    challenge = client.post(
        "/admin/settings/pix/challenge",
        json={
            "current_password": "Senha-atual-2026",
            "configuration": config,
        },
    )
    assert challenge.status_code == 202, challenge.text
    assert challenge.json()["proposal"]["receiver_name"] == "MARKINA"
    assert "copy_paste" not in challenge.json()["proposal"]
    assert client.get("/admin/settings/pix").json()["status"] == "unconfigured"
    challenge_id = challenge.json()["challenge_id"]
    with SessionLocal() as db:
        stored = db.get(AdminSecurityChallenge, UUID(challenge_id))
        assert config["copy_paste"] not in stored.encrypted_target
        assert config["copy_paste"] not in repr(stored)
        stored.secret_hash = token_hash("123456")
        db.commit()
    confirmed = client.post(
        "/admin/settings/pix/confirm",
        json={
            "challenge_id": challenge_id,
            "code": "123456",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "active"
    assert confirmed.json()["version"] == 1
    assert confirmed.json()["qr_png_data_url"].startswith("data:image/png;base64,")
    assert (
        client.post(
            "/admin/settings/pix/confirm",
            json={
                "challenge_id": challenge_id,
                "code": "123456",
            },
        ).status_code
        != 200
    )


def test_global_pix_denies_anonymous_and_client_access(client):
    client.cookies.clear()
    assert client.get("/admin/settings/pix").status_code == 403
    with SessionLocal() as db:
        subject = db.scalar(select(AdminUser.id))
        cookie = create_session(db, Response(), Role.CLIENT, subject)
        db.commit()
    client.cookies.set("markina_session", cookie)
    assert client.get("/admin/settings/pix").status_code == 403


def start_change(client, configuration=None):
    response = client.post(
        "/admin/settings/pix/challenge",
        json={
            "current_password": "Senha-atual-2026",
            "configuration": configuration,
        },
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        challenge = db.get(AdminSecurityChallenge, UUID(response.json()["challenge_id"]))
        challenge.secret_hash = token_hash("123456")
        db.commit()
    return {"challenge_id": response.json()["challenge_id"], "code": "123456"}


@pytest.mark.parametrize("mode", ["wrong_code", "expired", "other_session", "payload_changed"])
def test_confirmation_rejects_invalid_context(client, mode):
    payload = start_change(client)
    if mode == "wrong_code":
        payload["code"] = "654321"
        for _ in range(5):
            assert client.post("/admin/settings/pix/confirm", json=payload).status_code == 401
        payload["code"] = "123456"
    elif mode == "expired":
        with SessionLocal() as db:
            challenge = db.get(AdminSecurityChallenge, UUID(payload["challenge_id"]))
            challenge.expires_at = now() - timedelta(seconds=1)
            db.commit()
    elif mode == "other_session":
        with SessionLocal() as db:
            admin_id = db.scalar(select(AdminUser.id))
            cookie = create_session(db, Response(), Role.ADMIN, admin_id)
        client.cookies.set("markina_session", cookie)
    else:
        payload["configuration"] = {"copy_paste": "different@example.test"}
    assert client.post("/admin/settings/pix/confirm", json=payload).status_code in {401, 422}
    assert client.get("/admin/settings/pix").json()["status"] == "unconfigured"


def test_wrong_password_unavailable_channel_rate_limit_and_sensitive_audit(client, monkeypatch):
    request = {"current_password": "wrong", "configuration": None}
    assert client.post("/admin/settings/pix/challenge", json=request).status_code == 401
    request["current_password"] = "Senha-atual-2026"
    monkeypatch.setattr("app.admin_account._admin_whatsapp_phone", lambda db: None)
    assert client.post("/admin/settings/pix/challenge", json=request).status_code == 409
    for _ in range(3):
        assert client.post("/admin/settings/pix/challenge", json=request).status_code == 409
    assert client.post("/admin/settings/pix/challenge", json=request).status_code == 429
    with SessionLocal() as db:
        assert all(c.encrypted_target is None for c in db.scalars(select(AdminSecurityChallenge)))
        events = " ".join(e.subject for e in db.scalars(select(AuditEvent)))
        assert request["current_password"] not in events
        assert "+5511999999999" not in events


def test_pix_challenge_fails_closed_when_sensitive_payload_key_is_missing(
    client, monkeypatch
):
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "homolog-test-fingerprint-salt-32-bytes")
    monkeypatch.delenv("EMAIL_PAYLOAD_ENCRYPTION_KEY", raising=False)

    response = client.post(
        "/admin/settings/pix/challenge",
        json={
            "current_password": "Senha-atual-2026",
            "configuration": {
                "copy_paste": "financeiro@example.test",
                "receiver_name": "MARKINA",
                "receiver_city": "SAO PAULO",
            },
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Confirmação segura temporariamente indisponível."
    }
    with SessionLocal() as db:
        assert not list(db.scalars(select(AdminSecurityChallenge)))


def test_settings_are_read_only_in_sales_and_saving_without_pix_is_allowed(client):
    source = client.post("/admin/parent-galleries", json={"name": "Galeria PIX"}).json()["id"]
    url = f"/admin/parent-galleries/{source}/sales"
    request = {"pricing_mode": "fixed", "fixed_unit_price_cents": 700}
    saved = client.put(url, json=request)
    assert saved.status_code == 200, saved.text
    assert saved.json()["pix"]["scope"] == "global"
    assert not saved.json()["pix"]["checkout_available"]
    rejected = client.put(url, json={**request, "pix": {}})
    assert rejected.status_code == 422
    assert "O PIX agora é global" in rejected.text
    config = {
        "copy_paste": "photo@example.test",
        "receiver_name": "MARKINA",
        "receiver_city": "SAO PAULO",
    }
    assert (
        client.post("/admin/settings/pix/confirm", json=start_change(client, config)).status_code
        == 200
    )
    summary = client.get(url).json()["pix"]
    assert summary["checkout_available"]
    assert summary["receiver_name"] == "MARKINA"
    assert "copy_paste" not in summary
    with SessionLocal() as db:
        events = " ".join(e.subject for e in db.scalars(select(AuditEvent)))
        assert config["copy_paste"] not in events


def test_checkout_uses_global_versions_and_keeps_old_snapshots_and_selection(client):
    import json

    with SessionLocal() as db:
        admin_id = db.scalar(select(AdminUser.id))
        owner = Client(full_name="Cliente sintética", phone_e164="+5511999990001")
        parent = ParentGallery(
            name="Evento",
            pricing_mode="fixed",
            fixed_unit_price_cents=700,
            pricing_snapshot={"mode": "fixed", "unit_price_cents": 700},
        )
        db.add_all([owner, parent])
        db.flush()
        db.add(PriceRule(parent_gallery_id=parent.id, minimum_quantity=1,
                         maximum_quantity=None, unit_price_cents=700))
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Pasta", status="released")
        gallery = DerivedGallery(parent_gallery_id=parent.id, client_id=owner.id, name="Privada")
        db.add_all([folder, gallery])
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="foto.jpg",
            storage_key="synthetic.jpg",
        )
        db.add(photo)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo.id))
        selection = PhotoSelection(
            derived_gallery_id=gallery.id, client_id=owner.id, photo_asset_id=photo.id
        )
        db.add(selection)
        db.commit()
        for status in ("unconfigured", "review_required"):
            if status == "review_required":
                db.add(GlobalPixSettings(admin_user_id=admin_id, status=status))
                db.commit()
            with pytest.raises(CheckoutError, match="seleção foi mantida"):
                create_pending_checkout(
                    db, gallery=gallery, client=owner, checkout_key="blocked-checkout"
                )
            assert db.get(PhotoSelection, selection.id)
            assert not list(db.scalars(select(SaleOrder)))
        config = {
            "copy_paste": "first@example.test",
            "receiver_name": "PRIMEIRO",
            "receiver_city": "SAO PAULO",
            "instructions": "Primeira instrução",
        }
        first_settings = apply_configuration(
            db, admin_id=admin_id, proposed=json.loads(canonical_proposal(config, 0))
        )
        first_code = first_settings.copy_paste
        first = create_pending_checkout(
            db, gallery=gallery, client=owner, checkout_key="first-checkout"
        )
        db.commit()
        config["copy_paste"] = "second@example.test"
        config["receiver_name"] = "SEGUNDO"
        config["instructions"] = "Segunda instrução"
        apply_configuration(
            db, admin_id=admin_id, proposed=json.loads(canonical_proposal(config, 1))
        )
        db.add(
            PhotoSelection(
                derived_gallery_id=gallery.id, client_id=owner.id, photo_asset_id=photo.id
            )
        )
        db.flush()
        second = create_pending_checkout(
            db, gallery=gallery, client=owner, checkout_key="second-checkout"
        )
        db.commit()
        db.refresh(first)
        assert first.pix_copy_paste_snapshot == first_code
        assert first.pix_instructions_snapshot == "Primeira instrução"
        assert first.pix_configuration_snapshot["receiver_name"] == "PRIMEIRO"
        assert first.pix_configuration_snapshot["version"] == 1
        assert second.pix_copy_paste_snapshot != first_code
        assert second.pix_configuration_snapshot["version"] == 2
        apply_configuration(db, admin_id=admin_id, proposed=json.loads(canonical_proposal(None, 2)))
        db.commit()
        assert (
            create_pending_checkout(
                db, gallery=gallery, client=owner, checkout_key="first-checkout"
            ).id
            == first.id
        )


@pytest.mark.parametrize("value", ["529.982.247-25", "+55 (11) 99999-1234", "PHOTO@EXAMPLE.TEST"])
def test_global_key_normalization(value):
    configured = normalize_configuration(
        {"copy_paste": value, "receiver_name": "Markina", "receiver_city": "São Paulo"}
    )
    assert configured["copy_paste"].startswith("000201")
    assert configured["receiver_name"] == "MARKINA"


def test_removal_requires_confirmation_and_increments_version(client):
    config = {"copy_paste": "foto@example.test", "receiver_name": "MARKINA",
              "receiver_city": "SAO PAULO"}
    assert client.post("/admin/settings/pix/confirm", json=start_change(client, config)).status_code == 200
    removal = start_change(client)
    assert client.get("/admin/settings/pix").json()["status"] == "active"
    response = client.post("/admin/settings/pix/confirm", json=removal)
    assert response.status_code == 200
    assert response.json()["status"] == "unconfigured"
    assert response.json()["version"] == 2
    assert response.json()["copy_paste"] is None


def test_stale_proposal_rolls_back_confirmation(client):
    import json

    pending = start_change(client)
    config = {"copy_paste": "foto@example.test", "receiver_name": "MARKINA",
              "receiver_city": "SAO PAULO"}
    with SessionLocal() as db:
        admin_id = db.scalar(select(AdminUser.id))
        apply_configuration(db, admin_id=admin_id, proposed=json.loads(canonical_proposal(config, 0)))
        db.commit()
    response = client.post("/admin/settings/pix/confirm", json=pending)
    assert response.status_code == 409
    assert client.get("/admin/settings/pix").json()["status"] == "active"
    with SessionLocal() as db:
        challenge = db.get(AdminSecurityChallenge, UUID(pending["challenge_id"]))
        assert challenge.used_at is None
        assert challenge.encrypted_target is not None


def test_invalid_configuration_does_not_create_challenge(client):
    response = client.post("/admin/settings/pix/challenge", json={
        "current_password": "Senha-atual-2026",
        "configuration": {"copy_paste": "invalid"},
    })
    assert response.status_code == 422
    with SessionLocal() as db:
        assert not list(db.scalars(select(AdminSecurityChallenge)))


def test_br_code_confirmation_shows_actual_receiver_not_previous_form_value(client):
    from app.pix import build_static_pix_code

    response = client.post("/admin/settings/pix/challenge", json={
        "current_password": "Senha-atual-2026",
        "configuration": {
            "copy_paste": build_static_pix_code("novo@example.test", receiver_name="NOVO", receiver_city="RECIFE"),
            "receiver_name": "ANTERIOR", "receiver_city": "SAO PAULO",
        },
    })
    assert response.status_code == 202
    assert response.json()["proposal"]["receiver_name"] == "NOVO"
    assert response.json()["proposal"]["receiver_city"] == "RECIFE"
