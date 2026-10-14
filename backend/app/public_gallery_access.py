"""Autorização de Galeria pública decidida integralmente no backend."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    FolderClientGrant,
    GalleryAccessCapability,
    GalleryClientState,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    expired,
)
from app.client_identity import ClientIdentityConflict, resolve_client_by_phone
from app.parent_registration import link_client_to_parent


class PublicGalleryAccessDenied(RuntimeError):
    """A identidade não possui autoridade suficiente para a origem."""


class CanonicalPhotoAccessDenied(RuntimeError):
    """A foto não pertence ao público efetivo desta cliente."""


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
        select(ParentGalleryRegistration).join(Client, Client.id == ParentGalleryRegistration.client_id).where(
            ParentGalleryRegistration.tenant_id == Client.tenant_id,
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
            ParentGalleryRegistration.status == "active",
        )
    )


def client_otp_delivery_allowed(
    db: Session,
    *,
    parent: ParentGallery | None,
    phone_e164: str,
    capability: GalleryAccessCapability | None,
) -> bool:
    """Check invite-only eligibility without creating membership or a session."""
    if not parent or parent.access_mode != "invite_only":
        return True
    if capability and (
        capability.tenant_id != parent.tenant_id
        or capability.parent_gallery_id != parent.id
        or capability.status != "active"
        or (capability.expires_at and expired(capability.expires_at))
    ):
        return False
    # Shared private links retain their own enrollment contract.
    if capability and capability.scope == "private_gallery_link":
        return True
    try:
        client = resolve_client_by_phone(db, phone_e164, tenant_id=parent.tenant_id)
    except ClientIdentityConflict:
        return False
    if not client:
        return False
    if capability:
        if capability.scope == "parent_invite":
            return capability.client_id == client.id
        if capability.scope in {"private_invite", "private_client_invite"}:
            gallery = db.scalar(select(DerivedGallery).where(
                DerivedGallery.id == capability.derived_gallery_id,
                DerivedGallery.tenant_id == parent.tenant_id,
                DerivedGallery.parent_gallery_id == parent.id,
                DerivedGallery.client_id == client.id,
                DerivedGallery.access_enabled.is_(True),
            ))
            return capability.client_id == client.id and gallery is not None
        if capability.scope != "public_gallery":
            return False
    try:
        require_public_gallery_browsing(db, parent_gallery_id=parent.id, client_id=client.id)
    except PublicGalleryAccessDenied:
        return False
    return True


def apply_public_gallery_access(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    capability: GalleryAccessCapability | None = None,
    return_to: str | None = None,
) -> PublicGalleryAccessResult:
    from app.acervo_context import owned_record

    client = db.get(Client, client_id)
    if not client:
        raise PublicGalleryAccessDenied("Acesso não autorizado.")
    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=client.tenant_id)
    if not parent or not parent.active or parent.lifecycle_status != "active":
        raise PublicGalleryAccessDenied("A Galeria pública está indisponível.")
    registration = active_registration(
        db, parent_gallery_id=parent.id, client_id=client_id
    )
    capability_matches = bool(
        capability
        and capability.tenant_id == parent.tenant_id
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
    blocked_state = db.scalar(select(GalleryClientState.id).where(
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
        GalleryClientState.status != "active",
    ))
    if blocked_state:
        raise PublicGalleryAccessDenied("Acesso não autorizado.")
    return result.parent


def authorized_canonical_photos(parent_gallery_id: UUID, client_id: UUID):
    """Consulta única de fotos liberadas no público efetivo da cliente."""

    owner = select(Client.tenant_id).join(Tenant, Tenant.id == Client.tenant_id).where(
        Client.id == client_id, Tenant.status == "active",
    ).scalar_subquery()
    own_parent = select(ParentGallery.id).where(
        ParentGallery.id == parent_gallery_id, ParentGallery.tenant_id == owner,
        ParentGallery.active.is_(True), ParentGallery.lifecycle_status == "active",
    ).exists()
    granted = (
        select(FolderClientGrant.id)
        .join(
            GalleryClientState,
            and_(
                GalleryClientState.parent_gallery_id == FolderClientGrant.parent_gallery_id,
                GalleryClientState.client_id == FolderClientGrant.client_id,
            ),
        )
        .where(
            FolderClientGrant.folder_id == PhotoFolder.id,
            FolderClientGrant.tenant_id == owner,
            GalleryClientState.tenant_id == owner,
            FolderClientGrant.parent_gallery_id == parent_gallery_id,
            FolderClientGrant.client_id == client_id,
            GalleryClientState.status == "active",
        )
        .exists()
    )
    blocked_state = select(GalleryClientState.id).where(
        GalleryClientState.tenant_id == owner,
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
        GalleryClientState.status != "active",
    ).exists()
    return (
        select(PhotoAsset)
        .join(PhotoFolder, PhotoFolder.id == PhotoAsset.folder_id)
        .where(
            own_parent,
            PhotoAsset.tenant_id == owner,
            PhotoFolder.tenant_id == owner,
            PhotoAsset.parent_gallery_id == parent_gallery_id,
            PhotoAsset.derived_gallery_id.is_(None),
            PhotoAsset.available,
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.derived_gallery_id.is_(None),
            PhotoFolder.status == "released",
            PhotoFolder.purpose == "content",
            ~blocked_state,
            or_(
                PhotoFolder.audience_scope == "all",
                PhotoFolder.audience_scope.is_(None),  # pastas comuns legadas
                and_(PhotoFolder.audience_scope == "selected", granted),
            ),
        )
    )


def authorized_canonical_photo(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, photo_id: UUID
) -> PhotoAsset | None:
    return db.scalar(
        authorized_canonical_photos(parent_gallery_id, client_id).where(PhotoAsset.id == photo_id)
    )


def require_authorized_canonical_photo(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, photo_id: UUID
) -> tuple[ParentGallery, PhotoAsset]:
    parent = require_public_gallery_browsing(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id
    )
    photo = authorized_canonical_photo(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id, photo_id=photo_id
    )
    if not photo:
        raise CanonicalPhotoAccessDenied("Foto indisponível.")
    return parent, photo
