"""Gates de admissão e claim da restauração contra PostgreSQL sintético."""

import os
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth import (
    Base,
    FacialJob,
    FacialRollout,
    GalleryFacialPolicy,
    MediaDerivative,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    now,
)
from app.facial.indexing import enqueue_photo_index_if_eligible
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.lifecycle import admit_source
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_facial_indexing import _settings


@pytest.fixture
def client_db():
    """Schema descartável em banco cujo hostname existe só na rede de teste interna."""
    url = os.getenv("FACIAL_RESTORE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("FACIAL_RESTORE_TEST_DATABASE_URL não configurada")
    engine = create_engine(url, poolclass=NullPool)
    assert engine.dialect.name == "postgresql"
    assert engine.url.host == "postgres"
    assert engine.url.port == 5432
    assert engine.url.database == "pyp_photographer_test"
    schema = f"facial_restore_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = engine.execution_options(schema_translate_map={None: schema})
    try:
        rules = [
            (constraint, constraint._create_rule)
            for table in Base.metadata.tables.values()
            for constraint in table.constraints
        ]
        try:
            Base.metadata.create_all(engine)
        finally:
            for constraint, create_rule in rules:
                constraint._create_rule = create_rule
        with Session(engine) as db:
            yield db
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def _require_postgres(db: Session) -> None:
    if db.bind.dialect.name != "postgresql":
        pytest.skip("FACIAL restore integration requires PostgreSQL synthetic")


def _rollout(db: Session, tenant_id, gallery_id, settings, *, environment: str) -> None:
    db.add(FacialRollout(
        tenant_id=tenant_id,
        environment=environment,
        parent_gallery_id=gallery_id,
        status="active",
        stage="canary",
        model_version=settings.model_version,
        quality_version=settings.quality_version,
        calibration_version=settings.calibration_version,
        legal_notice_version=settings.legal_notice_version,
        consent_version=settings.consent_version,
        legal_basis_reference=settings.legal_basis_reference,
        retention_policy_version=settings.retention_policy_version,
        approved_by_admin_id=None,
        approved_at=None,
        approval_reference=None,
        activated_at=now(),
    ))
    db.flush()


def _jpeg() -> bytes:
    result = BytesIO()
    Image.new("RGB", (32, 32), (18, 64, 120)).save(result, format="JPEG")
    return result.getvalue()


def _photo_fixture(db: Session, root: Path):
    from app.media import derivatives_root, safe_derivative_path

    parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Galeria facial sintética")
    db.add(parent)
    db.flush()
    folder = PhotoFolder(
        tenant_id=FIXTURE_TENANT_ID,
        parent_gallery_id=parent.id,
        name="Conteúdo sintético",
        status="released",
        purpose="content",
    )
    db.add(folder)
    db.flush()
    photo = PhotoAsset(
        tenant_id=FIXTURE_TENANT_ID,
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename="foto-sintetica.jpg",
        storage_key=f"synthetic/{uuid4()}.jpg",
        available=True,
    )
    db.add(photo)
    db.flush()

    relative_root = root.resolve().relative_to(derivatives_root())
    analysis_derivative = MediaDerivative(
        tenant_id=FIXTURE_TENANT_ID,
        photo_asset_id=photo.id,
        variant="admin_preview",
        status="ready",
        relative_path=(relative_root / str(photo.id) / "admin_preview.jpg").as_posix(),
    )
    protected_derivative = MediaDerivative(
        tenant_id=FIXTURE_TENANT_ID,
        photo_asset_id=photo.id,
        variant="client_preview",
        status="ready",
        relative_path=(relative_root / str(photo.id) / "client_preview.jpg").as_posix(),
    )
    policy = GalleryFacialPolicy(
        tenant_id=FIXTURE_TENANT_ID,
        parent_gallery_id=parent.id,
        status="active",
        legal_notice_version="notice-v1",
        legal_basis_reference="synthetic-only",
        retention_policy_version="retention-v1",
        minor_policy_version="minor-disabled-v1",
        model_version="model-v1",
        quality_version="quality-v1",
        calibration_version="calibration-v1",
    )
    db.add_all((analysis_derivative, protected_derivative, policy))
    db.commit()

    path = safe_derivative_path(analysis_derivative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic protected preview")
    return photo, analysis_derivative, path


def test_postgres_strict_rollout_gates_upload_and_index_admission(
    client_db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_postgres(client_db)

    client_db.add(Tenant(id=FIXTURE_TENANT_ID, status="active"))
    client_db.commit()

    derivative_root = tmp_path / "derivatives"
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "sources"))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "true")
    settings = replace(
        _settings(derivative_root / "assets"),
        require_explicit_rollout=True,
    )

    # Galeria sem registro não pode receber fonte facial quando o modo estrito está ligado.
    upload_photo, _, _ = _photo_fixture(client_db, derivative_root / "upload")
    assert admit_source(client_db, upload_photo, _jpeg(), settings=settings) is None
    assert client_db.scalar(select(func.count()).select_from(FacialJob)) == 0

    _rollout(
        client_db, FIXTURE_TENANT_ID, upload_photo.parent_gallery_id,
        settings, environment="test",
    )
    admitted = admit_source(client_db, upload_photo, _jpeg(), settings=settings)
    assert admitted is not None and admitted.state == "receiving"
    client_db.rollback()

    # Um rollout do ambiente anterior não libera uma galeria no ambiente atual.
    wrong_environment_photo, _, _ = _photo_fixture(
        client_db, derivative_root / "wrong-environment",
    )
    _rollout(
        client_db, FIXTURE_TENANT_ID, wrong_environment_photo.parent_gallery_id,
        settings, environment="staging",
    )
    assert admit_source(
        client_db, wrong_environment_photo, _jpeg(), settings=settings,
    ) is None

    # A admissão de indexação continua restrita à galeria registrada; uma galeria criada
    # depois do canary não herda o rollout.
    index_photo, derivative, path = _photo_fixture(client_db, derivative_root / "index")
    _rollout(client_db, FIXTURE_TENANT_ID, index_photo.parent_gallery_id,
             settings, environment="test")
    queued = enqueue_photo_index_if_eligible(
        client_db, index_photo, derivative, derivative_path=path, settings=settings,
    )
    assert queued is not None

    later_photo, later_derivative, later_path = _photo_fixture(
        client_db, derivative_root / "created-later",
    )
    assert enqueue_photo_index_if_eligible(
        client_db, later_photo, later_derivative,
        derivative_path=later_path, settings=settings,
    ) is None
    assert client_db.scalar(select(func.count()).select_from(FacialJob)) == 1


