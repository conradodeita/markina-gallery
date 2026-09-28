"""Autorização, escopo e apresentação das configurações por pasta."""

from app.auth import ParentGallery, PhotoAsset, PhotoFolder, PreviewAdjustment
from app.folder_processing import effective_preview
from app.preview_adjustment.service import adjusted_path, process_one
from tests.test_preview_adjustment import BrightEngine

pytest_plugins = ["tests.test_preview_adjustment"]


def test_folder_processing_api_auth_and_override(api_client):
    client, factory, photo_id = api_client
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder_id, gallery_id = photo.folder_id, photo.parent_gallery_id
        other = PhotoFolder(parent_gallery_id=gallery_id, name="Outra", purpose="content", position=1)
        cover = PhotoFolder(parent_gallery_id=gallery_id, name="Capa", purpose="cover_assets", position=2)
        db.add_all((other, cover))
        db.commit()
        other_id, cover_id = other.id, cover.id
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
    assert initial.json()["preview_mode"] == "inherit"
    assert initial.json()["total_photos"] == 1
    assert client.get(f"/admin/photo-folders/{cover_id}/processing").status_code == 404
    assert client.patch(endpoint, json={"preview_mode": "custom", "facial_mode": "off",
                                        "preview_strength": 80, "preview_exposure_tenths": 5}).status_code == 422
    custom = client.patch(endpoint, json={"preview_mode": "custom", "facial_mode": "off",
                                        "preview_strength": 60, "preview_exposure_tenths": 5})
    assert custom.status_code == 200, custom.text
    assert custom.json()["effective_preview"]["exposure_tenths"] == 5
    assert custom.json()["facial_allowed"] is False
    assert client.post(f"{endpoint}/facial/reprocess").status_code == 409
    with factory() as db:
        assert effective_preview(db, db.get(PhotoFolder, other_id)).mode == "inherit"
    assert client.post(f"{endpoint}/preview/enqueue").json()["queued"] == 1
    assert process_one(factory, BrightEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id) is not None
    assert client.get(endpoint).json()["comparison_photo_id"] == str(photo_id)
    off = client.patch(endpoint, json={"preview_mode": "off", "facial_mode": "off",
                                     "preview_strength": 60, "preview_exposure_tenths": 5})
    assert off.status_code == 200, off.text
    with factory() as db:
        assert adjusted_path(db, photo_id) is None
    assert client.post(f"{endpoint}/preview/enqueue").status_code == 409
    assert client.get(f"/admin/photo-folders/{other_id}/processing").json()["preview_mode"] == "inherit"

    with factory() as db:
        db.get(ParentGallery, gallery_id).active = False
        db.commit()
    assert client.get(endpoint).status_code == 409
    assert client.post(f"{endpoint}/preview/enqueue").status_code == 409


def test_folder_override_is_independent_of_gallery_default(prepared):
    from app.folder_processing import configure_folder
    from app.preview_adjustment.service import configure, enqueue

    factory, photo_id = prepared
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="inherit",
                         strength=50, exposure_tenths=5)
        assert enqueue(db, photo_id, retry=True)
        db.commit()
        configure(db, photo.parent_gallery_id, False, 50, 3)
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
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="inherit",
                         strength=50, exposure_tenths=5)
        assert enqueue(db, photo_id, retry=True)
        db.commit()
    assert process_one(factory, RecordingEngine())
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        configure(db, photo.parent_gallery_id, False, 50, 7)
        configure_folder(db, photo.folder_id, preview_mode="custom", facial_mode="inherit",
                         strength=50, exposure_tenths=6)
        assert enqueue(db, photo_id, retry=True)
        db.commit()
    assert process_one(factory, RecordingEngine())
    assert pixels[0] == pixels[1]
    with factory() as db:
        assert adjusted_path(db, photo_id) is not None


def test_folder_change_during_render_never_publishes_stale_result(prepared):
    from app.folder_processing import configure_folder
    from app.preview_adjustment.service import enqueue

    factory, photo_id = prepared
    with factory() as db:
        folder_id = db.get(PhotoAsset, photo_id).folder_id
        configure_folder(db, folder_id, preview_mode="custom", facial_mode="inherit",
                         strength=50, exposure_tenths=5)
        assert enqueue(db, photo_id, retry=True)
        db.commit()

    class ChangedEngine(BrightEngine):
        def render(self, image, strength):
            with factory() as db:
                configure_folder(db, folder_id, preview_mode="custom", facial_mode="inherit",
                                 strength=50, exposure_tenths=6)
                db.commit()
            return super().render(image, strength)

    assert process_one(factory, ChangedEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id) is None


def test_cleanup_refuses_active_folder_override(prepared):
    import pytest

    from app.folder_processing import configure_folder
    from app.preview_adjustment.cleanup import cleanup

    factory, photo_id = prepared
    with factory() as db:
        folder_id = db.get(PhotoAsset, photo_id).folder_id
        configure_folder(db, folder_id, preview_mode="custom", facial_mode="inherit",
                         strength=50, exposure_tenths=5)
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
        db.add_all(PhotoAsset(id=uuid4(), parent_gallery_id=gallery_id, folder_id=folder_id,
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
