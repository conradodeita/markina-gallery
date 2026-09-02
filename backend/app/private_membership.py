"""Resolução transacional de membros em galerias privadas compartilhadas."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    ParentGallery,
    now,
)


class PrivateMembershipError(RuntimeError):
    """A associação solicitada não respeita a origem ou seu estado."""


class PrivateMembershipConflict(PrivateMembershipError):
    """A cliente já está associada a outra privada da mesma origem."""


@dataclass(frozen=True)
class PrivateMembershipResolution:
    gallery: DerivedGallery
    membership: DerivedGalleryMembership
    gallery_created: bool
    membership_created: bool


def membership_for_client(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    lock: bool = False,
) -> DerivedGalleryMembership | None:
    query = select(DerivedGalleryMembership).where(
        DerivedGalleryMembership.parent_gallery_id == parent_gallery_id,
        DerivedGalleryMembership.client_id == client_id,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def operational_galleries_for_client(
    db: Session,
    *,
    client_id: UUID,
    require_access_enabled: bool = True,
) -> list[DerivedGallery]:
    """Lista associações ativas e, transitoriamente, privadas legadas sem backfill."""

    membership_query = (
        select(DerivedGallery)
        .join(
            DerivedGalleryMembership,
            DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id,
        )
        .where(
            DerivedGalleryMembership.client_id == client_id,
            DerivedGalleryMembership.status == "active",
        )
    )
    if require_access_enabled:
        membership_query = membership_query.where(DerivedGallery.access_enabled)
    membership_galleries = list(db.scalars(membership_query))
    membership_ids = {gallery.id for gallery in membership_galleries}

    any_membership = (
        select(DerivedGalleryMembership.id)
        .where(DerivedGalleryMembership.derived_gallery_id == DerivedGallery.id)
        .exists()
    )
    legacy_query = select(DerivedGallery).where(
        DerivedGallery.client_id == client_id,
        ~any_membership,
    )
    if require_access_enabled:
        legacy_query = legacy_query.where(DerivedGallery.access_enabled)
    for gallery in db.scalars(legacy_query):
        if gallery.id not in membership_ids:
            membership_galleries.append(gallery)
    return membership_galleries


def client_has_operational_membership(
    db: Session,
    *,
    gallery: DerivedGallery,
    client_id: UUID,
) -> bool:
    """Autoriza associação ativa; fallback legado só vale se não há membro algum."""

    membership = db.scalar(
        select(DerivedGalleryMembership).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id,
            DerivedGalleryMembership.client_id == client_id,
        )
    )
    if membership:
        return membership.status == "active"
    has_any_membership = db.scalar(
        select(DerivedGalleryMembership.id).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id
        )
    )
    return not has_any_membership and gallery.client_id == client_id


def _legacy_gallery_for_client(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
) -> DerivedGallery | None:
    return db.scalar(
        select(DerivedGallery).where(
            DerivedGallery.parent_gallery_id == parent_gallery_id,
            DerivedGallery.client_id == client_id,
        )
    )


def _create_legacy_compatible_gallery(
    db: Session,
    *,
    parent: ParentGallery,
    client: Client,
    name: str | None,
) -> tuple[DerivedGallery, bool]:
    gallery = _legacy_gallery_for_client(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
    )
    if gallery:
        return gallery, False
    try:
        with db.begin_nested():
            gallery = DerivedGallery(
                parent_gallery_id=parent.id,
                client_id=client.id,
                name=(name or f"{parent.name} — {client.full_name}")[:200],
                selection_expires_at=(
                    now() + timedelta(days=parent.selection_duration_days)
                    if parent.selection_duration_days
                    else None
                ),
            )
            db.add(gallery)
            db.flush()
        return gallery, True
    except IntegrityError:
        gallery = _legacy_gallery_for_client(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )
        if not gallery:
            raise
        return gallery, False


def ensure_private_membership(
    db: Session,
    *,
    parent: ParentGallery,
    client: Client,
    gallery: DerivedGallery | None = None,
    name: str | None = None,
    actor_admin_id: UUID | None = None,
) -> PrivateMembershipResolution:
    """Cria ou reutiliza a única associação da cliente naquela origem."""

    existing = membership_for_client(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        lock=True,
    )
    if existing:
        existing_gallery = db.get(DerivedGallery, existing.derived_gallery_id)
        if not existing_gallery:
            raise PrivateMembershipError("A associação aponta para uma galeria inexistente.")
        if gallery and existing.derived_gallery_id != gallery.id:
            raise PrivateMembershipConflict(
                "A cliente já pertence a outra galeria privada desta origem."
            )
        return PrivateMembershipResolution(
            gallery=existing_gallery,
            membership=existing,
            gallery_created=False,
            membership_created=False,
        )

    if gallery and gallery.parent_gallery_id != parent.id:
        raise PrivateMembershipError("A galeria privada não pertence à origem informada.")
    gallery_created = False
    if gallery is None:
        gallery, gallery_created = _create_legacy_compatible_gallery(
            db,
            parent=parent,
            client=client,
            name=name,
        )
    try:
        with db.begin_nested():
            membership = DerivedGalleryMembership(
                derived_gallery_id=gallery.id,
                parent_gallery_id=parent.id,
                client_id=client.id,
                actor_admin_id=actor_admin_id,
            )
            db.add(membership)
            db.flush()
        return PrivateMembershipResolution(
            gallery=gallery,
            membership=membership,
            gallery_created=gallery_created,
            membership_created=True,
        )
    except IntegrityError:
        membership = membership_for_client(
            db,
            parent_gallery_id=parent.id,
            client_id=client.id,
        )
        if not membership:
            raise
        if gallery and membership.derived_gallery_id != gallery.id:
            raise PrivateMembershipConflict(
                "A cliente já pertence a outra galeria privada desta origem."
            )
        resolved_gallery = db.get(DerivedGallery, membership.derived_gallery_id)
        if not resolved_gallery:
            raise PrivateMembershipError("A associação concorrente ficou inconsistente.")
        return PrivateMembershipResolution(
            gallery=resolved_gallery,
            membership=membership,
            gallery_created=False,
            membership_created=False,
        )


def block_private_membership(
    membership: DerivedGalleryMembership,
    *,
    actor_admin_id: UUID | None = None,
) -> DerivedGalleryMembership:
    if membership.status == "unlinked":
        raise PrivateMembershipError("Uma associação desvinculada não pode ser bloqueada.")
    if membership.status == "active":
        membership.status = "blocked"
        membership.blocked_at = now()
    membership.actor_admin_id = actor_admin_id
    return membership


def unblock_private_membership(
    membership: DerivedGalleryMembership,
    *,
    actor_admin_id: UUID | None = None,
) -> DerivedGalleryMembership:
    if membership.status == "unlinked":
        raise PrivateMembershipError("Reative a associação antes de desbloquear.")
    if membership.status == "blocked":
        membership.status = "active"
        membership.blocked_at = None
    membership.actor_admin_id = actor_admin_id
    return membership


def unlink_private_membership(
    membership: DerivedGalleryMembership,
    *,
    actor_admin_id: UUID | None = None,
) -> DerivedGalleryMembership:
    if membership.status != "unlinked":
        membership.status = "unlinked"
        membership.unlinked_at = now()
    membership.actor_admin_id = actor_admin_id
    return membership


def reactivate_private_membership(
    membership: DerivedGalleryMembership,
    *,
    gallery: DerivedGallery,
    actor_admin_id: UUID | None = None,
) -> DerivedGalleryMembership:
    if membership.status != "unlinked":
        raise PrivateMembershipError("Somente associação desvinculada pode ser reativada.")
    if gallery.parent_gallery_id != membership.parent_gallery_id:
        raise PrivateMembershipError("A reativação não pode trocar a origem da associação.")
    membership.derived_gallery_id = gallery.id
    membership.status = "active"
    membership.blocked_at = None
    membership.unlinked_at = None
    membership.actor_admin_id = actor_admin_id
    return membership
