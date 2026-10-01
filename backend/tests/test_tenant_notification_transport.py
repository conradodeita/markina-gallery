"""Contas sintéticas em PostgreSQL, sem HTTP de provedor, envio ou biometria."""

import base64
import json
from datetime import timedelta
from hashlib import sha256

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import auth, main, notification_delivery, worker
from app.auth import (
    NotificationDelivery,
    ParentGalleryRegistration,
    Tenant,
    TenantAdmin,
    WhatsAppChannelSettings,
    WhatsAppDelivery,
    WhatsAppDeliveryAttempt,
    WhatsAppWebhookReceipt,
    now,
)
from app.messaging import (
    SandboxWhatsAppProvider,
    WhatsAppConfigurationError,
    WhatsAppConnectionStatus,
    WhatsAppDeliveryError,
    WhatsAppDeliveryResult,
)
from app.notification_settings import enqueue_event, setting_for
from app.whatsapp_binding import photographer_phone, provider_for, resolve_binding, webhook_owner
from app.whatsapp_channel import configure_expected_phone
from app.whatsapp_webhook import process_whatsapp_webhook
from tests.test_tenant_client_auth import challenge, request
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_navigation import cookie
from tests.test_tenant_commerce import commerce as _commerce
from tests.test_tenant_commerce import reported

client_db, graph, links, commerce = _client_db, _graph, _links, _commerce


class Recorder(SandboxWhatsAppProvider):
    def __init__(self, *, phone=None, connection_hook=None, fail=False):
        self.calls, self.phone, self.connection_hook, self.fail = [], phone, connection_hook, fail

    def connection_status(self):
        if self.connection_hook:
            self.connection_hook()
        return WhatsAppConnectionStatus("open", self.phone)

    def send_transactional(self, phone_e164, message, *, idempotency_key):
        self.calls.append((phone_e164, message, idempotency_key))
        if self.fail:
            raise WhatsAppDeliveryError("Falha sintética.", transient=True)
        return WhatsAppDeliveryResult(sha256(idempotency_key.encode()).hexdigest(), phone_e164, "accepted")


@pytest.fixture
def transports(client_db, graph, links, monkeypatch):
    monkeypatch.setenv("TRANSACTIONAL_WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_OTP_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"s" * 32).decode())
    monkeypatch.setenv("WHATSAPP_RETRY_BASE_SECONDS", "0")
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(notification_delivery, "SessionLocal", factory)
    for index, row in enumerate(graph):
        row["admin"].email_verified = True
        row["admin_phone"] = f"+551199999001{index}"
        monkeypatch.setenv(f"WHATSAPP_BINDING_{chr(65+index)}_PHOTOGRAPHER_PHONE_E164", row["admin_phone"])
        client_db.add(ParentGalleryRegistration(tenant_id=row["tenant"].id,
            parent_gallery_id=row["parent"].id, client_id=row["client"].id, status="active"))
    client_db.commit()
    return factory


def evolution(monkeypatch, label):
    values = {"PROVIDER": "evolution", "CREDENTIAL_ENV": "development",
        "API_URL": "https://synthetic-provider.invalid", "API_KEY": "synthetic-only",
        "INSTANCE": f"synthetic-{label}", "WEBHOOK_URL": "https://synthetic-app.invalid/internal/whatsapp/webhook",
        "WEBHOOK_SECRET": f"synthetic-webhook-{label}"}
    for key, value in values.items():
        monkeypatch.setenv(f"WHATSAPP_BINDING_{label}_{key}", value)


def event(db, row):
    setting = setting_for(db, "first_access", tenant_id=row["tenant"].id)
    setting.whatsapp_body = f"Conta {row['admin'].email}: {{{{cliente}}}}"
    item = enqueue_event(db, tenant_id=row["tenant"].id, event_type="first_access", event_key="same-transport-key",
        parent_gallery_id=row["parent"].id, client_id=row["client"].id,
        recipients=[row["admin"].id], values={"cliente": row["client"].full_name, "galeria": row["parent"].name}, target_path="/admin")
    db.commit()
    return db.scalar(select(NotificationDelivery).where(NotificationDelivery.event_id == item.id,
        NotificationDelivery.channel == "whatsapp"))


def test_binding_ausente_sem_fallback_legado_e_OTP_nao_mutado(client_db, graph, links, transports, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(graph[0]["tenant"].id): "A"}))
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511888888888")
    assert photographer_phone(client_db, tenant_id=graph[0]["tenant"].id) == graph[0]["admin_phone"]
    with pytest.raises(WhatsAppConfigurationError):
        resolve_binding(client_db, graph[1]["tenant"].id)
    with pytest.raises(HTTPException) as exc:
        challenge(client_db, links[1][0])
    assert exc.value.status_code == 503
    assert client_db.scalar(select(func.count()).select_from(auth.AuthChallenge)) == 0
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 0


