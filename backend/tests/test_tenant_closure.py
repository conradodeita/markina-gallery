"""Encerramento autenticado preserva saldo, isolamento e idempotência."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.auth import AuditEvent, PhotographerTermsAcceptance, TenantClosureRequest
from app.tenant_closure import ClosureInput, request_closure
from tests.test_photographer_credits import create_accounts
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def prepare(db):
    _, tenant, _, photographer = create_accounts(db)
    db.add(PhotographerTermsAcceptance(
        tenant_id=tenant.id, admin_user_id=photographer.id, terms_version="synthetic-closure",
        terms_text="synthetic", terms_sha256="a" * 64, provider_identity="synthetic",
        photographer_identity="synthetic", environment="development"))
    db.commit()
    session = SimpleNamespace(role="admin", subject_id=photographer.id, tenant_id=tenant.id)
    payload = ClosureInput(request_id=uuid4(), confirm_closure=True,
                           acknowledge_remaining_balance=True, expected_balance=0,
                           terms_version="synthetic-closure", terms_sha256="a" * 64)
    return session, payload, tenant


def test_request_is_scoped_and_idempotent(client_db):
    session, payload, tenant = prepare(client_db)
    assert request_closure(client_db, session, payload)["replayed"] is False
    client_db.commit()
    assert tenant.lifecycle == "closing" and tenant.status == "active"
    assert request_closure(client_db, session, payload)["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(TenantClosureRequest)) == 1
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == "tenant.closure_requested")) == 1
    with pytest.raises(HTTPException) as duplicate:
        request_closure(client_db, session, payload.model_copy(update={"request_id": uuid4()}))
    assert duplicate.value.status_code == 409


@pytest.mark.parametrize("change", [
    {"confirm_closure": False}, {"acknowledge_remaining_balance": False},
    {"expected_balance": 1}, {"terms_sha256": "b" * 64},
])
def test_unconfirmed_or_stale_request_does_not_change_account(client_db, change):
    session, payload, tenant = prepare(client_db)
    with pytest.raises(HTTPException):
        request_closure(client_db, session, payload.model_copy(update=change))
    assert tenant.lifecycle == "open"
    assert client_db.scalar(select(func.count()).select_from(TenantClosureRequest)) == 0


def test_other_tenant_and_client_cannot_request_closure(client_db):
    session, payload, tenant = prepare(client_db)
    for attacker in (SimpleNamespace(role="client", subject_id=session.subject_id, tenant_id=tenant.id),
                     SimpleNamespace(role="admin", subject_id=uuid4(), tenant_id=tenant.id)):
        with pytest.raises(HTTPException) as denial:
            request_closure(client_db, attacker, payload)
        assert denial.value.status_code == 403
    assert tenant.lifecycle == "open"


def test_closing_blocks_legacy_upload_and_credit_reservation_before_any_work(client_db):
    from app.auth import PhotoCreditOperation
    from app.photographer_credits import reserve_photo_credit
    from app.photographer_onboarding import require_upload_ready

    session, payload, tenant = prepare(client_db)
    request_closure(client_db, session, payload)
    client_db.commit()
    for operation in (
        lambda: require_upload_ready(client_db, tenant_id=tenant.id, admin_id=session.subject_id),
        lambda: reserve_photo_credit(client_db, tenant.id, uuid4(), "not-read.jpg", None),
    ):
        with pytest.raises(HTTPException) as refusal:
            operation()
        assert refusal.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation)) == 0


def test_gallery_and_source_routes_reject_before_body_or_media_lookup(client_db, monkeypatch):
    import asyncio

    from app import main

    session, payload, tenant = prepare(client_db)
    request_closure(client_db, session, payload)
    client_db.commit()
    monkeypatch.setattr(main, "directory_tenant_id", lambda *_: tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda *_: session)
    monkeypatch.setattr(main, "current_session", lambda *_: session)

    class NeverReadRequest:
        async def body(self):
            pytest.fail("Corpo do upload foi lido antes da recusa")

    request = NeverReadRequest()
    for create in (
        lambda: main.create_parent_gallery(None, request, client_db),
        lambda: main.create_photo_folder(uuid4(), None, request, client_db),
        lambda: main.create_admin_client_restricted_folder(uuid4(), uuid4(), None, request, client_db),
        lambda: main.create_private_gallery_folder(uuid4(), None, request, client_db),
        lambda: main.register_folder_photo_asset(uuid4(), None, request, client_db),
        lambda: main.register_parent_gallery_cover_photo(uuid4(), None, request, client_db),
        lambda: asyncio.run(main.import_photo_source(uuid4(), request, client_db)),
    ):
        with pytest.raises(HTTPException) as refusal:
            create()
        assert refusal.value.status_code == 409


def test_closed_denies_operational_access_but_preserves_financial_reconciliation(client_db):
    from app.acervo_context import require_active_owner
    from app.auth import require_client_auth_tenant
    from app.tenancy import (
        TenantContextError,
        bind_financial_reconciliation,
        enable_domain_guard,
        require_admin_tenant,
    )

    session, _, tenant = prepare(client_db)
    tenant.lifecycle = "closed"
    client_db.commit()
    with pytest.raises(TenantContextError):
        require_admin_tenant(client_db, session.subject_id)
    with pytest.raises(HTTPException):
        require_active_owner(client_db, tenant.id)
    with pytest.raises(HTTPException):
        require_client_auth_tenant(client_db, tenant.id)
    enable_domain_guard(client_db)
    bind_financial_reconciliation(client_db, tenant.id)
    from app.payment_availability import lock_payment_account

    lock_payment_account(client_db, tenant.id, reconciliation=True)
    with pytest.raises(HTTPException):
        require_active_owner(client_db, tenant.id)
    with pytest.raises(HTTPException):
        lock_payment_account(client_db, tenant.id)
    client_db.add(AuditEvent(tenant_id=tenant.id, event="synthetic.reconciled", subject="synthetic"))
    client_db.commit()
    assert tenant.lifecycle == "closed"


def test_closed_owner_keeps_explicit_global_console_scope_only(client_db):
    from app.platform_console import require_console_owner
    from app.tenancy import TenantContextError, require_admin_tenant

    owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    owner_tenant.lifecycle = tenant.lifecycle = "closed"
    client_db.commit()
    owner_session = SimpleNamespace(subject_id=owner.id, tenant_id=owner_tenant.id)
    require_console_owner(client_db, owner_session)
    with pytest.raises(TenantContextError):
        require_admin_tenant(client_db, owner.id)
    with pytest.raises(TenantContextError):
        require_admin_tenant(client_db, photographer.id, platform_scope=True)


def test_closed_owner_session_only_authenticates_global_scope(client_db, monkeypatch):
    from contextlib import contextmanager

    from fastapi import Response
    from starlette.requests import Request

    from app import auth

    owner_tenant, _, owner, _ = create_accounts(client_db)
    owner_tenant.lifecycle = "closed"
    client_db.commit()
    token = auth.create_session(client_db, Response(), auth.Role.ADMIN, owner.id,
                                tenant_id=owner_tenant.id, platform_scope=True)

    @contextmanager
    def same_db():
        yield client_db

    monkeypatch.setattr(auth, "SessionLocal", same_db)
    request = Request({"type": "http", "headers": [(b"cookie", f"markina_session={token}".encode())]})
    assert auth.current_session(request, auth.Role.ADMIN, platform_scope=True).subject_id == owner.id
    with pytest.raises(HTTPException):
        auth.current_session(request, auth.Role.ADMIN)


def test_closed_tenant_queued_notification_never_calls_provider(client_db, monkeypatch):
    from contextlib import contextmanager
    from datetime import timedelta

    from app import notification_delivery
    from app.auth import NotificationDelivery, NotificationEvent, now
    from app.notification_settings import setting_for

    session, _, tenant = prepare(client_db)
    setting_for(client_db, "first_access", tenant_id=tenant.id)
    client_db.flush()
    event = NotificationEvent(tenant_id=tenant.id, event_key="closed-only", event_type="first_access",
                              template_version=1, push_title="Synthetic", push_body="Synthetic",
                              whatsapp_body="Synthetic", target_path="/admin",
                              expires_at=now() + timedelta(days=1))
    client_db.add(event)
    client_db.flush()
    delivery = NotificationDelivery(tenant_id=tenant.id, event_id=event.id, channel="push",
                                    recipient_role="admin", recipient_id=session.subject_id,
                                    admin_recipient_id=session.subject_id)
    client_db.add(delivery)
    tenant.lifecycle = "closed"
    client_db.commit()

    @contextmanager
    def same_db():
        yield client_db

    monkeypatch.setattr(notification_delivery, "SessionLocal", same_db)
    assert notification_delivery.process_next_notification(
        "push", push_sender=lambda *_a, **_k: pytest.fail("Envio indevido para conta encerrada")) is False
    assert delivery.status == "queued" and delivery.attempts == 0


def test_closed_tenant_media_job_remains_queued(client_db, monkeypatch):
    from contextlib import contextmanager

    from app import worker
    from app.auth import MediaJob
    from tests.test_photographer_credits import create_photo

    _, _, tenant = prepare(client_db)
    photo = create_photo(client_db, tenant.id)
    job = MediaJob(tenant_id=tenant.id, photo_asset_id=photo.id)
    client_db.add(job)
    tenant.lifecycle = "closed"
    client_db.commit()

    @contextmanager
    def same_db():
        yield client_db

    monkeypatch.setattr(worker, "SessionLocal", same_db)
    assert worker.process_next_media_job() is False
    assert job.status == "queued" and job.attempts == 0


def test_closed_tenant_payment_and_whatsapp_workers_leave_deliveries_queued(client_db, monkeypatch):
    from contextlib import contextmanager
    from datetime import timedelta

    from app import worker
    from app.auth import (
        Client,
        DerivedGallery,
        ParentGallery,
        PaymentCommunication,
        PaymentNotificationOutbox,
        SaleOrder,
        WhatsAppDelivery,
        now,
    )

    _, _, tenant = prepare(client_db)
    client = Client(tenant_id=tenant.id, full_name="Cliente sintético", phone_e164="+5511999990101")
    parent = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    client_db.add_all([client, parent])
    client_db.flush()
    gallery = DerivedGallery(
        tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id, name="Privada",
    )
    client_db.add(gallery)
    client_db.flush()
    order = SaleOrder(
        tenant_id=tenant.id, derived_gallery_id=gallery.id, client_id=client.id,
        payment_status="pending", total_cents=100,
    )
    client_db.add(order)
    client_db.flush()
    communication = PaymentCommunication(
        tenant_id=tenant.id, sale_order_id=order.id, client_id=client.id,
        idempotency_key="closed-worker-payment",
    )
    client_db.add(communication)
    client_db.flush()
    payment_notice = PaymentNotificationOutbox(
        tenant_id=tenant.id, payment_communication_id=communication.id,
        recipient_phone=client.phone_e164, template_kind="confirmed",
        idempotency_key="closed-worker-payment-notice",
    )
    queued = WhatsAppDelivery(
        tenant_id=tenant.id, kind="payment", source_type="payment_notification_outbox",
        source_id="synthetic-queued", recipient_phone=client.phone_e164,
        template_kind="confirmed", idempotency_key="closed-worker-whatsapp-queued",
    )
    stale = WhatsAppDelivery(
        tenant_id=tenant.id, kind="payment", source_type="payment_notification_outbox",
        source_id="synthetic-stale", recipient_phone=client.phone_e164,
        template_kind="confirmed", idempotency_key="closed-worker-whatsapp-stale",
        status="processing", attempts=1, updated_at=now() - timedelta(minutes=10),
    )
    unknown = WhatsAppDelivery(
        tenant_id=tenant.id, kind="payment", source_type="payment_notification_outbox",
        source_id="synthetic-unknown", recipient_phone=client.phone_e164,
        template_kind="confirmed", idempotency_key="closed-worker-whatsapp-unknown",
        status="unknown", attempts=1, external_message_id="synthetic-external-id",
    )
    client_db.add_all([payment_notice, queued, stale, unknown])
    tenant.lifecycle = "closed"
    client_db.commit()

    @contextmanager
    def same_db():
        yield client_db

    monkeypatch.setattr(worker, "SessionLocal", same_db)
    monkeypatch.setattr(
        worker, "provider_for",
        lambda *_args, **_kwargs: pytest.fail("Provedor não pode ser consultado para tenant encerrado"),
    )

    assert worker.materialize_next_payment_notification() is False
    assert worker.process_next_whatsapp_delivery() is False
    assert worker.reconcile_next_unknown_delivery() is False
    assert payment_notice.status == "queued" and payment_notice.attempts == 0
    assert queued.status == "queued" and queued.attempts == 0
    assert stale.status == "processing" and stale.attempts == 1
    assert unknown.status == "unknown" and unknown.attempts == 1


def test_closed_tenant_reopening_notice_stays_queued(client_db, monkeypatch):
    from contextlib import contextmanager

    from app import worker
    from app.auth import (
        Client,
        GalleryClientState,
        GalleryReopeningNotificationOutbox,
        GalleryReopeningRequest,
        ParentGallery,
    )

    _, _, tenant = prepare(client_db)
    client = Client(tenant_id=tenant.id, full_name="Cliente sintético", phone_e164="+5511999990102")
    parent = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    client_db.add_all([client, parent])
    client_db.flush()
    client_db.add(GalleryClientState(
        tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id,
    ))
    client_db.flush()
    reopening = GalleryReopeningRequest(
        tenant_id=tenant.id, parent_gallery_id=parent.id, requested_by_client_id=client.id,
        idempotency_key="closed-worker-reopening",
    )
    client_db.add(reopening)
    client_db.flush()
    notice = GalleryReopeningNotificationOutbox(
        tenant_id=tenant.id, gallery_reopening_request_id=reopening.id,
        recipient_phone="+5511999990103", status="queued",
    )
    client_db.add(notice)
    tenant.lifecycle = "closed"
    client_db.commit()

    @contextmanager
    def same_db():
        yield client_db

    monkeypatch.setattr(worker, "SessionLocal", same_db)
    monkeypatch.setattr(
        worker, "provider_for",
        lambda *_args, **_kwargs: pytest.fail("Provedor não pode ser consultado para tenant encerrado"),
    )

    assert worker.process_next_gallery_reopening_notification() is False
    assert notice.status == "queued" and notice.attempts == 0


def test_closed_privacy_cleanup_continues_without_allowing_login(client_db):
    from datetime import timedelta

    from app.auth import AuthChallenge, cleanup_expired_client_otp_pii, now
    from app.tenancy import TenantContextError, bind_privacy_retention, require_admin_tenant

    session, _, tenant = prepare(client_db)
    challenge = AuthChallenge(tenant_id=tenant.id, kind="client_otp", subject="+5511999990001",
                              subject_fingerprint="synthetic-fingerprint", client_name="Synthetic",
                              secret_hash="synthetic", expires_at=now() - timedelta(days=1))
    client_db.add(challenge)
    tenant.lifecycle = "closed"
    client_db.commit()
    bind_privacy_retention(client_db, tenant.id)
    assert cleanup_expired_client_otp_pii(client_db, tenant_id=tenant.id) == 1
    assert challenge.subject is None and challenge.client_name is None
    with pytest.raises(TenantContextError):
        require_admin_tenant(client_db, session.subject_id)
