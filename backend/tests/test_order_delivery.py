import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.auth import (
    AuditEvent,
    AuthChallenge,
    AuthSession,
    Client,
    ClientPhone,
    DerivedGallery,
    NotificationDelivery,
    NotificationEvent,
    ParentGallery,
    PaymentCommunication,
    PaymentGroup,
    SaleOrder,
    SessionLocal,
    Tenant,
    now,
    token_hash,
)
from app.main import app
from app.messaging import SandboxWhatsAppProvider, WhatsAppDeliveryError
from app.notification_delivery import process_next_notification
from app.notification_settings import save_setting
from app.order_delivery import lock_delivery_order, set_delivery
from app.push_subscriptions import subscribe
from app.web_push import PushFailure
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_notification_settings import isolated_schema  # noqa: F401
from tests.test_private_upload_batches import setup_private
from tests.test_push_subscriptions import subscription

ALBUM = "https://photos.app.goo.gl/SyntheticAlbum"
SECOND = "https://photos.google.com/share/Synthetic?key=AccessToken"
PURCHASE_HOST = "a.fotografo.exemplo.com"


def setup_order(status="confirmed", grouped=False):
    admin, gallery_id, _ = setup_private()
    with SessionLocal() as db:
        db.get(Tenant, FIXTURE_TENANT_ID).canonical_host = PURCHASE_HOST
        gallery = db.get(DerivedGallery, gallery_id)
        client = db.get(Client, gallery.client_id)
        db.add(ClientPhone(tenant_id=FIXTURE_TENANT_ID, client_id=client.id, phone_e164=client.phone_e164, active=True, verified_at=now()))
        orders = []
        for _ in range(2 if grouped else 1):
            order = SaleOrder(tenant_id=FIXTURE_TENANT_ID, client_id=client.id, derived_gallery_id=gallery.id,
                              derived_gallery_id_snapshot=gallery.id, derived_gallery_name_snapshot="Privada",
                              parent_gallery_id_snapshot=gallery.parent_gallery_id, parent_gallery_name_snapshot="Evento",
                              payment_status=status, total_cents=1200, confirmed_at=now() if status == "confirmed" else None)
            db.add(order)
            db.flush()
            orders.append(order.id)
        communication = PaymentCommunication(tenant_id=FIXTURE_TENANT_ID, client_id=client.id, idempotency_key="synthetic-payment-1",
                                               sale_order_id=orders[0], status="confirmed" if status == "confirmed" else "pending_review")
        db.add(communication)
        db.add(AuthSession(subject_id=client.id, role="client", token_hash=token_hash("delivery-client"), expires_at=now() + timedelta(hours=1), tenant_id=FIXTURE_TENANT_ID, client_subject_id=client.id))
        db.commit()
        communication_id = communication.id
    browser = TestClient(app, base_url=f"https://{PURCHASE_HOST}")
    browser.cookies.set("markina_session", "delivery-client")
    return admin, browser, orders, communication_id


def send(admin, order, url=ALBUM, version=0):
    return admin.put(f"/admin/orders/{order}/delivery", json={"album_url": url, "version": version})


def events():
    with SessionLocal() as db:
        return list(db.scalars(select(NotificationEvent).where(NotificationEvent.event_type == "order_delivery_ready")))


def test_delivery_persistence_scope_validation_and_audit():
    admin, client, orders, _ = setup_order(grouped=True)
    order = orders[0]
    assert send(client, order).status_code == 403
    assert send(TestClient(app), order).status_code == 403
    assert send(admin, uuid4()).status_code == 404
    assert admin.put(f"/admin/orders/{order}/delivery", json={"album_url": ALBUM, "version": 0}, headers={"Origin": "https://attacker.invalid"}).status_code == 403
    response = send(admin, order)
    assert response.status_code == 200, response.text
    assert response.json()["delivery"]["version"] == 1
    assert len(events()) == 1
    assert send(admin, order).json()["unchanged"]
    assert send(admin, order, "javascript:alert(1)", 1).status_code == 422
    assert send(admin, order, SECOND, 0).status_code == 409
    history = client.get("/library/purchases").json()["orders"]
    assert {row["id"]: row["delivery_album_url"] for row in history} == {str(order): ALBUM, str(orders[1]): None}
    dashboard = admin.get("/admin/payment-communications").json()
    projected = {row["id"]: row["delivery"] for group in dashboard["groups"] for row in group["orders"]}
    assert projected[str(order)]["album_url"] == ALBUM
    assert projected[str(order)]["can_resend"] is True
    assert projected[str(orders[1])]["album_url"] is None
    with SessionLocal() as db:
        assert db.get(SaleOrder, order).total_cents == 1200
        log = db.scalar(select(AuditEvent).where(AuditEvent.event == "order.delivery_available"))
        assert str(order) in log.subject and ":admin:" in log.subject and ALBUM not in log.subject
        owner = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash("delivery-client")))
        other = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Outra", phone_e164="+5511888877777")
        db.add(other)
        db.flush()
        owner.subject_id = other.id
        owner.client_subject_id = other.id
        db.commit()
    assert client.get("/library/purchases").json()["orders"] == []


