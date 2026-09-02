"""Etapas concretas e idempotentes de limpeza operacional de galerias."""

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import (
    AuditEvent,
    AuthChallenge,
    DerivedGallery,
    DerivedGalleryMembership,
    DerivedGalleryPhoto,
    GalleryAccess,
    GalleryAccessCapability,
    GalleryLifecycleOperation,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    SaleOrder,
    SaleOrderItem,
    minimize_client_challenge_pii,
)
from app.commercial_removal import apply_commercial_removal_policy
from app.media import derivatives_root, source_root


def prepare_lifecycle_history(db: Session, operation: GalleryLifecycleOperation) -> None:
    """Congela o histórico e a mídia comprada antes da primeira etapa destrutiva."""

    if operation.operation_type == "unlink_client":
        private_id = db.scalar(
            select(DerivedGalleryMembership.derived_gallery_id).where(
                DerivedGalleryMembership.parent_gallery_id
                == operation.target_parent_gallery_id,
                DerivedGalleryMembership.client_id == operation.target_client_id,
            )
        )
        if private_id is None:
            private_id = db.scalar(
                select(DerivedGallery.id).where(
                    DerivedGallery.parent_gallery_id
                    == operation.target_parent_gallery_id,
                    DerivedGallery.client_id == operation.target_client_id,
                )
            )
        report = apply_commercial_removal_policy(
            db,
            parent_gallery_id=operation.target_parent_gallery_id,
            client_id=operation.target_client_id,
            derived_gallery_id=private_id,
        )
        manifest = dict(operation.manifest or {})
        manifest["history_preparation"] = {
            "confirmed_orders": report.confirmed_orders,
            "cancelled_pending_orders": report.cancelled_pending_orders,
        }
        operation.manifest = manifest
        return

    retained_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.derived_gallery_id.in_(
            select(DerivedGallery.id).where(
                DerivedGallery.parent_gallery_id == operation.target_parent_gallery_id
            )
        )
    )
    removable_photo_ids = list(
        db.scalars(
            select(PhotoAsset.id).where(
                PhotoAsset.parent_gallery_id == operation.target_parent_gallery_id,
                PhotoAsset.id.not_in(retained_photo_ids),
            )
        )
    )
    confirmed_orders: set[str] = set()
    cancelled_pending_orders: set[str] = set()
    for photo_id in removable_photo_ids:
        affected = {
            str(order.id): order.payment_status
            for order in db.scalars(
                select(SaleOrder)
                .join(SaleOrderItem)
                .where(SaleOrderItem.photo_asset_id_snapshot == photo_id)
            )
        }
        apply_commercial_removal_policy(
            db,
            parent_gallery_id=operation.target_parent_gallery_id,
            photo_asset_id=photo_id,
        )
        confirmed_orders.update(
            order_id
            for order_id, payment_status in affected.items()
            if payment_status == "confirmed"
        )
        cancelled_pending_orders.update(
            order_id for order_id, payment_status in affected.items() if payment_status == "pending"
        )
    manifest = dict(operation.manifest or {})
    manifest["history_preparation"] = {
        "confirmed_orders": len(confirmed_orders),
        "cancelled_pending_orders": len(cancelled_pending_orders),
    }
    operation.manifest = manifest


def _delete_count(db: Session, model, *criteria) -> int:
    result = db.execute(delete(model).where(*criteria).execution_options(synchronize_session=False))
    return result.rowcount or 0


def _manifest_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Manifesto contém caminho operacional inválido.") from exc
    return candidate


def remove_operational_storage(_db: Session, operation: GalleryLifecycleOperation) -> None:
    """Remove somente arquivos operacionais congelados no manifesto da operação."""

    manifest = dict(operation.manifest or {})
    storage_manifest = manifest.get("operational_storage")
    if not isinstance(storage_manifest, dict):
        raise TypeError("Manifesto de armazenamento operacional ausente.")
    source_entries = storage_manifest.get("sources", [])
    derivative_entries = storage_manifest.get("derivatives", [])
    paths: list[Path] = []
    source_base = source_root()
    derivative_base = derivatives_root()
    for entry in source_entries:
        paths.append(_manifest_path(source_base, entry["storage_key"]))
    for entry in derivative_entries:
        paths.append(_manifest_path(derivative_base, entry["relative_path"]))

    removed_files = 0
    missing_files = 0
    for path in paths:
        if path.is_file():
            path.unlink()
            removed_files += 1
        elif path.exists():
            raise ValueError("Manifesto operacional aponta para item não regular.")
        else:
            missing_files += 1
    manifest["storage_cleanup"] = {
        "expected_files": len(paths),
        "removed_files": removed_files,
        "missing_files": missing_files,
    }
    operation.manifest = manifest


