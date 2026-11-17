"""Serviços tenant-safe para a carteira pré-paga do fotógrafo."""

from __future__ import annotations

import re
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditAllocationEvent,
    MediaArchiveRecoveryCreditReservation,
    PhotoAsset,
    PhotoCreditOperation,
    PhotoCreditOperationEvent,
    PhotographerCreditAllocationEvent,
    PhotographerCreditEntry,
    PhotographerCreditPackage,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    audit,
    now,
)
from app.credit_history import history_page, photo_history_context
from app.media import safe_source_path_from_credit_snapshot
from app.mercadopago_credit_purchases import (
    financial_review_count,
    financial_review_items,
    tenant_has_financial_hold,
)
from app.system_monitor.access import is_owner


def source_fingerprint_state(path: Path, expected_fingerprint: str) -> bool | None:
    """True = conteúdo exato; False = caminho ausente; None = estado conflitante/ilegível."""
    digest = sha256()
    try:
        with path.open("rb") as stored:
            for chunk in iter(lambda: stored.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return False
    except OSError:
        return None
    return True if digest.hexdigest() == expected_fingerprint else None


def fingerprint_from_storage_key(storage_key: str) -> str | None:
    """Obtém o fingerprint de chaves legadas e das novas chaves por intenção."""
    basename = storage_key.rsplit("/", 1)[-1]
    match = re.fullmatch(
        r"([0-9a-f]{64})(?:-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?\.jpg",
        basename,
    )
    return match.group(1) if match else None


def _require_owner(db: Session, owner_admin_id: UUID) -> None:
    if not is_owner(db, owner_admin_id):
        raise HTTPException(
            403,
            "Acesso não autorizado.",
            headers={"Cache-Control": "private, no-store"},
        )


def wallet_snapshot(db: Session, tenant_id: UUID) -> dict[str, object]:
    wallet = db.get(TenantCreditWallet, tenant_id, populate_existing=True)
    if wallet is None:
        raise HTTPException(503, "Carteira indisponível.")

    as_of = now()
    review_count = financial_review_count(db, tenant_id)
    financial_hold = review_count > 0

    pending = db.scalar(select(func.coalesce(func.sum(PhotoCreditOperation.quantity), 0)).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.status.in_(("reserved", "reconciliation_required")),
    )) or 0
    pending_archive = db.scalar(select(func.coalesce(
        func.sum(MediaArchiveRecoveryCreditReservation.reserved_credits), 0,
    )).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
        MediaArchiveRecoveryCreditReservation.status.in_(("reserved", "reconciliation_required")),
    )) or 0
    ledger_balance = db.scalar(select(func.coalesce(func.sum(PhotographerCreditEntry.delta), 0)).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
    )) or 0
    if wallet.mode == "unmetered":
        available = None
    else:
        available = int(ledger_balance) - int(pending) - int(pending_archive)
        if available < 0:
            raise HTTPException(503, "Carteira indisponível.")

    recent_consumption = db.scalar(select(func.coalesce(func.sum(-PhotographerCreditEntry.delta), 0)).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.entry_type == "upload_consumption",
        PhotographerCreditEntry.created_at >= as_of - timedelta(days=30),
    )) or 0

    pending_upload_operations = int(db.scalar(select(func.count(PhotoCreditOperation.id)).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.status.in_(("reserved", "reconciliation_required")),
    )) or 0)
    pending_recovery_operations = int(db.scalar(select(func.count(MediaArchiveOperation.id)).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.operation_type == "restore",
        MediaArchiveOperation.status.in_(
            ("queued", "processing", "reconciliation_required"),
        ),
    )) or 0)

    return {
        "mode": wallet.mode,
        "available_credits": available,
        "reserved_credits": int(pending + pending_archive) if wallet.mode == "finite" else 0,
        "pending_operations": pending_upload_operations + pending_recovery_operations,
        "pending_upload_operations": pending_upload_operations,
        "pending_recovery_operations": pending_recovery_operations,
        "recent_consumed_credits": int(recent_consumption),
        "recent_period_days": 30,
        "can_upload_content": (wallet.mode == "unmetered" or int(available or 0) > 0) and not financial_hold,
        "financial_review_hold": financial_hold,
        "financial_review_count": review_count,
        "as_of": as_of,
    }


def list_entries(db: Session, tenant_id: UUID, *, limit: int = 30) -> list[dict[str, object]]:
    entries = db.scalars(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
    ).order_by(PhotographerCreditEntry.created_at.desc(), PhotographerCreditEntry.id.desc()).limit(limit))
    return [
        {
            **entry_payload(entry),
        }
        for entry in entries
    ]


def list_packages(db: Session, owner_admin_id: UUID) -> list[dict[str, object]]:
    _require_owner(db, owner_admin_id)
    packages = db.scalars(select(PhotographerCreditPackage).order_by(
        PhotographerCreditPackage.created_at.desc(), PhotographerCreditPackage.id.desc(),
    ))
    return [package_payload(package) for package in packages]