def test_templates_destinatarios_idempotencia_e_retry_A_B(client_db, graph, transports):
    deliveries = [event(client_db, row) for row in graph]
    adapter = Recorder(fail=True)
    assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    client_db.expire_all()
    assert deliveries[0].status == "queued" and deliveries[0].attempts == 1
    assert deliveries[1].attempts == 0
    assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    for item in deliveries:
        client_db.refresh(item)
        item.next_attempt_at = now() - timedelta(seconds=1)
    client_db.commit()
    adapter.fail = False
    for _ in graph:
        assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    for row, delivery in zip(graph, deliveries, strict=True):
        client_db.refresh(delivery)
        assert delivery.status == "accepted" and delivery.attempts == 2
        calls = [call for call in adapter.calls if str(row["tenant"].id) in call[2]]
        assert len(calls) == 2 and calls[0][2] == calls[1][2]
        assert all(call[0] == row["admin_phone"] and row["admin"].email in call[1] for call in calls)
    assert len({call[2] for call in adapter.calls}) == 2


def test_suspensao_durante_consulta_canal_preserva_A_e_envia_B(client_db, graph, transports, monkeypatch):
    deliveries = [event(client_db, row) for row in graph]
    evolution(monkeypatch, "A")
    configure_expected_phone(client_db, graph[0]["admin_phone"], tenant_id=graph[0]["tenant"].id)
    def suspend():
        with transports() as other:
            other.get(Tenant, graph[0]["tenant"].id).status = "suspended"
            other.commit()
    adapter = Recorder(phone=graph[0]["admin_phone"], connection_hook=suspend)
    assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    assert adapter.calls == []
    client_db.expire_all()
    assert deliveries[0].status == "queued" and deliveries[0].attempts == 0
    assert deliveries[1].status == "queued" and deliveries[1].attempts == 0
    assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=Recorder())
    client_db.refresh(deliveries[1])
    assert deliveries[1].status == "accepted"


def test_revogacao_membership_apos_consulta_canal_impede_envio(client_db, graph, transports, monkeypatch):
    item = event(client_db, graph[0])
    evolution(monkeypatch, "A")
    configure_expected_phone(client_db, graph[0]["admin_phone"], tenant_id=graph[0]["tenant"].id)
    def revoke():
        with transports() as other:
            member = other.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == graph[0]["tenant"].id))
            member.active = False
            other.commit()
    adapter = Recorder(phone=graph[0]["admin_phone"], connection_hook=revoke)
    assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    client_db.refresh(item)
    assert adapter.calls == [] and item.status == "failed"
    assert client_db.scalar(select(TenantAdmin.active).where(TenantAdmin.tenant_id == graph[0]["tenant"].id)) is False


def test_OTP_owner_origem_resend_e_attempts_preservam_B(client_db, graph, links, transports):
    challenges = [challenge(client_db, token) for token, _ in links]
    old = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == str(challenges[0].id)))
    auth.resend_client_challenge(client_db, challenges[0].id, "synthetic-ip", tenant_id=graph[0]["tenant"].id)
    client_db.refresh(old)
    assert old.status == "expired"
    adapter = Recorder()
    assert worker.process_next_whatsapp_delivery(adapter=adapter)
    assert worker.process_next_whatsapp_delivery(adapter=adapter)
    assert len(adapter.calls) == 2 and all(call[0] == "+5511999990001" for call in adapter.calls)
    attempts = list(client_db.scalars(select(WhatsAppDeliveryAttempt)))
    assert {row.tenant_id for row in attempts} == {row["tenant"].id for row in graph}
    assert all(row.result == "accepted" for row in attempts)
    assert client_db.scalar(select(func.count()).select_from(WhatsAppDelivery).where(WhatsAppDelivery.status == "accepted")) == 2


