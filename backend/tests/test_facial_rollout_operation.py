"""Operação protegida de ativação e suspensão facial."""

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.auth import (
    AdminUser,
    AuditEvent,
    Base,
    FacialRollout,
    FacialRolloutOperation,
    ParentGallery,
)
from app.facial.config import FacialSettings
from app.facial.rollout import FacialRolloutError
from app.facial.rollout_operation import (
    REQUIRED_GATES,
    FacialRolloutOperationError,
    FacialRolloutOperationProof,
    execute_protected_rollout_operation,
)


def _settings(*, environment: str = "test", enabled: bool = True) -> FacialSettings:
    return FacialSettings(
        enabled=enabled,
        environment=environment,
        credential_environment=environment,
        manifest_path=Path("manifest.json"),
        model_root=Path("models"),
        reference_root=Path("references"),
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
        legal_notice_version="notice-v1",
        consent_version="consent-v1",
        legal_basis_reference="legal-v1",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-v1",
        similarity_threshold_milli=750,
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


def _proof(admin_id, gallery_ids, **changes) -> FacialRolloutOperationProof:
    values = {
        "action": "activate",
        "environment": "test",
        "stage": "canary",
        "deployment_sha": "a" * 40,
        "inventory_reference": "inventory-opaque-v1",
        "backup_reference": "backup-opaque-v1",
        "gate_set_version": "production-gates-v1",
        "approved_gates": REQUIRED_GATES,
        "allowlist": tuple(gallery_ids),
        "confirmation": "ACTIVATE_FACIAL_TEST_CANARY",
        "actor_admin_id": admin_id,
    }
    values.update(changes)
    return FacialRolloutOperationProof(**values)


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = AdminUser(
        id=uuid4(),
        email="rollout-operation@example.test",
        password_hash="unused",
        totp_secret="unused",
    )
    galleries = [ParentGallery(id=uuid4(), name=f"Evento {index}") for index in range(2)]
    db.add_all((admin, *galleries))
    db.commit()
    return db, admin, galleries


def test_protected_operation_activates_exact_allowlist_and_records_aggregate_receipt() -> None:
    db, admin, galleries = _fixture()
    operation = execute_protected_rollout_operation(
        db,
        proof=_proof(admin.id, [gallery.id for gallery in galleries]),
        settings=_settings(),
    )
    db.commit()

    assert operation.allowlist_count == 2
    assert db.scalar(select(func.count()).select_from(FacialRolloutOperation)) == 1
    assert set(db.scalars(select(FacialRollout.stage))) == {"canary"}
    assert set(db.scalars(select(FacialRollout.status))) == {"active"}
    audit = " ".join(db.scalars(select(AuditEvent.subject)))
    assert "inventory-opaque-v1" not in audit
    assert "backup-opaque-v1" not in audit
    assert all(str(gallery.id) not in operation.allowlist_digest for gallery in galleries)


def test_homologation_runtime_uses_canonical_homolog_rollout_scope() -> None:
    db, admin, galleries = _fixture()
    operation = execute_protected_rollout_operation(
        db,
        proof=_proof(
            admin.id,
            [galleries[0].id],
            environment="homolog",
            confirmation="ACTIVATE_FACIAL_HOMOLOG_CANARY",
        ),
        settings=_settings(environment="homologation"),
    )
    db.commit()

    rollout = db.scalar(select(FacialRollout))
    assert operation.environment == "homolog"
    assert rollout is not None and rollout.environment == "homolog"


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"deployment_sha": "short"}, "SHA integral"),
        ({"inventory_reference": ""}, "Inventário"),
        ({"backup_reference": ""}, "Inventário"),
        ({"gate_set_version": ""}, "Inventário"),
        ({"approved_gates": frozenset({"security"})}, "Todos os gates"),
        ({"allowlist": ()}, "Allowlist"),
        ({"confirmation": "YES"}, "Confirmação"),
        ({"environment": "qa"}, "Ambiente"),
    ],
)
def test_protected_operation_rejects_missing_fields(changes, match: str) -> None:
    db, admin, galleries = _fixture()
    with pytest.raises(FacialRolloutOperationError, match=match):
        execute_protected_rollout_operation(
            db,
            proof=_proof(admin.id, [galleries[0].id], **changes),
            settings=_settings(),
        )


def test_protected_operation_rejects_scope_drift_and_unapproved_production() -> None:
    db, admin, galleries = _fixture()
    proof = _proof(admin.id, [galleries[0].id])
    with pytest.raises(FacialRolloutOperationError, match="Escopo diverge"):
        execute_protected_rollout_operation(
            db,
            proof=proof,
            settings=_settings(environment="homolog"),
        )

    production_proof = replace(
        proof,
        environment="production",
        confirmation="ACTIVATE_FACIAL_PRODUCTION_CANARY",
    )
    with pytest.raises(FacialRolloutError, match="Calibração"):
        execute_protected_rollout_operation(
            db,
            proof=production_proof,
            settings=_settings(environment="production"),
        )


def test_protected_suspend_requires_same_stage_and_suspends_allowlist() -> None:
    db, admin, galleries = _fixture()
    settings = _settings()
    execute_protected_rollout_operation(
        db,
        proof=_proof(admin.id, [galleries[0].id]),
        settings=settings,
    )
    db.commit()
    suspend = _proof(
        admin.id,
        [galleries[0].id],
        action="suspend",
        confirmation="SUSPEND_FACIAL_TEST_CANARY",
    )
    execute_protected_rollout_operation(db, proof=suspend, settings=settings)
    db.commit()
    rollout = db.scalar(select(FacialRollout))
    assert rollout is not None and rollout.status == "suspended"

    divergent = replace(suspend, stage="limited", confirmation="SUSPEND_FACIAL_TEST_LIMITED")
    with pytest.raises(FacialRolloutOperationError, match="diverge"):
        execute_protected_rollout_operation(db, proof=divergent, settings=settings)