def list_active_packages(db: Session) -> list[dict[str, object]]:
    """Lista somente ofertas prontas para exibição no catálogo do fotógrafo."""
    packages = db.scalars(select(PhotographerCreditPackage).where(
        PhotographerCreditPackage.active.is_(True),
        PhotographerCreditPackage.price_cents.is_not(None),
        PhotographerCreditPackage.currency_code.is_not(None),
    ).order_by(
        PhotographerCreditPackage.created_at.desc(), PhotographerCreditPackage.id.desc(),
    ))
    return [package_payload(package) for package in packages]


def list_credit_tenants(db: Session, owner_admin_id: UUID) -> list[dict[str, object]]:
    """Lista resumos compactos para a interface global, sem carregar históricos."""
    _require_owner(db, owner_admin_id)
    rows = db.execute(
        select(
            Tenant.id,
            Tenant.status,
            Tenant.canonical_host,
            TenantCreditWallet.mode,
            AdminUser.email,
        )
        .join(TenantCreditWallet, TenantCreditWallet.tenant_id == Tenant.id)
        .outerjoin(
            TenantAdmin,
            and_(TenantAdmin.tenant_id == Tenant.id, TenantAdmin.active.is_(True)),
        )
        .outerjoin(AdminUser, AdminUser.id == TenantAdmin.admin_user_id)
        .order_by(Tenant.created_at.desc(), Tenant.id, AdminUser.email)
    ).all()

    as_of = now()
    grouped: dict[UUID, dict[str, object]] = {}
    for tenant_id, status, canonical_host, mode, email in rows:
        item = grouped.setdefault(tenant_id, {
            "tenant_id": str(tenant_id),
            "status": status,
            "canonical_host": canonical_host,
            "mode": mode,
            "admin_emails": [],
        })
        if email and email not in item["admin_emails"]:
            item["admin_emails"].append(email)

    ledger_balances = {
        tenant_id: int(balance or 0)
        for tenant_id, balance in db.execute(select(
            PhotographerCreditEntry.tenant_id,
            func.sum(PhotographerCreditEntry.delta),
        ).group_by(PhotographerCreditEntry.tenant_id)).all()
    }
    pending_totals = {
        tenant_id: (int(quantity or 0), int(count or 0))
        for tenant_id, quantity, count in db.execute(select(
            PhotoCreditOperation.tenant_id,
            func.sum(PhotoCreditOperation.quantity),
            func.count(PhotoCreditOperation.id),
        ).where(
            PhotoCreditOperation.status.in_(("reserved", "reconciliation_required")),
        ).group_by(PhotoCreditOperation.tenant_id)).all()
    }
    archive_pending_totals = {
        tenant_id: int(quantity or 0)
        for tenant_id, quantity in db.execute(select(
            MediaArchiveRecoveryCreditReservation.tenant_id,
            func.sum(MediaArchiveRecoveryCreditReservation.reserved_credits),
        ).where(
            MediaArchiveRecoveryCreditReservation.status.in_(
                ("reserved", "reconciliation_required"),
            ),
        ).group_by(MediaArchiveRecoveryCreditReservation.tenant_id)).all()
    }
    archive_pending_counts = {
        tenant_id: int(count or 0)
        for tenant_id, count in db.execute(select(
            MediaArchiveOperation.tenant_id,
            func.count(MediaArchiveOperation.id),
        ).where(
            MediaArchiveOperation.operation_type == "restore",
            MediaArchiveOperation.status.in_(
                ("queued", "processing", "reconciliation_required"),
            ),
        ).group_by(MediaArchiveOperation.tenant_id)).all()
    }
    recent_consumption = {
        tenant_id: int(quantity or 0)
        for tenant_id, quantity in db.execute(select(
            PhotographerCreditEntry.tenant_id,
            func.sum(-PhotographerCreditEntry.delta),
        ).where(
            PhotographerCreditEntry.entry_type == "upload_consumption",
            PhotographerCreditEntry.created_at >= as_of - timedelta(days=30),
        ).group_by(PhotographerCreditEntry.tenant_id)).all()
    }

    result: list[dict[str, object]] = []
    for tenant_id, item in grouped.items():
        mode = str(item["mode"])
        pending_quantity, pending_count = pending_totals.get(tenant_id, (0, 0))
        archive_pending_quantity = archive_pending_totals.get(tenant_id, 0)
        balance = ledger_balances.get(tenant_id, 0) - pending_quantity - archive_pending_quantity
        valid = mode == "unmetered" or balance >= 0
        item["wallet"] = {
            "mode": mode,
            "available_credits": None if mode == "unmetered" or not valid else balance,
            "reserved_credits": pending_quantity + archive_pending_quantity if mode == "finite" else 0,
            "pending_operations": pending_count + archive_pending_counts.get(tenant_id, 0),
            "recent_consumed_credits": recent_consumption.get(tenant_id, 0),
            "recent_period_days": 30,
            "can_upload_content": True if mode == "unmetered" else (balance > 0 if valid else None),
            "state": "available" if valid else "unavailable",
            "as_of": as_of,
        }
        result.append(item)
    return result


