"""Fronteiras HTTP do Checkout Transparente e configuração por conta."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_account import (
    AdminAccountError,
    active_admin_for_session,
    challenge_target,
    create_security_challenge,
    reauthenticate_admin,
    resend_security_challenge,
    verify_security_challenge,
)
from app.admin_security import AdminSecurityConfigurationError
from app.auth import (
    AdminSecurityChallenge,
    Role,
    audit,
    current_session,
    enforce_rate_limit,
    neutral_error,
    now,
    pii_fingerprint,
)
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationSecretError
from app.mercadopago_checkout import (
    active_payments,
    cancel_payment,
    own_payment,
    payment_payload,
    prepare_payment,
    reconcile,
    submit_payment,
)
from app.mercadopago_provider import MercadoPagoError
from app.mercadopago_settings import apply_proposal, prepare_proposal, settings_payload
from app.messaging import WhatsAppConfigurationError
from app.payment_availability import lock_payment_account


class SensitiveRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def bounded(request):
            parts, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 32768:
                    return JSONResponse({"detail": "Solicitação excede o limite."}, status_code=413)
                parts.append(chunk)
            request._body = b"".join(parts)
            response = await original(request)
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
            return response
        return bounded


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr
    expected_version: int = Field(ge=0)
    pix_enabled: bool
    mercadopago_enabled: bool
    access_token: SecretStr | None = None
    public_key: str | None = None
    webhook_secret: SecretStr | None = None


class ConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID


class PrepareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cart_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: UUID
    method: Literal["credit_card", "pix"]


class SubmitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr | None = None
    payment_method_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    identification_number: str = Field(pattern=r"^[0-9]{11}$")


class CreditPurchasePrepareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    package_id: UUID
    idempotency_key: str = Field(min_length=16, max_length=160)


class PayerAddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    zip_code: str = Field(min_length=8, max_length=9, pattern=r"^[0-9]{5}-?[0-9]{3}$")
    street_name: str = Field(min_length=2, max_length=120)
    street_number: str = Field(min_length=1, max_length=20)
    neighborhood: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    complement: str = Field(default="", max_length=80)

    @field_validator("street_number")
    @classmethod
    def normalize_street_number(cls, value: str) -> str:
        if value.upper() in {"SN", "S/N"}:
            return "S/N"
        if not value.isdigit():
            raise ValueError("Informe o número do endereço ou S/N.")
        return value

    @field_validator("state")
    @classmethod
    def brazilian_state_code(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
            "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
            "SP", "SE", "TO",
        }:
            raise ValueError("Informe uma UF brasileira válida.")
        return normalized


class CreditPurchaseSubmitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["credit_card", "pix"]
    token: SecretStr | None = None
    payment_method_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    identification_number: str = Field(pattern=r"^[0-9]{11}$")
    payer_address: PayerAddressInput


def register_mercadopago_routes(
    app, *, db_session, require_same_origin, commerce_client, admin_tenant_context,
):
    router = APIRouter(route_class=SensitiveRoute)

    def admin_context(request, db):
        session = current_session(request, Role.ADMIN)
        admin = active_admin_for_session(db, session)
        return session, admin

    def credit_buyer_context(request, db):
        session, admin = admin_context(request, db)
        tenant_id = admin_tenant_context(db, request)
        if tenant_id != session.tenant_id:
            raise HTTPException(status_code=403, detail="Acesso negado.")
        return session, admin, tenant_id

    def credit_purchase_action(request, db, operation, *, rate_limit: str | None = None):
        require_same_origin(request)
        session, admin, tenant_id = credit_buyer_context(request, db)
        if rate_limit:
            enforce_rate_limit(
                db, rate_limit, str(admin.id),
                request.client.host if request.client else "unknown",
            )
        from app.mercadopago_credit_purchases import credit_purchase_payload

        try:
            purchase = operation(session, admin, tenant_id)
            payload = credit_purchase_payload(db, purchase)
            db.commit()
            return payload
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from None

    @router.get("/admin/settings/payment-providers")
    def get_settings(request: Request, db: Annotated[Session, Depends(db_session)]):
        session, _admin = admin_context(request, db)
        return settings_payload(db, session.tenant_id)

    @router.post("/admin/settings/payment-providers/challenge", status_code=202)
    def settings_challenge(payload: SettingsInput, request: Request,
                           db: Annotated[Session, Depends(db_session)]):
        require_same_origin(request)
        session, admin = admin_context(request, db)
        enforce_rate_limit(db, "admin_payment_providers", str(admin.id),
                           request.client.host if request.client else "unknown")
        try:
            reauthenticate_admin(admin, payload.current_password.get_secret_value())
        except AdminAccountError:
            audit(db, "payment_providers.reauthentication_failed", str(admin.id),
                  tenant_id=session.tenant_id)
            db.commit()
            raise neutral_error() from None
        lock_payment_account(db, session.tenant_id)
        try:
            target = prepare_proposal(db, session.tenant_id, payload)
            challenge, _code, queued = create_security_challenge(
                db, purpose="change_payment_otp", admin=admin, session_id=session.id,
                subject_fingerprint=pii_fingerprint(str(admin.id)), target=target,
                tenant_id=session.tenant_id)
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except (IntegrationSecretError, MercadoPagoError, AdminSecurityConfigurationError,
                WhatsAppConfigurationError):
            db.rollback()
            raise HTTPException(status_code=503,
                                detail="Confirmação segura indisponível. Confira a configuração.") from None
        if not queued:
            challenge.used_at = now()
            challenge.encrypted_target = None
            db.commit()
            raise HTTPException(status_code=409, detail="Canal administrativo indisponível.")
        return {"challenge_id": str(challenge.id), "expires_at": challenge.expires_at.isoformat(),
                "message": "Código enviado ao WhatsApp administrativo."}

    @router.post("/admin/settings/payment-providers/confirm")
    def settings_confirm(payload: ConfirmInput, request: Request,
                         db: Annotated[Session, Depends(db_session)]):
        require_same_origin(request)
        session, admin = admin_context(request, db)
        lock_payment_account(db, session.tenant_id)
        stored = db.scalar(select(AdminSecurityChallenge).where(
            AdminSecurityChallenge.id == payload.challenge_id,
            AdminSecurityChallenge.tenant_id == session.tenant_id).with_for_update())
        if not stored or stored.admin_id != admin.id:
            raise neutral_error()
        try:
            challenge = verify_security_challenge(
                db, challenge_id=payload.challenge_id, purpose="change_payment_otp",
                code=payload.code, session_id=session.id, tenant_id=session.tenant_id)
            target = challenge_target(challenge)
            if challenge.target_fingerprint != pii_fingerprint(target.strip().casefold()):
                raise AdminAccountError("Proposta indisponível.")
            result = apply_proposal(db, session.tenant_id, target)
        except AdminAccountError:
            db.rollback()
            raise neutral_error() from None
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from None
        challenge.encrypted_target = None
        db.commit()
        return result

    @router.post("/admin/settings/payment-providers/resend")
    def settings_resend(payload: ResendInput, request: Request,
                        db: Annotated[Session, Depends(db_session)]):
        require_same_origin(request)
        session, admin = admin_context(request, db)
        lock_payment_account(db, session.tenant_id)
        challenge = db.scalar(select(AdminSecurityChallenge).where(
            AdminSecurityChallenge.id == payload.challenge_id,
            AdminSecurityChallenge.tenant_id == session.tenant_id).with_for_update())
        if not challenge or challenge.admin_id != admin.id:
            raise neutral_error()
        try:
            resend_security_challenge(
                db, challenge_id=payload.challenge_id, purpose="change_payment_otp",
                tenant_id=session.tenant_id, session_id=session.id)
        except (AdminAccountError, WhatsAppConfigurationError):
            raise neutral_error() from None
        return {"message": "Código reenviado."}

    def checkout_action(request, db, operation):
        require_same_origin(request)
        client = commerce_client(request, db)
        try:
            payment = operation(client)
            result = payment_payload(db, payment)
            db.commit()
            return result
        except CheckoutError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from None

    @router.get("/library/mercadopago/active")
    def active_checkout(request: Request, db: Annotated[Session, Depends(db_session)]):
        client = commerce_client(request, db)
        payments = active_payments(db, client)
        return {"payments": [payment_payload(db, payment) for payment in payments]}

    @router.post("/library/mercadopago/prepare")
    def prepare_checkout(payload: PrepareInput, request: Request,
                         db: Annotated[Session, Depends(db_session)]):
        require_same_origin(request)
        client = commerce_client(request, db)
        enforce_rate_limit(db, "mercadopago_prepare", str(client.id),
                           request.client.host if request.client else "unknown")
        return checkout_action(request, db, lambda client: prepare_payment(
            db, client, revision=payload.cart_revision, key=payload.idempotency_key,
            method=payload.method))

    @router.get("/library/mercadopago/{payment_id}")
    def get_checkout(payment_id: UUID, request: Request,
                     db: Annotated[Session, Depends(db_session)]):
        client = commerce_client(request, db)
        try:
            return payment_payload(db, own_payment(db, payment_id, client))
        except CheckoutError:
            raise HTTPException(status_code=404, detail="Compra indisponível.") from None

    @router.post("/library/mercadopago/{payment_id}/submit")
    def submit_checkout(payment_id: UUID, payload: SubmitInput, request: Request,
                        db: Annotated[Session, Depends(db_session)]):
        return checkout_action(request, db, lambda client: submit_payment(
            db, client, payment_id, payload))

    @router.post("/library/mercadopago/{payment_id}/reconcile")
    def reconcile_checkout(payment_id: UUID, request: Request,
                           db: Annotated[Session, Depends(db_session)]):
        return checkout_action(request, db, lambda client: reconcile(db, client, payment_id))

    @router.post("/library/mercadopago/{payment_id}/cancel")
    def cancel_checkout(payment_id: UUID, request: Request,
                        db: Annotated[Session, Depends(db_session)]):
        return checkout_action(request, db, lambda client: cancel_payment(db, client, payment_id))

    @router.get("/admin/credits/purchases")
    def credit_purchase_history(
        request: Request,
        db: Annotated[Session, Depends(db_session)],
        limit: int = Query(default=20, ge=1, le=100),
    ):
        from app.auth import TenantCreditWallet
        from app.mercadopago_credit_purchases import list_credit_purchases

        _session, _admin, tenant_id = credit_buyer_context(request, db)
        wallet = db.get(TenantCreditWallet, tenant_id)
        if not wallet or wallet.mode != "finite":
            raise HTTPException(status_code=403, detail="Histórico disponível para fotógrafos ativos.")
        return {"items": list_credit_purchases(db, tenant_id, limit=limit)}

    @router.get("/admin/credits/purchases/active")
    def active_credit_purchases(
        request: Request,
        db: Annotated[Session, Depends(db_session)],
    ):
        from app.auth import TenantCreditWallet
        from app.mercadopago_credit_purchases import active_credit_purchases as list_active

        _session, _admin, tenant_id = credit_buyer_context(request, db)
        wallet = db.get(TenantCreditWallet, tenant_id)
        if not wallet or wallet.mode != "finite":
            raise HTTPException(status_code=403, detail="Compras disponíveis para fotógrafos ativos.")
        return {"items": list_active(db, tenant_id)}

    @router.post("/admin/credits/purchases/prepare")
    def prepare_credit_purchase_route(
        payload: CreditPurchasePrepareInput,
        request: Request,
        db: Annotated[Session, Depends(db_session)],
    ):
        from app.mercadopago_credit_purchases import prepare_credit_purchase

        return credit_purchase_action(
            request, db,
            lambda session, _admin, tenant_id: prepare_credit_purchase(
                db,
                tenant_id=tenant_id,
                buyer_admin_id=session.subject_id,
                package_id=payload.package_id,
                idempotency_key=payload.idempotency_key,
            ),
            rate_limit="mercadopago_credit_prepare",
        )

    @router.get("/admin/credits/purchases/{purchase_id}")
    def get_credit_purchase(
        purchase_id: UUID,
        request: Request,
        db: Annotated[Session, Depends(db_session)],
    ):
        from app.mercadopago_credit_purchases import credit_purchase_payload, owned_credit_purchase

        _session, _admin, tenant_id = credit_buyer_context(request, db)
        try:
            return credit_purchase_payload(db, owned_credit_purchase(db, tenant_id, purchase_id))
        except CheckoutError:
            raise HTTPException(status_code=404, detail="Compra de créditos indisponível.") from None

    @router.post("/admin/credits/purchases/{purchase_id}/submit")
    def submit_credit_purchase_route(
        purchase_id: UUID,
        payload: CreditPurchaseSubmitInput,
        request: Request,
        db: Annotated[Session, Depends(db_session)],
    ):
        from app.mercadopago_credit_purchases import submit_credit_purchase

        return credit_purchase_action(
            request, db,
            lambda _session, _admin, tenant_id: submit_credit_purchase(
                db,
                tenant_id=tenant_id,
                purchase_id=purchase_id,
                method=payload.method,
                data=payload,
            ),
            rate_limit="mercadopago_credit_submit",
        )

    @router.post("/admin/credits/purchases/{purchase_id}/reconcile")
    def reconcile_credit_purchase_route(
        purchase_id: UUID,
        request: Request,
        db: Annotated[Session, Depends(db_session)],
    ):
        from app.mercadopago_credit_purchases import reconcile_credit_purchase

        return credit_purchase_action(
            request, db,
            lambda _session, _admin, tenant_id: reconcile_credit_purchase(db, tenant_id, purchase_id),
            rate_limit="mercadopago_credit_reconcile",
        )

    @router.post("/mercadopago/webhooks/{account_id}")
    async def webhook(account_id: UUID, request: Request,
                      db: Annotated[Session, Depends(db_session)]):
        from starlette.concurrency import run_in_threadpool

        from app.mercadopago_webhook import receive_notification
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Notificação inválida.") from None
        return await run_in_threadpool(
            receive_notification, db, account_id, request.query_params, body,
            request.headers.get("x-signature", ""), request.headers.get("x-request-id", ""))

    app.include_router(router)