def test_delivery_notice_uses_only_the_order_tenant_subdomain():
    admin, customer, orders, _ = setup_order()
    order_id = orders[0]
    drive_album = "https://drive.google.com/file/d/AlbumA/view?usp=sharing"
    with SessionLocal() as db:
        owner_a = db.scalar(select(Client).where(Client.tenant_id == FIXTURE_TENANT_ID))
        tenant_b = Tenant(status="active", canonical_host="b.fotografo.exemplo.com")
        db.add(tenant_b)
        db.flush()
        db.add(Client(tenant_id=tenant_b.id, full_name="Cadastro independente B",
                      phone_e164=owner_a.phone_e164))
        db.commit()
    response = send(admin, order_id, drive_album)
    assert response.status_code == 200
    notice = events()[0]
    assert f"https://{PURCHASE_HOST}/library/purchases#order-{order_id}" in notice.whatsapp_body
    assert "drive.google.com" not in notice.whatsapp_body
    assert "b.fotografo.exemplo.com" not in notice.whatsapp_body
    assert notice.target_path == f"/library/purchases#order-{order_id}"
    customer_order = next(order for order in customer.get("/library/purchases").json()["orders"] if order["id"] == str(order_id))
    assert customer_order["delivery_album_url"] == drive_album


def test_purchase_link_reauthentication_is_host_and_client_scoped(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_PII_FINGERPRINT_SALT", "synthetic-purchase-login-salt")
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(FIXTURE_TENANT_ID): "A"}))
    monkeypatch.setenv("WHATSAPP_BINDING_A_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_BINDING_A_CREDENTIAL_ENV", "development")
    _admin, customer, orders, _ = setup_order()
    order_id = orders[0]
    with SessionLocal() as db:
        other_tenant = Tenant(status="active", canonical_host="b.fotografo.exemplo.com")
        db.add(other_tenant)
        db.flush()
        other_client = Client(tenant_id=other_tenant.id, full_name="Cadastro independente B",
                              phone_e164="+5511999999999")
        db.add(other_client)
        db.flush()
        db.add(ClientPhone(tenant_id=other_tenant.id, client_id=other_client.id,
                           phone_e164=other_client.phone_e164, active=True, verified_at=now()))
        db.add(AuthSession(tenant_id=other_tenant.id, subject_id=other_client.id, role="client",
                           token_hash=token_hash("client-b-session"),
                           client_subject_id=other_client.id,
                           expires_at=now() + timedelta(hours=1)))
        db.commit()
    customer.cookies.clear()
    customer.base_url = f"https://{PURCHASE_HOST}"
    return_to = f"/library/purchases#order-{order_id}"
    challenge_response = customer.post("/auth/client/challenge", json={
        "phone": "+5511999999999", "return_to": return_to,
    })
    assert challenge_response.status_code == 202, challenge_response.text
    challenge_id = challenge_response.json()["challenge_id"]
    with SessionLocal() as db:
        challenge = db.get(AuthChallenge, UUID(challenge_id))
        assert challenge.tenant_id == FIXTURE_TENANT_ID
        assert challenge.parent_gallery_id is None and challenge.gallery_capability_id is None
        assert challenge.return_to == return_to
        challenge.secret_hash = token_hash("123456")
        db.commit()
    verified = customer.post("/auth/client/verify", json={"challenge_id": challenge_id, "code": "123456"})
    assert verified.status_code == 200, verified.text
    assert verified.json()["destination"] == return_to
    assert customer.get(f"/auth/destination?return_to={return_to.replace('#', '%23')}").json()["destination"] == return_to

    foreign_host = TestClient(app, base_url="https://b.fotografo.exemplo.com")
    foreign_host.cookies.set("markina_session", customer.cookies.get("markina_session"))
    assert foreign_host.get("/auth/destination").status_code == 403
    tenant_a_host = TestClient(app, base_url=f"https://{PURCHASE_HOST}")
    tenant_a_host.cookies.set("markina_session", "client-b-session")
    assert tenant_a_host.get("/auth/destination").status_code == 403