def search_credit_tenants(
    db: Session, owner_admin_id: UUID, query: str, *, limit: int = 10,
) -> list[dict[str, object]]:
    """Preserva a lista de sugestões para consumidores anteriores à paginação."""
    return browse_credit_tenants(
        db, owner_admin_id, query=query, limit=max(1, min(int(limit), 20)),
    )["items"]


def browse_credit_tenants(
    db: Session,
    owner_admin_id: UUID,
    *,
    query: str = "",
    mode: Literal["all", "alphabetical", "recent"] | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, object]:
    """Consulta explícita do proprietário, sem ler saldo nem histórico por item."""
    _require_owner(db, owner_admin_id)
    if mode not in {None, "all", "alphabetical", "recent"} or not 1 <= limit <= 20 or not 0 <= offset <= 100_000:
        raise HTTPException(422, "Parâmetros de consulta inválidos.")
    normalized = query.strip().casefold()
    if mode is None and len(normalized) < 2:
        return {"items": [], "has_more": False}
    identities = select(
        TenantAdmin.tenant_id,
        func.count(AdminUser.id).label("admin_count"),
        func.min(AdminUser.email).label("admin_email"),
    ).join(AdminUser, AdminUser.id == TenantAdmin.admin_user_id).where(
        TenantAdmin.active.is_(True),
    ).group_by(TenantAdmin.tenant_id).subquery()
    statement = (
        select(
            Tenant.id,
            Tenant.status,
            Tenant.canonical_host,
            Tenant.photographer_name,
            identities.c.admin_count,
            identities.c.admin_email,
        )
        .join(TenantCreditWallet, TenantCreditWallet.tenant_id == Tenant.id)
        .join(identities, identities.c.tenant_id == Tenant.id)
    )
    if normalized:
        email_match = select(TenantAdmin.id).join(
            AdminUser, AdminUser.id == TenantAdmin.admin_user_id,
        ).where(
            TenantAdmin.tenant_id == Tenant.id,
            TenantAdmin.active.is_(True),
            func.lower(AdminUser.email).contains(normalized, autoescape=True),
        ).exists()
        statement = statement.where(or_(
            func.lower(Tenant.photographer_name).contains(normalized, autoescape=True),
            email_match,
        ))
    if mode == "all":
        statement = statement.order_by(Tenant.id)
    elif mode == "alphabetical":
        unique_email = case(
            (identities.c.admin_count == 1, func.lower(identities.c.admin_email)),
            else_=None,
        )
        statement = statement.order_by(
            func.coalesce(func.lower(Tenant.photographer_name), unique_email).asc().nulls_last(),
            Tenant.id,
        )
    else:
        statement = statement.order_by(Tenant.created_at.desc(), Tenant.id)
    rows = db.execute(statement.offset(offset).limit(limit + 1)).all()
    items = [
        {
            "tenant_id": str(tenant_id),
            "status": status,
            "canonical_host": canonical_host,
            "photographer_name": photographer_name,
            "admin_email": admin_email if admin_count == 1 else None,
        }
        for tenant_id, status, canonical_host, photographer_name, admin_count, admin_email in rows[:limit]
    ]
    return {"items": items, "has_more": len(rows) > limit}


def credit_tenant_detail(
    db: Session, owner_admin_id: UUID, tenant_id: UUID,
) -> dict[str, object]:
    """Retorna histórico e parcelas revogáveis somente para o tenant selecionado."""
    _require_owner(db, owner_admin_id)
    if db.get(TenantCreditWallet, tenant_id) is None:
        raise HTTPException(404, "Carteira não encontrada.")

    grants = list(db.scalars(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.entry_type == "owner_grant",
    ).order_by(PhotographerCreditEntry.created_at.desc(), PhotographerCreditEntry.id.desc())))
    grant_ids = [grant.id for grant in grants]
    allocation_totals: dict[UUID, dict[str, int]] = {}
    if grant_ids:
        for source_id, event_type, quantity in db.execute(select(
            PhotographerCreditAllocationEvent.source_entry_id,
            PhotographerCreditAllocationEvent.event_type,
            func.sum(PhotographerCreditAllocationEvent.quantity),
        ).where(
            PhotographerCreditAllocationEvent.tenant_id == tenant_id,
            PhotographerCreditAllocationEvent.source_entry_id.in_(grant_ids),
        ).group_by(
            PhotographerCreditAllocationEvent.source_entry_id,
            PhotographerCreditAllocationEvent.event_type,
        )).all():
            allocation_totals.setdefault(source_id, {})[event_type] = int(quantity or 0)
        for source_id, event_type, quantity in db.execute(select(
            MediaArchiveRecoveryCreditAllocationEvent.source_entry_id,
            MediaArchiveRecoveryCreditAllocationEvent.event_type,
            func.sum(MediaArchiveRecoveryCreditAllocationEvent.quantity),
        ).where(
            MediaArchiveRecoveryCreditAllocationEvent.tenant_id == tenant_id,
            MediaArchiveRecoveryCreditAllocationEvent.source_entry_id.in_(grant_ids),
        ).group_by(
            MediaArchiveRecoveryCreditAllocationEvent.source_entry_id,
            MediaArchiveRecoveryCreditAllocationEvent.event_type,
        )).all():
            totals = allocation_totals.setdefault(source_id, {})
            totals[event_type] = totals.get(event_type, 0) + int(quantity or 0)

    revocable_grants = []
    for grant in grants:
        totals = allocation_totals.get(grant.id, {})
        used = totals.get("consumed", 0) + totals.get("revoked", 0)
        reserved = totals.get("reserved", 0)
        closed = totals.get("consumed", 0) + totals.get("released", 0)
        free = grant.delta - used - max(0, reserved - closed)
        revocable_grants.append({
            **entry_payload(grant),
            "quantity": grant.delta,
            "revocable_quantity": max(0, free),
        })
    return {
        "wallet": wallet_snapshot(db, tenant_id),
        "entries": list_entries(db, tenant_id),
        "history": history_page(db, tenant_id),
        "revocable_grants": revocable_grants,
        "financial_reviews": financial_review_items(db, tenant_id),
    }


