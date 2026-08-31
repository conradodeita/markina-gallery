"""Emissão e resolução de capacidades opacas de acesso a galerias."""

from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import GalleryAccessCapability, expired, now


def capability_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def issue_gallery_capability(
    db: Session,
    *,
    parent_gallery_id: UUID,
    scope: str,
    client_id: UUID | None = None,
    derived_gallery_id: UUID | None = None,
    expires_at=None,
    actor_admin_id: UUID | None = None,
    rotated_from_id: UUID | None = None,
) -> tuple[GalleryAccessCapability, str]:
    """Retorna o segredo somente na emissão e persiste exclusivamente seu hash."""

    token = token_urlsafe(32)
    capability = GalleryAccessCapability(
        parent_gallery_id=parent_gallery_id,
        derived_gallery_id=derived_gallery_id,
        client_id=client_id,
        scope=scope,
        token_hash=capability_hash(token),
        status="active",
        expires_at=expires_at,
        actor_admin_id=actor_admin_id,
        rotated_from_id=rotated_from_id,
    )
    db.add(capability)
    db.flush()
    return capability, token


def resolve_gallery_capability(
    db: Session, token: str
) -> GalleryAccessCapability | None:
    capability = db.scalar(
        select(GalleryAccessCapability).where(
            GalleryAccessCapability.token_hash == capability_hash(token)
        )
    )
    if not capability or capability.status != "active":
        return None
    if capability.expires_at and expired(capability.expires_at):
        capability.status = "expired"
        return None
    capability.last_used_at = now()
    return capability


def revoke_gallery_capability(capability: GalleryAccessCapability) -> None:
    if capability.status == "active":
        capability.status = "revoked"
        capability.revoked_at = now()


def consume_gallery_capability(capability: GalleryAccessCapability) -> None:
    """Consome convites individuais somente depois da validação OTP completa."""

    if capability.scope == "public_gallery":
        return
    if capability.status != "active":
        raise ValueError("Somente um convite ativo pode ser consumido.")
    capability.status = "consumed"
    capability.consumed_at = now()


def rotate_gallery_capability(
    db: Session, capability: GalleryAccessCapability, *, actor_admin_id: UUID | None = None
) -> tuple[GalleryAccessCapability, str]:
    if capability.status != "active":
        raise ValueError("Somente uma capacidade ativa pode ser rotacionada.")
    capability.status = "rotated"
    capability.revoked_at = now()
    db.flush()
    return issue_gallery_capability(
        db,
        parent_gallery_id=capability.parent_gallery_id,
        derived_gallery_id=capability.derived_gallery_id,
        client_id=capability.client_id,
        scope=capability.scope,
        expires_at=capability.expires_at,
        actor_admin_id=actor_admin_id,
        rotated_from_id=capability.id,
    )
