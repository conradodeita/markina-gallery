"""Callbacks são candidatos; confirmação exige consulta autenticada ao provedor."""

from uuid import UUID

from sqlalchemy import select

from app.auth import ProviderPayment
from app.payment_provider import PaymentCheckRequest
from app.provider_confirmation import apply_payment_check


def verify_candidate(db, *, payment_id: UUID, transaction_nsu: str, slug: str,
                     redirect_url: str, provider_factory, skip_confirmed=False):
    payment = db.scalar(select(ProviderPayment).where(
        ProviderPayment.id == payment_id, ProviderPayment.provider == "infinitepay"))
    if payment is None:
        return "missing"
    if skip_confirmed and payment.state == "confirmed":
        return "verified"
    provider = provider_factory(tenant_id=payment.tenant_id, db=db,
                                credential_id=payment.credential_id, redirect_url=redirect_url)
    if provider is None:
        return "unavailable"
    try:
        result = provider.check_payment(PaymentCheckRequest(
            payment_id=payment.id, tenant_id=payment.tenant_id, handle=payment.handle_snapshot,
            transaction_nsu=transaction_nsu, slug=slug, expected_total_cents=payment.total_cents))
        apply_payment_check(db, payment.id, requested_slug=slug, result=result)
        db.commit()
        return result.outcome
    finally:
        close = getattr(provider, "close", None)
        if close:
            close()
