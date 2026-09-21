from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.asset_removal import (
    enqueue_file_cleanup,
    preserve_asset_history,
    process_file_cleanup,
    removed_movements_payload,
)
from app.auth import (
    Client,
    DerivedGallery,
    GalleryLifecycleOperation,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    RemovedPhotoMovement,
    SaleOrder,
    SaleOrderItem,
    SessionLocal,
)
from app.gallery_cleanup import (
    prepare_lifecycle_history,
    remove_operational_records,
    remove_operational_storage,
)
from app.gallery_lifecycle import gallery_operational_storage_manifest, retry_failed_operation
from app.main import _delete_photo_records, app
from app.unified_checkout import prepare_group, report_group
from tests.test_unified_checkout import isolated_cart_database, setup_cart  # noqa: F401


@pytest.mark.parametrize("reported", [False, True])
def test_public_deletion_preserves_group_and_text_without_acervo(tmp_path, monkeypatch, reported):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    owner, other, galleries = setup_cart()
    with SessionLocal() as db:
        group = prepare_group(db, db.get(Client, owner))
        if reported:
            report_group(db, client=db.get(Client, owner), group_id=group.id,
                         revision=group.revision, key="report-before-delete")
        db.commit()
        parent_id = db.get(DerivedGallery, galleries[0]).parent_gallery_id
        before = [(o.id, o.total_cents, o.payment_status) for o in db.scalars(select(SaleOrder).order_by(SaleOrder.id))]
        operation = GalleryLifecycleOperation(operation_type="delete_parent_gallery",
            target_parent_gallery_id=parent_id, actor_admin_id=uuid4(), idempotency_key=str(uuid4()),
            manifest={"operational_storage": gallery_operational_storage_manifest(db, parent_id)})
        db.add(operation)
        db.flush()
        prepare_lifecycle_history(db, operation)
        db.commit()
        remove_operational_storage(db, operation)
        remove_operational_records(db, operation)
        db.commit()
        assert db.get(ParentGallery, parent_id).lifecycle_status == "deleted"
        assert not db.get(DerivedGallery, galleries[0])
        assert db.scalar(select(func.count(PhotoAsset.id)).where(PhotoAsset.parent_gallery_id == parent_id)) == 0
        assert db.scalar(select(func.count(PhotoFolder.id)).where(PhotoFolder.parent_gallery_id == parent_id)) == 0
        assert db.get(DerivedGallery, galleries[1])
        assert [(o.id, o.total_cents, o.payment_status) for o in db.scalars(select(SaleOrder).order_by(SaleOrder.id))] == before
        db.refresh(group)
        assert group.state == ("reported" if reported else "unavailable")
        assert group.total_cents == 2100
        assert all(i.filename_snapshot for i in db.scalars(select(SaleOrderItem)))
        assert removed_movements_payload(db, client_id=other) == []
        if not reported:
            assert len(removed_movements_payload(db, client_id=owner)) == 2
            next_group = prepare_group(db, db.get(Client, owner))
            assert next_group.id != group.id and next_group.total_cents == 700
        db.commit()
    browser = TestClient(app)
    browser.cookies.set("markina_session", "cart-test")
    response = browser.get('/library/purchases')
    assert response.status_code == 200, response.text
    assert any(g['id'] == str(group.id) for g in response.json()['payment_groups'])
    for g in response.json()['payment_groups']:
        for o in g['orders']:
            if o['gallery_removed']:
                assert all(item['preview_url'] is None for item in o['items'])


def test_photo_removal_preserves_selection_without_creating_order(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    owner, _, galleries = setup_cart()
    with SessionLocal() as db:
        photo = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == galleries[0]))
        preserve_asset_history(db, photo.parent_gallery_id, photo_ids=[photo.id])
        preserve_asset_history(db, photo.parent_gallery_id, photo_ids=[photo.id])
        paths = _delete_photo_records(db, photo)
        cleanup = enqueue_file_cleanup(db, paths)
        db.commit()
        assert process_file_cleanup(db, cleanup)
        assert db.scalar(select(func.count(RemovedPhotoMovement.id))) == 1
        assert db.scalar(select(func.count(SaleOrder.id))) == 0
        assert db.scalar(select(func.count(PhotoSelection.id))) == 2
        assert removed_movements_payload(db, client_id=owner)[0]['filename'] == photo.filename


