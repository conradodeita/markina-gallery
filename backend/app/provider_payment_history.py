"""Read-only projection of retired provider-payment recovery history."""

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import AuditEvent, ProviderPaymentReceipt

RECOVERY_EVENT = "provider_payment.cart_reopened"
LEGACY_RECOVERY_PREFIX = "IP_RECOVERY_20261021_V1:"
RECONCILIATION_RECEIPT_STATES = frozenset({"queued", "processing", "verified"})


def _recovery_events(tenant_id: UUID, payment_ids: list[str]):
    return select(AuditEvent).where(
        AuditEvent.tenant_id == tenant_id,
        or_(
            and_(
                AuditEvent.event == RECOVERY_EVENT,
                func.substr(AuditEvent.subject, 1, 36).in_(payment_ids),
            ),
            and_(
                AuditEvent.event == "provider_payment.owner_recovery",
                AuditEvent.subject.startswith(LEGACY_RECOVERY_PREFIX),
                func.substr(
                    AuditEvent.subject,
                    len(LEGACY_RECOVERY_PREFIX) + 1,
                    36,
                ).in_(payment_ids),
            ),
        ),
    )


def cart_recovery_statuses(
    db: Session, *, tenant_id: UUID, payments,
) -> dict[UUID, dict[str, object]]:
    """Classify preserved audit and receipt records; never changes payment data."""
    owned = {
        payment.id: payment
        for payment in payments
        if payment.tenant_id == tenant_id
    }
    if not owned:
        return {}

    payment_id_strings = {str(identifier) for identifier in owned}
    recovered_at: dict[str, str] = {}
    recovery_times = {}
    for event in db.scalars(
        _recovery_events(tenant_id, list(payment_id_strings)).order_by(
            AuditEvent.created_at,
            AuditEvent.id,
        )
    ):
        parts = event.subject.split(":", 2)
        identifier = parts[0] if event.event == RECOVERY_EVENT else (
            parts[1] if len(parts) > 1 else ""
        )
        if identifier not in payment_id_strings:
            continue
        recovered_at[identifier] = event.created_at.isoformat()
        recovery_times[identifier] = event.created_at

    blocked: set[UUID] = set()
    late_receipts: set[UUID] = set()
    receipts = db.scalars(
        select(ProviderPaymentReceipt).where(
            ProviderPaymentReceipt.tenant_id == tenant_id,
            ProviderPaymentReceipt.payment_id.in_(owned),
        )
    )
    for receipt in receipts:
        if receipt.state in RECONCILIATION_RECEIPT_STATES:
            blocked.add(receipt.payment_id)
        recovery_time = recovery_times.get(str(receipt.payment_id))
        observed_at = receipt.processed_at or receipt.created_at
        # Persisted timestamps are UTC; synthetic SQLite rows may be naive.
        if recovery_time and observed_at.replace(tzinfo=None) >= recovery_time.replace(tzinfo=None):
            late_receipts.add(receipt.payment_id)

    statuses: dict[UUID, dict[str, object]] = {}
    for identifier, payment in owned.items():
        reopened_at = recovered_at.get(str(identifier))
        requires_reconciliation = bool(
            reopened_at
            and (
                identifier in blocked
                or identifier in late_receipts
                or payment.confirmed_at
                or payment.provider_transaction_nsu
                or payment.state != "exception"
            )
        )
        statuses[identifier] = {
            "reopened_at": reopened_at,
            "requires_reconciliation": requires_reconciliation,
            "historical_only": bool(
                reopened_at and payment.state == "exception" and not requires_reconciliation
            ),
        }
    return statuses
