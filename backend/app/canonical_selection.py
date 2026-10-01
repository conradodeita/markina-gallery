"""Seleção individual na galeria canônica, sem criar galeria derivada."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.acervo_context import client_tenant_id
from app.auth import (
    Client,
    GalleryClientState,
    PhotoAsset,
    PhotoSelection,
    expired,
    now,
)
from app.checkout import client_photo_is_frozen_any
from app.public_gallery_access import (
    CanonicalPhotoAccessDenied,
    PublicGalleryAccessDenied,
    authorized_canonical_photos,
    require_authorized_canonical_photo,
    require_public_gallery_browsing,
)


class CanonicalSelectionUnavailable(RuntimeError):
    """A cliente ou a foto não permite alterar a seleção."""


@dataclass(frozen=True)
class CanonicalSelectionResult:
    state: GalleryClientState
    state_created: bool
    selection_created: bool
    quantity: int


@dataclass(frozen=True)
class CanonicalUnselectionResult:
    selection_removed: bool
    quantity: int


def _selection_quantity(db: Session, *, parent_gallery_id: UUID, client_id: UUID) -> int:
    tenant_id = client_tenant_id(db, client_id)
    allowed = authorized_canonical_photos(parent_gallery_id, client_id).with_only_columns(
        PhotoAsset.id
    )
    return db.scalar(
        select(func.count(PhotoSelection.id)).where(PhotoSelection.tenant_id == tenant_id).where(
            PhotoSelection.parent_gallery_id == parent_gallery_id,
            PhotoSelection.client_id == client_id,
            PhotoSelection.photo_asset_id.in_(allowed),
        )
    ) or 0


def select_canonical_photo(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, photo_id: UUID
) -> CanonicalSelectionResult:
    tenant_id = client_tenant_id(db, client_id)
    db.scalar(select(Client.id).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    try:
        parent, _photo = require_authorized_canonical_photo(
            db, parent_gallery_id=parent_gallery_id, client_id=client_id, photo_id=photo_id
        )
    except (CanonicalPhotoAccessDenied, PublicGalleryAccessDenied) as exc:
        raise CanonicalSelectionUnavailable("Foto indisponível para esta cliente.") from exc
    lookup = select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
    )
    state = db.scalar(lookup.with_for_update())
    state_created = False
    if not state:
        try:
            with db.begin_nested():
                state = GalleryClientState(
                    parent_gallery_id=parent_gallery_id,
                    client_id=client_id,
                    status="active",
                    selection_expires_at=(
                        now() + timedelta(days=parent.selection_duration_days)
                        if parent.selection_duration_days else None
                    ),
                 tenant_id=tenant_id)
                db.add(state)
                db.flush()
            state_created = True
        except IntegrityError:
            state = db.scalar(lookup.with_for_update())
            if not state:
                raise
    if state.status != "active" or (
        state.selection_expires_at and expired(state.selection_expires_at)
    ):
        raise CanonicalSelectionUnavailable("O prazo ou acesso desta cliente está indisponível.")
    if client_photo_is_frozen_any(db, client_id=client_id, photo_id=photo_id):
        raise CanonicalSelectionUnavailable("Esta foto já integra uma compra ou pagamento comunicado.")
    if state.selection_expires_at is None and parent.selection_duration_days and not db.scalar(
        select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
            PhotoSelection.parent_gallery_id == parent_gallery_id,
            PhotoSelection.client_id == client_id,
        ).limit(1)
    ):
        state.selection_expires_at = now() + timedelta(days=parent.selection_duration_days)
    selection_lookup = select(PhotoSelection.id).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id == client_id,
        PhotoSelection.photo_asset_id == photo_id,
    )
    selection_created = False
    if not db.scalar(selection_lookup):
        try:
            with db.begin_nested():
                db.add(PhotoSelection(
                    parent_gallery_id=parent_gallery_id,
                    client_id=client_id,
                    photo_asset_id=photo_id,
                 tenant_id=tenant_id))
                db.flush()
            selection_created = True
        except IntegrityError:
            if not db.scalar(selection_lookup):
                raise
    return CanonicalSelectionResult(
        state=state,
        state_created=state_created,
        selection_created=selection_created,
        quantity=_selection_quantity(db, parent_gallery_id=parent_gallery_id, client_id=client_id),
    )


def unselect_canonical_photo(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID, photo_id: UUID
) -> CanonicalUnselectionResult:
    tenant_id = client_tenant_id(db, client_id)
    require_public_gallery_browsing(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id
    )
    require_authorized_canonical_photo(
        db, parent_gallery_id=parent_gallery_id, client_id=client_id, photo_id=photo_id
    )
    db.scalar(select(Client.id).where(Client.tenant_id == tenant_id).where(Client.id == client_id).with_for_update())
    state = db.scalar(select(GalleryClientState).where(GalleryClientState.tenant_id == tenant_id).where(
        GalleryClientState.parent_gallery_id == parent_gallery_id,
        GalleryClientState.client_id == client_id,
    ).with_for_update())
    if state and (state.status != "active" or (
        state.selection_expires_at and expired(state.selection_expires_at)
    )):
        raise CanonicalSelectionUnavailable("O prazo ou acesso desta cliente está indisponível.")
    selection = db.scalar(select(PhotoSelection).where(PhotoSelection.tenant_id == tenant_id).where(
        PhotoSelection.parent_gallery_id == parent_gallery_id,
        PhotoSelection.client_id == client_id,
        PhotoSelection.photo_asset_id == photo_id,
    ))
    if selection:
        db.delete(selection)
        db.flush()
    return CanonicalUnselectionResult(
        selection_removed=bool(selection),
        quantity=_selection_quantity(db, parent_gallery_id=parent_gallery_id, client_id=client_id),
    )
