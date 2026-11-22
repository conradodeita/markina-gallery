"""Configuração sensível por tenant; sem fallback de credenciais entre contas."""

import json
import os
import re
from uuid import UUID, uuid4

from sqlalchemy import select

from app.acervo_context import require_active_owner
from app.auth import MercadoPagoAccount, PaymentPreferences, audit
from app.checkout import CheckoutError
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope
from app.mercadopago_provider import OrdersProvider


def preferences(db, tenant_id):
    require_active_owner(db, tenant_id)
    return db.scalar(select(PaymentPreferences).where(
        PaymentPreferences.tenant_id == tenant_id).execution_options(populate_existing=True))


def account_for(db, account_id, tenant_id):
    if not account_id:
        return None
    return db.scalar(select(MercadoPagoAccount).where(
        MercadoPagoAccount.id == account_id, MercadoPagoAccount.tenant_id == tenant_id
    ).execution_options(populate_existing=True))


def can_create(account):
    return bool(account and account.status == "active" and (
        account.test_account or os.getenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS") == "true"))


def test_customer_allowed(account, client_id):
    if not account.test_account:
        return True
    raw = os.getenv("MERCADOPAGO_TEST_CUSTOMERS", "").strip()
    if not raw:
        return os.getenv("APP_ENV", "development") in {"development", "test"}
    try:
        if len(raw) > 16384:
            return False
        entries = json.loads(raw)
        if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
            return False
        allowed = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"tenant_id", "client_id"}:
                return False
            allowed.add((UUID(entry["tenant_id"]), UUID(entry["client_id"])))
        return (account.tenant_id, client_id) in allowed
    except (ValueError, TypeError, AttributeError):
        return False


def effective_mercadopago(db, tenant_id, *, client_id=None):
    pref = preferences(db, tenant_id)
    account = account_for(db, pref.account_id, tenant_id) if pref else None
    if not pref or not pref.mercadopago_enabled or not can_create(account):
        return None
    if not test_customer_allowed(account, client_id):
        return None
    try:
        IntegrationCipher()
    except IntegrationSecretError:
        return None
    return account


def settings_payload(db, tenant_id):
    pref = preferences(db, tenant_id)
    account = account_for(db, pref.account_id, tenant_id) if pref else None
    return {
        "version": pref.version if pref else 0,
        "pix_enabled": pref.pix_enabled if pref else True,
        "mercadopago_enabled": pref.mercadopago_enabled if pref else False,
        "mercadopago_available": effective_mercadopago(db, tenant_id) is not None,
        "account": {
            "id": str(account.id), "seller_id": account.seller_id,
            "status": account.status, "test_account": account.test_account,
            "webhook_path": f"/api/mercadopago/webhooks/{account.id}",
        } if account else None,
    }


def credential_provider(account):
    cipher = IntegrationCipher()
    token = cipher.decrypt(SecretEnvelope.from_payload(account.access_token_envelope),
                           tenant_id=account.tenant_id, credential_id=account.id)
    return OrdersProvider(token)


def prepare_proposal(db, tenant_id, payload):
    pref = preferences(db, tenant_id)
    if payload.expected_version != (pref.version if pref else 0):
        raise CheckoutError("A configuração mudou. Recarregue e confira novamente.")
    supplied = [payload.access_token, payload.public_key, payload.webhook_secret]
    proposed_account = None
    if any(supplied):
        if not all(supplied):
            raise CheckoutError("Informe Access Token, Public Key e assinatura do webhook.")
        token = payload.access_token.get_secret_value().strip()
        public_key = payload.public_key.strip()
        signature = payload.webhook_secret.get_secret_value().strip()
        if not re.fullmatch(r"APP_USR-[A-Za-z0-9_-]{5,490}", token):
            raise CheckoutError("Use as credenciais Orders da aplicação do fotógrafo.")
        if not re.fullmatch(r"APP_USR-[A-Za-z0-9_-]{5,190}", public_key) or len(signature) < 16:
            raise CheckoutError("Confira a Public Key e a assinatura do webhook da aplicação.")
        identity = OrdersProvider(token).identity()
        seller_id = str(identity.get("id", ""))
        if identity.get("site_id") != "MLB" or not re.fullmatch(r"[0-9]{1,32}", seller_id):
            raise CheckoutError("A conta recebedora brasileira não pôde ser validada.")
        account_id = uuid4()
        cipher = IntegrationCipher()
        proposed_account = {
            "id": str(account_id), "seller_id": seller_id, "public_key": public_key,
            "test_account": "test_user" in identity.get("tags", []),
            "access_token_envelope": cipher.encrypt(
                token, tenant_id=tenant_id, credential_id=account_id).payload(),
            "webhook_secret_envelope": cipher.encrypt(
                signature, tenant_id=tenant_id, credential_id=account_id).payload(),
        }
        candidate = MercadoPagoAccount(tenant_id=tenant_id, status="active", **{
            **proposed_account, "id": account_id})
    else:
        candidate = account_for(db, pref.account_id, tenant_id) if pref else None
    if payload.mercadopago_enabled and not can_create(candidate):
        raise CheckoutError(
            "Configure uma conta de teste válida antes de habilitar Mercado Pago. "
            "Contas reais exigem liberação operacional do servidor.")
    return json.dumps({
        "version": payload.expected_version, "pix_enabled": payload.pix_enabled,
        "mercadopago_enabled": payload.mercadopago_enabled, "account": proposed_account,
        "account_id": str(pref.account_id) if pref and pref.account_id else None,
    }, sort_keys=True, separators=(",", ":"))


def apply_proposal(db, tenant_id, target):
    proposed = json.loads(target)
    pref = preferences(db, tenant_id)
    if proposed["version"] != (pref.version if pref else 0):
        raise CheckoutError("A configuração mudou. Solicite nova confirmação.")
    if not pref:
        pref = PaymentPreferences(tenant_id=tenant_id, version=0)
        db.add(pref)
    if proposed["account"]:
        values = proposed["account"]
        account = MercadoPagoAccount(
            tenant_id=tenant_id, **{**values, "id": UUID(values["id"])})
        db.add(account)
        db.flush()
        pref.account_id = account.id
    pref.pix_enabled = proposed["pix_enabled"]
    pref.mercadopago_enabled = proposed["mercadopago_enabled"]
    pref.version += 1
    db.flush()
    audit(db, "payment_providers.configured", str(pref.id), tenant_id=tenant_id)
    return settings_payload(db, tenant_id)
