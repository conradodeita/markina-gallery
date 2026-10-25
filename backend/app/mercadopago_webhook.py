"""Inbox Orders assinada e consumo durável, sem confiar em estados do callback."""

import hashlib
import hmac
import re
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.acervo_context import require_active_owner
from app.auth import (
    Client,
    MercadoPagoAccount,
    MercadoPagoPayment,
    MercadoPagoWebhook,
    SessionLocal,
    Tenant,
    now,
)
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope
from app.mercadopago_checkout import apply_order, lock_customer, own_payment, reconcile, utc
from app.mercadopago_provider import MercadoPagoError
from app.mercadopago_settings import account_for, credential_provider
from app.payment_availability import lock_payment_account
from app.tenancy import domain_session


def receive_notification(db, account_id, query, body, signature, request_id):
    account = db.scalar(select(MercadoPagoAccount).where(MercadoPagoAccount.id == account_id))
    if not account:
        raise HTTPException(status_code=401, detail="Notificação não autorizada.")
    require_active_owner(db, account.tenant_id)
    data_id = query.get("data.id", "")
    if (not re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", data_id)
            or not isinstance(body, dict) or body.get("type") != "order"
            or not isinstance(body.get("data"), dict)
            or body["data"].get("id") != data_id
            or ("user_id" in body and str(body["user_id"]) != account.seller_id)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", request_id)):
        raise HTTPException(status_code=401, detail="Notificação não autorizada.")
    try:
        values = {}
        for part in signature.split(","):
            key, value = part.strip().split("=", 1)
            if key in values:
                raise ValueError()
            values[key] = value
        ts, digest = values["ts"], values["v1"]
        if not re.fullmatch(r"[0-9]{1,20}", ts) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError()
        secret = IntegrationCipher().decrypt(
            SecretEnvelope.from_payload(account.webhook_secret_envelope),
            tenant_id=account.tenant_id, credential_id=account.id)
        manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{ts};"
        expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, digest):
            raise ValueError()
    except (ValueError, KeyError, IntegrationSecretError):
        raise HTTPException(status_code=401, detail="Notificação não autorizada.") from None
    identity = hashlib.sha256(f"{data_id}:{request_id}:{signature}".encode()).hexdigest()
    existing = db.scalar(select(MercadoPagoWebhook.id).where(
        MercadoPagoWebhook.tenant_id == account.tenant_id,
        MercadoPagoWebhook.account_id == account.id, MercadoPagoWebhook.digest == identity))
    if not existing:
        try:
            with db.begin_nested():
                db.add(MercadoPagoWebhook(
                    tenant_id=account.tenant_id, account_id=account.id,
                    provider_order_id=data_id, digest=identity))
                db.flush()
        except IntegrityError:
            if not db.scalar(select(MercadoPagoWebhook.id).where(
                MercadoPagoWebhook.tenant_id == account.tenant_id,
                MercadoPagoWebhook.account_id == account.id, MercadoPagoWebhook.digest == identity
            )):
                raise
    db.commit()
    return {"received": True}


def process_next_mercadopago_event(*, session_factory=SessionLocal):
    with domain_session(session_factory) as db:
        candidate = db.scalar(select(MercadoPagoWebhook).where(
            MercadoPagoWebhook.tenant_id.in_(select(Tenant.id).where(Tenant.status == "active")),
            MercadoPagoWebhook.state.in_(("queued", "processing")),
            MercadoPagoWebhook.next_attempt_at <= now(),
            or_(MercadoPagoWebhook.lease_until.is_(None), MercadoPagoWebhook.lease_until < now()),
        ).order_by(MercadoPagoWebhook.created_at).with_for_update(skip_locked=True).limit(1))
        if not candidate:
            return False
        require_active_owner(db, candidate.tenant_id)
        candidate.state = "processing"
        candidate.lease_until = now() + timedelta(seconds=90)
        candidate.attempts += 1
        event_id, owner, claim = candidate.id, candidate.tenant_id, candidate.attempts
        db.commit()
    with domain_session(session_factory) as db:
        lock_payment_account(db, owner)
        event = db.scalar(select(MercadoPagoWebhook).where(
            MercadoPagoWebhook.id == event_id, MercadoPagoWebhook.tenant_id == owner,
            MercadoPagoWebhook.state == "processing", MercadoPagoWebhook.attempts == claim,
        ).with_for_update())
        if not event:
            return True
        payment = db.scalar(select(MercadoPagoPayment).where(
            MercadoPagoPayment.tenant_id.in_(select(Tenant.id).where(Tenant.status == "active")),
            MercadoPagoPayment.tenant_id == owner, MercadoPagoPayment.account_id == event.account_id,
            MercadoPagoPayment.provider_order_id == event.provider_order_id))
        resource = None
        if not payment:
            try:
                event_account = account_for(db, event.account_id, owner)
                resource = credential_provider(event_account).get(event.provider_order_id)
                reference = UUID(resource.get("external_reference", ""))
                payment = db.scalar(select(MercadoPagoPayment).join(
                    MercadoPagoAccount, MercadoPagoAccount.id == MercadoPagoPayment.account_id).where(
                    MercadoPagoPayment.id == reference, MercadoPagoPayment.tenant_id == owner,
                    MercadoPagoAccount.tenant_id == owner,
                    MercadoPagoAccount.seller_id == event_account.seller_id))
            except (MercadoPagoError, IntegrationSecretError, ValueError, TypeError):
                _retry_event(event)
                db.commit()
                return True
        if not payment or not payment.sent_at:
            event.state, event.processed_at, event.lease_until = "ignored", now(), None
            db.commit()
            return True
        client = db.scalar(select(Client).where(
            Client.id == payment.client_id, Client.tenant_id == owner))
        lock_customer(db, client)
        payment = own_payment(db, payment.id, client, lock=True)
        if not payment.provider_order_id:
            payment.provider_order_id = event.provider_order_id
            db.flush()
        if resource is not None:
            apply_order(db, payment, resource)
        else:
            payment = reconcile(db, client, payment.id)
        event = db.scalar(select(MercadoPagoWebhook).where(
            MercadoPagoWebhook.id == event_id, MercadoPagoWebhook.tenant_id == owner,
            MercadoPagoWebhook.state == "processing", MercadoPagoWebhook.attempts == claim,
        ).with_for_update())
        if not event:
            db.rollback()
            return True
        if payment.error_category:
            _retry_event(event)
        else:
            event.state, event.processed_at, event.lease_until = "done", now(), None
        db.commit()
    return True


def _retry_event(event):
    event.state = "queued" if event.attempts < 12 else "failed"
    event.lease_until = None
    event.next_attempt_at = now() + timedelta(seconds=min(3600, 15 * 2 ** min(event.attempts, 8)))


def reconcile_next_mercadopago_payment(*, session_factory=SessionLocal):
    with domain_session(session_factory) as db:
        payment = db.scalar(select(MercadoPagoPayment).where(
            MercadoPagoPayment.tenant_id.in_(select(Tenant.id).where(Tenant.status == "active")),
            MercadoPagoPayment.sent_at.is_not(None),
            MercadoPagoPayment.next_check_at <= now(),
        ).order_by(MercadoPagoPayment.next_check_at).limit(1))
        if not payment:
            return False
        client = db.scalar(select(Client).where(
            Client.id == payment.client_id, Client.tenant_id == payment.tenant_id))
        lock_customer(db, client)
        payment = own_payment(db, payment.id, client, lock=True)
        if utc(payment.next_check_at) > now():
            return False
        reconcile(db, client, payment.id)
        db.commit()
        return True
