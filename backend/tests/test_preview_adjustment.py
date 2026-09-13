from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PreviewAdjustment,
    PreviewAdjustmentSettings,
)


@pytest.fixture
def database(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'adjustment.db'}")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    yield engine
    engine.dispose()


def make_photo(db):
    parent = ParentGallery(name="Amostra")
    db.add(parent)
    db.flush()
    folder = PhotoFolder(parent_gallery_id=parent.id, name="Fotos", purpose="content")
    db.add(folder)
    db.flush()
    photo = PhotoAsset(
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename="foto.jpg",
        storage_key=f"{uuid4()}.jpg",
    )
    db.add(photo)
    db.commit()
    return photo


def test_settings_default_constraints_and_photo_cascade(database):
    with Session(database) as db:
        config = PreviewAdjustmentSettings()
        db.add(config)
        photo = make_photo(db)
        assert not config.enabled
        db.add(PreviewAdjustment(photo_asset_id=photo.id, generation=1, fingerprint="a" * 64))
        db.commit()
        db.execute(delete(PhotoAsset).where(PhotoAsset.id == photo.id))
        db.commit()
        assert db.get(PreviewAdjustment, photo.id) is None
        config.strength = 101
        with pytest.raises(IntegrityError):
            db.commit()


def test_engine_isolated_bounded_and_does_not_change_input(monkeypatch):
    from pathlib import Path

    from PIL import Image

    from app.preview_adjustment.engine import RawTherapeeEngine

    seen = []

    def command(args, **kwargs):
        seen.append(args)
        assert kwargs["timeout"] == 90
        assert kwargs["env"]["OMP_NUM_THREADS"] == "1"
        assert kwargs.get("shell", False) is False
        assert "-a" in args  # RawTherapee deve aceitar PNG mesmo fora das extensões padrão.
        source = Path(args[-1])
        assert source.name == "input.png"
        Image.new("RGB", (40, 30), (100, 100, 100)).save(args[2])

    monkeypatch.setattr("app.preview_adjustment.engine.subprocess.run", command)
    original = Image.new("RGB", (40, 30), (40, 40, 40))
    result = RawTherapeeEngine().render(original, 50)
    assert original.getpixel((0, 0)) == (40, 40, 40)
    assert result.getpixel((0, 0)) == (70, 70, 70)
    assert not Path(seen[0][-1]).exists()


@pytest.fixture
def prepared(database):
    from PIL import Image
    from sqlalchemy.orm import sessionmaker

    from app.media import generate_derivatives, safe_source_path
    from app.preview_adjustment.service import configure

    factory = sessionmaker(database, expire_on_commit=False)
    with factory() as db:
        photo = make_photo(db)
        path = safe_source_path(photo)
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (320, 180), (45, 65, 85)).save(path)
        configure(db, True, 50)
        db.commit()
        generate_derivatives(db, photo)
        return factory, photo.id


class BrightEngine:
    def render(self, image, strength):
        from PIL import ImageEnhance

        return ImageEnhance.Brightness(image).enhance(1.3)


def test_job_idempotency_fallback_and_byte_preservation(prepared):
    from sqlalchemy import select

    from app.auth import MediaDerivative
    from app.media import safe_derivative_path
    from app.preview_adjustment.service import (
        adjusted_path,
        configure,
        enqueue,
        presentation_path,
        process_one,
    )

    factory, photo_id = prepared
    with factory() as db:
        originals = {
            row.variant: safe_derivative_path(row).read_bytes()
            for row in db.scalars(select(MediaDerivative))
        }
        assert not enqueue(db, photo_id)
        assert adjusted_path(db, photo_id) is None
    assert process_one(factory, BrightEngine())
    assert not process_one(factory, BrightEngine())
    with factory() as db:
        path = adjusted_path(db, photo_id)
        assert path and path.read_bytes() != originals["client_preview"]
        for row in db.scalars(select(MediaDerivative)):
            assert safe_derivative_path(row).read_bytes() == originals[row.variant]
        assert not enqueue(db, photo_id, retry=True)
        configure(db, False, 50)
        db.commit()
        row = db.scalar(select(MediaDerivative).where(MediaDerivative.variant == "client_preview"))
        assert presentation_path(db, row).read_bytes() == originals["client_preview"]
        assert path.is_file()


