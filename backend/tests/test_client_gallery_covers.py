from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    DerivedGallery,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    SessionLocal,
)
from app.main import app
from tests.test_unified_checkout import isolated_cart_database, setup_cart  # noqa: F401


def test_library_cover_uses_authorized_destination_and_revalidates_media(tmp_path, monkeypatch):
    owner_id, _, gallery_ids = setup_cart()
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path))
    from PIL import Image
    Image.new("RGB", (60, 40), "blue").save(tmp_path / "cover.jpg")
    with SessionLocal() as db:
        gallery = db.get(DerivedGallery, gallery_ids[0])
        parent = db.get(ParentGallery, gallery.parent_gallery_id)
        photo = db.scalar(select(PhotoAsset).where(PhotoAsset.derived_gallery_id == gallery.id))
        parent.cover_photo_id = photo.id
        derivative = MediaDerivative(photo_asset_id=photo.id, variant="admin_preview",
                                     relative_path="cover.jpg", status="ready", width=60, height=40)
        db.add(derivative)
        db.commit()
        parent_id, derivative_id = parent.id, derivative.id
    browser = TestClient(app)
    assert browser.get("/library").status_code == 403
    browser.cookies.set("markina_session", "cart-test")

    def journey():
        return next(row for row in browser.get("/library").json()["journeys"] if row["id"] == str(parent_id))

    cover = journey()["cover_preview_url"]
    assert cover == f"/gallery/{gallery_ids[0]}/cover-preview"
    image = browser.get(cover)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert image.content.startswith(b"\xff\xd8")
    assert next(row for row in browser.get("/library").json()["journeys"] if row["id"] != str(parent_id))["cover_preview_url"] is None
    with SessionLocal() as db:
        db.add(ParentGalleryRegistration(parent_gallery_id=parent_id, client_id=owner_id, status="active"))
        db.commit()
    assert journey()["cover_preview_url"] == f"/public-galleries/{parent_id}/cover-preview"
    assert browser.get(journey()["cover_preview_url"]).status_code == 200
    with SessionLocal() as db:
        db.get(DerivedGallery, gallery_ids[0]).access_enabled = False
        db.commit()
    assert journey()["cover_preview_url"] is None
    assert browser.get(cover).status_code == 403
    with SessionLocal() as db:
        db.get(DerivedGallery, gallery_ids[0]).access_enabled = True
        db.get(MediaDerivative, derivative_id).status = "failed"
        db.commit()
    assert journey()["cover_preview_url"] is None
    browser.cookies.clear()
    assert browser.get(cover).status_code == 403
