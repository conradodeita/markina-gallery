"""Resumo administrativo das pastas privadas de uma única galeria-fonte."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    PhotoAsset,
    PhotoFolder,
)


def private_folder_overview(
    db: Session, parent_gallery_id: UUID, *, tenant_id: UUID
) -> list[dict[str, object]]:
    galleries = list(db.execute(
        select(DerivedGallery, Client.full_name)
        .join(Client, Client.id == DerivedGallery.client_id)
        .join(PhotoFolder, PhotoFolder.derived_gallery_id == DerivedGallery.id)
        .where(
            DerivedGallery.tenant_id == tenant_id,
            Client.tenant_id == tenant_id,
            DerivedGallery.parent_gallery_id == parent_gallery_id,
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.purpose == "content",
        )
        .distinct()
        .order_by(DerivedGallery.created_at, DerivedGallery.id)
    ))
    if not galleries:
        return []
    gallery_ids = [gallery.id for gallery, _ in galleries]
    folders = defaultdict(list)
    for folder, count in db.execute(
        select(PhotoFolder, func.count(PhotoAsset.id))
        .outerjoin(PhotoAsset, (
            (PhotoAsset.folder_id == PhotoFolder.id)
            & (PhotoAsset.derived_gallery_id == PhotoFolder.derived_gallery_id)
            & (PhotoAsset.parent_gallery_id == parent_gallery_id)
            & (PhotoAsset.tenant_id == tenant_id)
        ))
        .where(
            PhotoFolder.tenant_id == tenant_id,
            PhotoFolder.parent_gallery_id == parent_gallery_id,
            PhotoFolder.derived_gallery_id.in_(gallery_ids),
            PhotoFolder.purpose == "content",
        )
        .group_by(PhotoFolder)
        .order_by(PhotoFolder.position, PhotoFolder.created_at, PhotoFolder.id)
    ):
        folders[folder.derived_gallery_id].append({
            "id": str(folder.id), "name": folder.name, "status": folder.status,
            "position": folder.position, "photo_count": count,
        })
    members = defaultdict(list)
    for gallery_id, client_id, name in db.execute(
        select(DerivedGalleryMembership.derived_gallery_id, Client.id, Client.full_name)
        .join(Client, Client.id == DerivedGalleryMembership.client_id)
        .where(
            DerivedGalleryMembership.tenant_id == tenant_id,
            Client.tenant_id == tenant_id,
            DerivedGalleryMembership.parent_gallery_id == parent_gallery_id,
            DerivedGalleryMembership.derived_gallery_id.in_(gallery_ids),
            DerivedGalleryMembership.status == "active",
        )
        .order_by(Client.full_name, Client.id)
    ):
        members[gallery_id].append({"id": str(client_id), "name": name})
    return [{
        "id": str(gallery.id), "name": gallery.name,
        "owner": {"id": str(gallery.client_id), "name": owner_name},
        "active_members": members[gallery.id], "folders": folders[gallery.id],
    } for gallery, owner_name in galleries]
