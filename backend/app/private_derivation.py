"""Derivação privada transacional a partir de uma Galeria pública."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.acervo_context import client_tenant_id, owned_record
from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoSelection,
    expired,
)
from app.checkout import (
    client_photo_is_frozen,
    lock_client_commerce,
    synchronize_editable_draft,
)
from app.notification_events import record_gallery_milestone
from app.parent_registration import link_client_to_parent
from app.private_membership import ensure_private_membership
from app.public_gallery_access import authorized_canonical_photo


class PrivateDerivationError(RuntimeError):
    """A origem, identidade ou janela não permite a derivação solicitada."""


class FacialDerivationUnavailable(PrivateDerivationError):
    """A porta facial existe, mas permanece fechada até spike/change próprios."""


def derive_approved_facial_result(*_args, **_kwargs):
    """Porta futura deliberadamente desativada; não é exposta por endpoint."""

    raise FacialDerivationUnavailable(
        "A derivação facial ainda não está habilitada para este produto."
    )


@dataclass
class PrivateDerivationResult:
    gallery: DerivedGallery
    gallery_created: bool
    reference_created: bool
    selection_created: bool


@dataclass
class AdminPrivateDerivationResult:
    gallery: DerivedGallery
    gallery_created: bool
    references_created: int


def _insert_once(db: Session, record, lookup) -> bool:
    if db.scalar(lookup):
        return False
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
        return True
    except IntegrityError:
        if not db.scalar(lookup):
            raise
        return False


def ensure_private_photo_reference(
    db: Session,
    *,
    tenant_id: UUID,
    gallery_id: UUID,
    photo_id: UUID,
    origin: str,
) -> bool:
    """Mantém uma referência única e registra cada justificativa que a sustenta."""

    gallery = owned_record(db, DerivedGallery, gallery_id, tenant_id=tenant_id)
    photo = owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)
    if not gallery or not photo or photo.parent_gallery_id != gallery.parent_gallery_id:
        raise PrivateDerivationError("Foto indisponível para esta galeria.")

    reference_lookup = select(DerivedGalleryPhoto.id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery_id,
        DerivedGalleryPhoto.tenant_id == tenant_id,
        DerivedGalleryPhoto.photo_asset_id == photo_id,
    )
    reference_created = _insert_once(
        db,
        DerivedGalleryPhoto(
            tenant_id=tenant_id,
            derived_gallery_id=gallery_id,
            photo_asset_id=photo_id,
            origin=origin,
        ),
        reference_lookup,
    )
    reference_id = db.scalar(reference_lookup)
    if not reference_id:
        raise PrivateDerivationError("Não foi possível registrar a foto na galeria privada.")
    _insert_once(
        db,
        DerivedGalleryPhotoOrigin(
            tenant_id=tenant_id,
            derived_gallery_photo_id=reference_id,
            origin=origin,
        ),
        select(DerivedGalleryPhotoOrigin.id).where(
            DerivedGalleryPhotoOrigin.tenant_id == tenant_id,
            DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference_id,
            DerivedGalleryPhotoOrigin.origin == origin,
        ),
    )
    return reference_created


def derive_client_selection(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    photo_id: UUID,
) -> PrivateDerivationResult:
    """Cria/reutiliza privada, referência client e seleção em uma transação."""
    tenant_id = client_tenant_id(db, client_id)

    db.scalar(select(Client.id).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    registration = db.scalar(
        select(ParentGalleryRegistration).where(ParentGalleryRegistration.tenant_id == tenant_id).where(
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    if not registration:
        existing_gallery = db.scalar(
            select(DerivedGallery).where(DerivedGallery.tenant_id == tenant_id).where(
                DerivedGallery.parent_gallery_id == parent_gallery_id,
                DerivedGallery.client_id == client_id,
            )
        )
    else:
        existing_gallery = None
    if not registration and existing_gallery:
        registration = link_client_to_parent(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            status="active",
        )
    photo = authorized_canonical_photo(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id, photo_id=photo_id
    )
    if (
        not parent
        or not parent.active
        or parent.lifecycle_status != "active"
        or not client
        or not registration
        or not photo
    ):
        raise PrivateDerivationError("Foto indisponível para esta cliente.")
    resolution = ensure_private_membership(
        db,
        parent=parent,
        client=client,
        gallery=existing_gallery,
    )
    gallery = resolution.gallery
    gallery_created = resolution.gallery_created
    lock_client_commerce(db, gallery_id=gallery.id, client_id=client.id)
    if resolution.membership.status != "active":
        raise PrivateDerivationError("O acesso desta cliente à galeria privada está bloqueado.")
    if not gallery.access_enabled:
        raise PrivateDerivationError("A galeria privada está bloqueada.")
    if gallery.selection_expires_at and expired(gallery.selection_expires_at):
        raise PrivateDerivationError("O prazo de seleção expirou.")
    if client_photo_is_frozen(
        db, gallery_id=gallery.id, client_id=client.id, photo_id=photo.id
    ):
        raise PrivateDerivationError("Foto indisponível para seleção.")

    reference_created = ensure_private_photo_reference(
        db,
        tenant_id=tenant_id,
        gallery_id=gallery.id,
        photo_id=photo.id,
        origin="client",
    )
    selection_lookup = select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.derived_gallery_id == gallery.id,
        PhotoSelection.photo_asset_id == photo.id,
        PhotoSelection.client_id == client.id,
    )
    selection_created = _insert_once(
        db,
        PhotoSelection(
            derived_gallery_id=gallery.id,
            photo_asset_id=photo.id,
            client_id=client.id,
         tenant_id=tenant_id),
        selection_lookup,
    )
    if selection_created:
        synchronize_editable_draft(db, gallery=gallery, client_id=client.id)
        record_gallery_milestone(db, kind="first_selection", parent_gallery_id=parent.id,
                                 client_id=client.id, gallery=gallery)
    return PrivateDerivationResult(
        gallery=gallery,
        gallery_created=gallery_created,
        reference_created=reference_created,
        selection_created=selection_created,
    )


def derive_admin_gallery(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    name: str | None = None,
) -> AdminPrivateDerivationResult:
    """Cria ou reutiliza uma privada administrativa vazia."""
    tenant_id = client_tenant_id(db, client_id)

    parent = owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
    client = owned_record(db, Client, client_id, tenant_id=tenant_id)
    if not parent or parent.lifecycle_status != "active" or not parent.active or not client:
        raise PrivateDerivationError("Galeria pública ou cliente indisponível.")

    link_client_to_parent(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        status="active",
    )
    resolution = ensure_private_membership(
        db,
        parent=parent,
        client=client,
        name=name,
    )
    if resolution.membership.status != "active":
        raise PrivateDerivationError("O acesso desta cliente à galeria privada está bloqueado.")
    gallery = resolution.gallery
    gallery_created = resolution.gallery_created
    return AdminPrivateDerivationResult(
        gallery=gallery,
        gallery_created=gallery_created,
        references_created=0,
    )
