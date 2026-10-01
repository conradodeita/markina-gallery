"""Workers A/B com JPEGs abstratos, motor sintético e nenhuma biometria/transporte."""


import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import media, worker
from app.auth import (
    BrandingSettings,
    MediaDerivative,
    MediaJob,
    NotificationDelivery,
    NotificationEvent,
    PhotoFolder,
    PreviewAdjustment,
    PrivateUploadBatch,
    PrivateUploadBatchAsset,
    Tenant,
    now,
)
from app.preview_adjustment import service
from app.private_upload_batches import process_ready_batches
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links

client_db = _client_db
graph = _graph
links = _links


class SyntheticEngine:
    def render(self, image, _strength):
        return image.copy()


@pytest.fixture
def jobs(client_db, graph, links, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(tmp_path / "history"))
    monkeypatch.setenv("FACIAL_ENABLED", "false")
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "false")
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    for row, label in zip(graph, ("A", "B"), strict=True):
        row["photo"].storage_key = f"tenants/{row['tenant'].id}/source/{row['photo'].id}.jpg"
        path = media.safe_source_path(row["photo"])
        path.parent.mkdir(parents=True)
        Image.new("RGB", (240, 160), (40, 70, 110)).save(path, "JPEG")
        client_db.add(BrandingSettings(tenant_id=row["tenant"].id, watermark_text=f"PROPRIETARIO {label}"))
        row["job"] = media.enqueue_derivatives(client_db, row["photo"])
    client_db.commit()
    return graph, factory


def generate(db, row):
    return media.generate_derivatives(db, row["photo"], row["job"])


def suspend(factory, owner):
    with factory() as db:
        db.get(Tenant, owner).status = "suspended"
        db.commit()


def test_derivados_e_ajustes_mesma_sequencia_preservam_marca_paths_e_retry_B(client_db, jobs):
    rows, factory = jobs
    for row in rows:
        service.configure(client_db, row["parent"].id, True, 50, tenant_id=row["tenant"].id)
    client_db.commit()
    previews = []
    for row in rows:
        derivatives = generate(client_db, row)
        assert len(derivatives) == 3 and all(d.tenant_id == row["tenant"].id for d in derivatives)
        assert all(d.relative_path.startswith(f"tenants/{row['tenant'].id}/photos/") for d in derivatives)
        previews.append(media.safe_derivative_path(next(d for d in derivatives if d.variant == "client_preview")).read_bytes())
    assert previews[0] != previews[1]
    assert service.process_one(factory, SyntheticEngine())
    assert service.process_one(factory, SyntheticEngine())
    client_db.expire_all()
    results = [client_db.get(PreviewAdjustment, row["photo"].id) for row in rows]
    assert all(r.status == "ready" and r.relative_path.startswith(f"tenants/{r.tenant_id}/photos/") for r in results)
    b_before = (results[1].relative_path, results[1].fingerprint, results[1].generation)
    first = rows[0]
    service.configure(client_db, first["parent"].id, True, 60, tenant_id=first["tenant"].id)
    assert service.enqueue(client_db, first["photo"].id, tenant_id=first["tenant"].id, retry=True)
    client_db.commit()
    assert service.process_one(factory, SyntheticEngine())
    client_db.refresh(results[1])
    assert (results[1].relative_path, results[1].fingerprint, results[1].generation) == b_before
    assert service.adjusted_path(client_db, rows[1]["photo"].id, tenant_id=rows[1]["tenant"].id)
    assert service.adjusted_path(client_db, rows[1]["photo"].id, tenant_id=rows[0]["tenant"].id) is None


def test_suspensao_durante_render_nao_publica_A_e_worker_avanca_B(client_db, jobs, monkeypatch):
    rows, factory = jobs
    first, second = rows
    original = Image.Image.save
    switched = False

    def saving(image, fp, *args, **kwargs):
        nonlocal switched
        result = original(image, fp, *args, **kwargs)
        if not switched and str(fp).endswith(".tmp"):
            switched = True
            suspend(factory, first["tenant"].id)
        return result

    monkeypatch.setattr(Image.Image, "save", saving)
    with pytest.raises(HTTPException):
        generate(client_db, first)
    assert not list((media.derivatives_root() / "tenants" / str(first["tenant"].id)).rglob("*.jpg"))
    assert client_db.scalar(select(func.count()).select_from(MediaDerivative).where(
        MediaDerivative.tenant_id == first["tenant"].id)) == 0
    assert worker.process_next_media_job()
    client_db.refresh(second["job"])
    assert second["job"].status == "completed"
    client_db.refresh(first["job"])
    assert first["job"].status == "queued"


