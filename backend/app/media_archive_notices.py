"""Caixa interna de avisos do arquivo frio, sem transporte externo."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import MediaArchiveCycle, MediaArchiveNotice, MediaArchiveOperation

NOTICE_COPY: dict[str, tuple[str, str]] = {
    "window_7_days": (
        "Uma pasta poderá ser arquivada em 7 dias",
        "A janela normal de reabertura termina em 7 dias. Depois desse prazo, a pasta pode entrar no arquivo frio.",
    ),
    "blocked_open_order": (
        "Arquivo frio aguardando pedido",
        "Uma pasta está elegível para arquivo, mas existe um pedido em aberto. O sistema verificará novamente depois que ele for concluído, cancelado ou reembolsado.",
    ),
    "archive_started": (
        "Transferência para arquivo frio iniciada",
        "A transferência de uma pasta para o arquivo frio começou. A mídia só ficará indisponível após a verificação completa.",
    ),
    "archive_completed": (
        "Pasta enviada ao arquivo frio",
        "A transferência foi verificada e a mídia da pasta ficará indisponível até uma recuperação.",
    ),
    "archive_failed": (
        "Falha ao enviar pasta ao arquivo frio",
        "A transferência não foi concluída. Consulte o estado da operação antes de tentar novamente.",
    ),
    "archive_reconciliation_required": (
        "Transferência para arquivo frio em conferência",
        "O resultado da transferência precisa ser conferido. Consulte o estado da operação antes de solicitar outra tentativa.",
    ),
    "recovery_started": (
        "Recuperação de pasta iniciada",
        "A transferência da pasta para o servidor começou. As fotos voltarão a ficar visíveis depois da verificação completa.",
    ),
    "recovery_completed": (
        "Pasta recuperada",
        "A transferência foi verificada e a pasta voltou a ficar disponível pelo prazo escolhido.",
    ),
    "recovery_failed": (
        "Falha ao recuperar pasta",
        "A transferência não foi concluída. Consulte o estado da operação antes de tentar novamente.",
    ),
    "recovery_reconciliation_required": (
        "Recuperação em conferência",
        "O resultado da transferência precisa ser conferido. Os créditos permanecem reservados enquanto isso.",
    ),
}


_TRANSFER_NOTICE_TYPES = {
    ("archive", "archive_started"): "archive_started",
    ("archive", "archive_completed"): "archive_completed",
    ("archive", "operation_failed"): "archive_failed",
    ("archive", "reconciliation_required"): "archive_reconciliation_required",
    ("restore", "recovery_started"): "recovery_started",
    ("restore", "recovery_completed"): "recovery_completed",
    ("restore", "operation_failed"): "recovery_failed",
    ("restore", "reconciliation_required"): "recovery_reconciliation_required",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)  # noqa: UP017 -- Runtime supports Python 3.10.
    return value.astimezone(timezone.utc)  # noqa: UP017 -- Runtime supports Python 3.10.


def record_notice(
    db: Session,
    *,
    tenant_id: UUID,
    cycle_id: UUID,
    notice_type: str,
    idempotency_key: str,
    at: datetime,
    deadline_at: datetime | None = None,
) -> MediaArchiveNotice:
    """Persiste um aviso fixo na transação chamadora, sem enviar mensagem."""
    copy = NOTICE_COPY.get(notice_type)
    if copy is None or len(idempotency_key) > 192:
        raise ValueError("Aviso de arquivo frio inválido.")
    existing = db.scalar(select(MediaArchiveNotice).where(
        MediaArchiveNotice.tenant_id == tenant_id,
        MediaArchiveNotice.idempotency_key == idempotency_key,
    ))
    if existing:
        return existing

    notice = MediaArchiveNotice(
        tenant_id=tenant_id,
        cycle_id=cycle_id,
        notice_type=notice_type,
        idempotency_key=idempotency_key,
        title=copy[0],
        body=copy[1],
        deadline_at=_utc(deadline_at) if deadline_at is not None else None,
        created_at=_utc(at),
    )
    try:
        with db.begin_nested():
            db.add(notice)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(MediaArchiveNotice).where(
            MediaArchiveNotice.tenant_id == tenant_id,
            MediaArchiveNotice.idempotency_key == idempotency_key,
        ))
        if existing is None:
            raise
        return existing
    return notice


def record_transfer_notice(
    db: Session,
    *,
    operation: MediaArchiveOperation,
    event_type: str,
    at: datetime,
) -> MediaArchiveNotice | None:
    notice_type = _TRANSFER_NOTICE_TYPES.get((operation.operation_type, event_type))
    if notice_type is None:
        return None
    cycle = db.get(MediaArchiveCycle, operation.cycle_id)
    if cycle is None or cycle.tenant_id != operation.tenant_id:
        raise ValueError("Ciclo incompatível com o aviso de transferência.")
    return record_notice(
        db,
        tenant_id=operation.tenant_id,
        cycle_id=cycle.id,
        notice_type=notice_type,
        idempotency_key=f"{notice_type}:{operation.id}",
        at=at,
    )


def supersede_window_notices_for_folder(
    db: Session,
    *,
    tenant_id: UUID,
    folder_id: UUID,
    current_deadline: datetime,
    at: datetime,
) -> int:
    """Marca prazos notificados anteriormente quando uma reabertura os altera."""
    deadline = _utc(current_deadline)
    notices = db.scalars(
        select(MediaArchiveNotice)
        .join(
            MediaArchiveCycle,
            and_(
                MediaArchiveCycle.id == MediaArchiveNotice.cycle_id,
                MediaArchiveCycle.tenant_id == MediaArchiveNotice.tenant_id,
            ),
        )
        .where(
            MediaArchiveNotice.tenant_id == tenant_id,
            MediaArchiveCycle.folder_id == folder_id,
            MediaArchiveNotice.notice_type == "window_7_days",
            MediaArchiveNotice.deadline_at.is_not(None),
            MediaArchiveNotice.superseded_at.is_(None),
        )
        .with_for_update(of=MediaArchiveNotice)
    )
    superseded = 0
    instant = _utc(at)
    for notice in notices:
        if _utc(notice.deadline_at) != deadline:
            notice.superseded_at = instant
            superseded += 1
    return superseded


def record_window_notice(
    db: Session,
    *,
    tenant_id: UUID,
    folder_id: UUID,
    cycle_id: UUID,
    effective_expiry: datetime,
    eligible_at: datetime,
    at: datetime,
) -> MediaArchiveNotice:
    supersede_window_notices_for_folder(
        db,
        tenant_id=tenant_id,
        folder_id=folder_id,
        current_deadline=eligible_at,
        at=at,
    )
    expiry = _utc(effective_expiry)
    return record_notice(
        db,
        tenant_id=tenant_id,
        cycle_id=cycle_id,
        notice_type="window_7_days",
        idempotency_key=f"window_7_days:{folder_id}:{int(expiry.timestamp())}",
        deadline_at=eligible_at,
        at=at,
    )


def record_open_order_block_notice(
    db: Session,
    *,
    tenant_id: UUID,
    cycle_id: UUID,
    at: datetime,
) -> MediaArchiveNotice:
    return record_notice(
        db,
        tenant_id=tenant_id,
        cycle_id=cycle_id,
        notice_type="blocked_open_order",
        idempotency_key=f"blocked_open_order:{cycle_id}",
        at=at,
    )
