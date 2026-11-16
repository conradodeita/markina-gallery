"""Pendências conservadoras e exceção temporal sem duplicar arquivo frio."""

from datetime import timedelta
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.auth import (
    AuditEvent,
    AuthSession,
    NotificationDelivery,
    NotificationEvent,
    NotificationSetting,
    PhotoFolder,
    PushSubscription,
    SessionLocal,
    Tenant,
    WhatsAppDelivery,
    engine,
    now,
)
from app.media_archive_guards import never_released_closure_folder
from app.tenant_closure import ClosureInput, finalize_closure, request_closure
from app.tenant_closure_obligations import evaluate_closure
from tests.schema_fixtures import create_test_schema
from tests.test_media_archive_scheduler import _engine_with_schema
from tests.test_photographer_credits import create_photo
from tests.test_tenant_closure import prepare


@pytest.fixture
def context():
    engine = _engine_with_schema()
    try:
        with Session(engine, expire_on_commit=False) as db:
            session, payload, tenant = prepare(db)
            request_closure(db, session, payload)
            db.commit()
            yield db, tenant
    finally:
        engine.dispose()


@pytest.fixture
def isolated_closure_postgres():
    if engine.dialect.name != "postgresql":
        pytest.skip("Requer PostgreSQL sintético local dedicado")
    schema = f"closure_notification_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine.update_execution_options(schema_translate_map={None: schema})
    try:
        create_test_schema(engine)
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.update_execution_options(schema_translate_map=None)


def test_no_obligations_is_ready_and_unrelated_tenant_does_not_interfere(context):
    from app.auth import Tenant

    db, tenant = context
    other = Tenant(lifecycle="closing")
    db.add(other)
    db.flush()
    create_photo(db, other.id)
    db.commit()
    assert evaluate_closure(db, tenant.id)["ready"] is True
    assert evaluate_closure(db, other.id)["ready"] is False


def test_order_payment_and_delivery_block_until_resolved(context):
    from app.auth import Client, GalleryClientState, ParentGallery, SaleOrder

    db, tenant = context
    gallery = ParentGallery(tenant_id=tenant.id, name="Synthetic")
    client = Client(tenant_id=tenant.id, full_name="Synthetic", phone_e164="+5511999990033")
    db.add_all([gallery, client])
    db.flush()
    db.add(GalleryClientState(tenant_id=tenant.id, parent_gallery_id=gallery.id, client_id=client.id))
    db.flush()
    order = SaleOrder(tenant_id=tenant.id, client_id=client.id, parent_gallery_id=gallery.id,
                      parent_gallery_id_snapshot=gallery.id, parent_gallery_name_snapshot="Synthetic",
                      derived_gallery_name_snapshot="Synthetic", total_cents=0, frozen_at=now())
    db.add(order)
    db.commit()
    assert evaluate_closure(db, tenant.id)["blockers"] == ["open_order"]
    order.payment_status = "not_required"
    order.payment_required_snapshot = False
    db.commit()
    assert evaluate_closure(db, tenant.id)["blockers"] == ["open_order"]
    order.delivery_album_url = "https://photos.google.com/synthetic"
    db.commit()
    assert evaluate_closure(db, tenant.id)["ready"] is True


def test_unreleased_folder_needs_archive_but_not_thirty_days(context):
    db, tenant = context
    photo = create_photo(db, tenant.id)
    folder = db.get(PhotoFolder, photo.folder_id)
    folder.audience_scope = "all"
    db.commit()
    assert never_released_closure_folder(db, folder)
    assert evaluate_closure(db, tenant.id)["blockers"] == ["media_not_archived"]
    folder.status = "released"
    folder.released_at = now()
    folder.access_expires_at = now() + timedelta(days=7)
    db.commit()
    assert "access_window" in evaluate_closure(db, tenant.id)["blockers"]
    folder.access_expires_at = None
    db.commit()
    assert "deadline_required" in evaluate_closure(db, tenant.id)["blockers"]


def test_legacy_unknown_or_positive_release_history_cannot_use_exception(context):
    db, tenant = context
    photo = create_photo(db, tenant.id)
    folder = db.get(PhotoFolder, photo.folder_id)
    assert not never_released_closure_folder(db, folder)
    folder.audience_scope = "all"
    db.add(AuditEvent(tenant_id=tenant.id, event="photo_folder.published", subject=f"{folder.id}:1"))
    db.commit()
    assert not never_released_closure_folder(db, folder)


