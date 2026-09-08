"""Operação explícita, auditável e fail-closed de rollout facial."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, FacialRolloutOperation, now
from app.facial.config import FacialSettings
from app.facial.rollout import (
    ACTIVE_STAGES,
    APPROVAL_REFERENCE_RE,
    ROLLOUT_ENVIRONMENTS,
    ROLLOUT_STAGES,
    activate_rollout,
    draft_from_settings,
    prepare_rollout,
    read_rollout,
    suspend_rollout,
)

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_GATES = frozenset(
    {
        "security",
        "privacy",
        "legal_basis",
        "calibration",
        "capacity",
        "recovery",
        "human_approval",
    }
)


class FacialRolloutOperationError(RuntimeError):
    """Recibo operacional ausente, divergente ou não autorizado."""


@dataclass(frozen=True)
class FacialRolloutOperationProof:
    action: str
    environment: str
    stage: str
    deployment_sha: str
    inventory_reference: str
    backup_reference: str
    gate_set_version: str
    approved_gates: frozenset[str]
    allowlist: tuple[UUID, ...]
    confirmation: str
    actor_admin_id: UUID


def execute_protected_rollout_operation(
    db: Session,
    *,
    proof: FacialRolloutOperationProof,
    settings: FacialSettings,
) -> FacialRolloutOperation:
    action = proof.action.strip().lower()
    environment = proof.environment.strip().lower()
    stage = proof.stage.strip().lower()
    if action not in {"activate", "suspend"}:
        raise FacialRolloutOperationError("Ação de rollout inválida.")
    if environment not in ROLLOUT_ENVIRONMENTS or stage not in ROLLOUT_STAGES:
        raise FacialRolloutOperationError("Ambiente ou etapa de rollout inválidos.")
    if environment != settings.environment:
        raise FacialRolloutOperationError("Escopo diverge da configuração do ambiente.")
    if not FULL_SHA_RE.fullmatch(proof.deployment_sha):
        raise FacialRolloutOperationError("SHA integral publicado é obrigatório.")
    references = (
        proof.inventory_reference,
        proof.backup_reference,
        proof.gate_set_version,
    )
    if any(not APPROVAL_REFERENCE_RE.fullmatch(value.strip()) for value in references):
        raise FacialRolloutOperationError("Inventário, backup e gates são obrigatórios.")
    if proof.approved_gates != REQUIRED_GATES:
        raise FacialRolloutOperationError("Todos os gates de rollout são obrigatórios.")
    allowlist = tuple(sorted(set(proof.allowlist), key=str))
    if not allowlist or len(allowlist) != len(proof.allowlist):
        raise FacialRolloutOperationError("Allowlist explícita e sem duplicidade é obrigatória.")
    expected_confirmation = f"{action.upper()}_FACIAL_{environment.upper()}_{stage.upper()}"
    if proof.confirmation != expected_confirmation:
        raise FacialRolloutOperationError("Confirmação explícita da operação inválida.")
    if db.get(AdminUser, proof.actor_admin_id) is None:
        raise FacialRolloutOperationError("Administrador aprovador indisponível.")
    if action == "activate" and stage in ACTIVE_STAGES and not settings.enabled:
        raise FacialRolloutOperationError("Kill switch precisa estar ativo para esta etapa.")

    digest = sha256("\n".join(map(str, allowlist)).encode("ascii")).hexdigest()
    operation = FacialRolloutOperation(
        environment=environment,
        action=action,
        stage=stage,
        deployment_sha=proof.deployment_sha,
        inventory_reference=proof.inventory_reference.strip(),
        backup_reference=proof.backup_reference.strip(),
        gate_set_version=proof.gate_set_version.strip(),
        allowlist_digest=digest,
        allowlist_count=len(allowlist),
        approved_by_admin_id=proof.actor_admin_id,
    )
    db.add(operation)
    db.flush()
    try:
        for gallery_id in allowlist:
            rollout = read_rollout(
                db,
                environment=environment,
                parent_gallery_id=gallery_id,
            )
            if action == "activate":
                if rollout is None:
                    rollout = prepare_rollout(
                        db,
                        environment=environment,
                        parent_gallery_id=gallery_id,
                        draft=draft_from_settings(settings),
                    )
                if stage in ACTIVE_STAGES:
                    activate_rollout(
                        db,
                        environment=environment,
                        parent_gallery_id=gallery_id,
                        actor_admin_id=proof.actor_admin_id,
                        approval_reference=f"rollout-operation:{operation.id}",
                        stage=stage,
                        settings=settings,
                    )
                elif rollout.status != "prepared":
                    raise FacialRolloutOperationError(
                        "Etapa dark exige rollout preparado e inativo."
                    )
            else:
                if rollout is None or rollout.stage != stage:
                    raise FacialRolloutOperationError(
                        "Suspensão diverge do escopo ou etapa ativa."
                    )
                suspend_rollout(
                    db,
                    environment=environment,
                    parent_gallery_id=gallery_id,
                    actor_admin_id=proof.actor_admin_id,
                )
    except Exception:
        db.rollback()
        raise
    operation.completed_at = now()
    db.add(
        AuditEvent(
            event=f"facial.rollout_operation_{action}",
            subject=(
                f"operation_id:{operation.id};environment:{environment};"
                f"stage:{stage};allowlist_count:{len(allowlist)}"
            ),
        )
    )
    db.flush()
    return operation