def test_cleanup_retries_io_failure_and_refuses_external_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    target = tmp_path / "source" / "photo.jpg"
    target.parent.mkdir()
    target.write_bytes(b'synthetic')
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            enqueue_file_cleanup(db, [tmp_path / 'other-project.jpg'])
        job = enqueue_file_cleanup(db, [target])
        db.commit()
        original = Path.unlink
        with monkeypatch.context() as patch:
            patch.setattr(Path, 'unlink', lambda *a, **kw: (_ for _ in ()).throw(PermissionError()))
            assert not process_file_cleanup(db, job)
        assert job.status == 'failed' and target.exists()
        assert process_file_cleanup(db, job)
        assert job.attempts == 2 and not target.exists()
        assert Path.unlink == original


def test_legacy_failed_operation_rebuilds_manifest_without_autoretry():
    _, _, galleries = setup_cart()
    with SessionLocal() as db:
        parent_id = db.get(DerivedGallery, galleries[0]).parent_gallery_id
        operation = GalleryLifecycleOperation(operation_type='delete_parent_gallery',
            target_parent_gallery_id=parent_id, actor_admin_id=uuid4(), idempotency_key=str(uuid4()),
            status='failed', manifest={'completed_steps':['preparing_history','removing_storage'],
                                      'operational_storage':{'sources':[], 'derivatives':[]}})
        db.add(operation)
        db.commit()
        assert operation.status == 'failed'
        retry_failed_operation(db, operation)
        assert operation.status == 'queued'
        assert operation.manifest['completed_steps'] == []
        assert len(operation.manifest['operational_storage']['sources']) == 2


def test_postgresql_report_racing_removal_keeps_one_consistent_group():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from app.auth import PaymentCommunication, PaymentGroup, engine
    from app.checkout import CheckoutError
    if engine.dialect.name != "postgresql":
        pytest.skip("Locks reais exigem PostgreSQL")
    owner, _, galleries = setup_cart()
    with SessionLocal() as db:
        group = prepare_group(db, db.get(Client, owner))
        db.commit()
        group_id, revision = group.id, group.revision
        photo = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == galleries[0]))
        photo_id, parent_id = photo.id, photo.parent_gallery_id
    barrier = Barrier(2)

    def remove():
        with SessionLocal() as db:
            barrier.wait(timeout=10)
            preserve_asset_history(db, parent_id, photo_ids=[photo_id])
            _delete_photo_records(db, db.get(PhotoAsset, photo_id))
            db.commit()

    def report():
        with SessionLocal() as db:
            barrier.wait(timeout=10)
            try:
                report_group(db, db.get(Client, owner), group_id, revision, "race-report")
                db.commit()
            except CheckoutError:
                db.rollback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        removal = pool.submit(remove)
        reporting = pool.submit(report)
        removal.result(timeout=30)
        reporting.result(timeout=30)
    with SessionLocal() as db:
        group = db.get(PaymentGroup, group_id)
        communications = list(db.scalars(select(PaymentCommunication)))
        assert group.state in {"unavailable", "reported"}
        assert len(communications) == (1 if group.state == "reported" else 0)
        assert group.total_cents == 2100
        assert db.scalar(select(func.count(SaleOrderItem.id))) == 3
        assert db.get(PhotoAsset, photo_id) is None