def test_postgres_claim_keeps_tenant_origin_and_rejects_cross_tenant_lease(
    client_db: Session,
) -> None:
    _require_postgres(client_db)
    owner_a = client_db.get(Tenant, FIXTURE_TENANT_ID)
    if owner_a is None:
        owner_a = Tenant(id=FIXTURE_TENANT_ID, status="active")
        client_db.add(owner_a)
        client_db.flush()
    owner_b = Tenant(status="active")
    client_db.add(owner_b)
    client_db.flush()
    gallery_a = ParentGallery(tenant_id=owner_a.id, name="Galeria A sintética")
    gallery_b = ParentGallery(tenant_id=owner_b.id, name="Galeria B sintética")
    client_db.add_all((gallery_a, gallery_b))
    client_db.flush()

    repository = FacialJobRepository()
    job_a, _ = repository.enqueue(
        client_db, tenant_id=owner_a.id, kind="cleanup",
        idempotency_key="facial-restore-test-a", parent_gallery_id=gallery_a.id,
        priority=1,
    )
    repository.enqueue(
        client_db, tenant_id=owner_b.id, kind="cleanup",
        idempotency_key="facial-restore-test-b", parent_gallery_id=gallery_b.id,
        priority=2,
    )
    client_db.commit()

    claim = repository.claim_next(client_db, lease_seconds=60, job_class="maintenance")
    assert claim is not None and claim.id == job_a.id and claim.tenant_id == owner_a.id
    forged = ClaimedFacialJob(
        id=claim.id, tenant_id=owner_b.id, lease_token=claim.lease_token, kind=claim.kind,
    )
    with pytest.raises(FacialJobError):
        repository.complete(client_db, forged)
    client_db.rollback()

    next_claim = repository.claim_next(client_db, lease_seconds=60, job_class="maintenance")
    assert next_claim is not None and next_claim.tenant_id == owner_b.id
    assert client_db.scalar(select(FacialJob.tenant_id).where(FacialJob.id == claim.id)) == owner_a.id