def test_purchase_login_on_unknown_host_does_not_create_challenge():
    _admin, customer, orders, _ = setup_order()
    customer.cookies.clear()
    customer.base_url = "https://unknown.fotografo.exemplo.com"
    result = customer.post("/auth/client/challenge", json={
        "phone": "+5511999999999", "return_to": f"/library/purchases#order-{orders[0]}",
    })
    assert result.status_code == 202
    assert "Se os dados puderem receber acesso" in result.json()["message"]
    with SessionLocal() as db:
        assert db.scalar(select(AuthChallenge).where(AuthChallenge.tenant_id == FIXTURE_TENANT_ID)) is None


def test_worker_cancels_delivery_if_canonical_host_changes_after_queue(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    admin, _, orders, _ = setup_order()
    order_id = orders[0]
    assert send(admin, order_id).status_code == 200
    original_body = events()[0].whatsapp_body
    assert f"https://{PURCHASE_HOST}/library/purchases#order-{order_id}" in original_body
    with SessionLocal() as db:
        db.get(Tenant, FIXTURE_TENANT_ID).canonical_host = "a2.fotografo.exemplo.com"
        db.commit()

    class UnexpectedDelivery(SandboxWhatsAppProvider):
        calls = 0

        def send_transactional(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("Aviso de host anterior não pode ser enviado.")

    provider = UnexpectedDelivery()
    assert process_next_notification("whatsapp", whatsapp_provider=provider)
    assert provider.calls == 0
    with SessionLocal() as db:
        item = db.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "whatsapp"))
        assert item.status == "cancelled" and item.last_error == "recipient_not_authorized"


def test_purchase_return_falls_back_for_order_from_another_tenant():
    _admin, _customer, _orders, _ = setup_order()
    with SessionLocal() as db:
        client_a = db.scalar(select(Client).where(Client.tenant_id == FIXTURE_TENANT_ID))
        tenant_b = Tenant(status="active", canonical_host="b.fotografo.exemplo.com")
        db.add(tenant_b)
        db.flush()
        client_b = Client(tenant_id=tenant_b.id, full_name="Cadastro B", phone_e164="+5511999999999")
        parent_b = ParentGallery(tenant_id=tenant_b.id, name="Galeria B")
        db.add_all([client_b, parent_b])
        db.flush()
        gallery_b = DerivedGallery(tenant_id=tenant_b.id, parent_gallery_id=parent_b.id,
                                   client_id=client_b.id, name="Privada B")
        db.add(gallery_b)
        db.flush()
        order_b = SaleOrder(tenant_id=tenant_b.id, client_id=client_b.id,
                            derived_gallery_id=gallery_b.id, derived_gallery_id_snapshot=gallery_b.id,
                            derived_gallery_name_snapshot="Privada B", parent_gallery_id_snapshot=parent_b.id,
                            parent_gallery_name_snapshot="Galeria B", payment_status="confirmed",
                            total_cents=1200, confirmed_at=now())
        db.add(order_b)
        db.commit()
        foreign_order_id = order_b.id
        return_to = f"/library/purchases#order-{foreign_order_id}"
        assert main._purchase_return_destination(
            db, return_to, tenant_id=FIXTURE_TENANT_ID, client_id=client_a.id,
        ) == "/library"