def test_source_failure_is_sanitized_and_never_ready(context, monkeypatch):
    from app import tenant_closure_obligations as obligations

    db, tenant = context
    def fail(*_args):
        raise SQLAlchemyError("sensitive synthetic diagnostic")
    monkeypatch.setattr(obligations, "_evaluate", fail)
    result = evaluate_closure(db, tenant.id)
    assert result["ready"] is False and result["blockers"] == ["source_unavailable"]
    assert "sensitive" not in str(result)


def test_finalization_revokes_sessions_and_is_audited_once(context):
    from sqlalchemy import func, select

    from app.auth import AuthSession, TenantClosureRequest
    from app.tenancy import enable_domain_guard
    from app.tenant_closure import finalize_closure

    db, tenant = context
    row = db.scalar(select(TenantClosureRequest).where(TenantClosureRequest.tenant_id == tenant.id))
    session = AuthSession(tenant_id=tenant.id, role="admin", subject_id=row.requested_by,
                          admin_subject_id=row.requested_by, token_hash="synthetic-closure",
                          expires_at=now() + timedelta(days=1))
    db.add(session)
    db.commit()
    enable_domain_guard(db)
    first_pass = finalize_closure(db, tenant.id)
    db.commit()
    assert not first_pass["ready"]
    assert tenant.lifecycle == "closing" and session.revoked_at is None
    assert finalize_closure(db, tenant.id)["ready"]
    db.commit()
    assert tenant.lifecycle == "closed" and tenant.status == "active"
    db.refresh(session)
    assert session.revoked_at is not None and row.closed_at is not None
    assert finalize_closure(db, tenant.id)["replayed"]
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.tenant_id == tenant.id, AuditEvent.event == "tenant.closure_completed")) == 1


def test_pending_media_keeps_account_and_session_open(context):
    from app.tenant_closure import finalize_closure

    db, tenant = context
    photo = create_photo(db, tenant.id)
    db.get(PhotoFolder, photo.folder_id).audience_scope = "all"
    db.commit()
    result = finalize_closure(db, tenant.id)
    db.commit()
    assert not result["ready"] and tenant.lifecycle == "closing"
    assert "media_not_archived" in result["blockers"]


def test_upload_reservation_blocks_and_residual_credits_are_preserved(context):
    from sqlalchemy import func, select

    from app.auth import PhotoCreditOperation, PhotographerCreditEntry
    from app.system_monitor.models import PlatformOwner

    db, tenant = context
    photo = create_photo(db, tenant.id)
    operation = PhotoCreditOperation(tenant_id=tenant.id, photo_asset_id=photo.id,
                                     photo_asset_id_snapshot=photo.id, storage_key_snapshot=photo.storage_key,
                                     payload_fingerprint="c" * 64)
    owner_id = db.scalar(select(PlatformOwner.admin_user_id))
    db.add_all([operation, PhotographerCreditEntry(
        tenant_id=tenant.id, entry_type="owner_grant", delta=9, idempotency_key="synthetic-preserved",
        global_owner_admin_id=owner_id)])
    db.commit()
    assert "processing_pending" in evaluate_closure(db, tenant.id)["blockers"]
    operation.status = "released"
    db.commit()
    assert "processing_pending" not in evaluate_closure(db, tenant.id)["blockers"]
    assert db.scalar(select(func.sum(PhotographerCreditEntry.delta)).where(
        PhotographerCreditEntry.tenant_id == tenant.id)) == 9