def test_removed_gallery_keeps_admin_decision_and_notification_history():
    from datetime import timedelta

    from app.auth import (
        AdminUser,
        AuthSession,
        NotificationEvent,
        PaymentCommunication,
        now,
        token_hash,
    )
    owner, _, galleries = setup_cart()
    with SessionLocal() as db:
        group = prepare_group(db, db.get(Client, owner))
        communication = report_group(db, db.get(Client, owner), group.id, group.revision, "before-removal")
        admin = db.scalar(select(AdminUser))
        db.add(AuthSession(subject_id=admin.id, role="admin", token_hash=token_hash("remove-admin"),
                           expires_at=now() + timedelta(hours=1)))
        db.commit()
        event_ids = set(db.scalars(select(NotificationEvent.id)))
        parent_id = db.get(DerivedGallery, galleries[0]).parent_gallery_id
        operation = GalleryLifecycleOperation(operation_type="delete_parent_gallery", target_parent_gallery_id=parent_id,
            actor_admin_id=admin.id, idempotency_key=str(uuid4()), manifest={})
        db.add(operation)
        prepare_lifecycle_history(db, operation)
        db.commit()
        remove_operational_records(db, operation)
        db.commit()
        assert event_ids <= set(db.scalars(select(NotificationEvent.id)))
        communication_id, group_id = communication.id, group.id
    browser = TestClient(app)
    browser.cookies.set("markina_session", "remove-admin")
    dashboard = browser.get("/admin/payment-communications")
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["total_cents"] == 2100
    result = browser.post(f"/admin/payment-communications/{communication_id}/decision",
        json={"decision":"confirmed", "payment_group_id":str(group_id)})
    assert result.status_code == 200, result.text
    with SessionLocal() as db:
        assert {order.payment_status for order in db.scalars(select(SaleOrder))} == {"confirmed"}
        assert db.get(PaymentCommunication, communication_id).status == "confirmed"


def test_dashboard_filters_text_history_and_client_cannot_read_other_owner():
    from datetime import timedelta

    from app.auth import AdminUser, AuthSession, now, token_hash
    _owner, other, galleries = setup_cart()
    with SessionLocal() as db:
        photo = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == galleries[0]))
        preserve_asset_history(db, photo.parent_gallery_id, photo_ids=[photo.id])
        _delete_photo_records(db, photo)
        admin = db.scalar(select(AdminUser))
        db.add_all([AuthSession(subject_id=admin.id, role="admin", token_hash=token_hash("history-admin"),
                                expires_at=now() + timedelta(hours=1)),
                    AuthSession(subject_id=other, role="client", token_hash=token_hash("history-other"),
                                expires_at=now() + timedelta(hours=1))])
        db.commit()
        parent_id = photo.parent_gallery_id
    browser = TestClient(app)
    browser.cookies.set("markina_session", "history-admin")
    assert browser.get("/admin/payment-communications").json()["removed_movements"] == []
    payload = browser.get(f"/admin/removed-photo-movements?parent_gallery_id={parent_id}&query=Cliente").json()
    assert len(payload["items"]) == 1
    assert browser.get(f"/admin/removed-photo-movements?parent_gallery_id={uuid4()}").json()["items"] == []
    browser.cookies.set("markina_session", "history-other")
    assert browser.get('/library/purchases').json()['removed_movements'] == []
    assert browser.get('/admin/payment-communications').status_code in (401, 403)
    assert browser.get('/admin/removed-photo-movements').status_code in (401, 403)


def test_private_deletion_removes_own_uploads_but_keeps_shared_original(tmp_path, monkeypatch):
    from datetime import timedelta

    from app.auth import AdminUser, AuthSession, DerivedGalleryPhoto, now, token_hash

    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    owner, _, galleries = setup_cart()
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, galleries[0])
        folder = PhotoFolder(parent_gallery_id=gallery.parent_gallery_id, name="Publica", status="released")
        db.add(folder)
        db.flush()
        shared = PhotoAsset(parent_gallery_id=gallery.parent_gallery_id, folder_id=folder.id,
                            filename="compartilhada.jpg", storage_key="shared.jpg")
        db.add(shared)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=shared.id, origin="admin"))
        own_photos = list(db.scalars(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == gallery.id)))
        own_ids = [photo.id for photo in own_photos]
        paths = [tmp_path / photo.storage_key for photo in own_photos]
        for path in paths + [tmp_path / shared.storage_key]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic")
        prepare_group(db, db.get(Client, owner))
        admin = db.scalar(select(AdminUser))
        db.add(AuthSession(subject_id=admin.id, role="admin", token_hash=token_hash("private-admin"),
                           expires_at=now() + timedelta(hours=1)))
        db.commit()
        shared_id = shared.id
    browser = TestClient(app)
    browser.cookies.set("markina_session", "private-admin")
    result = browser.delete(f"/admin/derived-galleries/{galleries[0]}")
    assert result.status_code == 204, result.text
    assert result.headers["X-Asset-Cleanup"] == "completed"
    with SessionLocal() as db:
        assert db.get(DerivedGallery, galleries[0]) is None
        assert db.get(DerivedGallery, galleries[1]) is not None
        assert all(db.get(PhotoAsset, photo_id) is None for photo_id in own_ids)
        assert db.get(PhotoAsset, shared_id) is not None
        assert len(removed_movements_payload(db, client_id=owner)) == 2
        assert db.scalar(select(func.count(SaleOrderItem.id))) == 3
    assert all(not path.exists() for path in paths)
    assert (tmp_path / "shared.jpg").exists()


