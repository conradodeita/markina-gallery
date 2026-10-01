"""Exclusões e histórico em schemas/arquivos descartáveis, sem biometria real."""

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import gallery_cleanup, gallery_lifecycle, historical_media, main, worker
from app.asset_removal import enqueue_file_cleanup, process_file_cleanup
from app.auth import (
    CommercialHistoryMedia,
    GalleryLifecycleOperation,
    MediaDerivative,
    PhotoAsset,
    SaleOrderItem,
    Tenant,
    TenantAdmin,
    now,
)
from app.commercial_retention import (
    CommercialRetentionPolicy,
    apply_commercial_media_retention,
    minimize_client_commercial_pii,
)
from app.facial.purge import purge_gallery_records
from app.media import safe_source_path
from app.tenancy import TenantContextError
from tests.test_tenant_commerce import client_db as _client_db
from tests.test_tenant_commerce import commerce as _commerce
from tests.test_tenant_commerce import graph as _graph
from tests.test_tenant_commerce import links as _links
from tests.test_tenant_commerce import reported

client_db = _client_db
graph = _graph
links = _links
commerce = _commerce


@pytest.fixture
def cleanup(client_db, commerce, tmp_path, monkeypatch):
    for kind in ("SOURCE", "DERIVATIVES", "HISTORY"):
        monkeypatch.setenv(f"MEDIA_{kind}_ROOT", str(tmp_path / kind.lower()))
    monkeypatch.setenv("FACIAL_REFERENCE_ROOT", str(tmp_path / "references"))
    factory = sessionmaker(bind=client_db.bind, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    for row in commerce:
        row["photo"].storage_key = f"tenants/{row['tenant'].id}/source/{row['photo'].id}.jpg"
        path = safe_source_path(row["photo"])
        path.parent.mkdir(parents=True)
        path.write_bytes(b"synthetic-no-faces")
        row["source_path"] = path
    client_db.commit()
    return commerce, factory


def deletion(db, row):
    row["admin_request"].scope["headers"].append((b"idempotency-key", b"same-job-key"))
    result = main.delete_parent_gallery(row["parent"].id, row["admin_request"], db)
    return db.get(GalleryLifecycleOperation, UUID(result["operation_id"]))


def test_key_legada_compartilhada_recusada_antes_da_exclusao_lifecycle(client_db, cleanup):
    rows, _factory = cleanup
    a, b = rows
    legacy_key = "legacy/synthetic-shared.jpg"
    legacy_path = a["source_path"].parents[3] / legacy_key
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes(b"synthetic-preserve-B")
    a["photo"].storage_key = legacy_key
    b["photo"].storage_key = "legacy/../" + legacy_key
    client_db.commit()
    operation = deletion(client_db, a)
    with pytest.raises(ValueError):
        gallery_cleanup.remove_operational_storage(client_db, operation)
    assert legacy_path.read_bytes() == b"synthetic-preserve-B"
    assert b["source_path"].exists()


def test_worker_exclui_A_preserva_acervo_B_e_retoma_sem_duplicar(client_db, cleanup):
    rows, _factory = cleanup
    a, b = rows
    b_before = (b["photo"].id, b["parent"].lifecycle_status, b["source_path"].read_bytes())
    operation = deletion(client_db, a)
    removed_photo_id = a["photo"].id
    assert worker.process_next_gallery_lifecycle_operation()
    client_db.expire_all()
    assert client_db.get(GalleryLifecycleOperation, operation.id).status == "completed"
    assert not a["source_path"].exists()
    assert client_db.get(PhotoAsset, removed_photo_id) is None
    assert (b["photo"].id, b["parent"].lifecycle_status, b["source_path"].read_bytes()) == b_before
    assert not worker.process_next_gallery_lifecycle_operation()


def test_manifesto_misto_recusado_antes_do_primeiro_unlink(client_db, cleanup):
    rows, _factory = cleanup
    a, b = rows
    operation = deletion(client_db, a)
    manifest = dict(operation.manifest)
    storage = dict(manifest["operational_storage"])
    storage["sources"] = [*storage["sources"], {"photo_id": str(b["photo"].id), "storage_key": b["photo"].storage_key}]
    manifest["operational_storage"] = storage
    operation.manifest = manifest
    client_db.commit()
    with pytest.raises(ValueError):
        gallery_cleanup.remove_operational_storage(client_db, operation)
    assert all(row["source_path"].exists() for row in rows)


@pytest.mark.parametrize("revoke", [False, True])
def test_suspensao_ou_revogacao_na_etapa_preserva_lease_e_B_avanca(client_db, cleanup, revoke):
    rows, factory = cleanup
    operations = [deletion(client_db, row) for row in rows]
    claim = gallery_lifecycle.claim_next_operation(client_db)
    assert claim[0] == operations[0].id

    def interrupt(db, operation):
        with factory() as other:
            if revoke:
                member = other.scalar(select(TenantAdmin).where(TenantAdmin.tenant_id == operation.tenant_id))
                member.active = False
            else:
                other.get(Tenant, operation.tenant_id).status = "suspended"
            other.commit()
        gallery_cleanup.remove_operational_storage(db, operation)

    with pytest.raises((HTTPException, TenantContextError)):
        gallery_lifecycle.process_claimed_operation(client_db, operation_id=claim[0], lease_token=claim[1],
            handlers={"preparing_history": interrupt})
    client_db.refresh(operations[0])
    assert operations[0].status == "preparing_history" and operations[0].lease_token is None
    assert operations[0].attempts == 0 and rows[0]["source_path"].exists()
    assert worker.process_next_gallery_lifecycle_operation()
    client_db.refresh(operations[1])
    assert operations[1].status == "completed" and not rows[1]["source_path"].exists()


def confirmed(db, rows, tmp_path):
    for row in rows:
        reported(db, row)
        main.decide_payment_communication(row["communication"].id,
            main.PaymentDecisionInput(decision="confirmed", payment_group_id=row["group"].id), row["admin_request"], db)
        row["item"] = db.scalar(select(SaleOrderItem).where(SaleOrderItem.sale_order_id == row["purchase"].id))
        key = f"tenants/{row['tenant'].id}/photos/{row['photo'].id}/client_preview.jpg"
        path = tmp_path / "derivatives" / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic-preview")
        db.add(MediaDerivative(tenant_id=row["tenant"].id, photo_asset_id=row["photo"].id,
            variant="client_preview", status="ready", relative_path=key))
    db.commit()


def test_historico_retencao_e_minimizacao_sao_proprios_e_legado_reutilizavel(client_db, cleanup, tmp_path):
    rows, _factory = cleanup
    confirmed(client_db, rows, tmp_path)
    for row in rows:
        owner = row["tenant"].id
        result = historical_media.prepare_confirmed_historical_media(client_db, parent_gallery_id=row["parent"].id, tenant_id=owner)
        assert result.prepared_items == 1
        manifest = client_db.scalar(select(CommercialHistoryMedia).where(CommercialHistoryMedia.tenant_id == owner))
        assert manifest.preview_storage_key.startswith(f"tenants/{owner}/items/")
        # Legacy key of this same item remains verifiable; never rewrite it on reuse.
        previous = historical_media.historical_media_path(manifest.preview_storage_key)
        manifest.preview_storage_key = f"items/{row['item'].id}/preview.jpg"
        legacy = historical_media.historical_media_path(manifest.preview_storage_key)
        legacy.parent.mkdir(parents=True)
        previous.replace(legacy)
        client_db.commit()
        assert historical_media.prepare_confirmed_historical_media(client_db, parent_gallery_id=row["parent"].id, tenant_id=owner).reused_items == 1
        row["history"] = manifest
        row["history_path"] = legacy
    a, b = rows
    with pytest.raises(ValueError):
        minimize_client_commercial_pii(client_db, client_id=b["client"].id, tenant_id=a["tenant"].id, permitted=True)
    assert minimize_client_commercial_pii(client_db, client_id=a["client"].id, tenant_id=a["tenant"].id, permitted=True) >= 1
    client_db.commit()
    instant = now() + timedelta(days=10)
    assert apply_commercial_media_retention(client_db, tenant_id=a["tenant"].id, instant=instant,
        policy=CommercialRetentionPolicy(None)).purged_items == 0
    assert apply_commercial_media_retention(client_db, tenant_id=a["tenant"].id, instant=instant,
        policy=CommercialRetentionPolicy(1)).purged_items == 1
    client_db.commit()
    client_db.refresh(b["history"])
    assert b["history"].status == "ready" and b["history_path"].exists()
    assert b["purchase"].client_name_snapshot is not None


def test_copia_historica_suspensa_antes_publicacao_nao_publica_A(client_db, cleanup, tmp_path, monkeypatch):
    rows, factory = cleanup
    confirmed(client_db, rows, tmp_path)
    original = historical_media.copyfileobj

    def copying(*args, **kwargs):
        result = original(*args, **kwargs)
        with factory() as other:
            other.get(Tenant, rows[0]["tenant"].id).status = "suspended"
            other.commit()
        return result

    monkeypatch.setattr(historical_media, "copyfileobj", copying)
    with pytest.raises(HTTPException):
        historical_media.prepare_confirmed_historical_media(client_db, parent_gallery_id=rows[0]["parent"].id,
            tenant_id=rows[0]["tenant"].id)
    client_db.rollback()
    assert not list((tmp_path / "history").rglob("*.jpg"))
    assert not list((tmp_path / "history").rglob("*.tmp"))
    monkeypatch.setattr(historical_media, "copyfileobj", original)
    assert historical_media.prepare_confirmed_historical_media(client_db, parent_gallery_id=rows[1]["parent"].id,
        tenant_id=rows[1]["tenant"].id).prepared_items == 1


def test_cleanup_duravel_recusa_arquivo_legado_B_antes_de_apagar_A(client_db, cleanup):
    rows, _factory = cleanup
    a, b = rows
    old_b_path = b["source_path"]
    b["photo"].storage_key = f"legacy/{b['photo'].id}.jpg"
    b["source_path"] = safe_source_path(b["photo"])
    b["source_path"].parent.mkdir(parents=True)
    old_b_path.replace(b["source_path"])
    job = enqueue_file_cleanup(client_db, [a["source_path"], b["source_path"]], tenant_id=a["tenant"].id)
    client_db.commit()
    assert not process_file_cleanup(client_db, job)
    assert job.status == "failed" and all(row["source_path"].exists() for row in rows)


def test_purge_facial_alheio_recusa_antes_de_tocar_referencia(client_db, cleanup, monkeypatch):
    rows, _factory = cleanup
    from app.facial import purge
    monkeypatch.setattr(purge, "delete_reference_file", lambda *_: pytest.fail("Não apagar referência"))
    with pytest.raises(ValueError):
        purge_gallery_records(client_db, parent_gallery_id=rows[1]["parent"].id, tenant_id=rows[0]["tenant"].id)
    assert all(row["source_path"].exists() for row in rows)


def test_limpeza_OTP_e_fontes_temporarias_nao_consume_conta_suspensa(client_db, cleanup, links, monkeypatch):
    import os
    from uuid import uuid4

    from app import auth
    from app.auth import PhotoAnalysis
    from app.facial.lifecycle import cleanup_sources, cleanup_upload_fragments
    from tests.test_tenant_client_auth import challenge
    rows, _factory = cleanup
    challenges = [challenge(client_db, link[0]) for link in links]
    fragments = []
    for row, otp in zip(rows, challenges, strict=True):
        otp.expires_at = now()-timedelta(hours=2)
        client_db.add(PhotoAnalysis(tenant_id=row["tenant"].id, photo_asset_id=row["photo"].id,
            source_fingerprint="synthetic", source_bytes=1, width=1, height=1, pipeline_version="synthetic",
            state="pending", expires_at=now()-timedelta(seconds=1)))
        staging = row["source_path"].parents[3] / "tenants" / str(row["tenant"].id) / ".pyp-uploading"
        staging.mkdir(parents=True, exist_ok=True)
        fragment = staging / f"{uuid4()}.part"
        fragment.write_bytes(b"synthetic")
        os.utime(fragment, (0, 0))
        fragments.append(fragment)
    rows[0]["tenant"].status = "suspended"
    client_db.commit()
    monkeypatch.setattr(worker, "_last_otp_privacy_cleanup", 0)
    assert worker.process_otp_privacy_cleanup()
    client_db.refresh(challenges[0]); client_db.refresh(challenges[1])
    assert challenges[0].subject and challenges[1].subject is None
    with pytest.raises(HTTPException):
        auth.cleanup_expired_client_otp_pii(client_db, tenant_id=rows[0]["tenant"].id)
    assert cleanup_sources(client_db) == 1
    assert rows[0]["source_path"].exists() and not rows[1]["source_path"].exists()
    # cleanup_sources also sweeps owned fragments; A remains suspended and untouched.
    cleanup_upload_fragments(db=client_db)
    assert fragments[0].exists() and not fragments[1].exists()
