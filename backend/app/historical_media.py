"""Preservação mínima e determinística de mídia comercial confirmada."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from shutil import copyfileobj
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.acervo_context import owned_record, require_active_owner
from app.auth import (
    CommercialHistoryMedia,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    SaleOrder,
    SaleOrderItem,
)
from app.media import safe_derivative_path, safe_source_path
from app.order_delivery import fulfillable_order_condition


class HistoricalMediaConflict(RuntimeError):
    """Arquivo histórico existente diverge do checksum registrado."""


@dataclass
class HistoricalMediaReport:
    confirmed_items: int = 0
    prepared_items: int = 0
    reused_items: int = 0
    preview_bytes: int = 0
    delivery_bytes: int = 0


def history_root() -> Path:
    return Path(os.getenv("MEDIA_HISTORY_ROOT", "./media/history")).resolve()


def historical_media_path(storage_key: str, *, tenant_id: UUID | None = None, item_id: UUID | None = None) -> Path:
    from app.media import media_namespace
    if tenant_id is not None:
        media_namespace(storage_key, tenant_id)
        if item_id is not None and not storage_key.startswith((f"items/{item_id}/", f"tenants/{tenant_id}/items/{item_id}/")):
            raise ValueError("Caminho de histórico inválido.")
    candidate = (history_root() / storage_key).resolve()
    try:
        candidate.relative_to(history_root())
    except ValueError as exc:
        raise ValueError("Caminho de histórico inválido.") from exc
    if tenant_id is not None:
        resolved_key = candidate.relative_to(history_root()).as_posix()
        media_namespace(resolved_key, tenant_id)
        if item_id is not None and not resolved_key.startswith((f"items/{item_id}/", f"tenants/{tenant_id}/items/{item_id}/")):
            raise ValueError("Caminho de histórico inválido.")
    return candidate


def _checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_deterministic(source: Path, destination: Path, *, authorize: Callable[[], None]) -> tuple[str, int, bool]:
    authorize()
    if not source.is_file():
        raise FileNotFoundError("Mídia operacional necessária está indisponível.")
    source_checksum = _checksum(source)
    source_size = source.stat().st_size
    if destination.exists():
        if _checksum(destination) != source_checksum:
            raise HistoricalMediaConflict(
                "Arquivo histórico existente diverge da mídia operacional."
            )
        return source_checksum, source_size, False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    try:
        with source.open("rb") as source_stream, temporary.open("wb") as target_stream:
            copyfileobj(source_stream, target_stream, length=1024 * 1024)
        if _checksum(temporary) != source_checksum:
            raise HistoricalMediaConflict("Cópia histórica falhou na verificação.")
        authorize()
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return source_checksum, source_size, True


def _verify_ready_manifest(
    manifest: CommercialHistoryMedia, item: SaleOrderItem
) -> None:
    if not manifest.preview_storage_key or not manifest.checksum_sha256:
        raise HistoricalMediaConflict("Manifesto pronto não possui prévia verificável.")
    preview = historical_media_path(manifest.preview_storage_key, tenant_id=manifest.tenant_id, item_id=item.id)
    if not preview.is_file() or _checksum(preview) != manifest.checksum_sha256:
        raise HistoricalMediaConflict("Prévia histórica diverge do manifesto.")
    if manifest.delivery_storage_key:
        delivery = historical_media_path(manifest.delivery_storage_key, tenant_id=manifest.tenant_id, item_id=item.id)
        if not delivery.is_file():
            raise HistoricalMediaConflict("Entrega histórica está ausente.")
        if item.checksum_sha256_snapshot and _checksum(delivery) != item.checksum_sha256_snapshot:
            raise HistoricalMediaConflict("Entrega histórica diverge do item comercial.")
    elif not manifest.delivery_reference:
        raise HistoricalMediaConflict("Item histórico não possui entrega nem referência segura.")


def prepare_confirmed_historical_media(
    db: Session,
    *,
    parent_gallery_id: UUID,
    tenant_id: UUID,
    client_id: UUID | None = None,
    photo_asset_id: UUID | None = None,
    authorize: Callable[[], object] | None = None,
) -> HistoricalMediaReport:
    """Preserva itens confirmados ou finalizados sem cobrança do alvo, sem confirmar a transação."""

    if not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id):
        raise ValueError("Galeria indisponível.")
    order_query = select(SaleOrder.id).where(
        SaleOrder.tenant_id == tenant_id,
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
        fulfillable_order_condition(),
    )
    if client_id:
        order_query = order_query.where(SaleOrder.client_id == client_id)
    if photo_asset_id:
        order_query = order_query.join(
            SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id
        ).where(SaleOrderItem.tenant_id == tenant_id, SaleOrderItem.photo_asset_id_snapshot == photo_asset_id)
    order_ids = set(db.scalars(order_query))
    items = (
        list(
            db.scalars(
                select(SaleOrderItem)
                .where(SaleOrderItem.tenant_id == tenant_id, SaleOrderItem.sale_order_id.in_(order_ids))
                .order_by(SaleOrderItem.id)
                .with_for_update()
            )
        )
        if order_ids
        else []
    )
    report = HistoricalMediaReport(confirmed_items=len(items))
    for item in items:
        require_active_owner(db, tenant_id)
        manifest = db.scalar(
            select(CommercialHistoryMedia)
            .where(CommercialHistoryMedia.tenant_id == tenant_id, CommercialHistoryMedia.sale_order_item_id == item.id)
            .with_for_update()
        )
        if manifest and manifest.status == "ready":
            _verify_ready_manifest(manifest, item)
            report.reused_items += 1
            continue
        if not manifest:
            manifest = CommercialHistoryMedia(
                tenant_id=tenant_id,
                sale_order_item_id=item.id,
                status="preparing",
            )
            db.add(manifest)
            db.flush()
        else:
            manifest.status = "preparing"
            manifest.last_error = None

        photo = owned_record(db, PhotoAsset, item.photo_asset_id, tenant_id=tenant_id) if item.photo_asset_id else None
        if not photo or photo.parent_gallery_id != parent_gallery_id:
            raise FileNotFoundError("Foto operacional do item confirmado está ausente.")
        preview_derivative = db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.tenant_id == tenant_id,
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
        )
        if not preview_derivative:
            raise FileNotFoundError("Prévia protegida do item confirmado está ausente.")

        def authorize_copy(photo_id=photo.id):
            if authorize:
                authorize()
            if (not owned_record(db, ParentGallery, parent_gallery_id, tenant_id=tenant_id)
                    or not owned_record(db, PhotoAsset, photo_id, tenant_id=tenant_id)):
                raise FileNotFoundError("Origem histórica indisponível.")

        prefix = f"tenants/{tenant_id}/items/{item.id}"
        preview_key = manifest.preview_storage_key or f"{prefix}/preview.jpg"
        preview_checksum, preview_size, preview_created = _copy_deterministic(
            safe_derivative_path(preview_derivative),
            historical_media_path(preview_key, tenant_id=tenant_id, item_id=item.id),
            authorize=authorize_copy,
        )
        manifest.preview_storage_key = preview_key
        manifest.checksum_sha256 = preview_checksum
        manifest.media_type = "image/jpeg"
        manifest.size_bytes = preview_size
        if preview_created:
            report.preview_bytes += preview_size

        if not manifest.delivery_reference:
            suffix = Path(photo.filename).suffix.lower() or ".bin"
            delivery_key = manifest.delivery_storage_key or f"{prefix}/delivery{suffix}"
            delivery_checksum, delivery_size, delivery_created = _copy_deterministic(
                safe_source_path(photo),
                historical_media_path(delivery_key, tenant_id=tenant_id, item_id=item.id),
                authorize=authorize_copy,
            )
            manifest.delivery_storage_key = delivery_key
            item.checksum_sha256_snapshot = (
                item.checksum_sha256_snapshot or delivery_checksum
            )
            if item.checksum_sha256_snapshot != delivery_checksum:
                raise HistoricalMediaConflict(
                    "Entrega operacional diverge do checksum comercial congelado."
                )
            if delivery_created:
                report.delivery_bytes += delivery_size
        else:
            manifest.delivery_storage_key = None

        require_active_owner(db, tenant_id)
        manifest.status = "ready"
        manifest.last_error = None
        _verify_ready_manifest(manifest, item)
        report.prepared_items += 1
    db.flush()
    return report
