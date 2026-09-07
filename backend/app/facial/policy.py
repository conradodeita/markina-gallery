"""Política técnica facial automática e lifecycle operacional compatível."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuditEvent, GalleryFacialPolicy, ParentGallery, now
from app.facial.config import FacialSettings
from app.facial.purge import enqueue_gallery_purge


class FacialPolicyError(RuntimeError):
    """Política facial não pode avançar no estado solicitado."""


@dataclass(frozen=True)
class FacialPolicyDraft:
    legal_notice_version: str
    legal_basis_reference: str
    retention_policy_version: str
    minor_policy_version: str
    model_version: str
    quality_version: str
    calibration_version: str
    similarity_threshold_milli: int


def read_policy(db: Session, parent_gallery_id: UUID) -> GalleryFacialPolicy | None:
    return db.scalar(
        select(GalleryFacialPolicy).where(
            GalleryFacialPolicy.parent_gallery_id == parent_gallery_id
        )
    )


def ensure_automatic_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    settings: FacialSettings,
) -> tuple[GalleryFacialPolicy, bool]:
    """Garante a política interna sem exigir ação do fotógrafo.

    O segundo item indica se uma galeria ausente, inativa ou divergente precisa de
    backfill. Uma política já ativa e compatível não é alterada.
    """

    if not settings.enabled:
        raise FacialPolicyError("O processamento facial está desligado no ambiente.")
    parent = db.get(ParentGallery, parent_gallery_id)
    if (
        not parent
        or not parent.active
        or parent.lifecycle_status != "active"
    ):
        raise FacialPolicyError("Galeria pública indisponível para indexação facial.")
    draft = _draft_from_settings(settings)
    _validate_draft(draft)
    policy = read_policy(db, parent_gallery_id)
    previous_signature = _signature(policy)
    was_active = bool(policy and policy.status == "active")
    changed = not was_active or previous_signature != tuple(draft.__dict__.values())
    if not changed:
        assert policy is not None
        return policy, False

    instant = now()
    if policy is None:
        policy = GalleryFacialPolicy(
            parent_gallery_id=parent_gallery_id,
            status="active",
            actor_admin_id=None,
            activated_at=instant,
            index_generation=1,
            **draft.__dict__,
        )
        db.add(policy)
    else:
        if was_active and previous_signature != tuple(draft.__dict__.values()):
            enqueue_gallery_purge(
                db,
                parent_gallery_id=parent_gallery_id,
                reason=f"automatic-policy-version-change:{instant.isoformat()}",
            )
        for field_name, value in draft.__dict__.items():
            setattr(policy, field_name, value)
        policy.status = "active"
        policy.actor_admin_id = None
        policy.activated_at = instant
        policy.suspended_at = None
        policy.index_generation = max(1, policy.index_generation + 1)
        policy.updated_at = instant
    db.add(
        AuditEvent(
            event="facial.policy_activated_automatically",
            subject=(
                f"gallery_id:{parent_gallery_id};generation:{policy.index_generation};"
                f"reason:{'created' if previous_signature is None else 'reconciled'}"
            ),
        )
    )
    db.flush()
    return policy, True


def prepare_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
    draft: FacialPolicyDraft,
) -> GalleryFacialPolicy:
    parent = db.get(ParentGallery, parent_gallery_id)
    if not parent or parent.lifecycle_status in {"deleting", "deleted"}:
        raise FacialPolicyError("Galeria pública indisponível para política facial.")
    _validate_draft(draft)
    policy = read_policy(db, parent_gallery_id)
    previous_signature = _signature(policy) if policy else None
    was_active = bool(policy and policy.status == "active")
    if policy is None:
        policy = GalleryFacialPolicy(
            parent_gallery_id=parent_gallery_id,
            status="pending",
            actor_admin_id=actor_admin_id,
            **draft.__dict__,
        )
        db.add(policy)
    else:
        for field_name, value in draft.__dict__.items():
            setattr(policy, field_name, value)
        policy.status = "pending"
        policy.actor_admin_id = actor_admin_id
        policy.activated_at = None
        policy.updated_at = now()
    if was_active and previous_signature != _signature(policy):
        enqueue_gallery_purge(
            db,
            parent_gallery_id=parent_gallery_id,
            reason=f"policy-version-change:{policy.updated_at.isoformat()}",
        )
    db.add(
        AuditEvent(
            event="facial.policy_prepared",
            subject=f"gallery_id:{parent_gallery_id};actor_id:{actor_admin_id}",
        )
    )
    db.flush()
    return policy


def activation_inventory(
    policy: GalleryFacialPolicy | None, settings: FacialSettings
) -> list[str]:
    missing: list[str] = []
    if policy is None:
        return ["policy"]
    expected = {
        "kill_switch": settings.enabled,
        "environment": settings.credential_environment == settings.environment,
        "legal_notice_version": policy.legal_notice_version
        == settings.legal_notice_version,
        "legal_basis_reference": policy.legal_basis_reference
        == settings.legal_basis_reference,
        "retention_policy_version": policy.retention_policy_version
        == settings.retention_policy_version,
        "minor_policy_version": policy.minor_policy_version
        == settings.minor_policy_version,
        "model_version": policy.model_version == settings.model_version,
        "quality_version": policy.quality_version == settings.quality_version,
        "calibration_version": policy.calibration_version
        == settings.calibration_version,
        "encryption_key": bool(settings.active_key_id and settings.aead_keys),
        "minor_gate": not settings.minor_search_enabled
        or settings.private_homologation_active,
    }
    missing.extend(name for name, valid in expected.items() if not valid)
    return missing


def activate_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
    settings: FacialSettings,
) -> GalleryFacialPolicy:
    policy = read_policy(db, parent_gallery_id)
    missing = activation_inventory(policy, settings)
    if missing:
        raise FacialPolicyError(
            "Ativação facial recusada; requisitos ausentes: " + ", ".join(missing)
        )
    assert policy is not None
    policy.status = "active"
    policy.actor_admin_id = actor_admin_id
    policy.activated_at = now()
    policy.suspended_at = None
    policy.index_generation += 1
    policy.updated_at = now()
    db.add(
        AuditEvent(
            event="facial.policy_activated",
            subject=(
                f"gallery_id:{parent_gallery_id};actor_id:{actor_admin_id};"
                f"generation:{policy.index_generation}"
            ),
        )
    )
    db.flush()
    return policy


def suspend_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
) -> GalleryFacialPolicy:
    policy = read_policy(db, parent_gallery_id)
    if policy is None:
        raise FacialPolicyError("Política facial não encontrada.")
    if policy.status != "suspended":
        policy.status = "suspended"
        policy.actor_admin_id = actor_admin_id
        policy.suspended_at = now()
        policy.updated_at = now()
        enqueue_gallery_purge(
            db,
            parent_gallery_id=parent_gallery_id,
            reason=f"policy-suspended:{policy.updated_at.isoformat()}",
        )
        db.add(
            AuditEvent(
                event="facial.policy_suspended",
                subject=f"gallery_id:{parent_gallery_id};actor_id:{actor_admin_id}",
            )
        )
    db.flush()
    return policy


def revoke_policy(
    db: Session,
    *,
    parent_gallery_id: UUID,
    actor_admin_id: UUID,
) -> GalleryFacialPolicy:
    policy = read_policy(db, parent_gallery_id)
    if policy is None:
        raise FacialPolicyError("Política facial não encontrada.")
    if policy.status != "disabled":
        policy.status = "disabled"
        policy.actor_admin_id = actor_admin_id
        policy.suspended_at = now()
        policy.updated_at = now()
        enqueue_gallery_purge(
            db,
            parent_gallery_id=parent_gallery_id,
            reason=f"purpose-revoked:{policy.updated_at.isoformat()}",
        )
        db.add(
            AuditEvent(
                event="facial.policy_revoked",
                subject=f"gallery_id:{parent_gallery_id};actor_id:{actor_admin_id}",
            )
        )
    db.flush()
    return policy


def policy_payload(
    policy: GalleryFacialPolicy | None, settings: FacialSettings
) -> dict[str, object]:
    return {
        "status": policy.status if policy else "disabled",
        "ready_for_activation": not activation_inventory(policy, settings),
        "missing_requirements": activation_inventory(policy, settings),
        "legal_notice_version": (
            policy.legal_notice_version if policy else settings.legal_notice_version or None
        ),
        "legal_basis_reference": (
            policy.legal_basis_reference if policy else settings.legal_basis_reference or None
        ),
        "retention_policy_version": (
            policy.retention_policy_version
            if policy
            else settings.retention_policy_version or None
        ),
        "minor_policy_version": (
            policy.minor_policy_version if policy else settings.minor_policy_version or None
        ),
        "model_version": policy.model_version if policy else settings.model_version or None,
        "quality_version": policy.quality_version if policy else settings.quality_version or None,
        "calibration_version": (
            policy.calibration_version if policy else settings.calibration_version or None
        ),
        "similarity_threshold_milli": (
            policy.similarity_threshold_milli
            if policy
            else settings.similarity_threshold_milli
        ),
        "index_generation": policy.index_generation if policy else 0,
        "activated_at": policy.activated_at.isoformat()
        if policy and policy.activated_at
        else None,
        "suspended_at": policy.suspended_at.isoformat()
        if policy and policy.suspended_at
        else None,
    }


def _validate_draft(draft: FacialPolicyDraft) -> None:
    if any(not str(value).strip() for value in draft.__dict__.values() if isinstance(value, str)):
        raise FacialPolicyError("A política facial preparada está incompleta.")
    if not 0 <= draft.similarity_threshold_milli <= 1000:
        raise FacialPolicyError("Limiar facial inválido.")


def _draft_from_settings(settings: FacialSettings) -> FacialPolicyDraft:
    return FacialPolicyDraft(
        legal_notice_version=settings.legal_notice_version,
        legal_basis_reference=settings.legal_basis_reference,
        retention_policy_version=settings.retention_policy_version,
        minor_policy_version=settings.minor_policy_version,
        model_version=settings.model_version,
        quality_version=settings.quality_version,
        calibration_version=settings.calibration_version,
        similarity_threshold_milli=settings.similarity_threshold_milli,
    )


def _signature(policy: GalleryFacialPolicy | None) -> tuple[object, ...] | None:
    if policy is None:
        return None
    return (
        policy.legal_notice_version,
        policy.legal_basis_reference,
        policy.retention_policy_version,
        policy.minor_policy_version,
        policy.model_version,
        policy.quality_version,
        policy.calibration_version,
        policy.similarity_threshold_milli,
    )