def test_canal_delivery_api_e_retry_estrangeiro_neutro(client_db, graph, links, transports):
    for row in graph:
        challenge(client_db, next(token for token, cap in links if cap.tenant_id == row["tenant"].id))
    admin_request = request(cookie(client_db, graph[0], auth.Role.ADMIN))
    result = main.admin_whatsapp_deliveries(admin_request, None, client_db)
    own = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == graph[0]["tenant"].id))
    other = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.tenant_id == graph[1]["tenant"].id))
    assert [item["id"] for item in result] == [str(own.id)]
    with pytest.raises(HTTPException) as exc:
        main.retry_admin_whatsapp_delivery(other.id, main.WhatsAppRetryInput(confirm_duplicate_risk=True), admin_request, client_db)
    assert exc.value.status_code == 404
    payload = main.admin_whatsapp_channel(admin_request, client_db)
    assert payload["deliveries"] == {"queued": 1} and "API_KEY" not in str(payload)
    assert client_db.scalar(select(func.count()).select_from(WhatsAppChannelSettings)) == 1


def test_webhook_instance_segredo_recibo_e_id_externo_contextual(client_db, graph, transports, monkeypatch):
    for index, row in enumerate(graph):
        evolution(monkeypatch, chr(65+index))
        client_db.add(WhatsAppDelivery(tenant_id=row["tenant"].id, kind="payment", source_type="payment_notification_outbox",
            source_id="synthetic", template_kind="confirmed", idempotency_key="same-key", external_message_id="same-external", status="accepted"))
    client_db.commit()
    payload = {"instance": "synthetic-A", "event": "MESSAGES_UPDATE", "data": {"key": {"id": "same-external"}, "status": "read"}}
    with pytest.raises(HTTPException):
        webhook_owner(client_db, payload, "synthetic-webhook-B")
    owner = webhook_owner(client_db, payload, "synthetic-webhook-A")
    assert owner == graph[0]["tenant"].id
    assert process_whatsapp_webhook(client_db, payload, tenant_id=owner) == (True, "delivery_updated")
    assert process_whatsapp_webhook(client_db, payload, tenant_id=owner) == (False, "duplicate")
    rows = list(client_db.scalars(select(WhatsAppDelivery).order_by(WhatsAppDelivery.created_at)))
    assert [row.status for row in rows] == ["read", "accepted"]
    # Processador interno também contextualiza fingerprint; fronteira HTTP prova instância/secret.
    assert process_whatsapp_webhook(client_db, payload, tenant_id=graph[1]["tenant"].id) == (True, "delivery_updated")
    assert client_db.scalar(select(func.count()).select_from(WhatsAppWebhookReceipt)) == 2


@pytest.mark.parametrize("collision", ["alias", "instance", "secret", "environment"])
def test_binding_ambiguo_ou_ambiente_incorreto_recusado(client_db, graph, transports, monkeypatch, collision):
    evolution(monkeypatch, "A")
    evolution(monkeypatch, "B")
    if collision == "alias":
        monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(row["tenant"].id): "A" for row in graph}))
    else:
        key, value = {"instance": ("INSTANCE", "synthetic-A"), "secret": ("WEBHOOK_SECRET", "synthetic-webhook-A"),
            "environment": ("CREDENTIAL_ENV", "production")}[collision]
        monkeypatch.setenv(f"WHATSAPP_BINDING_B_{key}", value)
    owner = graph[1]["tenant"].id if collision == "environment" else graph[0]["tenant"].id
    with pytest.raises(WhatsAppConfigurationError):
        provider_for(client_db, tenant_id=owner, adapter=Recorder())
    if collision == "environment":
        assert resolve_binding(client_db, graph[0]["tenant"].id).name == "evolution"


