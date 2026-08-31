"""Identidade única de cliente a partir do telefone comprovado por OTP."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Client, ClientPhone, now


class ClientIdentityConflict(ValueError):
    """Indica que o telefone já identifica outra cliente ou que há legado incoerente."""


def resolve_client_by_phone(db: Session, phone_e164: str) -> Client | None:
    """Prioriza telefone ativo verificado e usa o canônico apenas como compatibilidade."""

    verified_phone = db.scalar(
        select(ClientPhone).where(
            ClientPhone.phone_e164 == phone_e164,
            ClientPhone.active,
            ClientPhone.verified_at.is_not(None),
        )
    )
    canonical = db.scalar(select(Client).where(Client.phone_e164 == phone_e164))
    if verified_phone and canonical and verified_phone.client_id != canonical.id:
        raise ClientIdentityConflict(
            "Telefone verificado e telefone canônico apontam para clientes diferentes."
        )
    return db.get(Client, verified_phone.client_id) if verified_phone else canonical


def assert_phone_available(
    db: Session, phone_e164: str, *, client_id=None
) -> ClientPhone | None:
    """Reserva ativa, mesmo ainda não verificada, não pode pertencer a outra cliente."""

    canonical = db.scalar(select(Client).where(Client.phone_e164 == phone_e164))
    if canonical and canonical.id != client_id:
        raise ClientIdentityConflict("Este WhatsApp já pertence a outra cliente.")
    active_phone = db.scalar(
        select(ClientPhone).where(
            ClientPhone.phone_e164 == phone_e164,
            ClientPhone.active,
        )
    )
    if active_phone and active_phone.client_id != client_id:
        raise ClientIdentityConflict("Este WhatsApp já pertence a outra cliente.")
    return active_phone


def verify_canonical_phone(
    db: Session, client: Client, phone_e164: str
) -> ClientPhone:
    """Materializa a prova OTP sem trocar silenciosamente a identidade canônica."""

    if client.phone_e164 != phone_e164:
        raise ClientIdentityConflict("O telefone comprovado diverge do cadastro canônico.")
    active_phone = assert_phone_available(db, phone_e164, client_id=client.id)
    other_active = db.scalar(
        select(ClientPhone).where(
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
            client_id=client.id,
            phone_e164=phone_e164,
            active=True,
        )
        db.add(active_phone)
    active_phone.verified_at = active_phone.verified_at or now()
    return active_phone


def change_verified_phone(
    db: Session, client: Client, phone_e164: str
) -> ClientPhone:
    """Troca o telefone em uma transação, aposentando a identidade anterior."""

    target = assert_phone_available(db, phone_e164, client_id=client.id)
    timestamp = now()
    for current in db.scalars(
        select(ClientPhone).where(
            ClientPhone.client_id == client.id,
            ClientPhone.active,
            ClientPhone.phone_e164 != phone_e164,
        )
    ):
        current.active = False
        current.retired_at = timestamp
    if not target:
        target = ClientPhone(
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