@pytest.mark.parametrize("status", ["pending", "cancelled"])
def test_payment_gate_and_removal(status):
    admin, client, orders, _ = setup_order(status)
    order = orders[0]
    assert send(admin, order).status_code == 409
    with SessionLocal() as db:
        db.get(SaleOrder, order).delivery_album_url = ALBUM
        db.commit()
    assert client.get("/library/purchases").json()["orders"][0]["delivery_album_url"] is None
    assert admin.post(f"/admin/orders/{order}/delivery/resend", json={"version": 0, "operation_id": str(uuid4())}).status_code == 409
    assert send(admin, order, None).status_code == 200
    assert events() == []


def test_resend_idempotency_current_templates_and_removed_link():
    admin, _, orders, _ = setup_order()
    order = orders[0]
    send(admin, order)
    with SessionLocal() as db:
        save_setting(db, "order_delivery_ready", {"whatsapp_body": "Texto atualizado", "push_enabled": False}, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    path = f"/admin/orders/{order}/delivery/resend"
    payload = {"version": 1, "operation_id": str(uuid4())}
    first = admin.post(path, json=payload)
    assert first.status_code == 200, first.text
    assert admin.post(path, json=payload).json()["notification"] == first.json()["notification"]
    assert len(events()) == 2
    assert events()[1].whatsapp_body == "Texto atualizado"
    assert admin.post(path, json={**payload, "operation_id": str(uuid4())}).status_code == 200
    assert len(events()) == 3
    assert send(admin, order, SECOND, 1).status_code == 200
    assert admin.post(path, json=payload).status_code == 409
    assert send(admin, order, None, 2).status_code == 200
    assert admin.post(path, json={**payload, "version": 3}).status_code == 409
    assert len(events()) == 4


def test_rollback_cannot_publish_or_queue():
    admin, _, orders, _ = setup_order()
    with SessionLocal() as db:
        actor = db.scalar(select(AuthSession).where(AuthSession.role == "admin")).subject_id
        set_delivery(db, lock_delivery_order(db, orders[0], tenant_id=FIXTURE_TENANT_ID), ALBUM, 0, actor)
        db.rollback()
    assert events() == []
    assert send(admin, orders[0]).json()["delivery"]["version"] == 1


def test_correction_reconfirmation_never_replays_old_notice(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    admin, client, orders, communication = setup_order()
    order = orders[0]
    send(admin, order)
    corrected = admin.post(f"/admin/payment-communications/{communication}/correction", json={"idempotency_key": "delivery-correction-1"})
    assert corrected.status_code == 200, corrected.text
    assert client.get("/library/purchases").json()["orders"][0]["delivery_album_url"] is None
    with SessionLocal() as db:
        saved = db.get(SaleOrder, order)
        assert saved.delivery_album_url == ALBUM and saved.delivery_revision == 2
        saved.payment_status = "confirmed"
        db.commit()
    assert client.get("/library/purchases").json()["orders"][0]["delivery_album_url"] == ALBUM
    assert process_next_notification("whatsapp", whatsapp_provider=SandboxWhatsAppProvider())
    with SessionLocal() as db:
        assert db.scalar(select(NotificationDelivery)).status == "cancelled"


def test_worker_failure_and_removed_operational_gallery(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    admin, client, orders, _ = setup_order()
    order = orders[0]
    send(admin, order)
    with SessionLocal() as db:
        row = db.get(SaleOrder, order)
        row.derived_gallery_id = None
        row.assets_removed_at = now()
        db.commit()
    class Failing(SandboxWhatsAppProvider):
        def send_transactional(self, *_args, **_kwargs):
            raise WhatsAppDeliveryError("Falha sintética", transient=False)
    assert process_next_notification("whatsapp", whatsapp_provider=Failing())
    with SessionLocal() as db:
        assert db.scalar(select(NotificationDelivery)).status == "failed"
    assert client.get("/library/purchases").json()["orders"][0]["delivery_album_url"] == ALBUM


def test_disabled_channels_do_not_replay():
    admin, _, orders, _ = setup_order()
    with SessionLocal() as db:
        save_setting(db, "order_delivery_ready", {"whatsapp_enabled": False, "push_enabled": False}, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    response = send(admin, orders[0])
    assert response.json()["notification"]["channels"] == []
    with SessionLocal() as db:
        save_setting(db, "order_delivery_ready", {"whatsapp_enabled": True}, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        assert list(db.scalars(select(NotificationDelivery))) == []
    assert len(events()) == 1


def test_grouped_correction_invalidates_each_delivery_without_combining_links():
    admin, client, orders, communication_id = setup_order(grouped=True)
    with SessionLocal() as db:
        first = db.get(SaleOrder, orders[0])
        group = PaymentGroup(tenant_id=FIXTURE_TENANT_ID, client_id=first.client_id, state="confirmed", revision="synthetic",
                             total_cents=2400, pix_copy_paste_snapshot="synthetic", pix_configuration_snapshot={})
        db.add(group)
        db.flush()
        for order_id in orders:
            db.get(SaleOrder, order_id).payment_group_id = group.id
        db.get(PaymentCommunication, communication_id).payment_group_id = group.id
        db.commit()
        group_id = group.id
    assert send(admin, orders[0]).status_code == 200
    assert send(admin, orders[1], SECOND).status_code == 200
    history = client.get("/library/purchases").json()["payment_groups"][0]["orders"]
    assert {row["delivery_album_url"] for row in history} == {ALBUM, SECOND}
    response = admin.post(f"/admin/payment-communications/{communication_id}/correction", json={"idempotency_key": "group-delivery-correction", "payment_group_id": str(group_id)})
    assert response.status_code == 200, response.text
    history = client.get("/library/purchases").json()["payment_groups"][0]["orders"]
    assert all(row["delivery_album_url"] is None for row in history)
    with SessionLocal() as db:
        rows = [db.get(SaleOrder, order) for order in orders]
        assert all(row.delivery_revision == 2 and row.payment_status == "pending" for row in rows)
        assert {row.delivery_album_url for row in rows} == {ALBUM, SECOND}


@pytest.mark.parametrize("mutation", ["replace", "remove", "expire", "wrong_recipient"])
def test_obsolete_or_expired_notice_never_reaches_provider(monkeypatch, mutation):
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    admin, _, orders, _ = setup_order()
    send(admin, orders[0])
    event = events()[0]
    if mutation == "replace":
        send(admin, orders[0], SECOND, 1)
    elif mutation == "remove":
        send(admin, orders[0], None, 1)
    else:
        with SessionLocal() as db:
            if mutation == "expire":
                db.get(NotificationEvent, event.id).expires_at = now() - timedelta(seconds=1)
            else:
                other = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Destinatário alheio", phone_e164="+5511999999632")
                db.add(other)
                db.flush()
                delivery = db.scalar(select(NotificationDelivery))
                delivery.recipient_id = delivery.client_recipient_id = other.id
            db.commit()
    class NeverSend(SandboxWhatsAppProvider):
        def send_transactional(self, *_a, **_k):
            pytest.fail("Aviso obsoleto não deve chegar ao provedor")
    assert process_next_notification("whatsapp", whatsapp_provider=NeverSend())
    with SessionLocal() as db:
        item = db.scalar(select(NotificationDelivery).where(NotificationDelivery.event_id == event.id))
        assert item.status == ("expired" if mutation == "expire" else "cancelled")
        assert item.attempts == 0


def test_push_independent_retry_and_destination(monkeypatch):
    monkeypatch.setenv("PUSH_SUBSCRIPTION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    admin, _, orders, _ = setup_order()
    with SessionLocal() as db:
        owner = db.scalar(select(AuthSession).where(AuthSession.role == "client"))
        subscribe(db, owner, "synthetic-delivery-device", subscription())
        db.commit()
    send(admin, orders[0])
    def fail(*_a, **_k):
        raise PushFailure("unavailable", status=503, transient=True)
    assert process_next_notification("push", push_sender=fail)
    assert process_next_notification("whatsapp", whatsapp_provider=SandboxWhatsAppProvider())
    with SessionLocal() as db:
        items = {row.channel: row for row in db.scalars(select(NotificationDelivery))}
        assert items["push"].status == "queued" and items["whatsapp"].status == "accepted"
        items["push"].next_attempt_at = now() - timedelta(seconds=1)
        db.commit()
    received = []
    process_next_notification("push", push_sender=lambda _subscription, payload, **_kw: received.append(payload))
    assert received[0]["path"] == f"/library/purchases#order-{orders[0]}"
    assert ALBUM not in str(received)