@pytest.mark.parametrize("mutation", ["disable", "source", "protection", "delete", "gallery"])
def test_inflight_result_cannot_override_changed_state(prepared, mutation):
    from sqlalchemy import select

    from app.auth import BrandingSettings, MediaDerivative, MediaJob, now
    from app.preview_adjustment.service import adjusted_path, configure, process_one

    factory, photo_id = prepared

    class ChangedEngine(BrightEngine):
        def render(self, image, strength):
            with factory() as db:
                if mutation == "disable":
                    configure(db, False, 50)
                elif mutation == "source":
                    db.scalar(
                        select(MediaDerivative).where(MediaDerivative.variant == "admin_preview")
                    ).updated_at = now()
                elif mutation == "protection":
                    db.add(BrandingSettings(watermark_text="NOVA MARCA"))
                elif mutation == "gallery":
                    photo = db.get(PhotoAsset, photo_id)
                    db.get(ParentGallery, photo.parent_gallery_id).lifecycle_status = "deleting"
                else:
                    db.execute(delete(MediaDerivative))
                    db.execute(delete(MediaJob))
                    db.execute(delete(PhotoAsset).where(PhotoAsset.id == photo_id))
                db.commit()
            return super().render(image, strength)

    assert process_one(factory, ChangedEngine())
    with factory() as db:
        assert adjusted_path(db, photo_id) is None


def test_failure_retry_and_expired_claim(prepared):
    from datetime import timedelta

    from app.auth import now
    from app.preview_adjustment.service import enqueue, process_one

    class BadEngine:
        def render(self, image, strength):
            raise RuntimeError("secret path should not be exposed")

    factory, photo_id = prepared
    assert process_one(factory, BadEngine())
    with factory() as db:
        row = db.get(PreviewAdjustment, photo_id)
        assert row.status == "failed" and "secret" not in row.last_error
        assert enqueue(db, photo_id, retry=True)
        row.status, row.claim_token = "processing", str(uuid4())
        row.updated_at = now() - timedelta(minutes=5)
        db.commit()
    assert process_one(factory, BrightEngine())
    with factory() as db:
        assert db.get(PreviewAdjustment, photo_id).status == "ready"


def test_missing_result_falls_back_and_can_retry(prepared):
    from app.preview_adjustment.service import adjusted_path, enqueue, process_one

    factory, photo_id = prepared
    process_one(factory, BrightEngine())
    with factory() as db:
        adjusted_path(db, photo_id).unlink()
        assert adjusted_path(db, photo_id) is None
        assert enqueue(db, photo_id, retry=True)


def test_cleanup_is_scoped_and_requires_disable(prepared):
    from sqlalchemy import select

    from app.auth import MediaDerivative
    from app.media import safe_derivative_path
    from app.preview_adjustment.cleanup import cleanup
    from app.preview_adjustment.service import configure, process_one

    factory, photo_id = prepared
    process_one(factory, BrightEngine())
    with factory() as db:
        paths = [safe_derivative_path(row) for row in db.scalars(select(MediaDerivative))]
        original = {path: path.read_bytes() for path in paths}
        assert cleanup(db)["files"] == 1
        with pytest.raises(ValueError):
            cleanup(db, execute=True, worker_stopped=True)
        configure(db, False, 50)
        db.commit()
        with pytest.raises(ValueError):
            cleanup(db, execute=True)
        assert cleanup(db, execute=True, worker_stopped=True)["deleted"]
        assert db.get(PreviewAdjustment, photo_id) is None
        assert all(path.read_bytes() == data for path, data in original.items())
        assert db.get(PhotoAsset, photo_id)


@pytest.fixture
def api_client(prepared, monkeypatch):
    from datetime import timedelta

    from fastapi.testclient import TestClient

    from app import auth, main

    factory, photo_id = prepared
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    with factory() as db:
        db.add_all(
            [
                auth.AuthSession(
                    token_hash=auth.token_hash(f"adjustment-{role}"),
                    role=role,
                    subject_id=uuid4(),
                    expires_at=auth.now() + timedelta(hours=1),
                )
                for role in ("admin", "client")
            ]
        )
        db.commit()
    with TestClient(main.app) as client:
        yield client, factory, photo_id


