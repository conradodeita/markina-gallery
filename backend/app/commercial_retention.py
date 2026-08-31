"""Retenção explícita de mídia e minimização autorizada de PII comercial."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from os import getenv
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuditEvent, CommercialHistoryMedia, SaleOrder, SaleOrderItem, now
from app.historical_media import historical_media_path


class CommercialRetentionConfigurationError(ValueError):
    """A política configurada não é explícita ou segura para execução."""


class CommercialPiiMinimizationNotAuthorized(PermissionError):
    """A decisão externa necessária para minimizar PII não foi confirmada."""


@dataclass(frozen=True)
class CommercialRetentionPolicy:
    media_retention_days: int | None


@dataclass
class CommercialRetentionReport:
    eligible_items: int = 0
    purged_items: int = 0
    removed_files: int = 0


def commercial_retention_policy() -> CommercialRetentionPolicy:
    """Carrega uma duração explícita; vazio significa nenhuma limpeza automática."""

    raw_days = getenv("COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS", "").strip()
    if not raw_days:
        return CommercialRetentionPolicy(media_retention_days=None)
    try:
        days = int(raw_days)
    except ValueError as exc:
        raise CommercialRetentionConfigurationError(
            "COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS deve ser um inteiro positivo."
        ) from exc
    if days <= 0:
        raise CommercialRetentionConfigurationError(
            "COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS deve ser um inteiro positivo."
        )
    return CommercialRetentionPolicy(media_retention_days=days)


def apply_commercial_media_retention(
    db: Session,
    *,
    instant: datetime | None = None,
    policy: CommercialRetentionPolicy | None = None,
) -> CommercialRetentionReport:
    """Expurga somente mídia histórica vencida, preservando pedidos e itens."""

    effective_policy = policy or commercial_retention_policy()
    report = CommercialRetentionReport()
    if effective_policy.media_retention_days is None:
        return report
    instant = instant or now()
    cutoff = instant - timedelta(days=effective_policy.media_retention_days)
    rows = list(
        db.execute(
            select(CommercialHistoryMedia)
            .add_columns(SaleOrder.confirmed_at)
            .join(
                SaleOrderItem,
                SaleOrderItem.id == CommercialHistoryMedia.sale_order_item_id,
            )
            .join(SaleOrder, SaleOrder.id == SaleOrderItem.sale_order_id)
            .where(
                CommercialHistoryMedia.status == "ready",
                SaleOrder.payment_status == "confirmed",
                SaleOrder.confirmed_at.is_not(None),
                SaleOrder.confirmed_at <= cutoff,
            )
            .with_for_update()
        )
    )
    report.eligible_items = len(rows)
    for manifest, confirmed_at in rows:
        for storage_key in (
            manifest.preview_storage_key,
            manifest.delivery_storage_key,
        ):
            if storage_key:
                path = historical_media_path(storage_key)
                if path.is_file():
                    path.unlink()
                    report.removed_files += 1
        manifest.preview_storage_key = None
        manifest.delivery_storage_key = None
        manifest.delivery_reference = None
        manifest.checksum_sha256 = None
        manifest.media_type = None
        manifest.size_bytes = None
        manifest.status = "purged"
        manifest.retention_expires_at = confirmed_at + timedelta(
            days=effective_policy.media_retention_days
        )
        manifest.purged_at = instant
        manifest.last_error = None
        report.purged_items += 1
    db.flush()
    return report


def minimize_client_commercial_pii(
    db: Session,
    *,
    client_id: UUID,
    permitted: bool,
    instant: datetime | None = None,
) -> int:
    """Minimiza snapshots pessoais após decisão externa expressamente permitida."""

    if not permitted:
        raise CommercialPiiMinimizationNotAuthorized(
            "A minimização depende de autorização de privacidade válida."
        )
    instant = instant or now()
    changed = 0
    for order in db.scalars(
        select(SaleOrder).where(SaleOrder.client_id == client_id).with_for_update()
    ):
        if order.client_name_snapshot is not None or order.client_phone_snapshot is not None:
            order.client_name_snapshot = None
            order.client_phone_snapshot = None
            changed += 1
        order.pii_minimized_at = order.pii_minimized_at or instant
    if changed:
        db.add(
            AuditEvent(
                event="commercial_history.pii_minimized",
                subject=f"client_id:{client_id};orders:{changed}",
            )
        )
    db.flush()
    return changed