def test_worker_rotates_past_blocked_account_and_finalizes_ready_account(context, monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy.orm import sessionmaker

    from app import worker
    from app.auth import (
        AdminUser,
        PhotographerTermsAcceptance,
        Tenant,
        TenantAdmin,
        TenantCreditWallet,
    )
    from app.tenant_closure import ClosureInput

    db, tenant = context
    create_photo(db, tenant.id)
    other = Tenant()
    db.add(other)
    db.flush()
    admin = AdminUser(email="another-synthetic@example.test", password_hash="synthetic", email_verified=True,
                      totp_enabled=False)
    admin.tenant_memberships.append(TenantAdmin(tenant_id=other.id))
    db.add(admin)
    db.flush()
    db.add(TenantCreditWallet(tenant_id=other.id, mode="finite"))
    db.add(PhotographerTermsAcceptance(
        tenant_id=other.id, admin_user_id=admin.id, terms_version="synthetic-closure",
        terms_text="synthetic", terms_sha256="a" * 64, provider_identity="synthetic",
        photographer_identity="synthetic", environment="development"))
    db.commit()
    request_closure(db, SimpleNamespace(role="admin", subject_id=admin.id, tenant_id=other.id),
                    ClosureInput(request_id=uuid4(), confirm_closure=True,
                                 acknowledge_remaining_balance=True, expected_balance=0,
                                 terms_version="synthetic-closure", terms_sha256="a" * 64))
    db.commit()
    monkeypatch.setattr(worker, "SessionLocal", sessionmaker(bind=db.get_bind(), expire_on_commit=False))
    monkeypatch.setattr(worker, "_last_closure_cursor", None)
    results = [worker.process_next_tenant_closure() for _ in range(6)]
    assert False in results and True in results
    db.refresh(tenant)
    db.refresh(other)
    assert tenant.lifecycle == "closing" and other.lifecycle == "closed"


def test_finalization_preserves_explicitly_acknowledged_positive_balance():
    from sqlalchemy import func, select

    from app.auth import PhotographerCreditEntry
    from app.system_monitor.models import PlatformOwner
    from app.tenant_closure import finalize_closure

    engine = _engine_with_schema()
    try:
        with Session(engine, expire_on_commit=False) as db:
            session, payload, tenant = prepare(db)
            owner_id = db.scalar(select(PlatformOwner.admin_user_id))
            db.add(PhotographerCreditEntry(tenant_id=tenant.id, entry_type="owner_grant", delta=9,
                                           idempotency_key="acknowledged-residual",
                                           global_owner_admin_id=owner_id))
            db.commit()
            request_closure(db, session, payload.model_copy(update={"expected_balance": 9}))
            db.commit()
            assert not finalize_closure(db, tenant.id)["ready"]
            db.commit()
            assert finalize_closure(db, tenant.id)["ready"]
            db.commit()
            assert tenant.lifecycle == "closed"
            assert db.scalar(select(func.sum(PhotographerCreditEntry.delta)).where(
                PhotographerCreditEntry.tenant_id == tenant.id)) == 9
            assert db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
                PhotographerCreditEntry.tenant_id == tenant.id)) == 1
    finally:
        engine.dispose()


def test_queued_notifications_do_not_block_closure_but_processing_blocks(context):
    from sqlalchemy import select

    from app.auth import (
        NotificationDelivery,
        NotificationEvent,
        TenantClosureRequest,
        WhatsAppDelivery,
    )
    from app.notification_settings import setting_for

    db, tenant = context
    admin_id = db.scalar(select(TenantClosureRequest.requested_by).where(
        TenantClosureRequest.tenant_id == tenant.id,
    ))
    setting_for(db, "first_access", tenant_id=tenant.id)
    event = NotificationEvent(
        tenant_id=tenant.id,
        event_key="closure-queued-notice",
        event_type="first_access",
        template_version=1,
        push_title="Aviso sintético",
        push_body="Aviso sintético",
        whatsapp_body="Aviso sintético",
        target_path="/",
        expires_at=now() + timedelta(days=1),
    )
    db.add(event)
    db.flush()
    push = NotificationDelivery(
        tenant_id=tenant.id,
        event_id=event.id,
        channel="push",
        recipient_role="admin",
        recipient_id=admin_id,
        admin_recipient_id=admin_id,
        status="queued",
    )
    whatsapp = WhatsAppDelivery(
        tenant_id=tenant.id,
        kind="payment",
        source_type="synthetic",
        source_id="closure-queued-notice",
        template_kind="confirmed",
        idempotency_key="closure-queued-whatsapp",
        status="queued",
    )
    db.add_all([push, whatsapp])
    db.commit()

    assert evaluate_closure(db, tenant.id)["ready"] is True

    push.status = "processing"
    db.commit()
    assert evaluate_closure(db, tenant.id)["blockers"] == ["processing_pending"]

    push.status = "queued"
    whatsapp.status = "processing"
    db.commit()
    assert evaluate_closure(db, tenant.id)["blockers"] == ["processing_pending"]


