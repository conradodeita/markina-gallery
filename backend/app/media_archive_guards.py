"""Gates de elegibilidade e concorrência usados pelo executor de arquivo frio."""

from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    PhotoCreditOperation,
    PhotoFolder,
    PreviewAdjustment,
    SaleOrder,
    SaleOrderItem,
    Tenant,
)
from app.folder_access import folder_archive_eligible_at
from app.order_delivery import unresolved_order_condition


def _archive_order_blocker_condition():
    """Inclui pedidos em rascunho que ainda podem seguir para pagamento."""
    return or_(
        unresolved_order_condition(),
        and_(
            SaleOrder.payment_status == "pending",
            SaleOrder.frozen_at.is_(None),
            SaleOrder.checkout_key.is_not(None),
            SaleOrder.assets_removed_at.is_(None),
        ),
    )


def never_released_closure_folder(db: Session, folder: PhotoFolder) -> bool:
    """Exceção temporal só para pasta canônica em preparação, sem liberação."""
    if (folder.purpose != "content" or folder.status != "preparing"
            or folder.released_at is not None or folder.audience_scope not in {"all", "selected"}):
        return False
    lifecycle = db.scalar(select(Tenant.lifecycle).where(
        Tenant.id == folder.tenant_id, Tenant.status == "active"))
    if lifecycle != "closing":
        return False
    published = db.scalar(select(AuditEvent.id).where(
        AuditEvent.tenant_id == folder.tenant_id,
        AuditEvent.event.in_(("photo_folder.published", "photo_folder.released")),
        or_(AuditEvent.subject == str(folder.id), AuditEvent.subject.like(f"{folder.id}:%")),
    ).limit(1))
    return published is None


def isolated_closure_cover_folder(db: Session, folder: PhotoFolder) -> bool:
    if folder.purpose != "cover_assets" or folder.derived_gallery_id is not None:
        return False
    if db.scalar(select(Tenant.lifecycle).where(
        Tenant.id == folder.tenant_id, Tenant.status == "active")) not in {"closing", "closed"}:
        return False
    return db.scalar(select(PhotoFolder.id).where(
        PhotoFolder.tenant_id == folder.tenant_id,
        PhotoFolder.parent_gallery_id == folder.parent_gallery_id,
        PhotoFolder.purpose == "content",
    ).limit(1)) is None


def archive_blocker(
    db: Session, folder: PhotoFolder, *, at,
) -> str | None:
    """Retorna um código fixo quando ainda não é seguro congelar a pasta."""
    eligible_at = folder_archive_eligible_at(db, folder)
    current = at
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("O instante do arquivamento precisa conter fuso horário.")
    if ((eligible_at is None or eligible_at > current)
            and not never_released_closure_folder(db, folder)
            and not isolated_closure_cover_folder(db, folder)):
        return "not_eligible"

    folder_photo_ids = select(PhotoAsset.id).where(
        PhotoAsset.tenant_id == folder.tenant_id,
        PhotoAsset.parent_gallery_id == folder.parent_gallery_id,
        PhotoAsset.folder_id == folder.id,
    )
    if isolated_closure_cover_folder(db, folder) and db.scalar(select(SaleOrder.id).where(
        SaleOrder.tenant_id == folder.tenant_id,
        SaleOrder.parent_gallery_id_snapshot == folder.parent_gallery_id,
        _archive_order_blocker_condition(),
    ).limit(1)) is not None:
        return "open_order"
    open_order = db.scalar(
        select(SaleOrder.id)
        .join(
            SaleOrderItem,
            (SaleOrderItem.sale_order_id == SaleOrder.id)
            & (SaleOrderItem.tenant_id == SaleOrder.tenant_id),
        )
        .where(
            SaleOrder.tenant_id == folder.tenant_id,
            SaleOrder.parent_gallery_id_snapshot == folder.parent_gallery_id,
            SaleOrderItem.tenant_id == folder.tenant_id,
            or_(
                SaleOrderItem.folder_id_snapshot == folder.id,
                SaleOrderItem.photo_asset_id_snapshot.in_(folder_photo_ids),
            ),
            _archive_order_blocker_condition(),
        )
        .limit(1)
    )
    if open_order is not None:
        return "open_order"

    # Uma mídia em fila pode publicar um objeto depois do snapshot. O bloqueio
    # é conservador no escopo da galeria; os writers também travam as pastas.
    media_in_progress = db.scalar(
        select(MediaJob.id)
        .join(PhotoAsset, PhotoAsset.id == MediaJob.photo_asset_id)
        .where(
            MediaJob.tenant_id == folder.tenant_id,
            PhotoAsset.tenant_id == folder.tenant_id,
            PhotoAsset.parent_gallery_id == folder.parent_gallery_id,
            MediaJob.status.in_( ("queued", "processing") ),
        )
        .limit(1)
    )
    adjustment_in_progress = db.scalar(
        select(PreviewAdjustment.photo_asset_id)
        .join(PhotoAsset, PhotoAsset.id == PreviewAdjustment.photo_asset_id)
        .where(
            PreviewAdjustment.tenant_id == folder.tenant_id,
            PhotoAsset.tenant_id == folder.tenant_id,
            PhotoAsset.parent_gallery_id == folder.parent_gallery_id,
            PreviewAdjustment.status.in_( ("queued", "processing") ),
        )
        .limit(1)
    )
    pending_credit = db.scalar(
        select(PhotoCreditOperation.id)
        .where(
            PhotoCreditOperation.tenant_id == folder.tenant_id,
            PhotoCreditOperation.photo_asset_id_snapshot.in_(folder_photo_ids),
            PhotoCreditOperation.status.in_( ("reserved", "reconciliation_required") ),
        )
        .limit(1)
    )
    if media_in_progress is not None or adjustment_in_progress is not None or pending_credit is not None:
        return "media_processing"
    return None


def lock_archive_scope(
    db: Session, folder: PhotoFolder,
) -> tuple[PhotoFolder, ParentGallery] | None:
    """Trava galeria e depois pasta, na mesma ordem dos escritores de mídia."""
    gallery = db.scalar(
        select(ParentGallery)
        .where(
            ParentGallery.id == folder.parent_gallery_id,
            ParentGallery.tenant_id == folder.tenant_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not gallery or gallery.lifecycle_status != "active":
        return None
    locked_folder = db.scalar(
        select(PhotoFolder)
        .where(PhotoFolder.id == folder.id, PhotoFolder.tenant_id == folder.tenant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not locked_folder or locked_folder.parent_gallery_id != gallery.id:
        return None
    return locked_folder, gallery
