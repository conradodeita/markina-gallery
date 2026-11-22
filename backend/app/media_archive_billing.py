"""Reserva e cobrança idempotente de recuperações de arquivo frio."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCycle,
    MediaArchiveEvent,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditAllocationEvent,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    MediaArchiveRecoveryRequest,
    PhotoFolder,
    PhotographerCreditEntry,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureRecoveryItem,
    TenantCreditWallet,
    audit,
    now,
)
from app.mercadopago_credit_purchases import tenant_has_financial_hold
from app.photographer_credits import _lock_wallet, _source_available, wallet_snapshot
from app.system_monitor.access import is_owner

ALLOWED_RECOVERY_DURATIONS = (7, 14, 30)
_HELD_RESERVATION_STATES = ("reserved", "reconciliation_required")


def recovery_is_exempt(request: MediaArchiveRecoveryRequest) -> bool:
    return bool(request.owner_exempt or request.technical_cover_exempt)


def _is_platform_owner_tenant(db: Session, tenant_id: UUID) -> bool:
    from app.system_monitor.models import PlatformOwner

    tenant_ids = list(db.scalars(select(TenantAdmin.tenant_id).join(
        PlatformOwner, PlatformOwner.admin_user_id == TenantAdmin.admin_user_id,
    ).where(
        PlatformOwner.singleton == 1,
        TenantAdmin.active.is_(True),
    ).limit(2)))
    return len(tenant_ids) == 1 and tenant_ids[0] == tenant_id


def _owner_wallet_exemption(db: Session, tenant_id: UUID, wallet: TenantCreditWallet) -> bool:
    if wallet.mode != "unmetered":
        return False
    if not _is_platform_owner_tenant(db, tenant_id):
        raise HTTPException(503, "A carteira da conta precisa ser revisada.")
    return True


def recovery_pricing_payload(db: Session, tenant_id: UUID, admin_id: UUID) -> dict[str, object]:
    """Retorna preço dinâmico e saldo autoritativo para a conta autenticada."""
    wallet = db.get(TenantCreditWallet, tenant_id)
    if wallet is None:
        raise HTTPException(503, "Carteira indisponível.")
    setting = db.get(MediaArchiveRecoveryPricing, 1)
    owner_exempt = _owner_wallet_exemption(db, tenant_id, wallet)
    return {
        "recovery_fee_credits": setting.recovery_fee_credits if setting else None,
        "configured": bool(setting and setting.recovery_fee_credits is not None),
        "owner_exempt": owner_exempt,
        "available_credits": wallet_snapshot(db, tenant_id)["available_credits"],
        "duration_days": list(ALLOWED_RECOVERY_DURATIONS),
        "can_manage": is_owner(db, admin_id),
    }


def owner_recovery_pricing(db: Session, owner_admin_id: UUID) -> dict[str, object]:
    if not is_owner(db, owner_admin_id):
        raise HTTPException(403, "Acesso não autorizado.")
    setting = db.get(MediaArchiveRecoveryPricing, 1)
    return {
        "recovery_fee_credits": setting.recovery_fee_credits if setting else None,
        "configured": bool(setting and setting.recovery_fee_credits is not None),
        "updated_at": setting.updated_at if setting else None,
        "updated_by_admin_id": str(setting.updated_by_admin_id) if setting and setting.updated_by_admin_id else None,
    }


def update_recovery_pricing(
    db: Session,
    owner_admin_id: UUID,
    fee_credits: int | None,
    *,
    request_id: UUID,
) -> dict[str, object]:
    """Atualiza preço global com auditoria idempotente do PlatformOwner."""
    if not is_owner(db, owner_admin_id):
        raise HTTPException(403, "Acesso não autorizado.")
    if fee_credits is not None and (type(fee_credits) is not int or not 1 <= fee_credits <= 2_147_483_647):
        raise HTTPException(422, "A taxa deve ser uma quantidade inteira positiva de créditos.")
    value_fingerprint = sha256(
        f"media-archive-recovery-fee:v1:{fee_credits if fee_credits is not None else 'unset'}".encode("ascii")
    ).hexdigest()

    previous_event = db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    ))
    if previous_event is not None:
        setting = db.get(MediaArchiveRecoveryPricing, 1)
        if (
            previous_event.actor_admin_id != owner_admin_id
            or previous_event.action != "media_archive.recovery_pricing_updated"
            or previous_event.target_version != value_fingerprint
        ):
            raise HTTPException(409, "Identificador de ação já utilizado.")
        return owner_recovery_pricing(db, owner_admin_id)

    setting = db.scalar(select(MediaArchiveRecoveryPricing).where(
        MediaArchiveRecoveryPricing.id == 1,
    ).with_for_update())
    if setting is None:
        setting = MediaArchiveRecoveryPricing(id=1)
        db.add(setting)
        db.flush()
    previous_status = "configured" if setting.recovery_fee_credits is not None else "unconfigured"
    next_status = "configured" if fee_credits is not None else "unconfigured"
    setting.recovery_fee_credits = fee_credits
    setting.updated_by_admin_id = owner_admin_id
    setting.updated_at = now()
    db.add(PlatformAdminEvent(
        request_id=request_id,
        actor_admin_id=owner_admin_id,
        object_id=UUID(int=1),
        action="media_archive.recovery_pricing_updated",
        result="success",
        target_version=value_fingerprint,
        previous_status=previous_status,
        next_status=next_status,
        origin="web_console",
    ))
    db.flush()
    return owner_recovery_pricing(db, owner_admin_id)


def _active_allocatable_sources(db: Session, tenant_id: UUID, required: int):
    entries = db.scalars(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.delta > 0,
    ).order_by(
        PhotographerCreditEntry.created_at,
        PhotographerCreditEntry.id,
    ).with_for_update())
    remaining = required
    selected: list[tuple[PhotographerCreditEntry, int]] = []
    for entry in entries:
        available = max(0, _source_available(db, entry))
        take = min(available, remaining)
        if take:
            selected.append((entry, take))
            remaining -= take
        if remaining == 0:
            break
    if remaining:
        raise HTTPException(409, "Saldo insuficiente para recuperar esta pasta. Adquira créditos.")
    return selected


def _request_for_operation(db: Session, operation: MediaArchiveOperation, *, lock: bool = False):
    query = select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryRequest.operation_id == operation.id,
    )
    if lock:
        query = query.with_for_update()
    request = db.scalar(query)
    if request is None:
        raise HTTPException(503, "Registro de recuperação indisponível.")
    return request


def failed_recovery_cycle_id(
    db: Session,
    *,
    owner_admin_id: UUID,
    tenant_id: UUID,
    failed_operation_id: UUID,
) -> UUID:
    if not is_owner(db, owner_admin_id):
        raise HTTPException(403, "Acesso não autorizado.")
    failed = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == failed_operation_id,
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.operation_type == "restore",
        MediaArchiveOperation.status == "failed",
    ))
    if failed is None:
        raise HTTPException(409, "Retry só é permitido após uma falha comprovada.")
    _request_for_operation(db, failed)
    return failed.cycle_id


def _request_payload(
    db: Session,
    request: MediaArchiveRecoveryRequest,
    *,
    owner_view: bool = False,
) -> dict[str, object]:
    operation = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.id == request.operation_id,
        MediaArchiveOperation.tenant_id == request.tenant_id,
    ))
    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == request.cycle_id,
        MediaArchiveCycle.tenant_id == request.tenant_id,
    ))
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id,
        PhotoFolder.tenant_id == request.tenant_id,
    )) if cycle else None
    if operation is None or cycle is None or folder is None:
        raise HTTPException(503, "Registro de recuperação indisponível.")
    payload = {
        "operation_id": str(operation.id),
        "cycle_id": str(cycle.id),
        "folder_id": str(folder.id),
        "folder_name": folder.name,
        "status": operation.status,
        "duration_days": request.duration_days,
        "fee_credits": request.fee_credits_snapshot,
        "owner_exempt": request.owner_exempt,
        "technical_cover_exempt": request.technical_cover_exempt,
        "retry_of_operation_id": str(request.retry_of_operation_id) if request.retry_of_operation_id else None,
        "created_at": request.created_at,
        "updated_at": operation.updated_at,
        "completed_at": operation.completed_at,
    }
    if owner_view:
        payload.update({
            "stage": operation.stage,
            "requester_type": request.requester_type,
            "last_error_code": operation.last_error_code,
            "last_error": operation.last_error,
        })
    return payload


def list_recovery_candidates(db: Session, tenant_id: UUID, *, limit: int = 50) -> list[dict[str, object]]:
    """Lista somente ciclos arquivados pertencentes à conta autenticada."""
    rows = db.execute(select(MediaArchiveCycle, PhotoFolder).join(PhotoFolder, (
        (PhotoFolder.id == MediaArchiveCycle.folder_id)
        & (PhotoFolder.parent_gallery_id == MediaArchiveCycle.parent_gallery_id)
        & (PhotoFolder.tenant_id == MediaArchiveCycle.tenant_id)
    )).where(
        MediaArchiveCycle.tenant_id == tenant_id,
        MediaArchiveCycle.state == "archived",
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.purpose == "content",
    ).order_by(
        MediaArchiveCycle.archived_at.desc(),
        MediaArchiveCycle.updated_at.desc(),
        MediaArchiveCycle.id,
    ).limit(max(1, min(limit, 100)))).all()
    return [{
        "cycle_id": str(cycle.id),
        "folder_id": str(folder.id),
        "folder_name": folder.name,
        "cycle_number": cycle.cycle_number,
        "archived_at": cycle.archived_at,
    } for cycle, folder in rows]


def _append_recovery_event(
    db: Session,
    *,
    operation: MediaArchiveOperation,
    cycle: MediaArchiveCycle,
    event_type: str,
    actor_type: str,
    actor_admin_id: UUID | None,
    details: dict,
    at=None,
) -> None:
    db.add(MediaArchiveEvent(
        tenant_id=operation.tenant_id,
        cycle_id=cycle.id,
        operation_id=operation.id,
        actor_type=actor_type,
        actor_admin_id=actor_admin_id,
        event_type=event_type,
        cycle_state_before=cycle.state,
        cycle_state_after=cycle.state,
        operation_status_before=operation.status,
        operation_status_after=operation.status,
        details=details,
        created_at=at or now(),
    ))


def request_recovery(
    db: Session,
    *,
    tenant_id: UUID,
    actor_admin_id: UUID,
    cycle_id: UUID,
    duration_days: int,
    idempotency_key: str,
    retry_of_operation_id: UUID | None = None,
    closure_batch_id: UUID | None = None,
) -> dict[str, object]:
    """Cria pedido idempotente e reserva FIFO; não inicia download."""
    if type(duration_days) is not int or duration_days not in ALLOWED_RECOVERY_DURATIONS:
        raise HTTPException(422, "Escolha um prazo de 7, 14 ou 30 dias.")
    key = idempotency_key.strip()
    if not 1 <= len(key) <= 200:
        raise HTTPException(422, "Chave de idempotência inválida.")
    if retry_of_operation_id is not None and closure_batch_id is None:
        retry_request = db.scalar(select(MediaArchiveRecoveryRequest).where(
            MediaArchiveRecoveryRequest.operation_id == retry_of_operation_id,
            MediaArchiveRecoveryRequest.tenant_id == tenant_id))
        if retry_request is not None:
            closure_batch_id = retry_request.closure_batch_id
    if closure_batch_id is not None:
        from app.tenant_closure_recovery import bind_account_recovery, require_batch
        batch = require_batch(db, actor_admin_id, tenant_id, closure_batch_id)
        if batch.requested_by_owner_admin_id != actor_admin_id:
            raise HTTPException(403, "Acesso não autorizado.")
        bind_account_recovery(db, actor_admin_id, tenant_id)

    previous = db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.idempotency_key == key,
    ))
    if previous is not None:
        if previous.operation_type != "restore":
            raise HTTPException(409, "Chave de idempotência já usada em outra operação.")
        request = _request_for_operation(db, previous)
        if (
            previous.cycle_id != cycle_id
            or request.duration_days != duration_days
            or request.requested_by_admin_id != actor_admin_id
            or request.retry_of_operation_id != retry_of_operation_id
            or request.closure_batch_id != closure_batch_id
        ):
            raise HTTPException(409, "Chave de idempotência já usada em outra operação.")
        return _request_payload(db, request)

    actor_is_owner = is_owner(db, actor_admin_id)
    previous_request = None
    requester_type = "owner" if retry_of_operation_id is not None or closure_batch_id is not None else "tenant"
    if requester_type == "owner" and not actor_is_owner:
        raise HTTPException(403, "Acesso não autorizado.")
    if retry_of_operation_id is not None:
        failed = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.id == retry_of_operation_id,
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.operation_type == "restore",
            MediaArchiveOperation.status == "failed",
        ).with_for_update())
        if failed is None or failed.last_error_code is None:
            raise HTTPException(409, "Retry só é permitido após uma falha comprovada.")
        previous_request = _request_for_operation(db, failed)
        if previous_request.tenant_id != tenant_id:
            raise HTTPException(409, "A falha selecionada não corresponde à conta.")
        if previous_request.closure_batch_id is not None:
            closure_batch_id = previous_request.closure_batch_id
            from app.tenant_closure_recovery import bind_account_recovery
            bind_account_recovery(db, actor_admin_id, tenant_id)
    elif closure_batch_id is None:
        membership = db.scalar(select(TenantAdmin.id).where(
            TenantAdmin.tenant_id == tenant_id,
            TenantAdmin.admin_user_id == actor_admin_id,
            TenantAdmin.active.is_(True),
        ))
        if membership is None:
            raise HTTPException(403, "Acesso não autorizado a esta conta.")

    cycle = db.scalar(select(MediaArchiveCycle).where(
        MediaArchiveCycle.id == cycle_id,
        MediaArchiveCycle.tenant_id == tenant_id,
    ).with_for_update())
    if cycle is None:
        raise HTTPException(404, "Pasta arquivada não encontrada.")
    if cycle.state != "archived":
        raise HTTPException(409, "Esta pasta não está disponível para recuperação.")
    folder = db.scalar(select(PhotoFolder).where(
        PhotoFolder.id == cycle.folder_id,
        PhotoFolder.tenant_id == tenant_id,
        PhotoFolder.parent_gallery_id == cycle.parent_gallery_id,
        PhotoFolder.purpose.in_(("content", "cover_assets")),
    ))
    if folder is None:
        raise HTTPException(404, "Pasta arquivada não encontrada.")
    if folder.purpose == "cover_assets":
        from app.media_archive_guards import isolated_closure_cover_folder
        if closure_batch_id is None or not isolated_closure_cover_folder(db, folder):
            raise HTTPException(403, "Unidade técnica indisponível.")
    # The cycle lock serializes admissions; keep this read unlocked so it does not invert the worker's operation → cycle order.
    active = db.scalar(select(MediaArchiveOperation.id).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.cycle_id == cycle.id,
        MediaArchiveOperation.operation_type == "restore",
        MediaArchiveOperation.status.in_(("queued", "processing", "reconciliation_required")),
    ))
    if active is not None:
        raise HTTPException(409, "Já existe uma recuperação ativa para esta pasta.")

    wallet = _lock_wallet(db, tenant_id)
    owner_exempt = _owner_wallet_exemption(db, tenant_id, wallet)
    technical_cover_exempt = folder.purpose == "cover_assets" and not owner_exempt
    exempt = owner_exempt or technical_cover_exempt
    if retry_of_operation_id is not None:
        if previous_request is None or previous_request.owner_exempt != owner_exempt:
            raise HTTPException(503, "Preço original da recuperação indisponível.")
        if previous_request.technical_cover_exempt != technical_cover_exempt:
            raise HTTPException(503, "Isenção original da recuperação indisponível.")
        fee = None if exempt else previous_request.fee_credits_snapshot
    else:
        setting = db.scalar(select(MediaArchiveRecoveryPricing).where(
            MediaArchiveRecoveryPricing.id == 1,
        ).with_for_update())
        fee = None if exempt else (setting.recovery_fee_credits if setting else None)
    if not exempt and fee is None:
        if requester_type == "owner":
            raise HTTPException(503, "Preço original da recuperação indisponível.")
        raise HTTPException(409, "A recuperação paga ainda não está configurada pelo proprietário.")
    if not exempt and tenant_has_financial_hold(db, tenant_id):
        raise HTTPException(409, "A carteira aguarda revisão financeira do proprietário.")
    allocations = [] if exempt else _active_allocatable_sources(db, tenant_id, int(fee))

    operation_id = uuid4()
    operation = MediaArchiveOperation(
        id=operation_id,
        tenant_id=tenant_id,
        cycle_id=cycle.id,
        operation_type="restore",
        status="queued",
        stage=None,
        idempotency_key=key,
        actor_type=requester_type,
        actor_admin_id=actor_admin_id,
        details={
            "recovery_duration_days": duration_days,
            "owner_exempt": owner_exempt,
            "technical_cover_exempt": technical_cover_exempt,
            "manual_retry": retry_of_operation_id is not None,
        },
    )
    db.add(operation)
    db.flush()
    request = MediaArchiveRecoveryRequest(
        tenant_id=tenant_id,
        operation_id=operation.id,
        cycle_id=cycle.id,
        requester_type=requester_type,
        requested_by_admin_id=actor_admin_id,
        requested_by_tenant_admin_id=actor_admin_id if requester_type == "tenant" else None,
        requested_by_owner_admin_id=actor_admin_id if requester_type == "owner" else None,
        retry_of_operation_id=retry_of_operation_id,
        duration_days=duration_days,
        fee_credits_snapshot=fee,
        owner_exempt=owner_exempt,
        technical_cover_exempt=technical_cover_exempt,
        closure_batch_id=closure_batch_id,
    )
    db.add(request)
    reservation = MediaArchiveRecoveryCreditReservation(
        tenant_id=tenant_id,
        operation_id=operation.id,
        reserved_credits=0 if exempt else int(fee),
        status="exempt" if exempt else "reserved",
    )
    db.add(reservation)
    db.flush()
    for source, quantity in allocations:
        db.add(MediaArchiveRecoveryCreditAllocationEvent(
            tenant_id=tenant_id,
            operation_id=operation.id,
            source_entry_id=source.id,
            credit_entry_id=None,
            event_type="reserved",
            quantity=quantity,
            idempotency_key=f"archive-reserve:{operation.id}:{source.id}",
        ))
    _append_recovery_event(
        db, operation=operation, cycle=cycle, event_type="recovery_requested",
        actor_type=requester_type, actor_admin_id=actor_admin_id,
        details={
            "duration_days": duration_days,
            "fee_credits": fee,
            "owner_exempt": owner_exempt,
            "retry": retry_of_operation_id is not None,
        },
    )
    audit(db, "media_archive.recovery_requested", str(operation.id), tenant_id=tenant_id)
    if retry_of_operation_id is not None and closure_batch_id is not None:
        item = db.scalar(select(TenantClosureRecoveryItem).where(
            TenantClosureRecoveryItem.batch_id == closure_batch_id,
            TenantClosureRecoveryItem.tenant_id == tenant_id,
            TenantClosureRecoveryItem.operation_id == retry_of_operation_id))
        if item is None:
            raise HTTPException(409, "A tentativa não pertence ao lote de recuperação.")
        item.operation_id = operation.id
    db.flush()
    return _request_payload(db, request)


def _active_recovery_allocations(db: Session, tenant_id: UUID, operation_id: UUID):
    events = list(db.scalars(select(MediaArchiveRecoveryCreditAllocationEvent).where(
        MediaArchiveRecoveryCreditAllocationEvent.tenant_id == tenant_id,
        MediaArchiveRecoveryCreditAllocationEvent.operation_id == operation_id,
    ).order_by(
        MediaArchiveRecoveryCreditAllocationEvent.occurred_at,
        MediaArchiveRecoveryCreditAllocationEvent.id,
    )))
    by_source: dict[UUID, dict[str, object]] = {}
    for event in events:
        state = by_source.setdefault(event.source_entry_id, {"reserved": [], "closed": 0})
        if event.event_type == "reserved":
            state["reserved"].append((event.quantity, event.id))
        elif event.event_type in {"consumed", "released"}:
            state["closed"] = int(state["closed"]) + event.quantity
    active = []
    for source_id, state in by_source.items():
        closed = int(state["closed"])
        for quantity, reservation_id in state["reserved"]:
            close_quantity = min(int(quantity), closed)
            closed -= close_quantity
            if close_quantity < quantity:
                active.append((source_id, int(quantity - close_quantity), reservation_id))
    return active


def mark_recovery_uncertain(db: Session, *, operation: MediaArchiveOperation) -> None:
    reservation = db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryCreditReservation.operation_id == operation.id,
    ).with_for_update())
    if reservation is None:
        raise HTTPException(503, "Reserva de recuperação indisponível.")
    if reservation.status == "reserved":
        reservation.status = "reconciliation_required"
        reservation.updated_at = now()


def release_failed_recovery(db: Session, *, operation: MediaArchiveOperation, actor_admin_id=None) -> None:
    """Libera saldo somente quando o worker comprovou falha sem restaurar."""
    reservation = db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryCreditReservation.operation_id == operation.id,
    ).with_for_update())
    if reservation is None:
        raise HTTPException(503, "Reserva de recuperação indisponível.")
    if reservation.status == "exempt" or reservation.status == "released":
        return
    if reservation.status == "consumed":
        raise HTTPException(409, "Uma recuperação cobrada não pode liberar créditos.")
    _lock_wallet(db, operation.tenant_id)
    for source_id, quantity, reservation_id in _active_recovery_allocations(
        db, operation.tenant_id, operation.id,
    ):
        db.add(MediaArchiveRecoveryCreditAllocationEvent(
            tenant_id=operation.tenant_id,
            operation_id=operation.id,
            source_entry_id=source_id,
            credit_entry_id=None,
            event_type="released",
            quantity=quantity,
            idempotency_key=f"archive-release:{reservation_id}",
        ))
    reservation.status = "released"
    reservation.updated_at = now()


def consume_verified_recovery(
    db: Session,
    *,
    operation: MediaArchiveOperation,
    at,
) -> PhotographerCreditEntry | None:
    """Lança no máximo um débito; o caller precisa comprovar o pull inteiro."""
    request = _request_for_operation(db, operation, lock=True)
    reservation = db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == operation.tenant_id,
        MediaArchiveRecoveryCreditReservation.operation_id == operation.id,
    ).with_for_update())
    if reservation is None:
        raise HTTPException(503, "Reserva de recuperação indisponível.")
    wallet = _lock_wallet(db, operation.tenant_id)
    if recovery_is_exempt(request):
        actual_owner_exemption = _owner_wallet_exemption(db, operation.tenant_id, wallet)
        if request.owner_exempt != actual_owner_exemption or reservation.status != "exempt":
            raise HTTPException(503, "Isenção da recuperação inconsistente.")
        if request.technical_cover_exempt and wallet.mode != "finite":
            raise HTTPException(503, "Isenção da unidade técnica inconsistente.")
        if request.technical_cover_exempt:
            from app.media_archive_guards import isolated_closure_cover_folder
            cycle = db.get(MediaArchiveCycle, request.cycle_id)
            folder = db.get(PhotoFolder, cycle.folder_id) if cycle else None
            if folder is None or not isolated_closure_cover_folder(db, folder):
                raise HTTPException(503, "Isenção da unidade técnica inconsistente.")
        return None
    if request.fee_credits_snapshot is None or reservation.reserved_credits != request.fee_credits_snapshot:
        raise HTTPException(503, "Valor reservado não corresponde ao pedido.")

    if reservation.status == "consumed":
        existing = db.scalar(select(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == operation.tenant_id,
            PhotographerCreditEntry.archive_operation_id == operation.id,
            PhotographerCreditEntry.entry_type == "archive_recovery",
        ).with_for_update())
        events = list(db.scalars(select(MediaArchiveRecoveryCreditAllocationEvent).where(
            MediaArchiveRecoveryCreditAllocationEvent.tenant_id == operation.tenant_id,
            MediaArchiveRecoveryCreditAllocationEvent.operation_id == operation.id,
        )))
        consumed = sum(event.quantity for event in events if event.event_type == "consumed")
        if (
            existing is None
            or existing.delta != -request.fee_credits_snapshot
            or consumed != reservation.reserved_credits
            or _active_recovery_allocations(db, operation.tenant_id, operation.id)
        ):
            raise HTTPException(503, "Histórico financeiro da recuperação inconsistente.")
        return existing

    if wallet.mode != "finite" or reservation.status not in _HELD_RESERVATION_STATES:
        raise HTTPException(503, "Reserva financeira da recuperação inconsistente.")
    active = _active_recovery_allocations(db, operation.tenant_id, operation.id)
    if sum(quantity for _source_id, quantity, _reservation_id in active) != reservation.reserved_credits:
        raise HTTPException(503, "Alocações da recuperação não conferem com a reserva.")

    existing = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == operation.tenant_id,
        PhotographerCreditEntry.archive_operation_id == operation.id,
        PhotographerCreditEntry.entry_type == "archive_recovery",
    ).with_for_update())
    if existing is not None:
        raise HTTPException(503, "Histórico financeiro da recuperação inconsistente.")

    ledger_entry = PhotographerCreditEntry(
        tenant_id=operation.tenant_id,
        entry_type="archive_recovery",
        delta=-request.fee_credits_snapshot,
        idempotency_key=f"archive-recovery:{operation.id}",
        archive_operation_id=operation.id,
        actor_admin_id=request.requested_by_admin_id if request.requester_type == "tenant" else None,
        source_reference=str(request.cycle_id),
        description="Recuperação de arquivo frio",
        created_at=at,
    )
    db.add(ledger_entry)
    db.flush()
    for source_id, quantity, reservation_id in active:
        db.add(MediaArchiveRecoveryCreditAllocationEvent(
            tenant_id=operation.tenant_id,
            operation_id=operation.id,
            source_entry_id=source_id,
            credit_entry_id=ledger_entry.id,
            event_type="consumed",
            quantity=quantity,
            idempotency_key=f"archive-consume:{reservation_id}",
            occurred_at=at,
        ))
    reservation.status = "consumed"
    reservation.updated_at = at
    audit(db, "media_archive.recovery_credits_consumed", str(operation.id), tenant_id=operation.tenant_id)
    db.flush()
    return ledger_entry


def list_tenant_recoveries(db: Session, tenant_id: UUID, *, limit: int = 50) -> list[dict[str, object]]:
    requests = db.scalars(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == tenant_id,
    ).order_by(
        MediaArchiveRecoveryRequest.created_at.desc(),
        MediaArchiveRecoveryRequest.id.desc(),
    ).limit(max(1, min(limit, 100))))
    return [_request_payload(db, item) for item in requests]


def list_owner_recoveries(db: Session, owner_admin_id: UUID, tenant_id: UUID, *, limit: int = 50):
    if not is_owner(db, owner_admin_id):
        raise HTTPException(403, "Acesso não autorizado.")
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "Conta não encontrada.")
    requests = db.scalars(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == tenant_id,
    ).order_by(
        MediaArchiveRecoveryRequest.created_at.desc(),
        MediaArchiveRecoveryRequest.id.desc(),
    ).limit(max(1, min(limit, 100))))
    return [_request_payload(db, item, owner_view=True) for item in requests]
