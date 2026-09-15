from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    AuthSession,
    Base,
    NotificationDelivery,
    NotificationEvent,
    PaymentMessageTemplate,
    PushSubscription,
    SessionLocal,
    engine,
    now,
    token_hash,
)
from app.main import app
from app.notification_settings import enqueue_event, render_text, save_setting, setting_for


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
        session = AuthSession(subject_id=uuid4(), role=role, token_hash=token_hash(role),
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
    assert len(settings) == 6
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


def test_payment_legacy_api_delegates_to_the_single_source():
    with SessionLocal() as db:
        db.add(PaymentMessageTemplate(kind="confirmed", body="Texto antigo {{cliente}}"))
        db.commit()
    client = authenticated()
    assert client.get("/admin/payment-message-templates").json()["templates"]["confirmed"] == "Texto antigo {{cliente}}"
    response = client.put("/admin/payment-message-templates/confirmed", json={"body": "Novo {{cliente}}"})
    assert response.status_code == 200
    assert client.get("/admin/payment-message-templates").json()["templates"]["confirmed"] == "Novo {{cliente}}"
    central = client.get("/admin/notification-settings").json()["settings"]
    assert next(item for item in central if item["event_type"] == "payment_confirmed")["whatsapp_body"] == "Novo {{cliente}}"


def test_snapshot_dedupe_channels_and_no_replay():
    with SessionLocal() as db:
        recipient = uuid4()
        db.add(PushSubscription(endpoint_fingerprint="1" * 64, encrypted_subscription="ciphertext",
                                role="admin", subject_id=recipient))
        db.flush()
        args = {"event_type": "first_access", "event_key": "access:synthetic",
                "values": {"cliente": "Ana", "galeria": "Evento"}, "target_path": "/admin",
                "recipients": [recipient, recipient]}
        first = enqueue_event(db, **args)
        assert enqueue_event(db, **args).id == first.id
        db.commit()
        original_text, version = first.push_body, first.template_version
        assert len(list(db.scalars(select(NotificationDelivery)))) == 2
        save_setting(db, "first_access", {"push_enabled": False, "push_body": "Texto alterado"})
        db.commit()
        deliveries = {row.channel: row for row in db.scalars(select(NotificationDelivery))}
        assert deliveries["push"].status == "cancelled"
        assert deliveries["whatsapp"].status == "queued"
        assert first.push_body == original_text
        assert first.template_version == version
        save_setting(db, "first_access", {"push_enabled": True})
        db.commit()
        assert enqueue_event(db, **args).id == first.id
        assert deliveries["push"].status == "cancelled"
        assert len(list(db.scalars(select(NotificationEvent)))) == 1
        future = enqueue_event(db, **{**args, "event_key": "access:future"})
        assert future.push_body == "Texto alterado"
        assert future.template_version > version
        assert setting_for(db, "first_access").whatsapp_enabled


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
        setting_for(db, "first_access")
        db.commit()
    with SessionLocal() as db:
        enqueue_event(db, event_type="first_access", event_key="must-rollback", values={},
                      target_path="/admin", recipients=[uuid4()])
        db.rollback()
    with SessionLocal() as db:
        assert not list(db.scalars(select(NotificationEvent)))
        assert not list(db.scalars(select(NotificationDelivery)))