def create_package(
    db: Session,
    owner_admin_id: UUID,
    *,
    name: str,
    description: str | None,
    credit_quantity: int,
    price_cents: int | None,
    currency_code: str | None,
    active: bool,
) -> PhotographerCreditPackage:
    _require_owner(db, owner_admin_id)
    _validate_package(name, credit_quantity, price_cents, currency_code, active)
    package = PhotographerCreditPackage(
        name=name.strip(),
        description=description.strip() if description else None,
        credit_quantity=credit_quantity,
        price_cents=price_cents,
        currency_code=currency_code,
        active=active,
        created_by_admin_id=owner_admin_id,
        updated_by_admin_id=owner_admin_id,
    )
    db.add(package)
    db.flush()
    audit(db, "credit.package_created", str(package.id))
    return package


def update_package(
    db: Session,
    owner_admin_id: UUID,
    package_id: UUID,
    *,
    name: str,
    description: str | None,
    credit_quantity: int,
    price_cents: int | None,
    currency_code: str | None,
    active: bool,
) -> PhotographerCreditPackage:
    _require_owner(db, owner_admin_id)
    _validate_package(name, credit_quantity, price_cents, currency_code, active)
    package = db.scalar(select(PhotographerCreditPackage).where(
        PhotographerCreditPackage.id == package_id,
    ).with_for_update())
    if package is None:
        raise HTTPException(404, "Pacote não encontrado.")
    package.name = name.strip()
    package.description = description.strip() if description else None
    package.credit_quantity = credit_quantity
    package.price_cents = price_cents
    package.currency_code = currency_code
    package.active = active
    package.updated_by_admin_id = owner_admin_id
    package.updated_at = now()
    db.flush()
    audit(db, "credit.package_updated", str(package.id))
    return package


def grant_credits(
    db: Session,
    owner_admin_id: UUID,
    tenant_id: UUID,
    quantity: int,
    idempotency_key: str,
    reference: str,
) -> PhotographerCreditEntry:
    _require_owner(db, owner_admin_id)
    if quantity <= 0 or quantity > 2_147_483_647:
        raise HTTPException(422, "Quantidade de créditos inválida.")
    idempotency_key = idempotency_key.strip()
    if not idempotency_key or len(idempotency_key) > 240:
        raise HTTPException(422, "Chave de idempotência inválida.")
    reference = reference.strip()
    if not reference or len(reference) > 240:
        raise HTTPException(422, "Referência de concessão inválida.")

    wallet = db.scalar(select(TenantCreditWallet).where(
        TenantCreditWallet.tenant_id == tenant_id,
    ).with_for_update())
    if wallet is None or wallet.mode != "finite":
        raise HTTPException(409, "Carteira finita indisponível para concessão.")

    existing = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if (
            existing.entry_type == "owner_grant"
            and existing.delta == quantity
            and existing.global_owner_admin_id == owner_admin_id
            and existing.source_reference == reference
        ):
            return existing
        raise HTTPException(409, "Chave de idempotência já usada por outra operação.")

    entry = PhotographerCreditEntry(
        tenant_id=tenant_id,
        entry_type="owner_grant",
        delta=quantity,
        idempotency_key=idempotency_key,
        global_owner_admin_id=owner_admin_id,
        source_reference=reference,
        description="Créditos concedidos pelo proprietário da plataforma",
    )
    db.add(entry)
    db.flush()
    audit(db, "credit.owner_grant", str(entry.id), tenant_id=tenant_id)
    return entry