def test_processing_notification_outboxes_block_closure(context):
    from app.auth import (
        Client,
        FacialSearchNotificationOutbox,
        FacialSearchRequest,
        GalleryClientState,
        GalleryFacialPolicy,
        GalleryMembershipNotificationOutbox,
        GalleryReopeningNotificationOutbox,
        GalleryReopeningRequest,
        ParentGallery,
    )

    db, tenant = context
    parent = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
    client = Client(tenant_id=tenant.id, full_name="Cliente sintético", phone_e164="+5511999990028")
    db.add_all([parent, client])
    db.flush()
    db.add(GalleryClientState(tenant_id=tenant.id, parent_gallery_id=parent.id, client_id=client.id))
    db.flush()
    membership_notice = GalleryMembershipNotificationOutbox(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        event_key="closure-processing-membership",
        event_type="private_created",
        parent_name_snapshot=parent.name,
        derived_name_snapshot="Galeria privada sintética",
        external_status="queued",
    )
    reopening = GalleryReopeningRequest(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        requested_by_client_id=client.id,
        idempotency_key="closure-processing-reopening",
        status="refused",
    )
    db.add_all([membership_notice, reopening])
    db.flush()
    reopening_notice = GalleryReopeningNotificationOutbox(
        tenant_id=tenant.id,
        gallery_reopening_request_id=reopening.id,
        status="queued",
    )

    policy = GalleryFacialPolicy(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        status="active",
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
        legal_notice_version="synthetic-notice-v1",
        index_generation=1,
    )
    db.add(policy)
    db.flush()
    search = FacialSearchRequest(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        client_id=client.id,
        policy_id=policy.id,
        status="ready",
        reference_source="upload",
        authorization_method="explicit_consent",
        consent_version="synthetic-consent-v1",
        legal_notice_version="synthetic-notice-v1",
        subject_declaration="adult",
        model_version="synthetic-model-v1",
        quality_version="synthetic-quality-v1",
        index_generation=1,
        reference_locator_ciphertext=b"synthetic-ciphertext",
        reference_locator_nonce=b"synthetic-nonce",
        reference_key_id="synthetic-key",
        expires_at=now() + timedelta(days=1),
    )
    db.add(search)
    db.flush()
    facial_notice = FacialSearchNotificationOutbox(
        tenant_id=tenant.id,
        search_request_id=search.id,
        parent_gallery_id=parent.id,
        client_id=client.id,
        result_kind="ready",
        status="queued",
        idempotency_key="closure-processing-facial-notice",
        payload_ciphertext=b"synthetic-ciphertext",
        payload_nonce=b"synthetic-nonce",
        key_id="synthetic-key",
    )
    db.add_all([reopening_notice, facial_notice])
    db.commit()

    outboxes = (
        (membership_notice, "external_status"),
        (reopening_notice, "status"),
        (facial_notice, "status"),
    )
    assert evaluate_closure(db, tenant.id)["ready"] is True
    for outbox, status_field in outboxes:
        setattr(outbox, status_field, "processing")
        db.commit()
        assert evaluate_closure(db, tenant.id)["blockers"] == ["processing_pending"]
        setattr(outbox, status_field, "queued")
        db.commit()


