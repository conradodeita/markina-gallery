"""Regras e orquestração retomável do ciclo de vida da galeria."""

from collections.abc import Callable, Mapping
from datetime import timedelta
from secrets import token_hex
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    CommercialHistoryMedia,
    DerivedGallery,
    DerivedGalleryPhoto,
    GalleryAccessCapability,
    GalleryLifecycleOperation,
    MediaDerivative,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoComment,
    PhotoFavorite,
    PhotoFolder,
    PhotoSelection,
    PhotoView,
    SaleOrder,
    SaleOrderItem,
    now,
)


class InvalidLifecycleTransition(ValueError):
    """Indica tentativa de regressão ou salto de estado não permitido."""


class LifecycleLeaseConflict(RuntimeError):
    """A operação não pertence mais a este worker."""


class LifecycleStageUnavailable(RuntimeError):
    """Uma etapa ainda não possui executor registrado."""


LifecycleStageHandler = Callable[[Session, GalleryLifecycleOperation], None]
LIFECYCLE_STAGES = (
    "preparing_history",
    "removing_storage",
    "removing_records",
)


OPERATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"preparing_history", "failed", "cancelled"}),
    "preparing_history": frozenset({"removing_storage", "failed", "cancelled"}),
    "removing_storage": frozenset({"removing_records", "failed"}),
    "removing_records": frozenset({"completed", "failed"}),
    "failed": frozenset({"queued", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}


def transition_operation(
    operation: GalleryLifecycleOperation,
    target_status: str,
    *,
    error: str | None = None,
) -> None:
    """Aplica somente transições explícitas e mantém timestamps auditáveis."""

    allowed = OPERATION_TRANSITIONS.get(operation.status, frozenset())
    if target_status not in allowed:
        raise InvalidLifecycleTransition(
            f"Transição inválida: {operation.status} -> {target_status}."
        )
    operation.status = target_status
    operation.updated_at = now()
    operation.last_error = error if target_status == "failed" else None
    if target_status == "removing_storage" and operation.destructive_started_at is None:
        operation.destructive_started_at = now()
    if target_status == "completed":
        operation.completed_at = now()


def _manifest(operation: GalleryLifecycleOperation) -> dict:
    return dict(operation.manifest or {})


def gallery_deletion_inventory(db: Session, parent_gallery_id: UUID) -> dict:
    """Conta o escopo operacional removível e o histórico preservado, sem PII."""

    private_ids = select(DerivedGallery.id).where(
        DerivedGallery.parent_gallery_id == parent_gallery_id
    )
    retained_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.derived_gallery_id.in_(private_ids)
    )
    retained_folder_ids = select(PhotoAsset.folder_id).where(
        PhotoAsset.parent_gallery_id == parent_gallery_id,
        PhotoAsset.id.in_(retained_photo_ids),
    )
    removable_photo_ids = select(PhotoAsset.id).where(
        PhotoAsset.parent_gallery_id == parent_gallery_id,
        PhotoAsset.id.not_in(retained_photo_ids),
    )

    def count(model, *criteria) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0

    order_counts = {
        payment_status: total
        for payment_status, total in db.execute(
            select(SaleOrder.payment_status, func.count())
            .where(SaleOrder.parent_gallery_id_snapshot == parent_gallery_id)
            .group_by(SaleOrder.payment_status)
        )
    }
    return {
        "remove": {
            "folders": count(
                PhotoFolder,
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.id.not_in(retained_folder_ids),
            ),
            "photos": count(
                PhotoAsset,
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.id.not_in(retained_photo_ids),
            ),
            "media_derivatives": count(
                MediaDerivative,
                MediaDerivative.photo_asset_id.in_(removable_photo_ids),
            ),
            "registrations": count(
                ParentGalleryRegistration,
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
            ),
            "access_capabilities": count(
                GalleryAccessCapability,
                GalleryAccessCapability.parent_gallery_id == parent_gallery_id,
                GalleryAccessCapability.scope != "private_invite",
            ),
        },
        "preserve": {
            "clients": db.scalar(
                select(func.count(func.distinct(DerivedGallery.client_id))).where(
                    DerivedGallery.parent_gallery_id == parent_gallery_id
                )
            )
            or 0,
            "private_galleries": count(
                DerivedGallery,
                DerivedGallery.parent_gallery_id == parent_gallery_id,
            ),
            "photos_referenced_by_private": count(
                PhotoAsset,
                PhotoAsset.parent_gallery_id == parent_gallery_id,
                PhotoAsset.id.in_(retained_photo_ids),
            ),
            "folders_with_private_photos": count(
                PhotoFolder,
                PhotoFolder.parent_gallery_id == parent_gallery_id,
                PhotoFolder.id.in_(retained_folder_ids),
            ),
            "available_references": count(
                DerivedGalleryPhoto,
                DerivedGalleryPhoto.derived_gallery_id.in_(private_ids),
            ),
            "selections": count(
                PhotoSelection, PhotoSelection.derived_gallery_id.in_(private_ids)
            ),
            "favorites": count(
                PhotoFavorite, PhotoFavorite.derived_gallery_id.in_(private_ids)
            ),
            "comments": count(
                PhotoComment, PhotoComment.derived_gallery_id.in_(private_ids)
            ),
            "views": count(PhotoView, PhotoView.derived_gallery_id.in_(private_ids)),
            "orders": sum(order_counts.values()),
            "orders_by_status": {
                status: order_counts.get(status, 0)
                for status in ("pending", "confirmed", "cancelled")
            },
            "order_items": count(
                SaleOrderItem,
                SaleOrderItem.sale_order_id.in_(
                    select(SaleOrder.id).where(
                        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id
                    )
                ),
            ),
            "historical_media": count(
                CommercialHistoryMedia,
                CommercialHistoryMedia.sale_order_item_id.in_(
                    select(SaleOrderItem.id).where(
                        SaleOrderItem.sale_order_id.in_(
                            select(SaleOrder.id).where(
                                SaleOrder.parent_gallery_id_snapshot
                                == parent_gallery_id
                            )
                        )
                    )
                ),
            ),
        },
    }