def revoke_grant(
    db: Session,
    owner_admin_id: UUID,
    tenant_id: UUID,
    grant_entry_id: UUID,
    quantity: int,
    idempotency_key: str,
    reference: str,
) -> PhotographerCreditEntry:
    _require_owner(db, owner_admin_id)
    if quantity <= 0 or quantity > 2_147_483_647:
        raise HTTPException(422, "Quantidade de créditos inválida.")
    idempotency_key = idempotency_key.strip()
    reference = reference.strip()
    if not idempotency_key or len(idempotency_key) > 240:
        raise HTTPException(422, "Chave de idempotência inválida.")
    if not reference or len(reference) > 240:
        raise HTTPException(422, "Referência de revogação inválida.")

    _lock_finite_wallet(db, tenant_id)

    existing = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if (
            existing.entry_type == "grant_revocation"
            and existing.source_entry_id == grant_entry_id
            and existing.delta == -quantity
            and existing.global_owner_admin_id == owner_admin_id
            and existing.source_reference == reference
        ):
            _require_allocation_event(db, tenant_id, f"revoke:{existing.id}")
            return existing
        raise HTTPException(409, "Chave de idempotência já usada por outra operação.")

    grant = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.id == grant_entry_id,
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.entry_type == "owner_grant",
    ).with_for_update())
    if grant is None:
        raise HTTPException(404, "Concessão não encontrada.")
    if _source_available(db, grant) < quantity:
        raise HTTPException(409, "Quantidade excede os créditos livres dessa concessão.")

    entry = PhotographerCreditEntry(
        tenant_id=tenant_id,
        entry_type="grant_revocation",
        delta=-quantity,
        idempotency_key=idempotency_key,
        source_entry_id=grant.id,
        global_owner_admin_id=owner_admin_id,
        source_reference=reference,
        description="Créditos não utilizados revogados pelo proprietário da plataforma",
    )
    db.add(entry)
    db.flush()
    db.add(PhotographerCreditAllocationEvent(
        tenant_id=tenant_id,
        source_entry_id=grant.id,
        operation_id=None,
        credit_entry_id=entry.id,
        event_type="revoked",
        quantity=quantity,
        idempotency_key=f"revoke:{entry.id}",
    ))
    audit(db, "credit.owner_grant_revoked", str(entry.id), tenant_id=tenant_id)
    db.flush()
    return entry


def reserve_photo_credit(
    db: Session,
    tenant_id: UUID,
    photo_asset_id: UUID,
    storage_key: str,
    payload_fingerprint: str | None,
    *,
    actor_admin_id: UUID | None = None,
) -> PhotoCreditOperation | None:
    from app.tenant_closure import require_new_work

    require_new_work(db, tenant_id)
    wallet = _lock_wallet(db, tenant_id)
    if wallet.mode == "unmetered":
        return None
    if payload_fingerprint is None:
        raise HTTPException(422, "A chave da foto não contém uma identidade JPEG válida.")

    operation = db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo_asset_id,
    ).with_for_update())
    if operation is not None:
        if (
            operation.payload_fingerprint != payload_fingerprint
            or operation.storage_key_snapshot != storage_key
        ):
            raise HTTPException(409, "A identidade desta foto já está vinculada a outro conteúdo.")
        if operation.status == "consumed":
            return operation
        if tenant_has_financial_hold(db, tenant_id):
            raise HTTPException(409, "Novos uploads estão bloqueados até revisão financeira do proprietário.")
        if operation.status == "reconciliation_required":
            raise HTTPException(409, "A operação de upload aguarda reconciliação.")
        if operation.status == "reserved":
            _require_operation_reservation(db, operation)
            return operation

    elif tenant_has_financial_hold(db, tenant_id):
        raise HTTPException(409, "Novos uploads estão bloqueados até revisão financeira do proprietário.")

    source = _oldest_available_source(db, tenant_id)
    if source is None:
        raise HTTPException(409, "Saldo insuficiente.")
    if operation is None:
        operation = PhotoCreditOperation(
            tenant_id=tenant_id,
            photo_asset_id=photo_asset_id,
            photo_asset_id_snapshot=photo_asset_id,
            storage_key_snapshot=storage_key,
            payload_fingerprint=payload_fingerprint,
            quantity=1,
            status="reserved",
        )
        db.add(operation)
        db.flush()
    else:
        operation.status = "reserved"
        operation.completed_at = None
        operation.updated_at = now()

    db.add(PhotographerCreditAllocationEvent(
        tenant_id=tenant_id,
        source_entry_id=source.id,
        operation_id=operation.id,
        credit_entry_id=None,
        event_type="reserved",
        quantity=1,
        idempotency_key=f"reserve:{operation.id}:{uuid4()}",
    ))
    db.add(PhotoCreditOperationEvent(
        tenant_id=tenant_id,
        operation_id=operation.id,
        event_type="reserved",
        actor_admin_id=actor_admin_id,
        details={
            "source_entry_id": str(source.id),
            **photo_history_context(db, tenant_id, photo_asset_id),
        },
    ))
    db.flush()
    return operation


def record_upload_attempt(
    db: Session,
    operation: PhotoCreditOperation | None,
    *,
    actor_admin_id: UUID | None = None,
) -> None:
    if operation is None:
        return
    db.add(PhotoCreditOperationEvent(
        tenant_id=operation.tenant_id,
        operation_id=operation.id,
        event_type="upload_attempted",
        actor_admin_id=actor_admin_id,
        details={"payload_fingerprint": operation.payload_fingerprint},
    ))
    db.flush()


