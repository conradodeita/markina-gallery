"""Autorização, escopo e apresentação das configurações por pasta."""
from uuid import UUID

from app.auth import (
    FacialJob,
    FolderProcessingSettings,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
)
from app.folder_processing import effective_preview, facial_processing_allowed
from app.preview_adjustment.service import adjusted_path, enqueue, process_one
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_preview_adjustment import BrightEngine

pytest_plugins = ["tests.test_preview_adjustment"]


def test_public_autosave_requeues_only_its_folder_and_monitor_counts_real_work(api_client, monkeypatch):
    from sqlalchemy import select

    from app.auth import Tenant, now
    from app.system_monitor import telemetry
    from app.system_monitor.sources import job_counts

    monkeypatch.setattr(telemetry, "enabled", lambda: True)
    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder_id = photo.folder_id
        other_tenant = Tenant()
        db.add(other_tenant)
        db.flush()
        other_gallery = ParentGallery(tenant_id=other_tenant.id, name="Outro fotógrafo")
        db.add(other_gallery)
        db.flush()
        other_folder = PhotoFolder(tenant_id=other_tenant.id, parent_gallery_id=other_gallery.id,
                                   name="Pasta alheia", purpose="content", position=0)
        db.add(other_folder)
        db.flush()
        other_photo = PhotoAsset(tenant_id=other_tenant.id, parent_gallery_id=other_gallery.id,
                                 folder_id=other_folder.id, filename="alheia.jpg", storage_key="alheia.jpg", available=True)
        db.add(other_photo)
        db.flush()
        db.add(PreviewAdjustment(tenant_id=other_tenant.id, photo_asset_id=other_photo.id,
                                 status="queued", generation=7, fingerprint="b" * 64))
        db.commit()
        other_folder_id, other_photo_id = other_folder.id, other_photo.id
    client.cookies.set("markina_session", "adjustment-admin")
    endpoint = f"/admin/photo-folders/{folder_id}/processing"
    foreign = f"/admin/photo-folders/{other_folder_id}/processing"
    payload = {"preview_mode": "custom", "facial_mode": "on",
               "preview_strength": 60, "preview_exposure_tenths": 3}
    telemetry.drain()
    for _ in range(3):
        assert client.get(endpoint).status_code == 200
    assert client.get(foreign).status_code == 404
    assert client.patch(foreign, json=payload).status_code == 404
    for suffix in ("preview/enqueue", "facial/reprocess"):
        assert client.post(f"{foreign}/{suffix}").status_code == 404
    with factory() as db:
        assert len(list(db.scalars(select(PreviewAdjustment)))) == 2
        assert db.get(PreviewAdjustment, photo_id).generation == 1
    result = client.patch(endpoint, json=payload)
    assert result.status_code == 200, result.text
    with factory() as db:
        row = db.get(PreviewAdjustment, photo_id)
        assert (row.status, row.generation) == ("queued", 2)
        foreign_job = db.get(PreviewAdjustment, other_photo_id)
        assert (foreign_job.status, foreign_job.generation, foreign_job.fingerprint) == ("queued", 7, "b" * 64)
        counts = job_counts(db, now())["counts"]
        assert {"kind": "preview_adjustment", "state": "queued", "count": 2} in counts
    buckets, _, _ = telemetry.drain()
    assert not any(bucket[1].startswith("work.") for bucket in buckets)
    assert process_one(factory, BrightEngine())
    buckets, _, _ = telemetry.drain()
    assert sum(value[0] for key, value in buckets.items() if key[1] == "work.preview_adjustment") == 1


