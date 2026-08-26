import pytest
from PIL import Image

from app.auth import Base, ParentGallery, PhotoAsset, SessionLocal, engine
from app.media import generate_derivatives


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def test_generates_idempotent_protected_derivatives_without_exif(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    derivatives_root = tmp_path / "derivatives"
    source = source_root / "event" / "foto.jpg"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (2400, 1200), color=(60, 90, 120)).save(source, exif=b"Exif\x00\x00test")
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(source_root))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(derivatives_root))
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        photo = PhotoAsset(
            parent_gallery_id=parent.id, filename="foto.jpg", storage_key="event/foto.jpg"
        )
        db.add(photo)
        db.commit()
        first = generate_derivatives(db, photo)
        second = generate_derivatives(db, photo)
        assert {item.variant for item in first} == {"thumbnail", "client_preview", "admin_preview"}
        assert {item.id for item in first} == {item.id for item in second}
    client_preview = derivatives_root / str(photo.id) / "client_preview.jpg"
    admin_preview = derivatives_root / str(photo.id) / "admin_preview.jpg"
    assert client_preview.read_bytes() != admin_preview.read_bytes()
    with Image.open(client_preview) as rendered:
        assert rendered.width <= 1600
        assert not rendered.getexif()
