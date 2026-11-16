"""Projeção privada do histórico; não modifica lançamentos financeiros."""

from datetime import UTC
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, case, cast, func, literal, select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCycle,
    MediaArchiveOperation,
    ParentGallery,
    PhotoAsset,
    PhotoCreditOperation,
    PhotoCreditOperationEvent,
    PhotoFolder,
    PhotographerCreditEntry,
    TenantCreditWallet,
    now,
)


def photo_history_context(db: Session, tenant_id: UUID, photo_id: UUID) -> dict[str, str]:
    """Conserva somente a proveniência comprovada, sem interpretar storage_key."""
    row = db.execute(select(
        PhotoFolder.id, PhotoFolder.name, ParentGallery.id, ParentGallery.name,
    ).select_from(PhotoAsset).join(PhotoFolder, (
        (PhotoFolder.id == PhotoAsset.folder_id)
        & (PhotoFolder.parent_gallery_id == PhotoAsset.parent_gallery_id)
        & (PhotoFolder.tenant_id == tenant_id)
    )).join(ParentGallery, (
        (ParentGallery.id == PhotoAsset.parent_gallery_id)
        & (ParentGallery.tenant_id == tenant_id)
    )).where(PhotoAsset.id == photo_id, PhotoAsset.tenant_id == tenant_id)).one_or_none()
    if row is None:
        return {}
    return {
        "folder_id_snapshot": str(row[0]),
        "folder_name_snapshot": row[1],
        "parent_gallery_id_snapshot": str(row[2]),
        "parent_gallery_name_snapshot": row[3],
    }


def _uuid_text(value):
    # UUID nativo no PostgreSQL e CHAR(32) no SQLite têm a mesma chave de agrupamento.
    return func.lower(func.replace(cast(value, String), "-", ""))


def _history_rows(tenant_id: UUID, as_of):
    event = PhotoCreditOperationEvent
    contexts = select(
        event.operation_id,
        event.details["folder_id_snapshot"].as_string().label("folder_id"),
        event.details["folder_name_snapshot"].as_string().label("folder_name"),
        event.details["parent_gallery_id_snapshot"].as_string().label("gallery_id"),
        event.details["parent_gallery_name_snapshot"].as_string().label("gallery_name"),
        func.row_number().over(
            partition_by=event.operation_id, order_by=(event.occurred_at, event.id),
        ).label("position"),
    ).where(
        event.tenant_id == tenant_id, event.event_type == "reserved",
        event.details["folder_id_snapshot"].as_string().is_not(None),
    ).subquery()
    context = select(contexts).where(contexts.c.position == 1).subquery()
    entry, operation, asset = PhotographerCreditEntry, PhotoCreditOperation, PhotoAsset
    archive_operation, archive_cycle = MediaArchiveOperation, MediaArchiveCycle
    provenance = select(
        entry.id, entry.entry_type, entry.delta, entry.source_reference,
        entry.description, entry.created_at,
        func.coalesce(
            _uuid_text(context.c.folder_id),
            _uuid_text(archive_cycle.folder_id),
            _uuid_text(asset.folder_id),
        ).label("folder_id"),
        func.coalesce(
            _uuid_text(context.c.gallery_id),
            _uuid_text(archive_cycle.parent_gallery_id),
            _uuid_text(asset.parent_gallery_id),
        ).label("gallery_id"),
        context.c.folder_name.label("snapshot_folder_name"),
        context.c.gallery_name.label("snapshot_gallery_name"),
    ).select_from(entry).outerjoin(operation, (
        (operation.id == entry.operation_id) & (operation.tenant_id == tenant_id)
    )).outerjoin(archive_operation, (
        (archive_operation.id == entry.archive_operation_id)
        & (archive_operation.tenant_id == tenant_id)
    )).outerjoin(archive_cycle, (
        (archive_cycle.id == archive_operation.cycle_id)
        & (archive_cycle.tenant_id == tenant_id)
    )).outerjoin(context, context.c.operation_id == operation.id).outerjoin(asset, (
        (asset.id == operation.photo_asset_id_snapshot) & (asset.tenant_id == tenant_id)
    )).where(entry.tenant_id == tenant_id, entry.created_at <= as_of).subquery()
    upload = provenance.c.entry_type == "upload_consumption"
    group_key = case(
        (upload & provenance.c.folder_id.is_not(None), literal("folder:") + provenance.c.folder_id),
        else_=literal("entry:") + _uuid_text(provenance.c.id),
    )
    return select(
        provenance,
        group_key.label("group_key"),
        func.coalesce(PhotoFolder.name, provenance.c.snapshot_folder_name).label("folder_name"),
        func.coalesce(ParentGallery.name, provenance.c.snapshot_gallery_name).label("gallery_name"),
    ).outerjoin(PhotoFolder, (
        (_uuid_text(PhotoFolder.id) == provenance.c.folder_id) & (PhotoFolder.tenant_id == tenant_id)
    )).outerjoin(ParentGallery, (
        (_uuid_text(ParentGallery.id) == provenance.c.gallery_id) & (ParentGallery.tenant_id == tenant_id)
    )).subquery()


