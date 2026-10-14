"""Identidade própria da conta; telefone igual não vincula clientes de fotógrafos distintos."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Client, ClientPhone, Tenant, now


class ClientIdentityConflict(ValueError):
    """Indica que o telefone já identifica outra cliente ou que há legado incoerente."""


def require_identity_tenant(db: Session, tenant_id: UUID) -> None:
    tenant = db.get(Tenant, tenant_id, populate_existing=True) if tenant_id else None
    if tenant is None or tenant.status != "active":
        raise ClientIdentityConflict("Contexto de cliente indisponível.")


def require_client_owner(db: Session, client: Client, tenant_id: UUID) -> None:
    require_identity_tenant(db, tenant_id)
    if client.tenant_id != tenant_id:
        raise ClientIdentityConflict("Cliente indisponível neste contexto.")


def resolve_client_by_phone(db: Session, phone_e164: str, *, tenant_id: UUID) -> Client | None:
    """Prioriza telefone ativo verificado e usa o canônico apenas como compatibilidade."""

    require_identity_tenant(db, tenant_id)
    verified_phone = db.scalar(
        select(ClientPhone).where(
            ClientPhone.tenant_id == tenant_id,
            ClientPhone.phone_e164 == phone_e164,
            ClientPhone.active,
            ClientPhone.verified_at.is_not(None),
        )
    )
    canonical = db.scalar(select(Client).where(Client.tenant_id == tenant_id, Client.phone_e164 == phone_e164))
    if verified_phone and canonical and verified_phone.client_id != canonical.id:
        raise ClientIdentityConflict(
            "Telefone verificado e telefone canônico apontam para clientes diferentes."
        )
    if verified_phone:
        return db.scalar(select(Client).where(Client.id == verified_phone.client_id, Client.tenant_id == tenant_id))
    return canonical


def assert_phone_available(
    db: Session, phone_e164: str, *, tenant_id: UUID, client_id=None
) -> ClientPhone | None:
    """Reserva ativa, mesmo ainda não verificada, não pode pertencer a outra cliente."""

    require_identity_tenant(db, tenant_id)
    if client_id is not None and not db.scalar(select(Client.id).where(Client.id == client_id, Client.tenant_id == tenant_id)):
        raise ClientIdentityConflict("Cliente indisponível neste contexto.")
    canonical = db.scalar(select(Client).where(Client.tenant_id == tenant_id, Client.phone_e164 == phone_e164))
    if canonical and canonical.id != client_id:
        raise ClientIdentityConflict("Este WhatsApp já pertence a outra cliente.")
    active_phone = db.scalar(
        select(ClientPhone).where(
            ClientPhone.tenant_id == tenant_id,
            ClientPhone.phone_e164 == phone_e164,
            ClientPhone.active,
        )
    )
    if active_phone and active_phone.client_id != client_id:
        raise ClientIdentityConflict("Este WhatsApp já pertence a outra cliente.")
    return active_phone


def verify_canonical_phone(
    db: Session, client: Client, phone_e164: str, *, tenant_id: UUID
) -> ClientPhone:
    """Materializa a prova OTP sem trocar silenciosamente a identidade canônica."""

    require_client_owner(db, client, tenant_id)
    if client.phone_e164 != phone_e164:
        raise ClientIdentityConflict("O telefone comprovado diverge do cadastro canônico.")
    active_phone = assert_phone_available(db, phone_e164, tenant_id=tenant_id, client_id=client.id)
    other_active = db.scalar(
        select(ClientPhone).where(
            ClientPhone.tenant_id == tenant_id,
            ClientPhone.client_id == client.id,
            ClientPhone.active,
            ClientPhone.phone_e164 != phone_e164,
        )
    )
    if other_active:
        raise ClientIdentityConflict(
            "A cliente possui outro telefone ativo; reconciliação administrativa necessária."
        )
    if not active_phone:
        active_phone = ClientPhone(
            tenant_id=tenant_id,
            client_id=client.id,
            phone_e164=phone_e164,
            active=True,
        )
        db.add(active_phone)
    active_phone.verified_at = active_phone.verified_at or now()
    return active_phone


def change_verified_phone(
    db: Session, client: Client, phone_e164: str, *, tenant_id: UUID
) -> ClientPhone:
    """Troca o telefone em uma transação, aposentando a identidade anterior."""

    require_client_owner(db, client, tenant_id)
    target = assert_phone_available(db, phone_e164, tenant_id=tenant_id, client_id=client.id)
    timestamp = now()
    previous_phone = client.phone_e164
    previous_record = db.scalar(
        select(ClientPhone).where(
            ClientPhone.tenant_id == tenant_id,
            ClientPhone.client_id == client.id,
            ClientPhone.phone_e164 == previous_phone,
        )
    )
    if previous_phone != phone_e164 and not previous_record:
        db.add(
            ClientPhone(
                tenant_id=tenant_id,
                client_id=client.id,
                phone_e164=previous_phone,
                active=False,
                retired_at=timestamp,
            )
        )
    for current in db.scalars(
        select(ClientPhone).where(
            ClientPhone.tenant_id == tenant_id,
            ClientPhone.client_id == client.id,
            ClientPhone.active,
            ClientPhone.phone_e164 != phone_e164,
        )
    ):
        current.active = False
        current.retired_at = timestamp
    db.flush()
    if not target:
        target = ClientPhone(
            tenant_id=tenant_id,
            client_id=client.id,
            phone_e164=phone_e164,
            active=True,
        )
        db.add(target)
    target.active = True
    target.verified_at = target.verified_at or timestamp
    target.retired_at = None
    client.phone_e164 = phone_e164
    return target
