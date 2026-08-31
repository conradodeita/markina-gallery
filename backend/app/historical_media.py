"""Preservação mínima e determinística de mídia comercial confirmada."""

import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from shutil import copyfileobj
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    CommercialHistoryMedia,
    MediaDerivative,
    PhotoAsset,
    SaleOrder,
    SaleOrderItem,
)
from app.media import safe_derivative_path, safe_source_path


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


def historical_media_path(storage_key: str) -> Path:
    candidate = (history_root() / storage_key).resolve()
    try:
        candidate.relative_to(history_root())
    except ValueError as exc:
        raise ValueError("Caminho de histórico inválido.") from exc
    return candidate


def _checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_deterministic(source: Path, destination: Path) -> tuple[str, int, bool]:
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
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return source_checksum, source_size, True


def _verify_ready_manifest(
    manifest: CommercialHistoryMedia, item: SaleOrderItem
) -> None:
    if not manifest.preview_storage_key or not manifest.checksum_sha256:
        raise HistoricalMediaConflict("Manifesto pronto não possui prévia verificável.")
    preview = historical_media_path(manifest.preview_storage_key)
    if not preview.is_file() or _checksum(preview) != manifest.checksum_sha256:
        raise HistoricalMediaConflict("Prévia histórica diverge do manifesto.")
    if manifest.delivery_storage_key:
        delivery = historical_media_path(manifest.delivery_storage_key)
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
    client_id: UUID | None = None,
    photo_asset_id: UUID | None = None,
) -> HistoricalMediaReport:
    """Preserva somente itens confirmados do alvo, sem confirmar a transação."""

    order_query = select(SaleOrder.id).where(
        SaleOrder.parent_gallery_id_snapshot == parent_gallery_id,
        SaleOrder.payment_status == "confirmed",
    )
    if client_id:
        order_query = order_query.where(SaleOrder.client_id == client_id)
    if photo_asset_id:
        order_query = order_query.join(
            SaleOrderItem, SaleOrderItem.sale_order_id == SaleOrder.id
        ).where(SaleOrderItem.photo_asset_id_snapshot == photo_asset_id)
    order_ids = set(db.scalars(order_query))
    items = (
        list(
            db.scalars(
                select(SaleOrderItem)
                .where(SaleOrderItem.sale_order_id.in_(order_ids))
                .order_by(SaleOrderItem.id)
                .with_for_update()
            )
        )
        if order_ids
        else []
    )
    report = HistoricalMediaReport(confirmed_items=len(items))
    for item in items:
        manifest = db.scalar(
            select(CommercialHistoryMedia)
            .where(CommercialHistoryMedia.sale_order_item_id == item.id)
            .with_for_update()
        )
        if manifest and manifest.status == "ready":
            _verify_ready_manifest(manifest, item)
            report.reused_items += 1
            continue
        if not manifest:
            manifest = CommercialHistoryMedia(
                sale_order_item_id=item.id,
                status="preparing",
            )
            db.add(manifest)
            db.flush()
        else:
            manifest.status = "preparing"
            manifest.last_error = None

        photo = db.get(PhotoAsset, item.photo_asset_id) if item.photo_asset_id else None
        if not photo:
            raise FileNotFoundError("Foto operacional do item confirmado está ausente.")
        preview_derivative = db.scalar(
            select(MediaDerivative).where(
                MediaDerivative.photo_asset_id == photo.id,
                MediaDerivative.variant == "client_preview",
                MediaDerivative.status == "ready",
            )
        )
        if not preview_derivative:
            raise FileNotFoundError("Prévia protegida do item confirmado está ausente.")

        prefix = f"items/{item.id}"
        preview_key = f"{prefix}/preview.jpg"
        preview_checksum, preview_size, preview_created = _copy_deterministic(
            safe_derivative_path(preview_derivative),
            historical_media_path(preview_key),
        )
        manifest.preview_storage_key = preview_key
        manifest.checksum_sha256 = preview_checksum
        manifest.media_type = "image/jpeg"
        manifest.size_bytes = preview_size
        if preview_created:
            report.preview_bytes += preview_size

        if not manifest.delivery_reference:
            suffix = Path(photo.filename).suffix.lower() or ".bin"
            delivery_key = f"{prefix}/delivery{suffix}"
            delivery_checksum, delivery_size, delivery_created = _copy_deterministic(
                safe_source_path(photo),
                historical_media_path(delivery_key),
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

        manifest.status = "ready"
        manifest.last_error = None
        _verify_ready_manifest(manifest, item)
        report.prepared_items += 1
    db.flush()
    return report