def test_cleanup_failure_does_not_starve_other_jobs(tmp_path, monkeypatch):
    from app import worker

    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    with SessionLocal() as db:
        blocked = enqueue_file_cleanup(db, [tmp_path / "blocked.jpg"])
        other = enqueue_file_cleanup(db, [tmp_path / "other.jpg"])
        blocked.status, blocked.attempts = "failed", 1
        db.commit()
        other_id = other.id
    monkeypatch.setattr(worker, "_last_asset_cleanup", 0)
    assert worker.process_asset_file_cleanup()
    with SessionLocal() as db:
        from app.auth import AssetFileCleanup
        assert db.get(AssetFileCleanup, other_id).status == "completed"


def test_admin_removed_history_is_bounded_filtered_and_includes_galleries_without_orders():
    from datetime import UTC, datetime, timedelta

    from app.auth import AdminUser, AuthSession, now, token_hash

    owner, _, _ = setup_cart()
    parent_id, private_id = uuid4(), uuid4()
    instant = datetime(2026, 9, 1, 12, tzinfo=UTC)
    with SessionLocal() as db:
        for index in range(55):
            db.add(RemovedPhotoMovement(source_id=uuid4(), kind="selected", client_id=owner,
                parent_gallery_id=parent_id, derived_gallery_id=private_id, photo_id=uuid4(),
                parent_gallery_name="Galeria excluída sem pedido", gallery_name="Privada", folder_name="Pasta",
                filename=f"foto-{index}.jpg", occurred_at=instant))
        admin = db.scalar(select(AdminUser))
        db.add(AuthSession(subject_id=admin.id, role="admin", token_hash=token_hash("paged-admin"),
                           expires_at=now() + timedelta(hours=1)))
        db.commit()
        assert db.scalar(select(func.count(SaleOrder.id))) == 0
    browser = TestClient(app)
    assert browser.get('/admin/removed-photo-movements').status_code in (401, 403)
    browser.cookies.set("markina_session", "paged-admin")
    endpoint = f"/admin/removed-photo-movements?parent_gallery_id={parent_id}"
    first = browser.get(endpoint).json()
    assert first["galleries"] == [{"id": str(parent_id), "name": "Galeria excluída sem pedido"}]
    assert len(first["items"]) == 25 and first["page"]["has_more"]
    second = browser.get(endpoint + "&offset=25").json()
    last = browser.get(endpoint + "&offset=50").json()
    ids = [item["id"] for page in (first, second, last) for item in page["items"]]
    assert len(ids) == len(set(ids)) == 55
    assert len(last["items"]) == 5 and not last["page"]["has_more"]
    assert len(browser.get(endpoint + "&query=Cliente&created_from=2026-09-01T00:00:00Z&created_to=2026-09-01T23:59:59Z").json()["items"]) == 25
    for suffix in ("&query=Inexistente", "&created_from=2026-09-02T00:00:00Z", "&created_to=2026-08-31T23:59:59Z"):
        assert browser.get(endpoint + suffix).json()["items"] == []
    for suffix in ("&limit=51", "&offset=-1", "&created_from=2026-09-02T00:00:00Z&created_to=2026-09-01T00:00:00Z"):
        assert browser.get(endpoint + suffix).status_code == 422
    assert browser.get('/admin/payment-communications').json()['removed_movements'] == []