def client_unlink_inventory(
    db: Session, *, parent_gallery_id: UUID, client_id: UUID
) -> dict:
    """Conta somente o vínculo operacional escolhido e o histórico preservado."""

    private_ids = select(DerivedGallery.id).where(
        DerivedGallery.parent_gallery_id == parent_gallery_id,
        DerivedGallery.client_id == client_id,
    )

    def count(model, *criteria) -> int:
        return db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0

    order_query = select(SaleOrder.id).where(
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
        SaleOrder.client_id == client_id,
    )
    order_counts = {
        payment_status: total
        for payment_status, total in db.execute(
            select(SaleOrder.payment_status, func.count())
            .where(
                SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
                SaleOrder.client_id == client_id,
            )
            .group_by(SaleOrder.payment_status)
        )
    }
    return {
        "remove": {
            "registrations": count(
                ParentGalleryRegistration,
                ParentGalleryRegistration.parent_gallery_id == parent_gallery_id,
                ParentGalleryRegistration.client_id == client_id,
            ),
            "private_galleries": count(
                DerivedGallery,
                DerivedGallery.parent_gallery_id == parent_gallery_id,
                DerivedGallery.client_id == client_id,
            ),
            "available_references": count(
                DerivedGalleryPhoto,
                DerivedGalleryPhoto.derived_gallery_id.in_(private_ids),
            ),
            "selections": count(
                PhotoSelection, PhotoSelection.derived_gallery_id.in_(private_ids)
            ),
            "favorites": count(
                PhotoFavorite, PhotoFavorite.derived_gallery_id.in_(private_ids)
            ),
            "comments": count(
                PhotoComment, PhotoComment.derived_gallery_id.in_(private_ids)
            ),
            "views": count(PhotoView, PhotoView.derived_gallery_id.in_(private_ids)),
            "private_capabilities": count(
                GalleryAccessCapability,
                GalleryAccessCapability.derived_gallery_id.in_(private_ids),
            ),
        },
        "preserve": {
            "clients": 1,
            "photos": count(
                PhotoAsset, PhotoAsset.parent_gallery_id == parent_gallery_id
            ),
            "orders": sum(order_counts.values()),
            "orders_by_status": {
                status: order_counts.get(status, 0)
                for status in ("pending", "confirmed", "cancelled")
            },
            "order_items": count(
                SaleOrderItem, SaleOrderItem.sale_order_id.in_(order_query)
            ),
        },
    }