def test_push_mesmo_endpoint_A_B_revalidacao_sessao_e_revogacao(client_db, graph, transports, monkeypatch):
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    from app.push_subscriptions import revoke_installation, subscribe
    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSH_SUBSCRIPTION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    payload = {"endpoint": "https://fcm.googleapis.com/fcm/send/synthetic", "keys": {"p256dh": encode(key), "auth": encode(b"a" * 16)}}
    sessions, subscriptions = [], []
    for row in graph:
        raw = cookie(client_db, row, auth.Role.ADMIN)
        session = auth.current_session(request(raw), auth.Role.ADMIN)
        sessions.append(session)
        subscriptions.append(subscribe(client_db, session, "same-synthetic-installation", payload))
    client_db.commit()
    deliveries = [event(client_db, row) for row in graph]
    assert subscriptions[0].id != subscriptions[1].id and subscriptions[0].active
    own_session = client_db.get(auth.AuthSession, sessions[0].id)
    own_session.revoked_at = now()
    client_db.commit()
    calls = []
    sender = lambda data, message, **kwargs: calls.append(message)
    assert notification_delivery.process_next_notification("push", push_sender=sender)
    assert calls == []
    assert notification_delivery.process_next_notification("push", push_sender=sender)
    assert len(calls) == 1 and str(graph[1]["event"].id) != calls[0]["id"]
    client_db.refresh(subscriptions[1])
    before = (subscriptions[1].active, subscriptions[1].generation)
    with pytest.raises(HTTPException):
        revoke_installation(client_db, "same-synthetic-installation", sessions[0])
    client_db.refresh(subscriptions[1])
    assert (subscriptions[1].active, subscriptions[1].generation) == before
    assert len(deliveries) == 2


def test_aviso_facial_envelope_sintetico_A_B_criptografia_preservada(client_db, graph, transports, tmp_path, monkeypatch):
    from app.auth import FacialSearchRequest, GalleryFacialPolicy
    from app.facial.crypto import FacialCipher
    from app.facial.notifications import (
        enqueue_search_notification,
        process_next_search_notification,
    )
    from tests.test_facial_search_worker import _settings
    monkeypatch.setenv("PUBLIC_APP_ORIGIN", "http://localhost:3000")
    settings = _settings(tmp_path)
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    notices = []
    for row in graph:
        policy = GalleryFacialPolicy(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            model_version="model-v1", quality_version="quality-v1")
        client_db.add(policy)
        client_db.flush()
        source = FacialSearchRequest(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            client_id=row["client"].id, policy_id=policy.id, status="ready", subject_declaration="adult",
            consent_version="consent-v1", legal_notice_version="notice-v1", model_version="model-v1", quality_version="quality-v1",
            index_generation=1, expires_at=now()+timedelta(hours=1))
        client_db.add(source)
        client_db.flush()
        notice = enqueue_search_notification(client_db, request=source, result_status="ready", cipher=cipher, settings=settings)
        assert notice.tenant_id == row["tenant"].id and b"public-galleries" not in notice.payload_ciphertext
        notices.append(notice)
    client_db.commit()
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    adapter = Recorder()
    assert process_next_search_notification(client_db, provider=adapter, cipher=cipher, settings=settings)
    assert len(adapter.calls) == 1 and str(graph[1]["parent"].id) in adapter.calls[0][1]
    assert str(graph[0]["parent"].id) not in adapter.calls[0][1]
    client_db.refresh(notices[0])
    client_db.refresh(notices[1])
    assert notices[0].status == "queued" and notices[0].attempts == 0 and notices[0].payload_ciphertext
    assert notices[1].status == "sent" and not notices[1].payload_ciphertext


def test_canal_removido_antes_resend_preserva_hash_e_entrega(client_db, graph, links, transports, monkeypatch):
    row = challenge(client_db, links[1][0])
    before = row.secret_hash, row.resend_count, row.used_at
    delivery = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == str(row.id)))
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(graph[0]["tenant"].id): "A"}))
    with pytest.raises(HTTPException) as exc:
        auth.resend_client_challenge(client_db, row.id, "synthetic-ip", tenant_id=row.tenant_id)
    assert exc.value.status_code == 503
    client_db.refresh(row)
    client_db.refresh(delivery)
    assert (row.secret_hash, row.resend_count, row.used_at) == before
    assert delivery.status == "queued" and delivery.encrypted_payload


def test_provider_contextual_A_nao_pode_enviar_B(client_db, graph, transports):
    adapter = Recorder()
    owned = provider_for(client_db, tenant_id=graph[0]["tenant"].id, adapter=adapter)
    with pytest.raises(WhatsAppConfigurationError):
        provider_for(client_db, tenant_id=graph[1]["tenant"].id, adapter=owned)
    assert adapter.calls == []


def test_compatibilidade_canal_legado_exige_unica_conta_ativa(client_db, monkeypatch):
    row = Tenant()
    client_db.add(row)
    client_db.commit()
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", "{}")
    monkeypatch.setenv("WHATSAPP_PROVIDER", "sandbox")
    monkeypatch.setenv("WHATSAPP_PHOTOGRAPHER_PHONE_E164", "+5511888880010")
    assert photographer_phone(client_db, tenant_id=row.id) == "+5511888880010"
    second = Tenant()
    client_db.add(second)
    client_db.commit()
    with pytest.raises(WhatsAppConfigurationError):
        resolve_binding(client_db, row.id)