def remove_operational_records(db: Session, operation: GalleryLifecycleOperation) -> None:
    """Remove o grafo operacional da origem; histórico e cliente ficam fora do alvo."""

    if operation.operation_type == "unlink_client":
        _remove_client_link_records(db, operation)
        return
    if operation.operation_type != "delete_parent_gallery":
        raise ValueError("Tipo de operação de ciclo de vida inválido.")
    parent_id = operation.target_parent_gallery_id
    private_ids = list(
        db.scalars(select(DerivedGallery.id).where(DerivedGallery.parent_gallery_id == parent_id))
    )
    retained_photo_ids = (
        list(
            db.scalars(
                select(DerivedGalleryPhoto.photo_asset_id)
                .where(DerivedGalleryPhoto.derived_gallery_id.in_(private_ids))
                .distinct()
            )
        )
        if private_ids
        else []
    )
    photo_ids = list(
        db.scalars(
            select(PhotoAsset.id).where(
                PhotoAsset.parent_gallery_id == parent_id,
                PhotoAsset.id.not_in(retained_photo_ids),
            )
        )
    )
    removed: dict[str, int] = {}
    removed["access_capabilities"] = _delete_count(
        db,
        GalleryAccessCapability,
        GalleryAccessCapability.parent_gallery_id == parent_id,
    )
    removed["registrations"] = _delete_count(
        db,
        ParentGalleryRegistration,
        ParentGalleryRegistration.parent_gallery_id == parent_id,
    )
    challenges = list(
        db.scalars(select(AuthChallenge).where(AuthChallenge.parent_gallery_id == parent_id))
    )
    for challenge in challenges:
        if challenge.kind == "client_otp":
            minimize_client_challenge_pii(db, challenge)
    removed["auth_challenges"] = _delete_count(
        db, AuthChallenge, AuthChallenge.parent_gallery_id == parent_id
    )
    if photo_ids:
        removed["media_jobs"] = _delete_count(db, MediaJob, MediaJob.photo_asset_id.in_(photo_ids))
        removed["media_derivatives"] = _delete_count(
            db, MediaDerivative, MediaDerivative.photo_asset_id.in_(photo_ids)
        )
    else:
        removed["media_jobs"] = 0
        removed["media_derivatives"] = 0

    parent = db.get(ParentGallery, parent_id)
    if parent:
        parent.cover_photo_id = None
        db.flush()
    removed["photos"] = (
        _delete_count(db, PhotoAsset, PhotoAsset.id.in_(photo_ids)) if photo_ids else 0
    )
    removed["folders"] = _delete_count(
        db,
        PhotoFolder,
        PhotoFolder.parent_gallery_id == parent_id,
        PhotoFolder.id.not_in(
            select(PhotoAsset.folder_id).where(PhotoAsset.parent_gallery_id == parent_id)
        ),
    )
    if parent:
        parent.active = False
        parent.lifecycle_status = "deleted"
        removed["public_origins"] = 1
    else:
        removed["public_origins"] = 0
    removed["preserved_private_galleries"] = len(private_ids)
    removed["preserved_private_photos"] = len(retained_photo_ids)

    manifest = dict(operation.manifest or {})
    manifest["removed_records"] = removed
    operation.manifest = manifest
    db.add(
        AuditEvent(
            event="parent_gallery.operational_records_removed",
            subject=f"operation_id:{operation.id}",
        )
    )


def _remove_client_link_records(db: Session, operation: GalleryLifecycleOperation) -> None:
    parent_id = operation.target_parent_gallery_id
    client_id = operation.target_client_id
    if not client_id:
        raise ValueError("Operação de desvinculação sem cliente alvo.")
    membership = db.scalar(
        select(DerivedGalleryMembership).where(
            DerivedGalleryMembership.parent_gallery_id == parent_id,
            DerivedGalleryMembership.client_id == client_id,
        )
    )
    private_ids = [membership.derived_gallery_id] if membership else list(
        db.scalars(
            select(DerivedGallery.id).where(
                DerivedGallery.parent_gallery_id == parent_id,
                DerivedGallery.client_id == client_id,
            )
        )
    )
    removed: dict[str, int] = {}
    for name, model in (
        ("comments", PhotoComment),
        ("favorites", PhotoFavorite),
        ("views", PhotoView),
        ("selections", PhotoSelection),
    ):
        removed[name] = (
            _delete_count(
                db,
                model,
                model.derived_gallery_id.in_(private_ids),
                model.client_id == client_id,
            )
            if private_ids
            else 0
        )
    # Preço e PIX pertencem à Galeria pública e não ao vínculo removido.
    removed["price_rules"] = 0
    removed["pix_settings"] = 0
    removed["available_references"] = 0
    removed["legacy_access"] = (
        _delete_count(
            db,
            GalleryAccess,
            GalleryAccess.gallery_id.in_(private_ids),
            GalleryAccess.client_id == client_id,
        )
        if private_ids
        else 0
    )
    removed["private_capabilities"] = (
        _delete_count(
            db,
            GalleryAccessCapability,
            GalleryAccessCapability.derived_gallery_id.in_(private_ids),
            GalleryAccessCapability.client_id == client_id,
        )
        if private_ids
        else 0
    )
    removed["registrations"] = _delete_count(
        db,
        ParentGalleryRegistration,
        ParentGalleryRegistration.parent_gallery_id == parent_id,
        ParentGalleryRegistration.client_id == client_id,
    )
    removed["private_galleries"] = 0
    removed["memberships_unlinked"] = 0
    if membership and membership.status != "unlinked":
        membership.status = "unlinked"
        membership.unlinked_at = operation.updated_at
        removed["memberships_unlinked"] = 1
    manifest = dict(operation.manifest or {})
    manifest["removed_records"] = removed
    operation.manifest = manifest
    db.add(
        AuditEvent(
            event="parent_gallery.client_unlinked",
            subject=f"operation_id:{operation.id}",
        )
    )