def consume_photo_credit(
    db: Session,
    tenant_id: UUID,
    photo_asset_id: UUID,
    payload_fingerprint: str,
    *,
    actor_admin_id: UUID | None = None,
    reconciled: bool = False,
) -> PhotographerCreditEntry | None:
    wallet = _lock_wallet(db, tenant_id)
    if wallet.mode == "unmetered":
        return None
    operation = _lock_operation(db, tenant_id, photo_asset_id)
    if operation.payload_fingerprint != payload_fingerprint:
        raise HTTPException(409, "Fingerprint da operação não corresponde.")
    if operation.status == "consumed":
        entry = db.scalar(select(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == tenant_id,
            PhotographerCreditEntry.operation_id == operation.id,
            PhotographerCreditEntry.entry_type == "upload_consumption",
        ))
        if entry is None:
            raise HTTPException(503, "Histórico de créditos inconsistente.")
        return entry
    if operation.status not in {"reserved", "reconciliation_required"}:
        raise HTTPException(409, "A operação não possui uma reserva ativa.")
    source = _require_operation_reservation(db, operation)

    db.add(PhotoCreditOperationEvent(
        tenant_id=tenant_id,
        operation_id=operation.id,
        event_type="source_durable",
        actor_admin_id=actor_admin_id,
        details={"payload_fingerprint": operation.payload_fingerprint},
    ))

    entry = PhotographerCreditEntry(
        tenant_id=tenant_id,
        entry_type="upload_consumption",
        delta=-1,
        idempotency_key=f"upload:{operation.id}",
        operation_id=operation.id,
        source_entry_id=source.id,
        actor_admin_id=actor_admin_id,
        source_reference=str(operation.id),
        description="JPEG de conteúdo armazenado",
    )
    db.add(entry)
    db.flush()
    db.add(PhotographerCreditAllocationEvent(
        tenant_id=tenant_id,
        source_entry_id=source.id,
        operation_id=operation.id,
        credit_entry_id=entry.id,
        event_type="consumed",
        quantity=1,
        idempotency_key=f"consume:{operation.id}",
    ))
    operation.status = "consumed"
    operation.completed_at = now()
    operation.updated_at = operation.completed_at
    db.add(PhotoCreditOperationEvent(
        tenant_id=tenant_id,
        operation_id=operation.id,
        event_type="reconciled_consumed" if reconciled else "consumed",
        actor_admin_id=actor_admin_id,
        details={"credit_entry_id": str(entry.id), "source_entry_id": str(source.id)},
    ))
    db.flush()
    return entry


def release_photo_credit(
    db: Session,
    tenant_id: UUID,
    photo_asset_id: UUID,
    *,
    proven_pre_durable_failure: bool,
    actor_admin_id: UUID | None = None,
    reconciled: bool = False,
) -> PhotoCreditOperation:
    wallet = _lock_wallet(db, tenant_id)
    if wallet.mode == "unmetered":
        raise HTTPException(409, "Tenant ilimitado não possui reservas de crédito.")
    operation = _lock_operation(db, tenant_id, photo_asset_id)
    if operation.status == "released":
        return operation
    if operation.status == "consumed":
        raise HTTPException(409, "Uma operação consumida não pode liberar créditos.")
    if operation.status not in {"reserved", "reconciliation_required"}:
        raise HTTPException(409, "A operação não possui uma reserva ativa.")

    sources = _active_operation_sources(db, operation)
    if not sources:
        raise HTTPException(503, "Reserva de créditos inconsistente.")
    if not proven_pre_durable_failure:
        operation.status = "reconciliation_required"
        operation.updated_at = now()
        event_type = "reconciliation_required"
    else:
        for source_id, quantity, reservation_id in sources:
            db.add(PhotographerCreditAllocationEvent(
                tenant_id=tenant_id,
                source_entry_id=source_id,
                operation_id=operation.id,
                credit_entry_id=None,
                event_type="released",
                quantity=quantity,
                idempotency_key=f"release:{reservation_id}",
            ))
        operation.status = "released"
        operation.completed_at = now()
        operation.updated_at = operation.completed_at
        event_type = "reconciled_released" if reconciled else "released"
    db.add(PhotoCreditOperationEvent(
        tenant_id=tenant_id,
        operation_id=operation.id,
        event_type=event_type,
        actor_admin_id=actor_admin_id,
    ))
    db.flush()
    return operation


def reconcile_photo_credit(
    db: Session,
    tenant_id: UUID,
    photo_asset_id: UUID,
    payload_fingerprint: str,
    *,
    source_is_durable: bool | None,
    actor_admin_id: UUID | None = None,
) -> PhotographerCreditEntry | PhotoCreditOperation | None:
    """Resolve uma operação pendente somente com prova do arquivo ou da ausência dele."""
    _lock_wallet(db, tenant_id)
    operation = _lock_operation(db, tenant_id, photo_asset_id)
    if operation.payload_fingerprint != payload_fingerprint:
        raise HTTPException(409, "Fingerprint da operação não corresponde.")
    if operation.status in {"consumed", "released"}:
        return operation
    if source_is_durable is None and operation.status == "reconciliation_required":
        return operation
    if source_is_durable is True:
        return consume_photo_credit(
            db,
            tenant_id,
            photo_asset_id,
            payload_fingerprint,
            actor_admin_id=actor_admin_id,
            reconciled=True,
        )
    return release_photo_credit(
        db,
        tenant_id,
        photo_asset_id,
        proven_pre_durable_failure=source_is_durable is False,
        actor_admin_id=actor_admin_id,
        reconciled=True,
    )


