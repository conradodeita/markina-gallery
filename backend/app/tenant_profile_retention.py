"""Redução explícita e tenant-scoped de CPF/endereço após revisão do encerramento."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCycle,
    PhotographerBusinessProfile,
    PlatformAdminEvent,
    Tenant,
    TenantClosureMediaDeletionBatch,
    TenantClosureRequest,
    now,
)
from app.photographer_cpf import PhotographerCpfFingerprintError, cpf_matches_tenant
from app.private_fields import PrivateFieldError, decrypt_private_field
from app.system_monitor.access import is_owner
from app.tenant_closure_obligations import operational_obligation_blockers

CONFIRMATION = "REMOVER CPF E ENDEREÇO"


@dataclass(frozen=True)
class ProfileReductionPlan:
    closure: TenantClosureRequest | None
    profile: PhotographerBusinessProfile | None
    state: str
    blocker: str | None


def _verified_media_deletion(db: Session, tenant_id: UUID, closure_id: UUID) -> bool:
    from app.tenant_media_deletion import batch_inventory_snapshot

    batch = db.scalar(select(TenantClosureMediaDeletionBatch).where(
        TenantClosureMediaDeletionBatch.tenant_id == tenant_id,
        TenantClosureMediaDeletionBatch.closure_request_id == closure_id,
        TenantClosureMediaDeletionBatch.state == "completed",
    ))
    if batch is None:
        return False
    digest, count, size, cycle_ids, deleted = batch_inventory_snapshot(db, batch_id=batch.id)
    cycles = list(db.execute(select(MediaArchiveCycle.id, MediaArchiveCycle.state).where(
        MediaArchiveCycle.tenant_id == tenant_id,
    )))
    return bool(
        deleted and count > 0 and cycle_ids == {row.id for row in cycles}
        and all(row.state == "deleted" for row in cycles)
        and digest == batch.inventory_sha256 and count == batch.object_count
        and count == batch.verified_deleted_object_count and size == batch.total_bytes
    )


def profile_reduction_plan(db: Session, *, tenant_id: UUID) -> ProfileReductionPlan:
    from app.tenant_closure_recovery import _as_utc, _ten_year_anniversary

    tenant = db.get(Tenant, tenant_id, populate_existing=True)
    closure = db.scalar(select(TenantClosureRequest).where(
        TenantClosureRequest.tenant_id == tenant_id,
    ).order_by(TenantClosureRequest.requested_at.desc(), TenantClosureRequest.id.desc()).limit(1))
    profile = db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == tenant_id,
    ).execution_options(populate_existing=True))
    state = "unavailable" if profile is None else (
        "reduced" if profile.cpf_envelope is None and profile.address_envelope is None else "retained"
    )
    blocker = None
    if tenant is None or tenant.lifecycle != "closed":
        blocker = "account_not_closed"
    elif closure is None or closure.state != "closed" or closure.closed_at is None:
        blocker = "closure_history_unavailable"
    elif _as_utc(now()) < _ten_year_anniversary(_as_utc(closure.closed_at)):
        blocker = "review_not_due"
    elif profile is None:
        blocker = "profile_unavailable"
    elif state == "reduced":
        blocker = "already_reduced"
    elif operational_obligation_blockers(db, tenant_id):
        blocker = "obligations_pending"
    else:
        try:
            if profile.cpf_fingerprint and profile.cpf_fingerprint_key_version and profile.cpf_envelope:
                cpf = decrypt_private_field(profile.cpf_envelope, tenant_id=tenant_id, field="photographer-cpf")
                if not cpf_matches_tenant(db, tenant_id, cpf):
                    blocker = "identity_protection_unavailable"
            elif not _verified_media_deletion(db, tenant_id, closure.id):
                blocker = "identity_protection_unavailable"
        except (PrivateFieldError, PhotographerCpfFingerprintError):
            blocker = "identity_protection_unavailable"
    return ProfileReductionPlan(closure, profile, state, blocker)


def profile_retention_payload(db: Session, *, tenant_id: UUID) -> dict:
    plan = profile_reduction_plan(db, tenant_id=tenant_id)
    last = db.scalar(select(PlatformAdminEvent.created_at).where(
        PlatformAdminEvent.tenant_id == tenant_id,
        PlatformAdminEvent.action == "tenant.profile_reduced",
        PlatformAdminEvent.result == "success",
    ).order_by(PlatformAdminEvent.created_at.desc()).limit(1))
    return {
        "state": plan.state, "eligible": plan.blocker is None, "blocker": plan.blocker,
        "confirmation_phrase": CONFIRMATION, "reduced_at": last.isoformat() if last else None,
    }


def reduce_closed_profile(
    db: Session, *, owner_id: UUID, tenant_id: UUID, confirmation: str, confirm_review: bool,
) -> UUID:
    if not is_owner(db, owner_id):
        raise HTTPException(403, "Acesso não autorizado.")
    if confirmation != CONFIRMATION or confirm_review is not True:
        raise HTTPException(422, "Confirme a revisão e a redução solicitada.")
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                       .execution_options(populate_existing=True))
    if tenant is None:
        raise HTTPException(404, "Conta não encontrada.")
    db.scalar(select(PhotographerBusinessProfile).where(
        PhotographerBusinessProfile.tenant_id == tenant_id,
    ).with_for_update().execution_options(populate_existing=True))
    plan = profile_reduction_plan(db, tenant_id=tenant_id)
    if plan.blocker or plan.profile is None or plan.closure is None:
        raise HTTPException(409, "A revisão do cadastro ainda não atende às condições para redução.")
    plan.profile.cpf_envelope = None
    plan.profile.address_envelope = None
    db.flush()
    return plan.closure.id