def test_pagamento_de_grupo_envia_somente_admin_proprio(client_db, commerce, transports):
    for row in commerce:
        reported(client_db, row)
    adapter = Recorder()
    for _ in range(4):
        assert notification_delivery.process_next_notification("whatsapp", whatsapp_provider=adapter)
    assert len(adapter.calls) == 4
    for row in commerce:
        own = [call for call in adapter.calls if str(row["tenant"].id) in call[2]]
        assert len(own) == 2 and all(call[0] == row["admin_phone"] for call in own)
        assert sum("informou pagamento" in call[1] for call in own) == 1


def test_membership_reabertura_queue_suspensa_e_APIs_proprias(client_db, graph, transports, monkeypatch):
    from app.auth import (
        GalleryMembershipNotificationOutbox,
        GalleryReopeningNotificationOutbox,
        GalleryReopeningRequest,
    )
    from app.membership_notifications import enqueue_membership_notification
    monkeypatch.setenv("GALLERY_NOTIFICATION_EXTERNAL_ENABLED", "true")
    for row in graph:
        enqueue_membership_notification(client_db, event_key="same-membership", event_type="member_joined",
            parent=row["parent"], gallery=row["gallery"], client=row["client"])
        reopening = GalleryReopeningRequest(tenant_id=row["tenant"].id, derived_gallery_id=row["gallery"].id,
            requested_by_client_id=row["client"].id, idempotency_key="same-reopening")
        client_db.add(reopening)
        client_db.flush()
        client_db.add(GalleryReopeningNotificationOutbox(tenant_id=row["tenant"].id,
            gallery_reopening_request_id=reopening.id, recipient_phone=row["admin_phone"], status="queued"))
    client_db.commit()
    admin_request = request(cookie(client_db, graph[0], auth.Role.ADMIN))
    payload = main.admin_gallery_membership_notifications(admin_request, None, None, 50, client_db)
    assert len(payload["notifications"]) == 1 and payload["notifications"][0]["client_name"] == graph[0]["client"].full_name
    other = client_db.scalar(select(GalleryMembershipNotificationOutbox).where(
        GalleryMembershipNotificationOutbox.tenant_id == graph[1]["tenant"].id))
    with pytest.raises(HTTPException) as exc:
        main.read_admin_gallery_membership_notification(other.id, admin_request, client_db)
    assert exc.value.status_code == 404
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    adapter = Recorder()
    assert worker.process_next_gallery_membership_notification(adapter=adapter)
    assert worker.process_next_gallery_reopening_notification(adapter=adapter)
    assert len(adapter.calls) == 2 and all(call[0] == graph[1]["admin_phone"] for call in adapter.calls)
    assert client_db.scalar(select(GalleryMembershipNotificationOutbox.external_status).where(
        GalleryMembershipNotificationOutbox.tenant_id == graph[0]["tenant"].id)) == "queued"
    assert client_db.scalar(select(GalleryReopeningNotificationOutbox.status).where(
        GalleryReopeningNotificationOutbox.tenant_id == graph[0]["tenant"].id)) == "queued"


def test_OTP_source_estrangeira_recusada_antes_decrypt_sem_consumir_B(client_db, graph, links, transports):
    sources = [challenge(client_db, token) for token, _ in links]
    first = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == str(sources[0].id)))
    second = client_db.scalar(select(WhatsAppDelivery).where(WhatsAppDelivery.source_id == str(sources[1].id)))
    first.source_id = str(sources[1].id)
    client_db.commit()
    adapter = Recorder()
    assert worker.process_next_whatsapp_delivery(adapter=adapter)
    client_db.refresh(first)
    client_db.refresh(second)
    assert adapter.calls == [] and first.status == "failed" and second.attempts == 0
    assert second.encrypted_payload and second.status == "queued"
    assert worker.process_next_whatsapp_delivery(adapter=adapter)
    assert len(adapter.calls) == 1 and str(graph[1]["tenant"].id) in adapter.calls[0][2]