def test_admin_api_auth_comparison_and_immediate_disable(api_client):
    from app.preview_adjustment.service import process_one

    client, factory, photo_id = api_client
    root = "/admin/preview-adjustment"
    assert client.get(root).status_code == 403
    client.cookies.set("markina_session", "adjustment-client")
    assert client.patch(root, json={"enabled": True}).status_code == 403
    assert client.get(f"{root}/photos/{photo_id}/before").status_code == 403
    client.cookies.set("markina_session", "adjustment-admin")
    assert client.patch(root, json={"enabled": True, "strength": 200}).status_code == 422
    assert client.get(f"{root}/photos/{photo_id}/after").status_code == 404
    before = client.get(f"{root}/photos/{photo_id}/before")
    assert before.status_code == 200 and "no-store" in before.headers["cache-control"]
    process_one(factory, BrightEngine())
    after = client.get(f"{root}/photos/{photo_id}/after")
    assert after.status_code == 200 and before.content != after.content
    assert (
        client.get(f"/admin/photo-assets/{photo_id}/watermarked-preview").content == after.content
    )
    assert client.patch(root, json={"enabled": False, "strength": 50}).status_code == 200
    assert client.get(f"{root}/photos/{photo_id}/after").status_code == 404
    assert (
        client.get(f"/admin/photo-assets/{photo_id}/watermarked-preview").content == before.content
    )


def test_gallery_queue_and_progress_and_photo_deletion(api_client):
    from app.preview_adjustment.service import adjusted_path, process_one

    client, factory, photo_id = api_client
    client.cookies.set("markina_session", "adjustment-admin")
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        gallery_id, folder_id = photo.parent_gallery_id, photo.folder_id
    endpoint = f"/admin/preview-adjustment/galleries/{gallery_id}"
    assert client.get(endpoint).json()["counts"]["queued"] == 1
    assert client.post(f"{endpoint}/enqueue").json()["queued"] == 0
    process_one(factory, BrightEngine())
    with factory() as db:
        result = adjusted_path(db, photo_id)
    payload = client.get(endpoint).json()
    assert payload["counts"]["ready"] == 1
    assert payload["photos"][0]["id"] == str(photo_id)
    response = client.delete(f"/admin/photo-folders/{folder_id}/photos/{photo_id}")
    assert response.status_code == 204, response.text
    assert not result.exists()
    with factory() as db:
        assert db.get(PreviewAdjustment, photo_id) is None


def test_client_private_delivery_keeps_authorization_and_fallback(api_client):
    from sqlalchemy import select

    from app.auth import (
        AuthSession,
        Client,
        DerivedGallery,
        DerivedGalleryPhoto,
        GalleryAccess,
        token_hash,
    )
    from app.preview_adjustment.service import adjusted_path, configure, process_one

    client, factory, photo_id = api_client
    with factory() as db:
        owner = Client(full_name="Responsável de teste", phone_e164="+5511999999988")
        db.add(owner)
        db.flush()
        photo = db.get(PhotoAsset, photo_id)
        gallery = DerivedGallery(
            parent_gallery_id=photo.parent_gallery_id, client_id=owner.id, name="Privada de teste"
        )
        db.add(gallery)
        db.flush()
        db.add_all(
            [
                GalleryAccess(client_id=owner.id, gallery_id=gallery.id),
                DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo_id),
            ]
        )
        session = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_hash("adjustment-client"))
        )
        session.subject_id = owner.id
        db.commit()
        gallery_id = gallery.id
    endpoint = f"/gallery/{gallery_id}/photos/{photo_id}/preview"
    assert client.get(endpoint).status_code == 403
    client.cookies.set("markina_session", "adjustment-client")
    conventional = client.get(endpoint)
    assert conventional.status_code == 200
    process_one(factory, BrightEngine())
    result = client.get(endpoint)
    assert result.status_code == 200 and result.content != conventional.content
    assert result.headers["cache-control"] == "private, no-store"
    with factory() as db:
        assert result.content == adjusted_path(db, photo_id).read_bytes()
        configure(db, False, 50)
        db.commit()
    assert client.get(endpoint).content == conventional.content
    assert client.get(f"/gallery/{uuid4()}/photos/{photo_id}/preview").status_code == 403


