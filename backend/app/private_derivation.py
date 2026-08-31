"""Derivação privada transacional a partir de uma Galeria pública."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SaleOrder,
    SaleOrderItem,
    expired,
    now,
)
from app.parent_registration import link_client_to_parent


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


def ensure_private_gallery(
    db: Session,
    *,
    parent: ParentGallery,
    client: Client,
    name: str | None = None,
) -> tuple[DerivedGallery, bool]:
    gallery = db.scalar(
        select(DerivedGallery)
        .where(
            DerivedGallery.parent_gallery_id == parent.id,
            DerivedGallery.client_id == client.id,
        )
        .with_for_update()
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
        gallery = db.scalar(
            select(DerivedGallery).where(
                DerivedGallery.parent_gallery_id == parent.id,
                DerivedGallery.client_id == client.id,
            )
        )
        if not gallery:
            raise
        return gallery, False


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


def derive_client_selection(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    photo_id: UUID,
) -> PrivateDerivationResult:
    """Cria/reutiliza privada, referência client e seleção em uma transação."""

    parent = db.get(ParentGallery, parent_gallery_id)
    client = db.get(Client, client_id)
    registration = db.scalar(
        select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
            ParentGalleryRegistration.status == "active",
        )
    )
    photo = db.get(PhotoAsset, photo_id)
    folder = db.get(PhotoFolder, photo.folder_id) if photo else None
    existing_gallery = db.scalar(
        select(DerivedGallery).where(
            DerivedGallery.parent_gallery_id == parent_gallery_id,
            DerivedGallery.client_id == client_id,
        )
    )
    if not registration and existing_gallery:
        registration = link_client_to_parent(
            db,
            parent_gallery_id=parent_gallery_id,
            client_id=client_id,
            status="active",
        )
    if (
        not parent
        or not parent.active
        or parent.lifecycle_status != "active"
        or not client
        or not registration
        or not photo
        or photo.parent_gallery_id != parent.id
        or not photo.available
        or not folder
        or folder.status != "released"
    ):
        raise PrivateDerivationError("Foto indisponível para esta cliente.")
    gallery, gallery_created = (
        (existing_gallery, False)
        if existing_gallery
        else ensure_private_gallery(db, parent=parent, client=client)
    )
    if not gallery.access_enabled:
        raise PrivateDerivationError("A galeria privada está bloqueada.")
    if gallery.selection_expires_at and expired(gallery.selection_expires_at):
        raise PrivateDerivationError("O prazo de seleção expirou.")
    already_confirmed = db.scalar(
        select(SaleOrderItem.id)
        .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
        .where(
            SaleOrder.derived_gallery_id_snapshot == gallery.id,
            SaleOrder.client_id == client.id,
            SaleOrder.payment_status == "confirmed",
            SaleOrderItem.photo_asset_id_snapshot == photo.id,
        )
    )
    if already_confirmed:
        raise PrivateDerivationError("Foto indisponível para seleção.")

    reference_lookup = select(DerivedGalleryPhoto.id).where(
        DerivedGalleryPhoto.derived_gallery_id == gallery.id,
        DerivedGalleryPhoto.photo_asset_id == photo.id,
        DerivedGalleryPhoto.origin == "client",
    )
    reference_created = _insert_once(
        db,
        DerivedGalleryPhoto(
            derived_gallery_id=gallery.id,
            photo_asset_id=photo.id,
            origin="client",
        ),
        reference_lookup,
    )
    selection_lookup = select(PhotoSelection.id).where(
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
        ),
        selection_lookup,
    )
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
    photo_ids: set[UUID],
    name: str | None = None,
) -> AdminPrivateDerivationResult:
    """Cria/reutiliza privada administrativa somente com fotos publicadas."""

    if not photo_ids:
        raise PrivateDerivationError(
            "Selecione ao menos uma foto disponível para criar a galeria privada."
        )
    parent = db.get(ParentGallery, parent_gallery_id)
    client = db.get(Client, client_id)
    if not parent or parent.lifecycle_status != "active" or not parent.active or not client:
        raise PrivateDerivationError("Galeria pública ou cliente indisponível.")
    photos = list(
        db.scalars(
            select(PhotoAsset).where(
                PhotoAsset.id.in_(photo_ids),
                PhotoAsset.parent_gallery_id == parent.id,
                PhotoAsset.available,
            )
        )
    )
    if len(photos) != len(photo_ids):
        raise PrivateDerivationError(
            "Todas as fotos devem estar disponíveis na Galeria pública informada."
        )
    folder_ids = {photo.folder_id for photo in photos}
    released_folder_ids = set(
        db.scalars(
            select(PhotoFolder.id).where(
                PhotoFolder.id.in_(folder_ids),
                PhotoFolder.parent_gallery_id == parent.id,
                PhotoFolder.status == "released",
            )
        )
    )
    if released_folder_ids != folder_ids:
        raise PrivateDerivationError(
            "Fotos de pasta em preparação não podem ser distribuídas."
        )

    link_client_to_parent(
        db,
        parent_gallery_id=parent.id,
        client_id=client.id,
        status="active",
    )
    gallery, gallery_created = ensure_private_gallery(
        db, parent=parent, client=client, name=name
    )
    references_created = 0
    for photo in photos:
        references_created += int(
            _insert_once(
                db,
                DerivedGalleryPhoto(
                    derived_gallery_id=gallery.id,
                    photo_asset_id=photo.id,
                    origin="admin",
                ),
                select(DerivedGalleryPhoto.id).where(
                    DerivedGalleryPhoto.derived_gallery_id == gallery.id,
                    DerivedGalleryPhoto.photo_asset_id == photo.id,
                    DerivedGalleryPhoto.origin == "admin",
                ),
            )
        )
    return AdminPrivateDerivationResult(
        gallery=gallery,
        gallery_created=gallery_created,
        references_created=references_created,
    )