def test_SMTP_tecnico_sujeito_A_B_e_endereco_alterado_recusado(client_db, graph, transports):
    from app.admin_security import issue_admin_action_token
    from app.email_delivery import EmailDeliveryResult, enqueue_email
    deliveries = []
    for row in graph:
        token, _ = issue_admin_action_token(client_db, admin_id=row["admin"].id, purpose="password_reset")
        item = enqueue_email(client_db, kind="password_recovery", source_type="admin_action_token", source_id=str(token.id),
            recipient=row["admin"].email, subject="Sintético", text_body="Sem link real",
            idempotency_key=f"synthetic-mail:{token.id}", expires_at=token.expires_at)
        deliveries.append(item)
    client_db.commit()
    own_request = request(cookie(client_db, graph[0], auth.Role.ADMIN))
    assert main.admin_email_channel(own_request, client_db)["deliveries"] == {"queued": 1}
    graph[0]["admin"].email = "changed@example.test"
    client_db.commit()
    calls = []
    class Sender:
        def send(self, **kwargs):
            calls.append(kwargs)
            return EmailDeliveryResult("synthetic-only")
    assert worker.process_next_email_delivery(provider=Sender())
    assert calls == []
    assert worker.process_next_email_delivery(provider=Sender())
    assert len(calls) == 1 and calls[0]["recipient"] == graph[1]["admin"].email
    client_db.refresh(deliveries[0])
    client_db.refresh(deliveries[1])
    assert deliveries[0].status == "failed" and deliveries[1].status == "accepted"
    assert deliveries[0].encrypted_payload is None and deliveries[1].encrypted_payload is None


def test_PIX_canal_removido_nao_invalida_desafio_anterior(client_db, graph, transports, monkeypatch):
    from app import admin_account
    row = graph[0]
    source, _, queued = admin_account.create_security_challenge(client_db, purpose="change_pix_otp",
        subject_fingerprint="synthetic", admin=row["admin"], tenant_id=row["tenant"].id)
    assert queued
    before = source.secret_hash, source.resend_count, source.used_at
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(graph[1]["tenant"].id): "B"}))
    with pytest.raises(WhatsAppConfigurationError):
        admin_account.create_security_challenge(client_db, purpose="change_pix_otp", subject_fingerprint="synthetic",
            admin=row["admin"], tenant_id=row["tenant"].id)
    with pytest.raises(WhatsAppConfigurationError):
        admin_account.resend_security_challenge(client_db, challenge_id=source.id,
            purpose="change_pix_otp", tenant_id=row["tenant"].id)
    client_db.refresh(source)
    assert (source.secret_hash, source.resend_count, source.used_at) == before


@pytest.mark.parametrize("role", [auth.Role.CLIENT, auth.Role.ADMIN])
def test_logout_com_push_revoga_A_e_preserva_B(client_db, graph, transports, monkeypatch, role):
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from fastapi import Response
    from starlette.requests import Request

    from app.push_subscriptions import INSTALLATION_COOKIE, fingerprint, subscribe

    monkeypatch.setenv("WEB_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSH_SUBSCRIPTION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    payload = {"endpoint": "https://fcm.googleapis.com/fcm/send/logout-synthetic",
               "keys": {"p256dh": encode(key), "auth": encode(b"a" * 16)}}
    sessions, subscriptions, cookies = [], [], []
    installation = "synthetic-logout-installation"
    for row in graph:
        raw = cookie(client_db, row, role)
        session = auth.current_session(request(raw), role)
        cookies.append(raw)
        sessions.append(session)
        subscriptions.append(subscribe(client_db, session, fingerprint(installation), payload))
    client_db.commit()
    logout_request = Request({"type": "http", "method": "POST", "path": "/auth/logout",
        "headers": [(b"cookie", f"markina_session={cookies[0]}; {INSTALLATION_COOKIE}={installation}".encode())],
        "client": ("127.0.0.1", 1234)})
    response = main.logout(logout_request, Response())
    assert response.status_code == 204
    client_db.expire_all()
    assert client_db.get(auth.AuthSession, sessions[0].id).revoked_at is not None
    assert client_db.get(auth.AuthSession, sessions[1].id).revoked_at is None
    assert not client_db.get(auth.PushSubscription, subscriptions[0].id).active
    assert client_db.get(auth.PushSubscription, subscriptions[1].id).active
    assert auth.current_session(request(cookies[1]), role).id == sessions[1].id
    with pytest.raises(HTTPException) as exc:
        auth.current_session(request(cookies[0]), role)
    assert exc.value.status_code == 403