def test_optional_table_failure_does_not_break_conventional_import(prepared):
    from sqlalchemy import select

    from app.auth import MediaDerivative, MediaJob
    from app.media import generate_derivatives, safe_derivative_path
    from app.preview_adjustment.service import presentation_path

    factory, photo_id = prepared
    with factory() as db:
        db.execute(delete(PreviewAdjustment))
        db.commit()
        PreviewAdjustmentSettings.__table__.drop(db.get_bind())
        derivatives = generate_derivatives(db, db.get(PhotoAsset, photo_id))
        assert len(derivatives) == 3
        assert db.scalar(select(MediaJob)).status == "completed"
        row = db.scalar(select(MediaDerivative).where(MediaDerivative.variant == "client_preview"))
        assert presentation_path(db, row) == safe_derivative_path(row)


def test_public_delivery_requires_registration_and_released_folder(api_client):
    from sqlalchemy import select

    from app.auth import AuthSession, Client, ParentGalleryRegistration, token_hash
    from app.preview_adjustment.service import configure, process_one

    client, factory, photo_id = api_client
    with factory() as db:
        owner = Client(full_name="Teste de acesso", phone_e164="+5511999999977")
        db.add(owner)
        db.flush()
        photo = db.get(PhotoAsset, photo_id)
        gallery_id, folder_id = photo.parent_gallery_id, photo.folder_id
        db.get(ParentGallery, gallery_id).access_mode = "standard"
        db.get(PhotoFolder, folder_id).status = "preparing"
        session = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_hash("adjustment-client"))
        )
        session.subject_id = owner.id
        owner_id = owner.id
        db.commit()
    endpoint = f"/public-galleries/{gallery_id}/photos/{photo_id}/preview"
    assert client.get(endpoint).status_code == 403
    client.cookies.set("markina_session", "adjustment-client")
    assert client.get(endpoint).status_code == 403
    with factory() as db:
        db.add(
            ParentGalleryRegistration(
                parent_gallery_id=gallery_id,
                client_id=owner_id,
                status="active",
            )
        )
        db.commit()
    assert client.get(endpoint).status_code == 404
    with factory() as db:
        db.get(PhotoFolder, folder_id).status = "released"
        db.commit()
    before = client.get(endpoint)
    assert before.status_code == 200
    process_one(factory, BrightEngine())
    after = client.get(endpoint)
    assert after.status_code == 200 and after.content != before.content
    assert after.headers["cache-control"] == "private, no-store"
    with factory() as db:
        configure(db, False, 50)
        db.commit()
    assert client.get(endpoint).content == before.content


def test_lifecycle_manifest_includes_adjustment_and_preserves_private_reference(prepared):
    from app.auth import Client, DerivedGallery, DerivedGalleryPhoto
    from app.gallery_lifecycle import gallery_operational_storage_manifest
    from app.media import derivatives_root
    from app.preview_adjustment.service import adjusted_path, process_one

    factory, photo_id = prepared
    process_one(factory, BrightEngine())
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        relative = adjusted_path(db, photo_id).relative_to(derivatives_root()).as_posix()
        manifest = gallery_operational_storage_manifest(db, photo.parent_gallery_id)
        assert relative in [item["relative_path"] for item in manifest["derivatives"]]
        owner = Client(full_name="Teste privado", phone_e164="+5511999999966")
        db.add(owner)
        db.flush()
        gallery = DerivedGallery(
            parent_gallery_id=photo.parent_gallery_id,
            client_id=owner.id,
            name="Preservada",
        )
        db.add(gallery)
        db.flush()
        db.add(DerivedGalleryPhoto(derived_gallery_id=gallery.id, photo_asset_id=photo_id))
        db.commit()
        manifest = gallery_operational_storage_manifest(db, photo.parent_gallery_id)
        assert manifest == {"sources": [], "derivatives": []}
