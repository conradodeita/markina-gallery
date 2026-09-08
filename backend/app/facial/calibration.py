"""Gate humano e minimizado de calibração/equidade para produção."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuditEvent, FacialCalibrationApproval, now
from app.facial.config import FacialSettings

OPAQUE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,199}$")


class FacialCalibrationError(RuntimeError):
    """Aprovação de calibração inválida ou incompleta."""


def approve_calibration(
    db: Session,
    *,
    settings: FacialSettings,
    criteria_version: str,
    corpus_reference: str,
    approval_reference: str,
    relevant_group_count: int,
    approved_group_count: int,
    actor_admin_id: UUID,
) -> FacialCalibrationApproval:
    if settings.environment not in {"prod", "production"}:
        raise FacialCalibrationError("Aprovação de calibração pertence à produção.")
    references = (criteria_version, corpus_reference, approval_reference)
    if any(not OPAQUE_REFERENCE_RE.fullmatch(value.strip()) for value in references):
        raise FacialCalibrationError("Referência opaca de calibração inválida.")
    if relevant_group_count < 1 or approved_group_count != relevant_group_count:
        raise FacialCalibrationError("Todos os grupos relevantes exigem aprovação.")
    if db.get(AdminUser, actor_admin_id) is None:
        raise FacialCalibrationError("Administrador aprovador indisponível.")
    for prior in db.scalars(
        select(FacialCalibrationApproval).where(
            FacialCalibrationApproval.environment == settings.environment,
            FacialCalibrationApproval.model_version == settings.model_version,
            FacialCalibrationApproval.quality_version == settings.quality_version,
            FacialCalibrationApproval.calibration_version
            == settings.calibration_version,
            FacialCalibrationApproval.status == "approved",
        )
    ):
        prior.status = "revoked"
        prior.revoked_at = now()
        prior.updated_at = now()
    item = FacialCalibrationApproval(
        environment=settings.environment,
        model_version=settings.model_version,
        quality_version=settings.quality_version,
        calibration_version=settings.calibration_version,
        similarity_threshold_milli=settings.similarity_threshold_milli,
        criteria_version=criteria_version.strip(),
        corpus_reference=corpus_reference.strip(),
        approval_reference=approval_reference.strip(),
        relevant_group_count=relevant_group_count,
        approved_group_count=approved_group_count,
        approved_by_admin_id=actor_admin_id,
        status="approved",
    )
    db.add(item)
    db.flush()
    db.add(
        AuditEvent(
            event="facial.calibration_approved",
            subject=(
                f"calibration_id:{item.id};environment:{item.environment};"
                f"threshold:{item.similarity_threshold_milli};"
                f"groups:{item.approved_group_count}"
            ),
        )
    )
    db.flush()
    return item


def calibration_is_approved(db: Session, settings: FacialSettings) -> bool:
    if settings.environment not in {"prod", "production"}:
        return True
    return (
        db.scalar(
            select(FacialCalibrationApproval.id).where(
                FacialCalibrationApproval.environment == settings.environment,
                FacialCalibrationApproval.model_version == settings.model_version,
                FacialCalibrationApproval.quality_version == settings.quality_version,
                FacialCalibrationApproval.calibration_version
                == settings.calibration_version,
                FacialCalibrationApproval.similarity_threshold_milli
                == settings.similarity_threshold_milli,
                FacialCalibrationApproval.status == "approved",
                FacialCalibrationApproval.approved_group_count
                == FacialCalibrationApproval.relevant_group_count,
            )
        )
        is not None
    )
