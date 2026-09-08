"""Ciclo de vida persistente do rollout facial por ambiente e galeria."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, FacialRollout, ParentGallery, now
from app.facial.calibration import calibration_is_approved
from app.facial.config import FacialSettings
from app.facial.purge import enqueue_gallery_purge, invalidate_gallery_searches

ROLLOUT_ENVIRONMENTS = frozenset(
    {"local", "development", "test", "homolog", "staging", "prod", "production"}
)
ROLLOUT_STAGES = frozenset({"dark", "canary", "limited", "general"})
ACTIVE_STAGES = frozenset({"canary", "limited", "general"})
APPROVAL_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")


class FacialRolloutError(RuntimeError):
    """Transição de rollout inválida ou fora do escopo autorizado."""


@dataclass(frozen=True)
class FacialRolloutDraft:
    model_version: str
    quality_version: str
    calibration_version: str
    legal_notice_version: str
    consent_version: str
    legal_basis_reference: str
    retention_policy_version: str


def draft_from_settings(settings: FacialSettings) -> FacialRolloutDraft:
    return FacialRolloutDraft(
        model_version=settings.model_version,
        quality_version=settings.quality_version,
        calibration_version=settings.calibration_version,
        legal_notice_version=settings.legal_notice_version,
        consent_version=settings.consent_version,
        legal_basis_reference=settings.legal_basis_reference,
        retention_policy_version=settings.retention_policy_version,
    )


def read_rollout(
    db: Session,
    *,
    environment: str,
    parent_gallery_id: UUID,
    for_update: bool = False,
) -> FacialRollout | None:
    query = select(FacialRollout).where(
        FacialRollout.environment == environment,
        FacialRollout.parent_gallery_id == parent_gallery_id,
    )
    if for_update:
        query = query.with_for_update()
    return db.scalar(query)


def prepare_rollout(
    db: Session,
    *,
    environment: str,
    parent_gallery_id: UUID,
    draft: FacialRolloutDraft,
) -> FacialRollout:
    environment = _validate_environment(environment)
    _validate_draft(draft)
    parent = db.get(ParentGallery, parent_gallery_id)
    if parent is None or not parent.active or parent.lifecycle_status != "active":
        raise FacialRolloutError("Galeria pública indisponível para rollout facial.")
    rollout = read_rollout(
        db,
        environment=environment,
        parent_gallery_id=parent_gallery_id,
        for_update=True,
    )
    if rollout is not None and rollout.status == "active":
        raise FacialRolloutError("Suspenda o rollout ativo antes de prepará-lo novamente.")
    instant = now()
    values = draft.__dict__
    if rollout is None:
        rollout = FacialRollout(
            environment=environment,
            parent_gallery_id=parent_gallery_id,
            status="prepared",
            stage="dark",
            **values,
        )
        db.add(rollout)
    else:
        for name, value in values.items():
            setattr(rollout, name, value)
        rollout.status = "prepared"
        rollout.stage = "dark"
        rollout.approval_reference = None
        rollout.approved_by_admin_id = None
        rollout.approved_at = None
        rollout.activated_at = None
        rollout.suspended_at = None
        rollout.revoked_at = None
        rollout.updated_at = instant
    try:
        db.flush()
    except IntegrityError as error:
        raise FacialRolloutError("Já existe rollout facial para este ambiente e galeria.") from error
    _audit(db, rollout, "prepared")
    db.flush()
    return rollout


def activate_rollout(
    db: Session,
    *,
    environment: str,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
    approval_reference: str,
    stage: str,
    settings: FacialSettings,
) -> FacialRollout:
    environment = _validate_environment(environment)
    stage = stage.strip().lower()
    if stage not in ACTIVE_STAGES:
        raise FacialRolloutError("A ativação exige etapa canary, limited ou general.")
    if not APPROVAL_REFERENCE_RE.fullmatch(approval_reference.strip()):
        raise FacialRolloutError("Referência opaca de aprovação inválida.")
    if not settings.enabled or settings.environment != environment:
        raise FacialRolloutError("O kill switch e o ambiente facial não autorizam ativação.")
    if not calibration_is_approved(db, settings):
        raise FacialRolloutError("Calibração e grupos relevantes não foram aprovados.")
    if db.get(AdminUser, actor_admin_id) is None:
        raise FacialRolloutError("Administrador aprovador indisponível.")
    rollout = _required_rollout(
        db,
        environment=environment,
        parent_gallery_id=parent_gallery_id,
    )
    if rollout.status == "revoked":
        raise FacialRolloutError("Rollout revogado deve ser preparado novamente.")
    if rollout.status == "active":
        if (
            rollout.stage == stage
            and rollout.approved_by_admin_id == actor_admin_id
            and rollout.approval_reference == approval_reference.strip()
        ):
            return rollout
        raise FacialRolloutError("Rollout já está ativo com outro escopo de aprovação.")
    if rollout.status not in {"prepared", "suspended"}:
        raise FacialRolloutError("Estado de rollout inválido para ativação.")
    if not _versions_match(rollout, settings):
        raise FacialRolloutError("Versões do rollout divergem da configuração facial.")
    instant = now()
    rollout.status = "active"
    rollout.stage = stage
    rollout.approval_reference = approval_reference.strip()
    rollout.approved_by_admin_id = actor_admin_id
    rollout.approved_at = instant
    rollout.activated_at = instant
    rollout.suspended_at = None
    rollout.revoked_at = None
    rollout.updated_at = instant
    _audit(db, rollout, "activated", actor_admin_id=actor_admin_id)
    db.flush()
    return rollout


def suspend_rollout(
    db: Session,
    *,
    environment: str,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
) -> FacialRollout:
    rollout = _required_rollout(
        db,
        environment=_validate_environment(environment),
        parent_gallery_id=parent_gallery_id,
    )
    if rollout.status not in {"active", "suspended"}:
        raise FacialRolloutError("Somente rollout ativo pode ser suspenso.")
    if rollout.status == "active":
        instant = now()
        rollout.status = "suspended"
        rollout.suspended_at = instant
        rollout.updated_at = instant
        _audit(db, rollout, "suspended", actor_admin_id=actor_admin_id)
    _schedule_scope_shutdown(db, rollout, reason="suspended")
    db.flush()
    return rollout


def revoke_rollout(
    db: Session,
    *,
    environment: str,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
) -> FacialRollout:
    rollout = _required_rollout(
        db,
        environment=_validate_environment(environment),
        parent_gallery_id=parent_gallery_id,
    )
    if rollout.status != "revoked":
        instant = now()
        rollout.status = "revoked"
        rollout.revoked_at = instant
        rollout.updated_at = instant
        _audit(db, rollout, "revoked", actor_admin_id=actor_admin_id)
    _schedule_scope_shutdown(db, rollout, reason="revoked")
    db.flush()
    return rollout


def rollout_is_active(
    db: Session,
    *,
    settings: FacialSettings,
    parent_gallery_id: UUID,
    for_update: bool = False,
) -> bool:
    if not settings.enabled:
        return False
    if not calibration_is_approved(db, settings):
        return False
    rollout = read_rollout(
        db,
        environment=settings.environment,
        parent_gallery_id=parent_gallery_id,
        for_update=for_update,
    )
    return bool(
        rollout
        and rollout.status == "active"
        and rollout.stage in ACTIVE_STAGES
        and _versions_match(rollout, settings)
    )


def rollout_status_payload(
    rollout: FacialRollout | None,
    *,
    available: bool,
) -> dict[str, object]:
    """Expõe ao painel somente disponibilidade e estado operacional."""

    return {
        "status": rollout.status if rollout else "unavailable",
        "stage": rollout.stage if rollout else None,
        "available": available,
    }


def _required_rollout(
    db: Session, *, environment: str, parent_gallery_id: UUID
) -> FacialRollout:
    rollout = read_rollout(
        db,
        environment=environment,
        parent_gallery_id=parent_gallery_id,
        for_update=True,
    )
    if rollout is None:
        raise FacialRolloutError("Rollout facial não encontrado.")
    return rollout


def _validate_environment(environment: str) -> str:
    normalized = environment.strip().lower()
    if normalized not in ROLLOUT_ENVIRONMENTS:
        raise FacialRolloutError("Ambiente de rollout facial inválido.")
    return normalized


def _schedule_scope_shutdown(
    db: Session,
    rollout: FacialRollout,
    *,
    reason: str,
) -> None:
    invalidate_gallery_searches(
        db,
        parent_gallery_id=rollout.parent_gallery_id,
    )
    enqueue_gallery_purge(
        db,
        parent_gallery_id=rollout.parent_gallery_id,
        reason=f"rollout-{reason}:{rollout.id}",
    )


def _validate_draft(draft: FacialRolloutDraft) -> None:
    if any(not value.strip() for value in draft.__dict__.values()):
        raise FacialRolloutError("Versões e referências do rollout são obrigatórias.")


def _versions_match(rollout: FacialRollout, settings: FacialSettings) -> bool:
    expected = draft_from_settings(settings)
    return all(getattr(rollout, name) == value for name, value in expected.__dict__.items())


def _audit(
    db: Session,
    rollout: FacialRollout,
    action: str,
    *,
    actor_admin_id: UUID | None = None,
) -> None:
    actor = f";actor_id:{actor_admin_id}" if actor_admin_id else ""
    db.add(
        AuditEvent(
            event=f"facial.rollout_{action}",
            subject=(
                f"rollout_id:{rollout.id};gallery_id:{rollout.parent_gallery_id};"
                f"environment:{rollout.environment};stage:{rollout.stage}{actor}"
            ),
        )
    )
