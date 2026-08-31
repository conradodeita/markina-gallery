"""Vínculo individual entre cliente e Galeria pública, sem derivação privada."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import ParentGalleryRegistration


def link_client_to_parent(
    db: Session,
    *,
    parent_gallery_id: UUID,
    client_id: UUID,
    status: str = "active",
) -> ParentGalleryRegistration:
    """Cria ou ativa o vínculo sem criar uma ``DerivedGallery``."""

    registration = db.scalar(
        select(ParentGalleryRegistration).where(
            ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ParentGalleryRegistration.client_id == client_id,
        )
    )
    if registration:
        if status == "active":
            registration.status = "active"
        return registration
    try:
        with db.begin_nested():
            registration = ParentGalleryRegistration(
                parent_gallery_id=parent_gallery_id,
                client_id=client_id,
                status=status,
            )
            db.add(registration)
            db.flush()
    except IntegrityError:
        registration = db.scalar(
            select(ParentGalleryRegistration).where(
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
                ParentGalleryRegistration.client_id == client_id,
            )
        )
        if not registration:
            raise
        if status == "active":
            registration.status = "active"
    return registration
