"""Autorização de Galeria pública decidida integralmente no backend."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    GalleryAccessCapability,
    ParentGallery,
    ParentGalleryRegistration,
    expired,
)
from app.parent_registration import link_client_to_parent


class PublicGalleryAccessDenied(RuntimeError):
    """A identidade não possui autoridade suficiente para a origem."""


@dataclass
class PublicGalleryAccessResult:
    parent: ParentGallery
    state: str
    destination: str
    registration: ParentGalleryRegistration | None


def safe_internal_return(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return fallback
    return value[:512]


def active_capability_by_id(
    db: Session, capability_id: UUID | None
) -> GalleryAccessCapability | None:
    capability = db.get(GalleryAccessCapability, capability_id) if capability_id else None
    if not capability or capability.status != "active":
        return None
    if capability.expires_at and expired(capability.expires_at):
        capability.status = "expired"
        return None
    return db.scalar(
        select(GalleryAccessCapability)
        .where(GalleryAccessCapability.id == capability.id)
        .with_for_update()
    )


def active_registration(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID
) -> ParentGalleryRegistration | None:
    return db.scalar(
        select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
            ParentGalleryRegistration.status == "active",
        )
    )


def apply_public_gallery_access(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    capability: GalleryAccessCapability | None = None,
    return_to: str | None = None,
) -> PublicGalleryAccessResult:
    parent = db.get(ParentGallery, parent_gallery_id)
    if not parent or not parent.active or parent.lifecycle_status != "active":
        raise PublicGalleryAccessDenied("A Galeria pública está indisponível.")
    registration = active_registration(
        db, parent_gallery_id=parent.id, client_id=client_id
    )
    capability_matches = bool(
        capability
        and capability.status == "active"
        and capability.parent_gallery_id == parent.id
        and (
            capability.scope == "public_gallery"
            or (
                capability.scope == "parent_invite"
                and capability.client_id == client_id
            )
        )
    )

    if parent.access_mode == "collective_protected":
        if capability_matches:
            registration = link_client_to_parent(
                db,
                parent_gallery_id=parent.id,
                client_id=client_id,
                status="pending",
            )
        return PublicGalleryAccessResult(
            parent=parent,
            state="pending_review",
            destination="/library?access=pending",
            registration=registration,
        )
    if (parent.access_mode == "standard" and capability_matches) or (
        parent.access_mode == "invite_only"
        and capability_matches
        and capability
        and capability.scope == "parent_invite"
    ):
        registration = link_client_to_parent(
            db,
            parent_gallery_id=parent.id,
            client_id=client_id,
            status="active",
        )
    if not registration:
        raise PublicGalleryAccessDenied("Acesso não autorizado.")
    fallback = f"/public-galleries/{parent.id}"
    return PublicGalleryAccessResult(
        parent=parent,
        state="authorized",
        destination=safe_internal_return(return_to, fallback),
        registration=registration,
    )


def require_public_gallery_browsing(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID
) -> ParentGallery:
    result = apply_public_gallery_access(
        db,
        parent_gallery_id=parent_gallery_id,
        client_id=client_id,
    )
    if result.state != "authorized":
        raise PublicGalleryAccessDenied("A grade desta galeria não está disponível.")
    return result.parent
