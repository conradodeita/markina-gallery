"""Integração local do dispatcher de arquivo frio com storage sintético."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app import worker
from app.auth import (
    Base,
    MediaArchiveCoordinator,
    MediaArchiveCycle,
    MediaArchiveOperation,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    now,
)
from app.media_archive_staging import VolumeCapacity
from tests.test_media_archive_executor import InMemoryArchiveStorage, _restore_fixture


def _runtime_engine():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(MediaArchiveCoordinator(id=1))
        db.commit()
    return engine


@pytest.mark.parametrize(("closing_unreleased", "isolated_cover"), [(False, False), (True, False), (False, True)])
def test_worker_discovers_claims_and_completes_archive_with_injected_adapter(
    tmp_path: Path, monkeypatch, closing_unreleased, isolated_cover,
):
    engine = _runtime_engine()
    source_root = (tmp_path / "source").resolve()
    derivative_root = (tmp_path / "derivatives").resolve()
    history_root = (tmp_path / "history").resolve()
    staging_root = (tmp_path / "staging").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivative_root))
    monkeypatch.setenv("MEDIA_HISTORY_ROOT", str(history_root))
    monkeypatch.setenv("MEDIA_ARCHIVE_STAGING_ROOT", str(staging_root))
    monkeypatch.setenv("MEDIA_ARCHIVE_WORKER_ENABLED", "true")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_last_media_archive_discovery", 0.0)
    adapter = InMemoryArchiveStorage()
    monkeypatch.setattr(worker, "_MEDIA_ARCHIVE_RUNTIME_STORAGE", adapter)

    with factory() as db:
        tenant = Tenant()
        db.add(tenant)
        db.flush()
        gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética")
        db.add(gallery)
        db.flush()
        instant = now()
        folder = PhotoFolder(
            tenant_id=tenant.id,
            parent_gallery_id=gallery.id,
            name="Pasta vencida",
            purpose="content",
            status="released",
            position=0,
            released_at=instant - timedelta(days=90),
            access_duration_days=30,
            access_expires_at=instant - timedelta(days=61),
        )
        db.add(folder)
        if closing_unreleased or isolated_cover:
            tenant.lifecycle = "closing"
            folder.status = "preparing"
            folder.audience_scope = "all"
            folder.released_at = None
            folder.access_expires_at = None
            if isolated_cover:
                folder.purpose = "cover_assets"
                folder.audience_scope = None
        db.flush()
        photo_id = uuid4()
        storage_key = f"tenants/{tenant.id}/photos/{photo_id}/original.jpg"
        photo = PhotoAsset(
            id=photo_id,
            tenant_id=tenant.id,
            parent_gallery_id=gallery.id,
            folder_id=folder.id,
            filename="synthetic.jpg",
            storage_key=storage_key,
        )
        db.add(photo)
        if not closing_unreleased and not isolated_cover:
            from app.auth import Client, GalleryClientState, PhotoSelection
            db.flush()
            client = Client(tenant_id=tenant.id, full_name="Synthetic", phone_e164="+5511999990044")
            db.add(client)
            db.flush()
            db.add(GalleryClientState(tenant_id=tenant.id, parent_gallery_id=gallery.id, client_id=client.id))
            db.flush()
            db.add(PhotoSelection(tenant_id=tenant.id, parent_gallery_id=gallery.id,
                                  client_id=client.id, photo_asset_id=photo.id))
        db.commit()
        source_file = source_root.joinpath(*storage_key.split("/"))
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_bytes(b"synthetic-jpeg-for-dispatch")
        tenant_id, folder_id = tenant.id, folder.id

    assert worker.process_next_media_archive_operation() is True

    with factory() as db:
        cycle = db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.tenant_id == tenant_id,
            MediaArchiveCycle.folder_id == folder_id,
        ))
        assert cycle is not None
        assert cycle.state == "archived"
        operation = db.scalar(select(MediaArchiveOperation).where(
            MediaArchiveOperation.tenant_id == tenant_id,
            MediaArchiveOperation.cycle_id == cycle.id,
        ))
        assert operation is not None
        assert operation.status == "completed"
        from app.tenant_closure_obligations import evaluate_closure
        db.get(Tenant, tenant_id).lifecycle = "closing"
        db.commit()
        assert evaluate_closure(db, tenant_id)["blockers"] == []
        assert db.scalar(select(func.count()).select_from(MediaArchiveCoordinator).where(
            MediaArchiveCoordinator.active_operation_id.is_not(None),
        )) == 0
    assert len(adapter.objects) == 2  # foto e manifesto verificados
    assert not source_file.exists()
    engine.dispose()


def test_closed_gate_or_missing_adapter_does_not_discover_or_change_cycle(monkeypatch):
    def forbidden_session():
        raise AssertionError("Gate fechado não deve consultar nem alterar o banco.")

    monkeypatch.setattr(worker, "SessionLocal", forbidden_session)
    monkeypatch.setattr(worker, "_MEDIA_ARCHIVE_RUNTIME_STORAGE", None)
    monkeypatch.setattr(worker, "_last_media_archive_discovery", 0.0)
    assert worker.process_next_media_archive_operation(enabled=False) is False
    assert worker.process_next_media_archive_operation(enabled=True) is False


@pytest.mark.parametrize("staging_configuration", ["missing", "served_media"])
def test_invalid_staging_prevents_discovery_and_claims(
    tmp_path, monkeypatch, staging_configuration,
):
    def forbidden_session():
        raise AssertionError("Staging inválido não deve consultar nem alterar a fila.")

    served_root = (tmp_path / "served").resolve()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(served_root))
    monkeypatch.delenv("MEDIA_ARCHIVE_STAGING_ROOT", raising=False)
    if staging_configuration == "served_media":
        monkeypatch.setenv("MEDIA_ARCHIVE_STAGING_ROOT", str(served_root))
    monkeypatch.setattr(worker, "SessionLocal", forbidden_session)
    monkeypatch.setattr(worker, "_last_media_archive_discovery", 0.0)

    assert worker.process_next_media_archive_operation(
        enabled=True, storage=InMemoryArchiveStorage(),
    ) is False
    assert worker._last_media_archive_discovery == 0.0
    assert not served_root.exists()


def test_dispatcher_completes_restore_before_new_archive(tmp_path, monkeypatch):
    (
        engine, tenant_id, gallery_id, _folder_id, restore_cycle_id,
        _archive_operation_id, restore_operation_id, _selection_ids, _photo_ids,
        _payload_by_photo, _source_root, staging_root, adapter, _initial_claim,
    ) = _restore_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("MEDIA_ARCHIVE_STAGING_ROOT", str(staging_root))
    monkeypatch.setenv("MEDIA_ARCHIVE_WORKER_ENABLED", "true")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "_last_media_archive_discovery", 0.0)
    monkeypatch.setattr(worker, "_MEDIA_ARCHIVE_RUNTIME_STORAGE", adapter)

    with factory() as db:
        restore_operation = db.get(MediaArchiveOperation, restore_operation_id)
        coordinator = db.get(MediaArchiveCoordinator, 1)
        restore_operation.status = "queued"
        restore_operation.lease_token = None
        restore_operation.lease_expires_at = None
        coordinator.active_operation_id = None
        coordinator.lease_token = None
        coordinator.lease_expires_at = None
        db.add(PhotoFolder(
            tenant_id=tenant_id,
            parent_gallery_id=gallery_id,
            name="Outra pasta vencida",
            purpose="content",
            status="released",
            position=99,
            released_at=now() - timedelta(days=90),
            access_duration_days=30,
            access_expires_at=now() - timedelta(days=61),
        ))
        db.commit()

    def ample_capacity(_path):
        return VolumeCapacity("c" * 64, 100 * 1024**3, 90 * 1024**3)

    assert worker.process_next_media_archive_operation(
        capacity_provider=ample_capacity,
    ) is True

    with factory() as db:
        restore_operation = db.get(MediaArchiveOperation, restore_operation_id)
        assert restore_operation.status == "completed"
        assert db.get(MediaArchiveCycle, restore_cycle_id).state == "local"
        queued_archives = list(db.scalars(select(MediaArchiveOperation).where(
            MediaArchiveOperation.operation_type == "archive",
            MediaArchiveOperation.status == "queued",
        )))
        assert len(queued_archives) == 1
        coordinator = db.get(MediaArchiveCoordinator, 1)
        assert coordinator.active_operation_id is None
    engine.dispose()


def test_general_worker_cycle_calls_the_gated_archive_dispatcher(monkeypatch):
    import app.mercadopago_credit_purchases as credit_purchases
    import app.mercadopago_webhook as payment_webhook
    from app import photographer_signup

    called = []
    false_workers = (
        "process_ready_batches",
        "process_next_tenant_closure",
        "process_highres_cleanup",
        "process_asset_file_cleanup",
        "process_next_photo_credit_reconciliation",
        "process_next_gallery_lifecycle_operation",
        "process_next_media_job",
        "process_next_whatsapp_delivery",
        "process_next_email_delivery",
        "materialize_next_payment_notification",
        "process_next_gallery_membership_notification",
        "process_next_gallery_reopening_notification",
        "reconcile_next_unknown_delivery",
        "process_otp_privacy_cleanup",
        "process_admin_security_cleanup",
    )
    for name in false_workers:
        monkeypatch.setattr(worker, name, lambda *args, **kwargs: False)
    monkeypatch.setattr(worker, "process_next_notification", lambda *_args: False)
    monkeypatch.setattr(
        worker,
        "process_next_media_archive_operation",
        lambda: called.append("media_archive") or False,
    )
    monkeypatch.setattr(photographer_signup, "process_signup_expiry", lambda **_kwargs: False)
    monkeypatch.setattr(credit_purchases, "process_next_mercadopago_credit_purchase", lambda: False)
    monkeypatch.setattr(payment_webhook, "process_next_mercadopago_event", lambda: False)
    monkeypatch.setattr(payment_webhook, "reconcile_next_mercadopago_payment", lambda: False)

    assert worker.run_cycle() is False
    assert called == ["media_archive"]
