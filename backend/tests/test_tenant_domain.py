"""Gates de instalação e revalidação durante trabalho demorado, com dados sintéticos."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import main, media, notification_delivery, worker
from app.auth import (
    AuthChallenge,
    GalleryLifecycleOperation,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    WhatsAppDelivery,
)
from app.facial.jobs import FacialJobRepository
from app.gallery_cleanup import remove_operational_storage
from app.tenancy import TenantContextError, domain_session
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


def assets(db):
    tenant = Tenant()
    db.add(tenant)
    db.flush()
    parent = ParentGallery(name="Sintética", tenant_id=tenant.id)
    db.add(parent)
    db.flush()
    folder = PhotoFolder(tenant_id=tenant.id, name="Lote", parent_gallery_id=parent.id)
    db.add(folder)
    db.flush()
    photo = PhotoAsset(tenant_id=tenant.id, parent_gallery_id=parent.id, folder_id=folder.id,
                       filename="fake.jpg", storage_key="fake.jpg", available=False)
    db.add(photo)
    db.flush()
    job = MediaJob(tenant_id=tenant.id, photo_asset_id=photo.id, kind="generate_derivatives")
    db.add(job)
    db.commit()
    return tenant, parent, photo, job


@pytest.mark.parametrize("state", ["absent", "suspended", "second"])
def test_ausencia_suspensao_e_segunda_conta_sem_fallback(tenant_db, monkeypatch, state):
    tenant, facial = None, None
    if state != "absent":
        tenant, parent, photo, _job = assets(tenant_db)
        facial, _ = FacialJobRepository().enqueue(
            tenant_db, tenant_id=tenant.id, kind="index", idempotency_key="synthetic",
            parent_gallery_id=parent.id, photo_asset_id=photo.id,
            model_version="synthetic", quality_version="synthetic", preview_fingerprint="synthetic",
        )
        tenant_db.commit()
        if state == "suspended":
            tenant.status = "suspended"
        else:
            tenant_db.add(Tenant())
        tenant_db.commit()
    factory = sessionmaker(bind=tenant_db.bind, expire_on_commit=False)
    for module in (main, worker, notification_delivery):
        monkeypatch.setattr(module, "SessionLocal", factory)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/admin").status_code == 403
        capacity = client.get("/admin/capacity-observability")
        assert capacity.status_code == 403
        assert capacity.headers["cache-control"] == "no-store"
        response = client.post("/auth/client/challenge", json={"full_name": "Fake", "phone": "+5511999999999"})
        assert response.status_code == 401
    # Ausência de contexto não habilita OTP; claim usa o owner persistido do item.
    claim = FacialJobRepository().claim_next(tenant_db, lease_seconds=120)
    if state == "second":
        assert claim is not None and claim.tenant_id == tenant.id
    else:
        assert claim is None
        if facial:
            tenant_db.refresh(facial)
            assert facial.status == "queued" and facial.attempts == 0
    assert tenant_db.scalar(select(func.count()).select_from(AuthChallenge)) == 0
    assert tenant_db.scalar(select(func.count()).select_from(WhatsAppDelivery)) == 0


def test_revalidacao_de_commit_nao_publica_mudanca(tenant_db):
    tenant, _, photo, _ = assets(tenant_db)
    factory = sessionmaker(bind=tenant_db.bind, expire_on_commit=False)
    with pytest.raises(TenantContextError), domain_session(factory) as db:
        db.get(PhotoAsset, photo.id).available = True
        with factory() as peer:
            peer.get(Tenant, tenant.id).status = "suspended"
            peer.commit()
        db.commit()
    tenant_db.expire_all()
    assert not photo.available


def test_revogacao_durante_render_nao_publica_arquivo(tenant_db, monkeypatch, tmp_path):
    if tenant_db.bind.dialect.name != "postgresql":
        pytest.skip("Suspensão concorrente ao render exige PostgreSQL")
    tenant, _, photo, job = assets(tenant_db)
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    Image.new("RGB", (64, 64), "white").save(source / "fake.jpg")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(output))
    factory = sessionmaker(bind=tenant_db.bind)

    def revoked(image, _settings):
        with factory() as peer:
            peer.get(Tenant, tenant.id).status = "suspended"
            peer.commit()
        return image

    monkeypatch.setattr(media, "watermark", revoked)
    with pytest.raises(HTTPException) as exc:
        media.generate_derivatives(tenant_db, photo, job, variants={"client_preview"})
    assert exc.value.status_code == 403
    tenant_db.rollback()
    tenant_db.expire_all()
    assert not photo.available and job.status == "queued" and job.attempts == 0
    assert not list(output.rglob("*.jpg")) and not list(output.rglob("*.tmp"))


def test_revogacao_apos_claim_preserva_lease(tenant_db):
    tenant, parent, photo, _ = assets(tenant_db)
    repository = FacialJobRepository()
    job, _ = repository.enqueue(
        tenant_db, tenant_id=tenant.id, kind="index", idempotency_key="claim-synthetic", parent_gallery_id=parent.id,
        photo_asset_id=photo.id, model_version="synthetic", quality_version="synthetic",
        preview_fingerprint="synthetic",
    )
    tenant_db.commit()
    claim = repository.claim_next(tenant_db, lease_seconds=120)
    with sessionmaker(bind=tenant_db.bind)() as peer:
        peer.get(Tenant, tenant.id).status = "suspended"
        peer.commit()
    with pytest.raises(HTTPException) as exc:
        repository.complete(tenant_db, claim)
    assert exc.value.status_code == 403
    tenant_db.rollback()
    tenant_db.refresh(job)
    assert job.status == "processing" and job.lease_token == claim.lease_token and job.attempts == 1


def test_limpeza_revalida_antes_de_remover_arquivo(tenant_db, monkeypatch, tmp_path):
    tenant, parent, _, _ = assets(tenant_db)
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    path = tmp_path / "synthetic.jpg"
    path.write_bytes(b"synthetic")
    operation = GalleryLifecycleOperation(
        tenant_id=tenant.id, operation_type="delete_parent_gallery", target_parent_gallery_id=parent.id,
        manifest={"operational_storage": {"sources": [{"storage_key": path.name}]}},
    )
    tenant.status = "suspended"
    tenant_db.commit()
    with pytest.raises(HTTPException) as exc:
        remove_operational_storage(tenant_db, operation)
    assert exc.value.status_code == 403
    assert path.read_bytes() == b"synthetic"
    assert "storage_cleanup" not in operation.manifest