def _claim_stale_photo_credit_operation(
    db: Session,
    tenant_id: UUID,
    operation_id: UUID,
    stale_operation,
) -> PhotoCreditOperation | None:
    return db.scalar(
        select(PhotoCreditOperation)
        .join(Tenant, Tenant.id == PhotoCreditOperation.tenant_id)
        .where(
            Tenant.status == "active",
            PhotoCreditOperation.tenant_id == tenant_id,
            PhotoCreditOperation.id == operation_id,
            stale_operation,
        )
        .with_for_update(of=PhotoCreditOperation, skip_locked=True)
    )


def reconcile_next_stale_photo_credit_operation(db: Session) -> bool:
    """Reconcile uma reserva antiga por prova confinada da fonte persistida."""
    instant = now()
    stale_reservation_before = instant - timedelta(minutes=15)
    retry_unknown_before = instant - timedelta(minutes=1)
    stale_operation = or_(
        and_(
            PhotoCreditOperation.status == "reserved",
            PhotoCreditOperation.updated_at <= stale_reservation_before,
        ),
        and_(
            PhotoCreditOperation.status == "reconciliation_required",
            PhotoCreditOperation.updated_at <= retry_unknown_before,
        ),
    )
    candidate = db.execute(
        select(PhotoCreditOperation.tenant_id, PhotoCreditOperation.id)
        .join(Tenant, Tenant.id == PhotoCreditOperation.tenant_id)
        .where(
            Tenant.status == "active",
            stale_operation,
        )
        .order_by(PhotoCreditOperation.updated_at, PhotoCreditOperation.id)
        .limit(1)
    ).first()
    if candidate is None:
        return False

    tenant_id, operation_id = candidate
    _lock_wallet(db, tenant_id)
    operation = _claim_stale_photo_credit_operation(
        db, tenant_id, operation_id, stale_operation,
    )
    if operation is None:
        return False

    prior_status = operation.status
    source_is_durable: bool | None
    try:
        if operation.photo_asset_id is not None:
            photo = db.get(PhotoAsset, operation.photo_asset_id)
            if (
                photo is None
                or photo.tenant_id != operation.tenant_id
                or photo.storage_key != operation.storage_key_snapshot
            ):
                source_is_durable = None
            else:
                path = safe_source_path_from_credit_snapshot(
                    operation.storage_key_snapshot, operation.tenant_id,
                )
                source_is_durable = source_fingerprint_state(
                    path, operation.payload_fingerprint,
                )
        else:
            path = safe_source_path_from_credit_snapshot(
                operation.storage_key_snapshot, operation.tenant_id,
            )
            source_is_durable = source_fingerprint_state(
                path, operation.payload_fingerprint,
            )
    except (OSError, ValueError):
        source_is_durable = None

    reconcile_photo_credit(
        db,
        operation.tenant_id,
        operation.photo_asset_id_snapshot,
        operation.payload_fingerprint,
        source_is_durable=source_is_durable,
    )
    if source_is_durable is None and prior_status == "reconciliation_required":
        operation.updated_at = now()
        db.add(PhotoCreditOperationEvent(
            tenant_id=operation.tenant_id,
            operation_id=operation.id,
            event_type="reconciliation_required",
            details={"source_state": "unknown"},
        ))
    db.flush()
    return True


def entry_payload(entry: PhotographerCreditEntry) -> dict[str, object]:
    return {
        "id": str(entry.id),
        "type": entry.entry_type,
        "delta": entry.delta,
        "source_reference": entry.source_reference,
        "description": entry.description,
        "created_at": entry.created_at,
    }


def package_payload(package: PhotographerCreditPackage) -> dict[str, object]:
    return {
        "id": str(package.id),
        "name": package.name,
        "description": package.description,
        "credit_quantity": package.credit_quantity,
        "price_cents": package.price_cents,
        "currency_code": package.currency_code,
        "active": package.active,
        "created_at": package.created_at,
        "updated_at": package.updated_at,
    }


def _lock_wallet(db: Session, tenant_id: UUID) -> TenantCreditWallet:
    wallet = db.scalar(select(TenantCreditWallet).where(
        TenantCreditWallet.tenant_id == tenant_id,
    ).with_for_update())
    if wallet is None:
        raise HTTPException(503, "Carteira indisponível.")
    return wallet


def _lock_finite_wallet(db: Session, tenant_id: UUID) -> TenantCreditWallet:
    wallet = _lock_wallet(db, tenant_id)
    if wallet.mode != "finite":
        raise HTTPException(409, "Carteira finita indisponível.")
    return wallet


def _lock_operation(db: Session, tenant_id: UUID, photo_asset_id: UUID) -> PhotoCreditOperation:
    operation = db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo_asset_id,
    ).with_for_update())
    if operation is None:
        raise HTTPException(404, "Operação de créditos não encontrada.")
    return operation


