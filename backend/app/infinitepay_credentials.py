"""Cofre InfinitePay por conta; nenhuma operação externa ou endpoint de leitura."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import require_active_owner
from app.auth import InfinitePayCredential, InfinitePaySettings, ProviderPayment, now
from app.integration_secrets import IntegrationCipher, IntegrationSecretError, SecretEnvelope


def credential_key(db: Session, *, tenant_id: UUID, credential_id: UUID) -> str:
    require_active_owner(db, tenant_id)
    row = db.scalar(select(InfinitePayCredential).where(
        InfinitePayCredential.id == credential_id, InfinitePayCredential.tenant_id == tenant_id,
    ).execution_options(populate_existing=True))
    if row is None or row.revoked_at is not None or row.ciphertext is None or row.nonce is None:
        raise IntegrationSecretError("Credencial InfinitePay indisponível.")
    return IntegrationCipher().decrypt(SecretEnvelope(row.environment, row.key_id, row.nonce, row.ciphertext),
                                       tenant_id=tenant_id, credential_id=row.id)


def current_key(db: Session, *, tenant_id: UUID) -> str | None:
    from app.infinitepay_binding import api_key_for_tenant

    require_active_owner(db, tenant_id)
    settings = db.scalar(select(InfinitePaySettings).where(InfinitePaySettings.tenant_id == tenant_id)
                         .execution_options(populate_existing=True))
    if settings and settings.credential_source == "managed":
        return (credential_key(db, tenant_id=tenant_id, credential_id=settings.credential_id)
                if settings.credential_id else None)
    return api_key_for_tenant(tenant_id)


def credential_status(db: Session, *, tenant_id: UUID) -> dict:
    from app.infinitepay_binding import InfinitePayBindingError

    require_active_owner(db, tenant_id)
    try:
        IntegrationCipher()
        storage_available = True
    except IntegrationSecretError:
        storage_available = False
    try:
        configured = current_key(db, tenant_id=tenant_id) is not None
        state = "stored" if configured else "absent"
    except (IntegrationSecretError, InfinitePayBindingError):
        configured, state = False, "unavailable"
    return {"api_key_configured": configured, "credential_status": state,
            "credential_validation": "unavailable", "credential_storage_available": storage_available}


def prepare_secret(value: str, *, tenant_id: UUID) -> dict:
    credential_id = uuid4()
    envelope = IntegrationCipher().encrypt(value, tenant_id=tenant_id, credential_id=credential_id)
    return {"id": str(credential_id), "envelope": envelope.payload()}


def install_secret(db: Session, *, tenant_id: UUID, proposal: dict) -> UUID:
    try:
        credential_id = UUID(proposal["id"])
        envelope = SecretEnvelope.from_payload(proposal["envelope"])
        # Autentica o escopo novamente no momento do commit, sem persistir plaintext.
        IntegrationCipher().decrypt(envelope, tenant_id=tenant_id, credential_id=credential_id)
    except (KeyError, TypeError, ValueError):
        raise IntegrationSecretError("Credencial InfinitePay indisponível.") from None
    if db.get(InfinitePayCredential, credential_id) is not None:
        raise IntegrationSecretError("Credencial InfinitePay indisponível.")
    db.add(InfinitePayCredential(id=credential_id, tenant_id=tenant_id, environment=envelope.environment,
        key_id=envelope.key_id, nonce=envelope.nonce, ciphertext=envelope.ciphertext))
    db.flush()
    return credential_id


def has_unresolved_payments(db: Session, tenant_id: UUID) -> bool:
    return db.scalar(select(ProviderPayment.id).where(ProviderPayment.tenant_id == tenant_id,
        ProviderPayment.state.not_in(("confirmed", "failed_before_issue"))).limit(1)) is not None


def erase_secrets(db: Session, *, tenant_id: UUID) -> None:
    require_active_owner(db, tenant_id)
    for row in db.scalars(select(InfinitePayCredential).where(
        InfinitePayCredential.tenant_id == tenant_id, InfinitePayCredential.revoked_at.is_(None),
    ).with_for_update()):
        row.ciphertext = row.nonce = None
        row.revoked_at = now()


def rotate_secrets(db: Session, *, tenant_id: UUID, apply: bool = False) -> dict:
    from app.payment_availability import lock_payment_account

    lock_payment_account(db, tenant_id)
    cipher = IntegrationCipher()
    rows = list(db.scalars(select(InfinitePayCredential).where(
        InfinitePayCredential.tenant_id == tenant_id, InfinitePayCredential.revoked_at.is_(None),
    ).with_for_update()))
    changed = 0
    for row in rows:
        envelope = SecretEnvelope(row.environment, row.key_id, row.nonce, row.ciphertext)
        rotated = cipher.rotate(envelope, tenant_id=tenant_id, credential_id=row.id)
        if row.key_id != cipher.active_key_id:
            changed += 1
            if apply:
                row.key_id, row.nonce, row.ciphertext = rotated.key_id, rotated.nonce, rotated.ciphertext
    return {"checked": len(rows), "requiring_rotation": changed, "applied": apply}