def test_suspensao_no_motor_de_ajuste_preserva_B_e_recusa_publicacao_A(client_db, jobs):
    rows, factory = jobs
    for row in rows:
        service.configure(client_db, row["parent"].id, True, 50, tenant_id=row["tenant"].id)
    client_db.commit()
    for row in rows:
        generate(client_db, row)

    class SuspendingEngine:
        def render(self, image, _strength):
            suspend(factory, rows[0]["tenant"].id)
            return image.copy()

    assert service.process_one(factory, SuspendingEngine())
    client_db.expire_all()
    first = client_db.get(PreviewAdjustment, rows[0]["photo"].id)
    second = client_db.get(PreviewAdjustment, rows[1]["photo"].id)
    assert first.status != "ready" and first.relative_path is None
    assert second.status == "queued" and second.attempts == 0
    assert service.process_one(factory, SyntheticEngine())
    client_db.refresh(second)
    assert second.status == "ready"


def test_job_cruzado_e_namespace_alheio_recusados_legacy_preservado(client_db, jobs, monkeypatch):
    rows, _ = jobs
    first, second = rows
    with pytest.raises(ValueError):
        media.generate_derivatives(client_db, first["photo"], second["job"])
    assert second["job"].status == "queued" and second["job"].attempts == 0
    bad = MediaDerivative(tenant_id=first["tenant"].id, photo_asset_id=first["photo"].id,
        variant="client_preview", relative_path=f"tenants/{second['tenant'].id}/photos/other.jpg")
    with pytest.raises(ValueError):
        media.safe_derivative_path(bad)
    legacy_key = f"{first['photo'].id}/client_preview.jpg"
    bad.relative_path = legacy_key
    client_db.add(bad)
    client_db.commit()
    derivatives = generate(client_db, first)
    own = next(d for d in derivatives if d.variant == "client_preview")
    assert own.relative_path == legacy_key and media.safe_derivative_path(own).is_file()
    assert client_db.scalar(select(func.count()).select_from(MediaJob).where(
        MediaJob.tenant_id == second["tenant"].id, MediaJob.status == "queued")) == 1


def test_lotes_mesma_sequencia_nao_consumem_suspenso_e_recipient_alheio(client_db, jobs):
    rows, factory = jobs
    for row in rows:
        folder = PhotoFolder(tenant_id=row["tenant"].id, parent_gallery_id=row["parent"].id,
            derived_gallery_id=row["gallery"].id, name="Lote privado sintético", status="released")
        client_db.add(folder)
        client_db.flush()
        row["photo"].folder_id = folder.id
        row["photo"].derived_gallery_id = row["gallery"].id
        batch = PrivateUploadBatch(tenant_id=row["tenant"].id, derived_gallery_id=row["gallery"].id,
            actor_admin_id=row["admin"].id, status="closed", closed_at=now(),
            recipient_ids=[str(record["client"].id) for record in rows])
        client_db.add(batch)
        client_db.flush()
        client_db.add(PrivateUploadBatchAsset(tenant_id=row["tenant"].id, batch_id=batch.id, photo_asset_id=row["photo"].id))
        row["batch"] = batch
    client_db.commit()
    for row in rows:
        generate(client_db, row)
    suspend(factory, rows[0]["tenant"].id)
    assert process_ready_batches(client_db)
    client_db.refresh(rows[0]["batch"]); client_db.refresh(rows[1]["batch"])
    assert rows[0]["batch"].status == "closed" and rows[0]["batch"].announced_at is None
    assert rows[1]["batch"].status == "completed" and rows[1]["batch"].announced_at
    event = client_db.scalar(select(NotificationEvent).where(NotificationEvent.event_type == "private_photos_ready"))
    assert event.tenant_id == rows[1]["tenant"].id and event.client_id == rows[1]["client"].id
    deliveries = list(client_db.scalars(select(NotificationDelivery).where(NotificationDelivery.event_id == event.id)))
    assert all(d.tenant_id == rows[1]["tenant"].id and d.recipient_id == rows[1]["client"].id for d in deliveries)