def _utc(value):
    return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


def _limits(limit: int, offset: int):
    if not 1 <= limit <= 30 or not 0 <= offset <= 100000:
        raise HTTPException(422, "Paginação de histórico inválida.")


def _require_wallet(db, tenant_id):
    if db.get(TenantCreditWallet, tenant_id) is None:
        raise HTTPException(404, "Carteira não encontrada.")


def history_page(db: Session, tenant_id: UUID, *, limit: int = 30, offset: int = 0, as_of=None):
    """Agrupa antes do LIMIT; um upload não é uma linha do resumo da pasta."""
    _limits(limit, offset)
    _require_wallet(db, tenant_id)
    as_of = _utc(as_of or now())
    rows = _history_rows(tenant_id, as_of)
    totals = select(
        rows.c.group_key,
        func.sum(rows.c.delta).label("delta"),
        func.sum(case((rows.c.entry_type == "upload_consumption", 1), else_=0)).label("photo_count"),
        func.min(rows.c.created_at).label("first_at"),
        func.max(rows.c.created_at).label("last_at"),
    ).group_by(rows.c.group_key).subquery()
    latest = select(rows, func.row_number().over(
        partition_by=rows.c.group_key,
        order_by=(rows.c.created_at.desc(), rows.c.id.desc()),
    ).label("latest_position")).subquery()
    records = db.execute(select(
        totals, latest.c.entry_type, latest.c.source_reference, latest.c.description,
        latest.c.folder_id, latest.c.folder_name, latest.c.gallery_id, latest.c.gallery_name,
    ).join(latest, (latest.c.group_key == totals.c.group_key) & (latest.c.latest_position == 1))
        .order_by(totals.c.last_at.desc(), totals.c.group_key.desc())
        .limit(limit + 1).offset(offset)).mappings().all()
    items = []
    for row in records[:limit]:
        folder = row["group_key"].startswith("folder:")
        items.append({
            "id": row["group_key"],
            "type": "folder_upload" if folder else row["entry_type"],
            "delta": int(row["delta"]), "photo_count": int(row["photo_count"]),
            "source_reference": str(UUID(row["folder_id"])) if folder else row["source_reference"],
            "description": row["folder_name"] if folder else row["description"],
            "folder_id": (
                str(UUID(row["folder_id"]))
                if folder or row["entry_type"] == "archive_recovery" else None
            ),
            "related_folder_name": (
                row["folder_name"] if row["entry_type"] == "archive_recovery" else None
            ),
            "gallery_name": row["gallery_name"] if folder else None,
            "created_at": _utc(row["last_at"]), "first_at": _utc(row["first_at"]),
            "last_at": _utc(row["last_at"]),
            "folder_unidentified": row["entry_type"] == "upload_consumption" and not folder,
        })
    return {"items": items, "has_more": len(records) > limit, "as_of": as_of}


def folder_entry_page(db: Session, tenant_id: UUID, folder_id: UUID, *, limit: int = 20, offset: int = 0, as_of=None):
    _limits(limit, offset)
    _require_wallet(db, tenant_id)
    as_of = _utc(as_of or now())
    rows = _history_rows(tenant_id, as_of)
    folder_key = "folder:" + folder_id.hex
    archive_entry = (
        (rows.c.entry_type == "archive_recovery")
        & (rows.c.folder_id == folder_id.hex)
    )
    records = db.execute(select(rows).where(
        (rows.c.group_key == folder_key) | archive_entry,
    ).order_by(rows.c.created_at.desc(), rows.c.id.desc()).limit(limit + 1).offset(offset)).mappings().all()
    if not records:
        exists = offset > 0 and db.scalar(select(rows.c.id).where(
            (rows.c.group_key == folder_key) | archive_entry,
        ).limit(1)) is not None
        if not exists:
            raise HTTPException(404, "Histórico da pasta não encontrado.")
    return {"items": [{
        "id": str(row["id"]), "type": row["entry_type"], "delta": row["delta"],
        "source_reference": row["source_reference"], "description": row["description"],
        "created_at": _utc(row["created_at"]),
    } for row in records[:limit]], "has_more": len(records) > limit, "as_of": as_of}
