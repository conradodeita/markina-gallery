"""Avaliação conservadora e tenant-scoped das pendências de encerramento."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    FacialSearchNotificationOutbox,
    GalleryMembershipNotificationOutbox,
    GalleryReopeningNotificationOutbox,
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    MediaJob,
    MercadoPagoCreditPurchase,
    MercadoPagoPayment,
    NotificationDelivery,
    PhotoAsset,
    PhotoCreditOperation,
    PhotoFolder,
    PreviewAdjustment,
    SaleOrder,
    Tenant,
    WhatsAppDelivery,
    now,
)
from app.folder_access import folder_archive_eligible_at
from app.media_archive_guards import (
    archive_blocker,
    isolated_closure_cover_folder,
    never_released_closure_folder,
)
from app.media_archive_manifest import MediaArchiveManifestError, validate_stored_archive_manifest
from app.mercadopago_credit_purchases import financial_review_count
from app.order_delivery import unresolved_order_condition


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)  # noqa: UP017


def _exists(db: Session, model, tenant_id: UUID, *conditions) -> bool:
    return db.scalar(select(1).select_from(model).where(
        model.tenant_id == tenant_id, *conditions).limit(1)) is not None


def operational_obligation_blockers(db: Session, tenant_id: UUID) -> list[str]:
    """Critérios compartilhados; o chamador valida lifecycle e autorização."""
    reasons = set()
    if _exists(db, SaleOrder, tenant_id, unresolved_order_condition()):
        reasons.add("open_order")
    if _exists(db, MercadoPagoCreditPurchase, tenant_id,
               MercadoPagoCreditPurchase.state.in_(("submitting", "initiated", "pending", "processing", "verification_required"))):
        reasons.add("pending_payment")
    if _exists(db, MercadoPagoPayment, tenant_id,
               MercadoPagoPayment.state.in_(("sending", "initiated", "pending", "processing", "verification_required"))):
        reasons.add("pending_payment")
    if financial_review_count(db, tenant_id):
        reasons.add("financial_review")
    for model, status_column, statuses in (
        (MediaJob, MediaJob.status, ("queued", "processing")),
        (PreviewAdjustment, PreviewAdjustment.status, ("queued", "processing")),
        (PhotoCreditOperation, PhotoCreditOperation.status, ("reserved", "reconciliation_required")),
        (MediaArchiveOperation, MediaArchiveOperation.status, ("queued", "processing", "reconciliation_required")),
        (NotificationDelivery, NotificationDelivery.status, ("processing",)),
        (WhatsAppDelivery, WhatsAppDelivery.status, ("processing",)),
        (GalleryMembershipNotificationOutbox, GalleryMembershipNotificationOutbox.external_status, ("processing",)),
        (GalleryReopeningNotificationOutbox, GalleryReopeningNotificationOutbox.status, ("processing",)),
        (FacialSearchNotificationOutbox, FacialSearchNotificationOutbox.status, ("processing",)),
    ):
        if _exists(db, model, tenant_id, status_column.in_(statuses)):
            reasons.add("processing_pending")

    return sorted(reasons)


def _evaluate(db: Session, tenant_id: UUID, at: datetime) -> list[str]:
    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    if not tenant or tenant.lifecycle != "closing" or tenant.status != "active":
        return ["account_not_closing"]
    reasons = set(operational_obligation_blockers(db, tenant_id))
    all_folders = list(db.scalars(select(PhotoFolder).where(PhotoFolder.tenant_id == tenant_id)))
    folders = [folder for folder in all_folders
               if folder.purpose == "content" or isolated_closure_cover_folder(db, folder)]
    covered_sources = set()
    for folder in folders:
        if folder.purpose == "content" and not never_released_closure_folder(db, folder):
            eligibility = folder_archive_eligible_at(db, folder)
            if eligibility is None:
                reasons.add("deadline_required")
            elif _utc(eligibility) > at:
                reasons.add("access_window")
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.tenant_id == tenant_id, MediaArchiveCycle.folder_id == folder.id,
        ).order_by(MediaArchiveCycle.cycle_number.desc()).limit(1))
        if cycle is None or cycle.state not in {"archived", "deleted"}:
            reasons.add("media_not_archived")
            blocker = archive_blocker(db, folder, at=at)
            if blocker and blocker != "not_eligible":
                reasons.add(blocker)
            continue
        operation_type = "delete_remote" if cycle.state == "deleted" else "archive"
        if not _exists(db, MediaArchiveOperation, tenant_id,
                       MediaArchiveOperation.cycle_id == cycle.id,
                       MediaArchiveOperation.operation_type == operation_type,
                       MediaArchiveOperation.status == "completed"):
            reasons.add("archive_verification_pending")
            continue
        if cycle.state == "archived":
            try:
                manifest, _ = validate_stored_archive_manifest(cycle)
                objects = list(db.scalars(select(MediaArchiveObject).where(
                    MediaArchiveObject.tenant_id == tenant_id, MediaArchiveObject.cycle_id == cycle.id)))
                by_ref = {obj.source_ref: obj for obj in objects}
                expected = {item["source_ref"] for item in manifest["objects"]} | {"manifest:v1"}
                if set(by_ref) != expected:
                    raise MediaArchiveManifestError("Catálogo incompleto.")
                for item in manifest["objects"]:
                    obj = by_ref[item["source_ref"]]
                    if (str(obj.id) != item["object_id"] or obj.remote_object_id != item["remote_object_id"]
                            or obj.sha256 != item["sha256"] or obj.size_bytes != item["size_bytes"]):
                        raise MediaArchiveManifestError("Catálogo divergente.")
                manifest_row = by_ref["manifest:v1"]
                if not manifest_row.remote_object_id or manifest_row.sha256 != cycle.manifest_sha256:
                    raise MediaArchiveManifestError("Manifesto remoto não confirmado.")
                covered_sources.update(item["source_ref"] for item in manifest["objects"])
            except (MediaArchiveManifestError, KeyError, TypeError, ValueError):
                reasons.add("archive_verification_pending")
        elif cycle.manifest:
            covered_sources.update(item.get("source_ref") for item in cycle.manifest.get("objects", []))
    if _exists(db, PhotoAsset, tenant_id, PhotoAsset.folder_id.is_(None)):
        reasons.add("unassigned_media")
    if not folders and _exists(db, PhotoAsset, tenant_id):
        reasons.add("media_not_archived")
    if any(f"photo:{identity}:original" not in covered_sources
           for identity in db.scalars(select(PhotoAsset.id).where(PhotoAsset.tenant_id == tenant_id))):
        reasons.add("media_not_archived")
    return sorted(reasons)


def evaluate_closure(db: Session, tenant_id: UUID, *, at: datetime | None = None) -> dict:
    instant = at or now()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("O instante da avaliação precisa conter fuso horário.")
    try:
        with db.begin_nested():
            reasons = _evaluate(db, tenant_id, _utc(instant))
    except SQLAlchemyError:
        reasons = ["source_unavailable"]
    return {"ready": not reasons, "blockers": reasons, "observed_at": instant.isoformat()}