def _allocation_events(db: Session, tenant_id: UUID, source_entry_id: UUID):
    return list(db.scalars(select(PhotographerCreditAllocationEvent).where(
        PhotographerCreditAllocationEvent.tenant_id == tenant_id,
        PhotographerCreditAllocationEvent.source_entry_id == source_entry_id,
    ).order_by(PhotographerCreditAllocationEvent.occurred_at, PhotographerCreditAllocationEvent.id)))


def _source_available(db: Session, source: PhotographerCreditEntry) -> int:
    events = _allocation_events(db, source.tenant_id, source.id)
    archive_events = list(db.scalars(select(MediaArchiveRecoveryCreditAllocationEvent).where(
        MediaArchiveRecoveryCreditAllocationEvent.tenant_id == source.tenant_id,
        MediaArchiveRecoveryCreditAllocationEvent.source_entry_id == source.id,
    ).order_by(
        MediaArchiveRecoveryCreditAllocationEvent.occurred_at,
        MediaArchiveRecoveryCreditAllocationEvent.id,
    )))
    all_events = [*events, *archive_events]
    used = sum(event.quantity for event in all_events if event.event_type in {"consumed", "revoked"})
    reserved = sum(event.quantity for event in all_events if event.event_type == "reserved")
    closed_reservations = sum(
        event.quantity for event in all_events if event.event_type in {"consumed", "released"}
    )
    return source.delta - used - max(0, reserved - closed_reservations)


def _oldest_available_source(db: Session, tenant_id: UUID) -> PhotographerCreditEntry | None:
    entries = db.scalars(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant_id,
        PhotographerCreditEntry.delta > 0,
    ).order_by(PhotographerCreditEntry.created_at, PhotographerCreditEntry.id).with_for_update())
    return next((entry for entry in entries if _source_available(db, entry) > 0), None)


def _active_operation_sources(
    db: Session, operation: PhotoCreditOperation,
) -> list[tuple[UUID, int, UUID]]:
    events = list(db.scalars(select(PhotographerCreditAllocationEvent).where(
        PhotographerCreditAllocationEvent.tenant_id == operation.tenant_id,
        PhotographerCreditAllocationEvent.operation_id == operation.id,
    ).order_by(PhotographerCreditAllocationEvent.occurred_at, PhotographerCreditAllocationEvent.id)))
    by_source: dict[UUID, dict[str, object]] = {}
    for event in events:
        state = by_source.setdefault(event.source_entry_id, {"reserved": [], "closed": 0})
        if event.event_type == "reserved":
            state["reserved"].append((event.quantity, event.id))
        elif event.event_type in {"released", "consumed"}:
            state["closed"] += event.quantity
    active: list[tuple[UUID, int, UUID]] = []
    for source_id, state in by_source.items():
        reservations = state["reserved"]
        closed = int(state["closed"])
        for quantity, reservation_id in reservations:
            used_to_close = min(quantity, closed)
            closed -= used_to_close
            if used_to_close < quantity:
                active.append((source_id, quantity - used_to_close, reservation_id))
    return active


def _require_operation_reservation(
    db: Session, operation: PhotoCreditOperation,
) -> PhotographerCreditEntry:
    sources = _active_operation_sources(db, operation)
    if len(sources) != 1 or sources[0][1] != 1:
        raise HTTPException(503, "Reserva de créditos inconsistente.")
    source_id, _, _ = sources[0]
    source = db.scalar(select(PhotographerCreditEntry).where(
        PhotographerCreditEntry.id == source_id,
        PhotographerCreditEntry.tenant_id == operation.tenant_id,
        PhotographerCreditEntry.delta > 0,
    ))
    if source is None:
        raise HTTPException(503, "Origem da reserva indisponível.")
    return source


def _require_allocation_event(db: Session, tenant_id: UUID, idempotency_key: str) -> None:
    found = db.scalar(select(PhotographerCreditAllocationEvent.id).where(
        PhotographerCreditAllocationEvent.tenant_id == tenant_id,
        PhotographerCreditAllocationEvent.idempotency_key == idempotency_key,
    ))
    if found is None:
        raise HTTPException(503, "Alocação financeira inconsistente.")


def _validate_package(
    name: str,
    credit_quantity: int,
    price_cents: int | None,
    currency_code: str | None,
    active: bool,
) -> None:
    if not name.strip() or len(name.strip()) > 120:
        raise HTTPException(422, "Nome do pacote inválido.")
    if credit_quantity <= 0 or credit_quantity > 2_147_483_647:
        raise HTTPException(422, "Quantidade de créditos inválida.")
    if (price_cents is None) != (currency_code is None):
        raise HTTPException(422, "Preço e moeda devem ser informados em conjunto.")
    if price_cents is not None and (price_cents <= 0 or price_cents > 2_147_483_647):
        raise HTTPException(422, "Preço inválido.")
    if currency_code is not None and re.fullmatch(r"[A-Z]{3}", currency_code) is None:
        raise HTTPException(422, "Moeda inválida.")
    if active and (price_cents is None or currency_code is None):
        raise HTTPException(422, "Pacote sem preço não pode ser ativado.")