def test_folder_processing_api_auth_and_override(api_client):
    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder_id, gallery_id = photo.folder_id, photo.parent_gallery_id
        other = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id, name="Outra", purpose="content", position=1)
        cover = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id, name="Capa", purpose="cover_assets", position=2)
        private = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id, name="Acervo", purpose="content",
                              audience_scope="selected", position=3)
        db.add_all((other, cover, private))
        db.commit()
        other_id, cover_id, private_id = other.id, cover.id, private.id
    endpoint = f"/admin/photo-folders/{folder_id}/processing"
    assert client.get(endpoint).status_code == 403
    client.cookies.set("markina_session", "adjustment-client")
    assert client.patch(endpoint, json={"preview_mode": "off", "facial_mode": "off",
                                        "preview_strength": 50, "preview_exposure_tenths": 0}).status_code == 403
    client.cookies.set("markina_session", "adjustment-admin")
    assert client.patch(endpoint, headers={"Origin": "https://outro.exemplo"},
                        json={"preview_mode": "off", "facial_mode": "off",
                              "preview_strength": 50, "preview_exposure_tenths": 0}).status_code == 403
    initial = client.get(endpoint)
    assert initial.status_code == 200, initial.text
    assert initial.json()["preview_mode"] == "custom"
    assert initial.json()["facial_mode"] == "on"
    assert initial.json()["effective_preview"]["enabled"] is True
    assert initial.json()["total_photos"] == 1
    assert client.get(f"/admin/photo-folders/{cover_id}/processing").status_code == 404
    private_endpoint = f"/admin/photo-folders/{private_id}/processing"
    private_initial = client.get(private_endpoint)
    assert private_initial.status_code == 200
    assert private_initial.json()["private_folder"] is True
    public_listing = client.get(f"/admin/parent-galleries/{gallery_id}/folders").json()["folders"]
    assert str(private_id) not in {item["id"] for item in public_listing}
    all_listing = client.get(f"/admin/parent-galleries/{gallery_id}/folders?include_restricted=true").json()["folders"]
    private_summary = next(item for item in all_listing if item["id"] == str(private_id))
    assert private_summary["audience_scope"] == "selected"
    assert (private_initial.json()["preview_mode"], private_initial.json()["facial_mode"]) == ("custom", "on")
    assert (private_initial.json()["preview_strength"], private_initial.json()["preview_exposure_tenths"]) == (75, 0)
    private_saved = client.patch(private_endpoint, json={"preview_mode": "off", "facial_mode": "off",
                                                         "preview_strength": 60, "preview_exposure_tenths": -3})
    assert private_saved.status_code == 200, private_saved.text
    assert private_saved.json()["facial_allowed"] is True
    assert private_saved.json()["effective_preview"] == {
        "mode": "custom", "enabled": True, "strength": 60, "exposure_tenths": -3,
    }
    assert client.patch(endpoint, json={"preview_mode": "custom", "facial_mode": "off",
                                        "preview_strength": 80, "preview_exposure_tenths": 5}).status_code == 422
    custom = client.patch(endpoint, json={"preview_mode": "custom", "facial_mode": "off",
                                        "preview_strength": 60, "preview_exposure_tenths": 5})
    assert custom.status_code == 200, custom.text
    assert custom.json()["effective_preview"]["exposure_tenths"] == 5
    assert custom.json()["facial_allowed"] is False
    assert client.post(f"{endpoint}/facial/reprocess").status_code == 409
    with factory() as db:
        assert effective_preview(db, db.get(PhotoFolder, other_id)).mode == "custom"
    assert client.post(f"{endpoint}/preview/enqueue").json()["queued"] == 0
    assert process_one(factory, BrightEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is not None
    assert client.get(endpoint).json()["comparison_photo_id"] == str(photo_id)
    off = client.patch(endpoint, json={"preview_mode": "off", "facial_mode": "off",
                                     "preview_strength": 60, "preview_exposure_tenths": 5})
    assert off.status_code == 200, off.text
    with factory() as db:
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is None
    assert client.post(f"{endpoint}/preview/enqueue").status_code == 409
    assert client.get(f"/admin/photo-folders/{other_id}/processing").json()["preview_mode"] == "custom"

    with factory() as db:
        db.get(ParentGallery, gallery_id).active = False
        db.commit()
    assert client.get(endpoint).status_code == 409
    assert client.post(f"{endpoint}/preview/enqueue").status_code == 409


def test_public_folder_creation_uses_independent_defaults_without_gallery_inheritance(api_client):
    from app.preview_adjustment.service import configure as configure_gallery

    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        gallery_id = photo.parent_gallery_id
        configure_gallery(db, gallery_id, False, 63, 4, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    client.cookies.set("markina_session", "adjustment-admin")
    created = client.post(f"/admin/parent-galleries/{gallery_id}/folders", json={"name": "Snapshot"})
    assert created.status_code == 201, created.text
    folder_id = created.json()["id"]
    folder_uuid = UUID(folder_id)
    with factory() as db:
        row = db.get(FolderProcessingSettings, folder_uuid)
        assert row is not None
        assert (row.preview_mode, row.facial_mode, row.preview_strength, row.preview_exposure_tenths) == (
            "custom", "on", 50, 0,
        )
        assert effective_preview(db, db.get(PhotoFolder, folder_uuid)).enabled
        configure_gallery(db, gallery_id, False, 30, -7, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        assert effective_preview(db, db.get(PhotoFolder, folder_uuid)).enabled
        assert (effective_preview(db, db.get(PhotoFolder, folder_uuid)).strength,
                effective_preview(db, db.get(PhotoFolder, folder_uuid)).exposure_tenths) == (50, 0)
    assert client.get(f"/admin/photo-folders/{folder_id}/processing").json()["preview_mode"] == "custom"


def test_private_folder_creation_persists_independent_ready_defaults(api_client):
    from app.auth import Client, ParentGalleryRegistration

    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        gallery_id = photo.parent_gallery_id
        person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Cliente da pasta", phone_e164="+5511999999988")
        db.add(person)
        db.flush()
        db.add(ParentGalleryRegistration(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id,
            client_id=person.id, status="active",
        ))
        client_id = person.id
        db.commit()
    client.cookies.set("markina_session", "adjustment-admin")
    created = client.post(
        f"/admin/parent-galleries/{gallery_id}/clients/{client_id}/folders",
        json={"name": "Acervo independente"},
    )
    assert created.status_code == 201, created.text
    with factory() as db:
        row = db.get(FolderProcessingSettings, UUID(created.json()["id"]))
        assert row is not None
        assert (row.preview_mode, row.facial_mode, row.preview_strength, row.preview_exposure_tenths) == (
            "custom", "on", 75, 0,
        )


def test_private_folder_settings_are_fixed_auto_and_requeue_completed_face_photos(prepared):
    from app.folder_processing import configure_folder

    factory, photo_id = prepared
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder = db.get(PhotoFolder, photo.folder_id)
        folder.audience_scope = "selected"
        db.add(FacialJob(tenant_id=FIXTURE_TENANT_ID, kind="index", status="completed",
                         idempotency_key=f"private-index:{photo.id}", parent_gallery_id=photo.parent_gallery_id,
                         photo_asset_id=photo.id, model_version="model-v1", quality_version="quality-v1",
                         preview_fingerprint="a" * 64))
        db.flush()
        override = FolderProcessingSettings(tenant_id=FIXTURE_TENANT_ID, folder_id=folder.id,
                                            preview_mode="off", facial_mode="off", preview_strength=50)
        db.add(override)
        db.flush()
        # A public adjustment queued before this fixture becomes private is not
        # part of the private face-then-preview lifecycle.
        db.delete(db.get(PreviewAdjustment, photo.id))
        db.flush()
        assert effective_preview(db, folder).enabled
        assert (effective_preview(db, folder).strength, effective_preview(db, folder).exposure_tenths) == (75, 0)
        assert facial_processing_allowed(db, folder.id, tenant_id=FIXTURE_TENANT_ID)
        assert enqueue(db, photo.id, tenant_id=FIXTURE_TENANT_ID)
        db.commit()

    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        row = db.get(PreviewAdjustment, photo_id)
        assert row.status == "queued"
        configure_folder(db, photo.folder_id, tenant_id=FIXTURE_TENANT_ID,
                         preview_mode="off", facial_mode="off", strength=65, exposure_tenths=-2)
        assert effective_preview(db, db.get(PhotoFolder, photo.folder_id)).enabled
        assert (effective_preview(db, db.get(PhotoFolder, photo.folder_id)).strength,
                effective_preview(db, db.get(PhotoFolder, photo.folder_id)).exposure_tenths) == (65, -2)
        assert row.status == "queued"
        assert row.generation == 2
        db.commit()
    assert process_one(factory, BrightEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is not None


def test_private_adjustment_worker_cancels_stale_work_until_face_index_completes(prepared):
    factory, photo_id = prepared
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        db.get(PhotoFolder, photo.folder_id).audience_scope = "selected"
        db.get(PreviewAdjustment, photo_id).status = "queued"
        db.commit()

    assert process_one(factory, BrightEngine())
    with factory() as db:
        assert db.get(PreviewAdjustment, photo_id).status == "cancelled"
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is None


def test_folder_override_is_independent_of_gallery_default(prepared):
    from app.folder_processing import configure_folder
    from app.preview_adjustment.service import configure, enqueue

    factory, photo_id = prepared
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="on",
                         strength=50, exposure_tenths=5, tenant_id=FIXTURE_TENANT_ID)
        assert not enqueue(db, photo_id, retry=True, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        configure(db, photo.parent_gallery_id, False, 50, 3, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        assert effective_preview(db, db.get(PhotoFolder, photo.folder_id)).enabled
        assert effective_preview(db, db.get(PhotoFolder, photo.folder_id)).exposure_tenths == 5
        assert db.get(PreviewAdjustment, photo_id).status == "queued"


def test_repeated_folder_render_reads_conventional_preview(prepared):
    from app.folder_processing import configure_folder
    from app.preview_adjustment.service import configure, enqueue

    factory, photo_id = prepared
    pixels = []

    class RecordingEngine:
        def render(self, image, _strength):
            pixels.append(image.getpixel((0, 0)))
            return image.copy()

    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="on",
                         strength=50, exposure_tenths=5, tenant_id=FIXTURE_TENANT_ID)
        assert not enqueue(db, photo_id, retry=True, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    assert process_one(factory, RecordingEngine())
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        configure(db, photo.parent_gallery_id, False, 50, 7, tenant_id=FIXTURE_TENANT_ID)
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="on",
                         strength=50, exposure_tenths=6, tenant_id=FIXTURE_TENANT_ID)
        assert not enqueue(db, photo_id, retry=True, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
    assert process_one(factory, RecordingEngine())
    assert pixels[0] == pixels[1]
    with factory() as db:
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is not None


def test_folder_change_during_render_never_publishes_stale_result(prepared):
    from app.folder_processing import configure_folder
    from app.preview_adjustment.service import enqueue

    factory, photo_id = prepared
    with factory() as db:
        folder_id = db.get(PhotoAsset, photo_id).folder_id
        configure_folder(db, folder_id, preview_mode="custom", facial_mode="on",
                         strength=50, exposure_tenths=5, tenant_id=FIXTURE_TENANT_ID)
        assert not enqueue(db, photo_id, retry=True, tenant_id=FIXTURE_TENANT_ID)
        db.commit()

    class ChangedEngine(BrightEngine):
        def render(self, image, strength):
            with factory() as db:
                configure_folder(db, folder_id, preview_mode="custom", facial_mode="on",
                                 strength=50, exposure_tenths=6, tenant_id=FIXTURE_TENANT_ID)
                db.commit()
            return super().render(image, strength)

    assert process_one(factory, ChangedEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id, tenant_id=FIXTURE_TENANT_ID) is None


def test_cleanup_refuses_active_folder_override(prepared):
    import pytest

    from app.folder_processing import configure_folder
    from app.preview_adjustment.cleanup import cleanup

    factory, photo_id = prepared
    with factory() as db:
        folder_id = db.get(PhotoAsset, photo_id).folder_id
        configure_folder(db, folder_id, preview_mode="custom", facial_mode="on",
                         strength=50, exposure_tenths=5, tenant_id=FIXTURE_TENANT_ID)
        db.commit()
        with pytest.raises(ValueError, match="Desligue o módulo"):
            cleanup(db, execute=True, worker_stopped=True)


def test_facial_action_pages_and_retries_only_its_folder(api_client, monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4

    from app import folder_processing_api
    from app.facial.indexing import BackfillPage

    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder_id, gallery_id = photo.folder_id, photo.parent_gallery_id
        db.add_all(PhotoAsset(tenant_id=FIXTURE_TENANT_ID, id=uuid4(), parent_gallery_id=gallery_id, folder_id=folder_id,
                              filename=f"sintetica-{index}.jpg",
                              storage_key=f"{gallery_id}/sintetica-{index}.jpg", available=True)
                   for index in range(101))
        db.commit()
    monkeypatch.setattr(folder_processing_api, "facial_settings_from_environment",
                        lambda **_kwargs: SimpleNamespace(enabled=True))
    monkeypatch.setattr(folder_processing_api, "rollout_is_active", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(folder_processing_api, "enqueue_gallery_backfill_page",
                        lambda *_args, **_kwargs: BackfillPage(queued=0, scanned=0,
                                                                next_cursor=None, completed=True))
    pages = []
    def retry(_db, **kwargs):
        pages.append(kwargs["photo_ids"])
        assert kwargs["folder_id"] == folder_id
        return 0
    monkeypatch.setattr(folder_processing_api, "retry_all_failed_index_jobs", retry)
    client.cookies.set("markina_session", "adjustment-admin")
    endpoint = f"/admin/photo-folders/{folder_id}/processing/facial/reprocess"
    first = client.post(endpoint)
    assert first.status_code == 200, first.text
    assert first.json()["scanned"] == 100
    second = client.post(endpoint, params={"after": first.json()["next_cursor"]})
    assert second.status_code == 200, second.text
    assert second.json()["scanned"] == 2
    assert second.json()["next_cursor"] is None
    assert len(pages) == 2 and len(pages[0]) == 100 and len(pages[1]) == 2
    assert pages[0].isdisjoint(pages[1])