def gallery_operational_storage_manifest(
    db: Session, parent_gallery_id: UUID
) -> dict[str, list[dict[str, str]]]:
    """Congela somente chaves operacionais validadas por UUID, sem mídia histórica."""

    retained_photo_ids = select(DerivedGalleryPhoto.photo_asset_id).where(
        DerivedGalleryPhoto.derived_gallery_id.in_(
            select(DerivedGallery.id).where(
                DerivedGallery.parent_gallery_id == parent_gallery_id
            )
        )
    )
    removable_photo_ids = select(PhotoAsset.id).where(
        PhotoAsset.parent_gallery_id == parent_gallery_id,
        PhotoAsset.id.not_in(retained_photo_ids),
    )
    sources = [
        {"photo_id": str(photo_id), "storage_key": storage_key}
        for photo_id, storage_key in db.execute(
            select(PhotoAsset.id, PhotoAsset.storage_key)
            .where(PhotoAsset.id.in_(removable_photo_ids))
            .order_by(PhotoAsset.id)
        )
    ]
    derivatives = [
        {"derivative_id": str(derivative_id), "relative_path": relative_path}
        for derivative_id, relative_path in db.execute(
            select(MediaDerivative.id, MediaDerivative.relative_path)
            .where(
                MediaDerivative.photo_asset_id.in_(
                    removable_photo_ids
                ),
                MediaDerivative.relative_path.is_not(None),
            )
            .order_by(MediaDerivative.id)
        )
    ]
    return {"sources": sources, "derivatives": derivatives}


def claim_next_operation(
    db: Session, *, lease_seconds: int = 120
) -> tuple[UUID, str] | None:
    """Reserva uma operação nova ou interrompida com lease renovável."""

    instant = now()
    operation = db.scalar(
        select(GalleryLifecycleOperation)
        .where(
            GalleryLifecycleOperation.status.in_(("queued", *LIFECYCLE_STAGES)),
            or_(
                GalleryLifecycleOperation.lease_expires_at.is_(None),
                GalleryLifecycleOperation.lease_expires_at <= instant,
            ),
        )
        .order_by(GalleryLifecycleOperation.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if not operation:
        return None
    lease_token = token_hex(24)
    operation.lease_token = lease_token
    operation.lease_expires_at = instant + timedelta(seconds=lease_seconds)
    operation.attempts += 1
    if operation.status == "queued":
        transition_operation(operation, "preparing_history")
    db.commit()
    return operation.id, lease_token


def retry_failed_operation(db: Session, operation: GalleryLifecycleOperation) -> None:
    """Reagenda falha sem apagar o progresso já confirmado."""

    transition_operation(operation, "queued")
    operation.lease_token = None
    operation.lease_expires_at = None
    db.flush()


def sanitized_lifecycle_error(stage: str, error: Exception) -> str:
    if isinstance(error, LifecycleStageUnavailable):
        return str(error)[:500]
    return f"Falha interna na etapa {stage}."


def process_claimed_operation(
    db: Session,
    *,
    operation_id: UUID,
    lease_token: str,
    handlers: Mapping[str, LifecycleStageHandler],
    lease_seconds: int = 120,
) -> GalleryLifecycleOperation:
    """Executa etapas idempotentes e confirma progresso após cada uma."""

    while True:
        operation = db.get(GalleryLifecycleOperation, operation_id)
        if not operation:
            raise LookupError("Operação de ciclo de vida não encontrada.")
        if operation.status == "completed":
            return operation
        if operation.lease_token != lease_token:
            raise LifecycleLeaseConflict("Lease da operação não pertence ao worker.")
        stage = operation.status
        if stage not in LIFECYCLE_STAGES:
            raise InvalidLifecycleTransition(
                f"Operação reservada em estado inesperado: {stage}."
            )
        manifest = _manifest(operation)
        completed_steps = list(manifest.get("completed_steps", []))
        try:
            if stage not in completed_steps:
                handler = handlers.get(stage)
                if not handler:
                    raise LifecycleStageUnavailable(
                        f"Executor indisponível para a etapa {stage}."
                    )
                handler(db, operation)
                manifest = _manifest(operation)
                completed_steps = list(manifest.get("completed_steps", []))
                completed_steps.append(stage)
                manifest["completed_steps"] = completed_steps
                manifest.pop("failed_step", None)
                operation.manifest = manifest
            next_status = {
                "preparing_history": "removing_storage",
                "removing_storage": "removing_records",
                "removing_records": "completed",
            }[stage]
            transition_operation(operation, next_status)
            if next_status == "completed":
                operation.lease_token = None
                operation.lease_expires_at = None
            else:
                operation.lease_expires_at = now() + timedelta(seconds=lease_seconds)
            db.commit()
        except Exception as error:
            db.rollback()
            operation = db.get(GalleryLifecycleOperation, operation_id)
            if not operation or operation.lease_token != lease_token:
                raise LifecycleLeaseConflict(
                    "Lease perdido durante a falha da operação."
                ) from error
            manifest = _manifest(operation)
            manifest["failed_step"] = stage
            operation.manifest = manifest
            transition_operation(
                operation,
                "failed",
                error=sanitized_lifecycle_error(stage, error),
            )
            operation.lease_token = None
            operation.lease_expires_at = None
            db.commit()
            return operation
