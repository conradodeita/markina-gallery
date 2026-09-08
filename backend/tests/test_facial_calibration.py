"""Gate humano de calibração/equidade antes de produção."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    Base,
    FacialCalibrationApproval,
    ParentGallery,
)
from app.facial.calibration import (
    FacialCalibrationError,
    approve_calibration,
    calibration_is_approved,
)
from app.facial.config import FacialSettings
from app.facial.rollout import (
    FacialRolloutError,
    activate_rollout,
    draft_from_settings,
    prepare_rollout,
    rollout_is_active,
)


def _settings(*, threshold: int = 750) -> FacialSettings:
    return FacialSettings(
        enabled=True,
        environment="production",
        credential_environment="production",
        manifest_path=Path("manifest.json"),
        model_root=Path("models"),
        reference_root=Path("references"),
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        legal_notice_version="notice-v1",
        consent_version="consent-v1",
        legal_basis_reference="legal-basis-v1",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-v1",
        similarity_threshold_milli=threshold,
        active_key_id="key-v1",
        aead_keys={"key-v1": b"k" * 32},
        reference_retention_seconds=900,
        candidate_retention_seconds=86_400,
        queue_name="markina:facial:jobs",
        worker_concurrency=1,
        max_jobs_per_process=100,
        model_idle_seconds=300,
        job_lease_seconds=120,
        queue_block_seconds=10,
        max_reference_bytes=10_485_760,
        max_reference_pixels=25_000_000,
    )


def test_production_rollout_requires_matching_human_calibration_approval() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()
    with Session(engine) as db:
        gallery = ParentGallery(id=uuid4(), name="Evento produção")
        admin = AdminUser(
            id=uuid4(),
            email="calibration@example.test",
            password_hash="unused",
            totp_secret="unused",
        )
        db.add_all((gallery, admin))
        db.commit()
        prepare_rollout(
            db,
            environment="production",
            parent_gallery_id=gallery.id,
            draft=draft_from_settings(settings),
        )
        with pytest.raises(FacialRolloutError, match="Calibração"):
            activate_rollout(
                db,
                environment="production",
                parent_gallery_id=gallery.id,
                actor_admin_id=admin.id,
                approval_reference="rollout-approval-opaque",
                stage="canary",
                settings=settings,
            )

        with pytest.raises(FacialCalibrationError, match="Todos os grupos"):
            approve_calibration(
                db,
                settings=settings,
                criteria_version="criteria-v1",
                corpus_reference="corpus-opaque-v1",
                approval_reference="calibration-approval-opaque",
                relevant_group_count=5,
                approved_group_count=4,
                actor_admin_id=admin.id,
            )
        approval = approve_calibration(
            db,
            settings=settings,
            criteria_version="criteria-v1",
            corpus_reference="corpus-opaque-v1",
            approval_reference="calibration-approval-opaque",
            relevant_group_count=5,
            approved_group_count=5,
            actor_admin_id=admin.id,
        )
        activate_rollout(
            db,
            environment="production",
            parent_gallery_id=gallery.id,
            actor_admin_id=admin.id,
            approval_reference="rollout-approval-opaque",
            stage="canary",
            settings=settings,
        )
        db.commit()

        assert calibration_is_approved(db, settings) is True
        assert rollout_is_active(
            db, settings=settings, parent_gallery_id=gallery.id
        ) is True
        assert calibration_is_approved(db, _settings(threshold=751)) is False
        approval.status = "revoked"
        db.commit()
        assert rollout_is_active(
            db, settings=settings, parent_gallery_id=gallery.id
        ) is False
        audit = " ".join(db.scalars(select(AuditEvent.subject)))
        assert "corpus-opaque-v1" not in audit
        assert "calibration-approval-opaque" not in audit


def test_calibration_model_contains_no_inferred_attribute_or_raw_evidence_field() -> None:
    columns = set(FacialCalibrationApproval.__table__.c.keys())
    for forbidden in (
        "age",
        "gender",
        "race",
        "ethnicity",
        "identity",
        "image",
        "embedding",
        "phone",
        "name",
    ):
        assert forbidden not in columns