def test_notification_claims_lock_tenant_before_processing(monkeypatch):
    from sqlalchemy.dialects import postgresql

    from app import membership_notifications, notification_delivery, worker

    class CaptureSession:
        def __init__(self):
            self.statements = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def scalar(self, statement):
            self.statements.append(statement)

        def scalars(self, statement):
            self.statements.append(statement)
            return []

        def commit(self):
            pass

        def rollback(self):
            pass

    calls = (
        (notification_delivery, "process_next_notification", "notification_delivery", ("push",)),
        (worker, "process_next_whatsapp_delivery", "whatsapp_delivery", ()),
        (worker, "materialize_next_payment_notification", "payment_notification_outbox", ()),
        (worker, "process_next_gallery_reopening_notification", "gallery_reopening_notification_outbox", ()),
        (worker, "reconcile_next_unknown_delivery", "whatsapp_delivery", ()),
    )
    captures = []
    for module, function_name, table, args in calls:
        capture = CaptureSession()
        monkeypatch.setattr(module, "SessionLocal", lambda capture=capture: capture)
        getattr(module, function_name)(*args)
        captures.append((capture, table))

    membership_capture = CaptureSession()
    membership_notifications.process_next_membership_notification(membership_capture, lambda _row: None)
    captures.append((membership_capture, "gallery_membership_notification_outbox"))

    for capture, table in captures:
        compiled = [str(statement.compile(dialect=postgresql.dialect())) for statement in capture.statements]
        locks = [sql for sql in compiled if table in sql and "FOR UPDATE" in sql]
        assert locks
        assert all("FOR UPDATE OF tenant," in statement for statement in locks)
        assert all("SKIP LOCKED" in statement for statement in locks)


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Requer PostgreSQL sintético local dedicado")
def test_notification_claim_and_closure_race_postgresql(isolated_closure_postgres, monkeypatch):
    """Prova os dois vencedores do lock tenant/entrega com PostgreSQL real."""
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from app import notification_delivery, worker
    from app.auth import AdminUser, PhotographerTermsAcceptance, TenantAdmin, TenantCreditWallet
    from app.facial import closure_cleanup
    from tests.test_photographer_credits import create_accounts

    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    monkeypatch.setattr(notification_delivery, "decrypt_subscription", lambda _subscription: {})
    monkeypatch.setattr(worker, "provider_for", lambda _db, *, tenant_id, adapter=None: adapter)
    monkeypatch.setattr(worker, "require_ready_channel", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker, "delivery_message", lambda *_args, **_kwargs: "Aviso WhatsApp sintético")
    monkeypatch.setattr(closure_cleanup, "cleanup_tenant_biometrics", lambda *_args, **_kwargs: True)

    def create_case(case_number):
        with SessionLocal() as db:
            if case_number == 1:
                _, tenant, _, photographer = create_accounts(db)
            else:
                tenant = Tenant()
                db.add(tenant)
                db.flush()
                photographer = AdminUser(
                    email=f"photographer-{case_number}@example.test",
                    password_hash="synthetic",
                    totp_secret="synthetic",
                    email_verified=True,
                )
                photographer.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
                db.add_all([tenant, photographer])
                db.flush()
                db.add(TenantCreditWallet(tenant_id=tenant.id, mode="finite"))
                db.flush()
            db.add(PhotographerTermsAcceptance(
                tenant_id=tenant.id,
                admin_user_id=photographer.id,
                terms_version="synthetic-closure",
                terms_text="synthetic",
                terms_sha256="a" * 64,
                provider_identity="synthetic",
                photographer_identity="synthetic",
                environment="development",
            ))
            db.commit()
            session = SimpleNamespace(role="admin", subject_id=photographer.id, tenant_id=tenant.id)
            payload = ClosureInput(
                request_id=uuid4(), confirm_closure=True, acknowledge_remaining_balance=True,
                expected_balance=0, terms_version="synthetic-closure", terms_sha256="a" * 64,
            )
            request_closure(db, session, payload)
            event_type = "first_access"
            db.add(NotificationSetting(
                tenant_id=tenant.id, event_type=event_type, whatsapp_enabled=False, push_enabled=True,
                whatsapp_body="", push_title="Aviso sintético", push_body="Aviso sintético",
            ))
            db.flush()
            event = NotificationEvent(
                tenant_id=tenant.id,
                event_key=f"closure-race:{uuid4()}",
                event_type=event_type,
                template_version=1,
                push_title="Aviso sintético",
                push_body="Aviso sintético",
                whatsapp_body="",
                target_path="/admin",
                expires_at=now() + timedelta(days=1),
            )
            db.add(event)
            auth_session = AuthSession(
                tenant_id=tenant.id, token_hash=str(uuid4()), role="admin", subject_id=photographer.id,
                admin_subject_id=photographer.id, expires_at=now() + timedelta(days=1),
            )
            db.add(auth_session)
            db.flush()
            subscription = PushSubscription(
                tenant_id=tenant.id,
                endpoint_fingerprint=uuid4().hex + uuid4().hex,
                encrypted_subscription="synthetic",
                role="admin",
                subject_id=photographer.id,
                admin_subject_id=photographer.id,
                session_id=auth_session.id,
                generation=1,
                active=True,
            )
            db.add(subscription)
            db.flush()
            delivery = NotificationDelivery(
                tenant_id=tenant.id,
                event_id=event.id,
                channel="push",
                recipient_role="admin",
                recipient_id=photographer.id,
                admin_recipient_id=photographer.id,
                subscription_id=subscription.id,
                subscription_generation=subscription.generation,
                status="queued",
                next_attempt_at=now(),
            )
            db.add(delivery)
            whatsapp_delivery = WhatsAppDelivery(
                tenant_id=tenant.id,
                kind="payment",
                source_type="synthetic",
                source_id=str(uuid4()),
                recipient_phone="+5511999990999",
                template_kind="synthetic",
                idempotency_key=f"closure-race-wa:{uuid4()}",
                expires_at=now() + timedelta(days=1),
                status="queued",
                next_attempt_at=now(),
            )
            db.add(whatsapp_delivery)
            db.commit()
            return tenant.id, delivery.id, whatsapp_delivery.id

    first_tenant, first_delivery, first_whatsapp_delivery = create_case(1)
    sender_started, finish_sender = Event(), Event()
    sent = []

    def blocked_sender(*_args, **_kwargs):
        sent.append("first")
        sender_started.set()
        assert finish_sender.wait(10), "Sender sintético não foi liberado"

    with ThreadPoolExecutor(max_workers=2) as pool:
        worker_result = pool.submit(
            notification_delivery.process_next_notification, "push", push_sender=blocked_sender,
        )
        assert sender_started.wait(10), "Worker não reivindicou a entrega"
        with SessionLocal() as db:
            blocked = finalize_closure(db, first_tenant)
            db.commit()
        assert blocked["ready"] is False
        assert blocked["blockers"] == ["processing_pending"]
        finish_sender.set()
        assert worker_result.result(timeout=10) is True

    whatsapp_started, finish_whatsapp = Event(), Event()
    whatsapp_sent = []

    class BlockingWhatsAppProvider:
        def send_transactional(self, recipient_phone, _message, *, idempotency_key):
            whatsapp_sent.append(idempotency_key)
            whatsapp_started.set()
            assert finish_whatsapp.wait(10), "Envio WhatsApp sintético não foi liberado"
            return SimpleNamespace(
                recipient_phone_e164=recipient_phone,
                external_message_id=f"synthetic-{uuid4()}",
                provider_status="accepted",
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        whatsapp_result = pool.submit(
            worker.process_next_whatsapp_delivery, adapter=BlockingWhatsAppProvider(),
        )
        assert whatsapp_started.wait(10), "Worker WhatsApp não reivindicou a entrega"
        with SessionLocal() as db:
            blocked = finalize_closure(db, first_tenant)
            db.commit()
        assert blocked["ready"] is False
        assert blocked["blockers"] == ["processing_pending"]
        finish_whatsapp.set()
        assert whatsapp_result.result(timeout=10) is True

    with SessionLocal() as db:
        assert db.get(NotificationDelivery, first_delivery).status == "accepted"
        assert db.get(WhatsAppDelivery, first_whatsapp_delivery).status == "accepted"
        assert finalize_closure(db, first_tenant)["ready"] is True
        db.commit()
        assert db.get(Tenant, first_tenant).lifecycle == "closed"

    second_tenant, second_delivery, second_whatsapp_delivery = create_case(2)
    closure_has_lock, finish_closure = Event(), Event()
    def held_cleanup(*args, **kwargs):
        closure_has_lock.set()
        assert finish_closure.wait(10), "Finalização sintética não foi liberada"
        return True

    monkeypatch.setattr(closure_cleanup, "cleanup_tenant_biometrics", held_cleanup)

    def close_while_holding_lock():
        with SessionLocal() as db:
            result = finalize_closure(db, second_tenant)
            db.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        closing = pool.submit(close_while_holding_lock)
        assert closure_has_lock.wait(10), "Finalizador não alcançou a barreira de biometria"
        assert notification_delivery.process_next_notification(
            "push", push_sender=lambda *_args, **_kwargs: sent.append("second"),
        ) is False
        assert worker.process_next_whatsapp_delivery(adapter=BlockingWhatsAppProvider()) is False
        with SessionLocal() as db:
            assert db.get(NotificationDelivery, second_delivery).status == "queued"
            assert db.get(WhatsAppDelivery, second_whatsapp_delivery).status == "queued"
        finish_closure.set()
        assert closing.result(timeout=10)["ready"] is True

    assert sent == ["first"]
    assert len(whatsapp_sent) == 1
    with SessionLocal() as db:
        assert db.get(NotificationDelivery, second_delivery).status == "queued"
        assert db.get(WhatsAppDelivery, second_whatsapp_delivery).status == "queued"
        assert db.get(Tenant, second_tenant).lifecycle == "closed"
