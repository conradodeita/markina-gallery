from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.auth import (
    DerivedGallery,
    NotificationEvent,
    PaymentCommunication,
    PaymentConfirmationCorrection,
    PaymentNotificationOutbox,
    SaleOrder,
    SessionLocal,
)
from app.messaging import SandboxWhatsAppProvider, WhatsAppDeliveryError
from app.notification_delivery import process_next_notification
from app.notification_events import record_payment_event
from app.notification_settings import save_setting
from app.worker import materialize_next_payment_notification
from tests.test_notification_settings import isolated_schema  # noqa: F401
from tests.test_private_upload_batches import setup_private


@pytest.mark.parametrize("first_decision, final_decision", [("confirmed", "refused"), ("refused", "confirmed")])
def test_payment_decisions_unique_and_correction_silent(monkeypatch, first_decision, final_decision):
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511999999999")
    browser, gallery_id, _ = setup_private()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_id)
        order = SaleOrder(derived_gallery_id=gallery_id, client_id=gallery.client_id,
                          derived_gallery_id_snapshot=gallery_id, derived_gallery_name_snapshot="Privada",
                          parent_gallery_id_snapshot=gallery.parent_gallery_id,
                          parent_gallery_name_snapshot="Evento", total_cents=500)
        db.add(order)
        db.flush()
        communication = PaymentCommunication(sale_order_id=order.id, client_id=order.client_id,
                                             idempotency_key="reported")
        db.add(communication)
        db.flush()
        first = record_payment_event(db, communication=communication, order=order, event_type="payment_reported")
        assert record_payment_event(db, communication=communication, order=order, event_type="payment_reported").id == first.id
        db.commit()
        communication_id = communication.id
    url = f"/admin/payment-communications/{communication_id}"
    first_payment_status = "confirmed" if first_decision == "confirmed" else "cancelled"
    assert browser.post(f"{url}/decision", json={"decision": first_decision}).status_code == 200
    assert browser.post(f"{url}/decision", json={"decision": first_decision}).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2
        assert db.get(SaleOrder, order.id).payment_status == first_payment_status
    assert not materialize_next_payment_notification()  # projeção não vira fila duplicada
    class FailedProvider(SandboxWhatsAppProvider):
        def send_transactional(self, *_args, **_kwargs):
            raise WhatsAppDeliveryError("Falha sintética", transient=False)
    while process_next_notification("whatsapp", whatsapp_provider=FailedProvider()):
        pass
    with SessionLocal() as db:
        assert db.get(SaleOrder, order.id).payment_status == first_payment_status
        assert db.get(PaymentCommunication, communication_id).status == first_decision
    assert browser.post(f"{url}/correction", json={"idempotency_key": "correction-synthetic"}).status_code == 200
    assert browser.post(f"{url}/correction", json={"idempotency_key": "correction-synthetic"}).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(NotificationEvent.id))) == 2
        assert db.scalar(select(func.count(PaymentConfirmationCorrection.id))) == 1
        correction = db.scalar(select(PaymentConfirmationCorrection))
        assert correction.previous_communication_status == first_decision
        assert correction.previous_order_status == first_payment_status
        assert db.get(SaleOrder, order.id).payment_status == "pending"
    assert browser.post(f"{url}/decision", json={"decision": final_decision}).status_code == 200
    assert browser.post(f"{url}/decision", json={"decision": final_decision}).status_code == 200
    with SessionLocal() as db:
        events = list(db.scalars(select(NotificationEvent)))
        assert {event.event_type for event in events} == {"payment_reported", "payment_confirmed", "payment_refused"}
        assert {event.client_id for event in events} == {order.client_id}
        assert db.get(PaymentCommunication, UUID(str(communication_id))).status == final_decision
        assert db.get(SaleOrder, order.id).payment_status == ("confirmed" if final_decision == "confirmed" else "cancelled")
        assert db.scalar(select(func.count(PaymentNotificationOutbox.id))) >= 2
        save_setting(db, f"payment_{final_decision}", {"whatsapp_enabled": False})
        db.commit()
        projection = db.scalar(select(PaymentNotificationOutbox).where(PaymentNotificationOutbox.template_kind == final_decision))
        assert projection.status == "failed" and projection.last_error == "channel_disabled"
