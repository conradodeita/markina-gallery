"""Encerramento seguro de galerias privadas derivadas pela cliente."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import (
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    DerivedGalleryPhotoOrigin,
    GalleryAccess,
    GalleryAccessCapability,
    PhotoComment,
    PhotoFavorite,
    PhotoSelection,
    PhotoView,
)
from app.commercial_removal import apply_commercial_removal_policy


@dataclass
class PrivateSelectionRemovalResult:
    selection_removed: bool
    client_reference_removed: bool
    gallery_closed: bool


def remove_client_selection_and_close_if_empty(
    db: Session,
    *,
    gallery: DerivedGallery,
    client_id: UUID,
    photo_id: UUID,
) -> PrivateSelectionRemovalResult:
    """Remove apenas a justificativa client e encerra a privada realmente vazia."""

    selection = db.scalar(
        select(PhotoSelection).where(
            PhotoSelection.derived_gallery_id == gallery.id,
            PhotoSelection.photo_asset_id == photo_id,
            PhotoSelection.client_id == client_id,
        )
    )
    if not selection:
        return PrivateSelectionRemovalResult(False, False, False)

    apply_commercial_removal_policy(
        db,
        parent_gallery_id=gallery.parent_gallery_id,
        client_id=client_id,
        derived_gallery_id=gallery.id,
        photo_asset_id=photo_id,
    )
    db.delete(selection)
    reference = db.scalar(
        select(DerivedGalleryPhoto).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery.id,
            DerivedGalleryPhoto.photo_asset_id == photo_id,
        )
    )
    client_origin = (
        db.scalar(
            select(DerivedGalleryPhotoOrigin).where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id,
                DerivedGalleryPhotoOrigin.origin == "client",
            )
        )
        if reference
        else None
    )
    legacy_client_reference = bool(
        reference and not client_origin and reference.origin == "client"
    )
    other_client_selections = db.scalar(
        select(func.count()).select_from(PhotoSelection).where(
            PhotoSelection.derived_gallery_id == gallery.id,
            PhotoSelection.photo_asset_id == photo_id,
            PhotoSelection.client_id != client_id,
        )
    )
    if client_origin and not other_client_selections:
        db.delete(client_origin)
    db.flush()
    if reference:
        origins_left = db.scalar(
            select(func.count())
            .select_from(DerivedGalleryPhotoOrigin)
            .where(
                DerivedGalleryPhotoOrigin.derived_gallery_photo_id == reference.id
            )
        )
        if not origins_left and not other_client_selections:
            db.delete(reference)
            db.flush()

    references_left = db.scalar(
        select(func.count()).select_from(DerivedGalleryPhoto).where(
            DerivedGalleryPhoto.derived_gallery_id == gallery.id
        )
    )
    if references_left:
        return PrivateSelectionRemovalResult(
            True,
            bool(client_origin is not None or legacy_client_reference)
            and not other_client_selections,
            False,
        )

    for model in (PhotoComment, PhotoFavorite, PhotoView, PhotoSelection):
        db.execute(delete(model).where(model.derived_gallery_id == gallery.id))
    db.execute(delete(GalleryAccess).where(GalleryAccess.gallery_id == gallery.id))
    db.execute(
        delete(GalleryAccessCapability).where(
            GalleryAccessCapability.derived_gallery_id == gallery.id
        )
    )
    db.execute(
        delete(DerivedGalleryMembership).where(
            DerivedGalleryMembership.derived_gallery_id == gallery.id
        )
    )
    db.delete(gallery)
    db.flush()
    return PrivateSelectionRemovalResult(
        True,
        bool(client_origin is not None or legacy_client_reference)
        and not other_client_selections,
        True,
    )
