from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AdminUser,
    Base,
    Client,
    DerivedGallery,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    ParentGallery,
    PaymentMessageTemplate,
    PushSubscription,
    SessionLocal,
    Tenant,
    engine,
    now,
    token_hash,
)
from app.main import app
from app.notification_settings import (
    enqueue_event,
    render_text,
    render_whatsapp_text,
    save_setting,
    setting_for,
)
from tests.tenant_fixtures import FIXTURE_TENANT_ID, fixture_admin


@pytest.fixture(autouse=True)
def isolated_schema(monkeypatch):
    monkeypatch.setenv("TRANSACTIONAL_WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("BEGIN")
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def authenticated(role="admin"):
    with SessionLocal() as db:
        subject_id = uuid4()
        if role == "admin":
            admin = fixture_admin(AdminUser(email="notifications@example.test",
                                            password_hash="synthetic", totp_secret="synthetic",
                                            email_verified=True))
            db.add(admin)
            db.flush()
            subject_id = admin.id
        else:
            person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Cliente fixture", phone_e164="+5511999999630")
            db.add(person)
            db.flush()
            subject_id = person.id
        session = fixture_session(subject_id=subject_id, role=role, token_hash=token_hash(role),
                              expires_at=now() + timedelta(hours=1))
        db.add(session)
        db.commit()
    client = TestClient(app)
    client.cookies.set("markina_session", role)
    return client


def test_configuration_api_is_admin_only_and_validates_templates():
    assert TestClient(app).get("/admin/notification-settings").status_code == 403
    assert authenticated("client").get("/admin/notification-settings").status_code == 403
    client = authenticated()
    response = client.get("/admin/notification-settings")
    assert response.status_code == 200
    settings = response.json()["settings"]
    assert len(settings) == 7
    private_photos = next(item for item in settings if item["event_type"] == "private_photos_ready")
    assert "link_galeria" not in private_photos["allowed_variables"]
    assert "link_galeria" in private_photos["whatsapp_variables"]
    assert private_photos["whatsapp_body"].endswith("{{link_galeria}}.")
    assert "https://fotografo.exemplo/public-galleries/" in private_photos["preview"]["whatsapp_body"]
    item = settings[0]
    payload = {key: item[key] for key in ("version", "whatsapp_enabled", "push_enabled",
                                         "whatsapp_body", "push_title", "push_body")}
    for field, value in (("push_title", "a" * 61), ("push_body", "{{pedido}}"),
                          ("whatsapp_body", "<b>HTML</b>"),
                          ("push_body", "https://unsafe.invalid"), ("push_body", "{{cliente")):
        result = client.put("/admin/notification-settings/first_access", json={**payload, field: value})
        assert result.status_code == 422
    assert client.put("/admin/notification-settings/first_access", json={**payload, "push_body": "Linha 1\nLinha 2"}).status_code == 422
    assert client.put("/admin/notification-settings/first_access", json=payload,
                      headers={"Origin": "https://attacker.invalid"}).status_code == 403
    response = client.put("/admin/notification-settings/first_access", json={**payload, "push_enabled": False})
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert client.put("/admin/notification-settings/first_access", json=payload).status_code == 422


def test_link_compras_is_validated_and_rendered_only_for_delivery_whatsapp():
    link = "https://a.fotografo.example.com/library/purchases#order-00000000-0000-4000-8000-000000000001"
    body = "Fotos prontas: {{link_compras}}"
    assert render_whatsapp_text("order_delivery_ready", body, {"link_compras": link}, 500) == f"Fotos prontas: {link}"
    assert render_whatsapp_text("order_delivery_ready", body, {"link_compras": "https://evil.example/path"}, 500) == "Fotos prontas: "
    assert render_whatsapp_text("order_delivery_ready", body, {"link_compras": "https://a.example.com:bad/library/purchases#order-00000000-0000-4000-8000-000000000001"}, 500) == "Fotos prontas: "
    with pytest.raises(ValueError):
        render_text("order_delivery_ready", body, {"link_compras": link}, 500)
    with pytest.raises(ValueError):
        render_whatsapp_text("payment_confirmed", body, {"link_compras": link}, 500)


def test_link_galeria_is_validated_and_rendered_only_for_private_photo_whatsapp():
    gallery_id = "00000000-0000-4000-8000-000000000001"
    link = f"https://a.fotografo.example.com/public-galleries/{gallery_id}"
    body = "Acesso: {{link_galeria}}"
    assert render_whatsapp_text("private_photos_ready", body, {"link_galeria": link}, 500,
                                expected_gallery_host="a.fotografo.example.com") == f"Acesso: {link}"
    for invalid in (
        f"http://a.fotografo.example.com/public-galleries/{gallery_id}",
        f"https://evil.example.com/public-galleries/{gallery_id}",
        f"https://a.fotografo.example.com:443/public-galleries/{gallery_id}",
        f"https://user@a.fotografo.example.com/public-galleries/{gallery_id}",
        f"https://a.fotografo.example.com/public-galleries/{gallery_id}?next=evil",
        f"https://a.fotografo.example.com/public-galleries/{gallery_id}#fragment",
        "https://a.fotografo.example.com/library/purchases",
    ):
        assert render_whatsapp_text("private_photos_ready", body, {"link_galeria": invalid}, 500,
                                    expected_gallery_host="a.fotografo.example.com") == "Acesso: "
    with pytest.raises(ValueError):
        render_text("private_photos_ready", body, {"link_galeria": link}, 500)
    with pytest.raises(ValueError):
        render_whatsapp_text("payment_confirmed", body, {"link_galeria": link}, 500)


def test_private_photo_event_uses_parent_gallery_and_cancels_only_whatsapp_without_canonical_host():
    with SessionLocal() as db:
        tenant = db.get(Tenant, FIXTURE_TENANT_ID)
        tenant.status, tenant.canonical_host = "active", "photos.example.com"
        client = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Cliente", phone_e164="+5511999999630")
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Galeria principal")
        db.add_all([client, parent])
        db.flush()
        derived = DerivedGallery(
            tenant_id=tenant.id, parent_gallery_id=parent.id,
            client_id=client.id, name="Pasta privada",
        )
        db.add(derived)
        db.flush()
        supplied = "https://attacker.example/path"
        event = enqueue_event(
            db, event_type="private_photos_ready", event_key="private-ready:valid-host",
            values={"cliente": "Cliente", "galeria": "Galeria principal", "link_galeria": supplied},
            target_path=f"/public-galleries/{parent.id}", recipients=[client.id],
            parent_gallery_id=parent.id, derived_gallery_id=derived.id,
            client_id=client.id, tenant_id=tenant.id,
        )
        assert event.whatsapp_body.endswith(f"https://photos.example.com/public-galleries/{parent.id}.")
        assert supplied not in event.whatsapp_body
        restricted_event = enqueue_event(
            db, event_type="private_photos_ready", event_key="private-ready:restricted-folder",
            values={"cliente": "Cliente", "galeria": "Galeria principal"},
            target_path=f"/public-galleries/{parent.id}", recipients=[client.id],
            parent_gallery_id=parent.id, client_id=client.id, tenant_id=tenant.id,
        )
        assert restricted_event.whatsapp_body.endswith(
            f"https://photos.example.com/public-galleries/{parent.id}."
        )
        db.commit()

    with SessionLocal() as db:
        db.add(Tenant(id=uuid4(), status="active"))
        tenant = db.get(Tenant, FIXTURE_TENANT_ID)
        tenant.canonical_host = None
        client = db.scalar(select(Client).where(Client.tenant_id == tenant.id))
        parent = db.scalar(select(ParentGallery).where(ParentGallery.tenant_id == tenant.id))
        subscription = PushSubscription(
            tenant_id=tenant.id, endpoint_fingerprint="2" * 64, encrypted_subscription="ciphertext",
            role="client", subject_id=client.id, client_subject_id=client.id,
        )
        db.add(subscription)
        event = enqueue_event(
            db, event_type="private_photos_ready", event_key="private-ready:no-host",
            values={"cliente": "Cliente", "galeria": "Galeria principal"},
            target_path=f"/public-galleries/{parent.id}", recipients=[client.id],
            parent_gallery_id=parent.id, client_id=client.id, tenant_id=tenant.id,
        )
        db.flush()
        deliveries = {item.channel: item for item in db.scalars(
            select(NotificationDelivery).where(NotificationDelivery.event_id == event.id)
        )}
        assert deliveries["whatsapp"].status == "cancelled"
        assert deliveries["whatsapp"].last_error == "canonical_host_unavailable"
        assert deliveries["push"].status == "queued"
        assert "https://" not in event.whatsapp_body


def test_private_photo_event_without_source_cancels_only_whatsapp():
    with SessionLocal() as db:
        tenant = db.get(Tenant, FIXTURE_TENANT_ID)
        tenant.status, tenant.canonical_host = "active", "photos.example.com"
        client = Client(tenant_id=tenant.id, full_name="Cliente", phone_e164="+5511999999630")
        db.add(client)
        db.flush()
        db.add(PushSubscription(
            tenant_id=tenant.id, endpoint_fingerprint="3" * 64, encrypted_subscription="ciphertext",
            role="client", subject_id=client.id, client_subject_id=client.id,
        ))
        event = enqueue_event(
            db, event_type="private_photos_ready", event_key="private-ready:no-source",
            values={"cliente": "Cliente", "galeria": "Galeria principal"},
            target_path="/public-galleries/unavailable", recipients=[client.id],
            client_id=client.id, tenant_id=tenant.id,
        )
        deliveries = {item.channel: item for item in db.scalars(
            select(NotificationDelivery).where(NotificationDelivery.event_id == event.id)
        )}
        assert deliveries["whatsapp"].status == "cancelled"
        assert deliveries["push"].status == "queued"
        assert "https://" not in event.whatsapp_body


def test_payment_legacy_api_delegates_to_the_single_source():
    assert TestClient(app).get("/admin/payment-message-templates/migration-preview").status_code == 403
    with SessionLocal() as db:
        db.add(PaymentMessageTemplate(tenant_id=FIXTURE_TENANT_ID, kind="confirmed", body="Texto antigo {{cliente}}"))
        db.add(NotificationSetting(
            tenant_id=FIXTURE_TENANT_ID,
            event_type="payment_reported",
            whatsapp_body="{{cliente}} informou pagamento do pedido {{pedido}}.",
            push_title="Pagamento informado",
            push_body="{{cliente}} informou pagamento do pedido {{pedido}}.",
        ))
        db.commit()
    client = authenticated()
    assert client.get("/admin/payment-message-templates").json()["templates"]["confirmed"] == "Texto antigo {{cliente}}"
    preview_response = client.get("/admin/payment-message-templates/migration-preview")
    assert preview_response.status_code == 200
    assert preview_response.json()["templates"]["payment_confirmed.whatsapp_body"]["before"] == "Texto antigo {{cliente}}"
    assert preview_response.json()["templates"]["payment_confirmed.whatsapp_body"]["changed"] is False
    reported_preview = preview_response.json()["templates"]["payment_reported.whatsapp_body"]
    assert reported_preview["after"] == "{{cliente}} informou pagamento {{contexto_pagamento}}."
    with SessionLocal() as db:
        assert db.get(NotificationSetting, (FIXTURE_TENANT_ID, "payment_reported")).whatsapp_body == (
            "{{cliente}} informou pagamento do pedido {{pedido}}."
        )
    response = client.put("/admin/payment-message-templates/confirmed", json={"body": "Novo {{cliente}}"})
    assert response.status_code == 200
    assert client.get("/admin/payment-message-templates").json()["templates"]["confirmed"] == "Novo {{cliente}}"
    central = client.get("/admin/notification-settings").json()["settings"]
    assert next(item for item in central if item["event_type"] == "payment_confirmed")["whatsapp_body"] == "Novo {{cliente}}"


def test_snapshot_dedupe_channels_and_no_replay():
    with SessionLocal() as db:
        admin = fixture_admin(AdminUser(email="recipient@example.test", password_hash="synthetic", totp_secret="synthetic", email_verified=True))
        db.add(admin)
        db.flush()
        recipient = admin.id
        db.add(PushSubscription(tenant_id=FIXTURE_TENANT_ID, endpoint_fingerprint="1" * 64, encrypted_subscription="ciphertext",
                                role="admin", subject_id=recipient, admin_subject_id=recipient))
        db.flush()
        args = {"event_type": "first_access", "event_key": "access:synthetic",
                "values": {"cliente": "Ana", "galeria": "Evento"}, "target_path": "/admin",
                "recipients": [recipient, recipient]}
        first = enqueue_event(db, **args, tenant_id=FIXTURE_TENANT_ID)
        assert enqueue_event(db, **args, tenant_id=FIXTURE_TENANT_ID).id == first.id
        db.commit()
        original_text, version = first.push_body, first.template_version
        assert len(list(db.scalars(select(NotificationDelivery)))) == 2
        save_setting(db, "first_access", {"push_enabled": False, "push_body": "Texto alterado"}, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        deliveries = {row.channel: row for row in db.scalars(select(NotificationDelivery))}
        assert deliveries["push"].status == "cancelled"
        assert deliveries["whatsapp"].status == "queued"
        assert first.push_body == original_text
        assert first.template_version == version
        save_setting(db, "first_access", {"push_enabled": True}, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        assert enqueue_event(db, **args, tenant_id=FIXTURE_TENANT_ID).id == first.id
        assert deliveries["push"].status == "cancelled"
        assert len(list(db.scalars(select(NotificationEvent)))) == 1
        future = enqueue_event(db, **{**args, "event_key": "access:future"}, tenant_id=FIXTURE_TENANT_ID)
        assert future.push_body == "Texto alterado"
        assert future.template_version > version
        assert setting_for(db, "first_access", tenant_id=FIXTURE_TENANT_ID).whatsapp_enabled


@pytest.mark.parametrize("limit", [60, 140, 500])
def test_interpolation_shortens_names_without_overflow(limit):
    result = render_text("first_access", "{{cliente}} acessou {{galeria}}.",
                         {"cliente": "C" * 200, "galeria": "G" * 200}, limit)
    assert len(result) <= limit
    assert " acessou " in result
    assert "…" in result or limit == 500


def test_plain_text_values_do_not_inject_markup():
    result = render_text("first_access", "{{cliente}} acessou {{galeria}}.",
                         {"cliente": "<script>\nTeste", "galeria": "https://unsafe.invalid"}, 140)
    assert "<" not in result and "\n" not in result and "http" not in result


def test_event_rolls_back_with_business_transaction():
    with SessionLocal() as db:
        setting_for(db, "first_access", tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    with SessionLocal() as db:
        admin = fixture_admin(AdminUser(email="rollback@example.test", password_hash="synthetic", totp_secret="synthetic", email_verified=True))
        db.add(admin)
        db.flush()
        enqueue_event(db, event_type="first_access", event_key="must-rollback", values={},
                      target_path="/admin", recipients=[admin.id], tenant_id=FIXTURE_TENANT_ID)
        db.rollback()
    with SessionLocal() as db:
        assert not list(db.scalars(select(NotificationEvent)))
        assert not list(db.scalars(select(NotificationDelivery)))

from tests.tenant_fixtures import fixture_session
