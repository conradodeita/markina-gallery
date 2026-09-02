from io import BytesIO
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import (
    AdminUser,
    Base,
    Client,
    DerivedGallery,
    DerivedGalleryPhoto,
    MediaDerivative,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    SessionLocal,
    engine,
    password_hasher,
)
from app.main import app
from app.media import generate_derivatives


@pytest.fixture(autouse=True)
def clean_database():
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(connection)
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def authenticate_admin(client: TestClient) -> None:
    with SessionLocal() as db:
        admin = AdminUser(
            email="workflow@markina.test",
            password_hash=password_hasher.hash("senha-segura"),
            email_verified=True,
            totp_secret=pyotp.random_base32(),
        )
        db.add(admin)
        db.commit()
        secret = admin.totp_secret
    challenge = client.post(
        "/auth/admin/password",
        json={"email": "workflow@markina.test", "password": "senha-segura"},
    ).json()["challenge_id"]
    response = client.post(
        "/auth/admin/totp",
        json={"challenge_id": challenge, "code": pyotp.TOTP(secret).now()},
    )
    assert response.status_code == 200


def ready_photo(
    db,
    *,
    parent: ParentGallery,
    folder: PhotoFolder,
    available: bool = False,
    filename: str = "foto.jpg",
) -> PhotoAsset:
    photo = PhotoAsset(
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        filename=filename,
        storage_key=f"tests/{uuid4()}.jpg",
        available=available,
    )
    db.add(photo)
    db.flush()
    db.add(MediaJob(photo_asset_id=photo.id, status="completed", attempts=1))
    db.add(
        MediaDerivative(
            photo_asset_id=photo.id,
            variant="client_preview",
            relative_path=f"{photo.id}/client_preview.jpg",
            status="ready",
            width=1200,
            height=800,
        )
    )
    db.flush()
    return photo


def jpeg_bytes() -> bytes:
    payload = BytesIO()
    Image.new("RGB", (1200, 800), color=(34, 48, 67)).save(payload, format="JPEG")
    return payload.getvalue()


def test_only_one_cover_assets_folder_exists_per_parent() -> None:
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        db.add_all(
            [
                PhotoFolder(
                    parent_gallery_id=parent.id,
                    name="Capa A",
                    purpose="cover_assets",
                    position=-1,
                ),
                PhotoFolder(
                    parent_gallery_id=parent.id,
                    name="Capa B",
                    purpose="cover_assets",
                    position=-2,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_cover_assets_are_excluded_from_content_contracts(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        content = PhotoFolder(parent_gallery_id=parent.id, name="Cerimônia", status="released")
        cover = PhotoFolder(
            parent_gallery_id=parent.id,
            name="Capa técnica",
            purpose="cover_assets",
            position=-1,
        )
        db.add_all([content, cover])
        db.flush()
        ready_photo(db, parent=parent, folder=content, available=True, filename="conteudo.jpg")
        ready_photo(db, parent=parent, folder=cover, filename="capa.jpg")
        parent_id = parent.id
        db.commit()

    folders = client.get(f"/admin/parent-galleries/{parent_id}/folders")
    assert folders.status_code == 200
    assert folders.json()["total"] == 1
    assert folders.json()["folders"][0]["name"] == "Cerimônia"
    summary = client.get(f"/admin/parent-galleries/{parent_id}/summary").json()
    assert summary["counts"]["folders"] == 1
    assert summary["counts"]["photos"] == 1
    available = client.get(f"/admin/parent-galleries/{parent_id}/available-photos").json()
    assert [photo["name"] for photo in available["photos"]] == ["conteudo.jpg"]
    assert available["photos"][0]["width"] == 1200
    assert available["photos"][0]["height"] == 800
    assert available["photos"][0]["publication_state"] == "published"
    assert "storage_key" not in folders.text + str(available)


def test_publish_promotes_only_ready_unavailable_photos_without_private_links(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada")
        db.add(folder)
        db.flush()
        ready = ready_photo(db, parent=parent, folder=folder)
        pending = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=folder.id,
            filename="pendente.jpg",
            storage_key=f"tests/{uuid4()}.jpg",
            available=False,
        )
        db.add(pending)
        owner = Client(full_name="Cliente", phone_e164="+5511999999999")
        db.add(owner)
        db.flush()
        private = DerivedGallery(
            parent_gallery_id=parent.id,
            client_id=owner.id,
            name="Privada",
        )
        db.add(private)
        db.commit()
        folder_id, ready_id, pending_id = folder.id, ready.id, pending.id

    published = client.post(f"/admin/photo-folders/{folder_id}/publish", json={})
    assert published.status_code == 200
    assert published.json()["published_count"] == 1
    assert published.json()["pending_count"] == 1
    repeated = client.post(f"/admin/photo-folders/{folder_id}/publish", json={})
    assert repeated.status_code == 200
    assert repeated.json()["published_count"] == 0
    with SessionLocal() as db:
        assert db.get(PhotoAsset, ready_id).available is True
        assert db.get(PhotoAsset, pending_id).available is False
        assert list(db.scalars(select(DerivedGalleryPhoto))) == []


def test_publish_ready_parent_batch_reports_pending_and_publishes_all_ready(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento em lote")
        db.add(parent)
        db.flush()
        first = PhotoFolder(parent_gallery_id=parent.id, name="Primeira", position=0)
        second = PhotoFolder(parent_gallery_id=parent.id, name="Segunda", position=1)
        db.add_all([first, second])
        db.flush()
        ready_first = ready_photo(db, parent=parent, folder=first, filename="a.jpg")
        ready_second = ready_photo(db, parent=parent, folder=second, filename="b.jpg")
        pending = PhotoAsset(
            parent_gallery_id=parent.id,
            folder_id=second.id,
            filename="c.jpg",
            storage_key=f"tests/{uuid4()}.jpg",
            available=False,
        )
        db.add(pending)
        db.commit()
        parent_id = parent.id

    published = client.post(f"/admin/parent-galleries/{parent_id}/publish-ready")
    assert published.status_code == 200
    assert published.json()["published_count"] == 2
    assert published.json()["pending_count"] == 1
    assert published.json()["failed_count"] == 0
    assert published.json()["available_count"] == 2
    assert len(published.json()["folders"]) == 2
    with SessionLocal() as db:
        assert db.get(PhotoAsset, ready_first.id).available is True
        assert db.get(PhotoAsset, ready_second.id).available is True
        assert db.get(PhotoAsset, pending.id).available is False


def test_legacy_release_rejects_private_destinations_without_side_effects(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada")
        db.add(folder)
        db.flush()
        photo = ready_photo(db, parent=parent, folder=folder)
        folder_id, photo_id = folder.id, photo.id
        db.commit()

    response = client.post(
        f"/admin/photo-folders/{folder_id}/release",
        json={"gallery_ids": [str(uuid4())]},
    )
    assert response.status_code == 410
    with SessionLocal() as db:
        assert db.get(PhotoFolder, folder_id).status == "preparing"
        assert db.get(PhotoAsset, photo_id).available is False
        assert list(db.scalars(select(DerivedGalleryPhoto))) == []


def test_released_folder_accepts_incremental_registration_as_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Rodada", status="released")
        db.add(folder)
        db.flush()
        previous = ready_photo(db, parent=parent, folder=folder, available=True)
        folder_id, previous_id = folder.id, previous.id
        db.commit()

    registered = client.post(
        f"/admin/photo-folders/{folder_id}/photos",
        json={
            "filename": "nova.jpg",
            "storage_key": f"tests/{uuid4()}.jpg",
        },
    )
    assert registered.status_code == 201
    uploaded = client.put(
        f"/admin/photo-assets/{registered.json()['id']}/source",
        content=jpeg_bytes(),
        headers={"content-type": "image/jpeg"},
    )
    assert uploaded.status_code == 202
    with SessionLocal() as db:
        assert db.get(PhotoAsset, UUID(registered.json()["id"])).available is False
        assert db.get(PhotoAsset, previous_id).available is True


def test_admin_private_gallery_uses_only_published_photos_without_selecting_them(
    client: TestClient,
) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Origem publicada")
        other_parent = ParentGallery(name="Outra origem")
        owner = Client(full_name="Cliente publicada", phone_e164="+5511999999910")
        db.add_all([parent, other_parent, owner])
        db.flush()
        folder = PhotoFolder(parent_gallery_id=parent.id, name="Publicada", status="released")
        other_folder = PhotoFolder(
            parent_gallery_id=other_parent.id,
            name="Estrangeira",
            status="released",
        )
        db.add_all([folder, other_folder])
        db.flush()
        published = ready_photo(db, parent=parent, folder=folder, available=True)
        unpublished = ready_photo(
            db,
            parent=parent,
            folder=folder,
            available=False,
            filename="nao-publicada.jpg",
        )
        foreign = ready_photo(
            db,
            parent=other_parent,
            folder=other_folder,
            available=True,
            filename="outra-origem.jpg",
        )
        parent_id, owner_id = parent.id, owner.id
        published_id, unpublished_id, foreign_id = published.id, unpublished.id, foreign.id
        db.commit()

    available = client.get(
        f"/admin/parent-galleries/{parent_id}/available-photos"
    ).json()["photos"]
    assert [item["id"] for item in available] == [str(published_id)]
    link_only = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(owner_id),
            "name": "Privada",
            "photo_ids": [],
        },
    )
    assert link_only.status_code == 201
    assert link_only.json()["private_gallery_id"] is None

    created = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(owner_id),
            "name": "Privada",
            "photo_ids": [str(published_id)],
        },
    )
    repeated = client.post(
        "/admin/derived-galleries",
        json={
            "parent_gallery_id": str(parent_id),
            "client_id": str(owner_id),
            "name": "Privada",
            "photo_ids": [str(published_id)],
        },
    )
    assert created.status_code == repeated.status_code == 201
    assert created.json()["gallery_created"] is True
    assert repeated.json()["gallery_created"] is False
    assert created.json()["references_created"] == 1
    assert repeated.json()["references_created"] == 0
    with SessionLocal() as db:
        assert db.scalar(select(PhotoSelection)) is None

    for rejected_id in (unpublished_id, foreign_id):
        rejected = client.post(
            "/admin/derived-galleries",
            json={
                "parent_gallery_id": str(parent_id),
                "client_id": str(owner_id),
                "name": "Privada",
                "photo_ids": [str(rejected_id)],
            },
        )
        assert rejected.status_code == 422

    aggregate = client.get(f"/admin/parent-galleries/{parent_id}/clients").json()["clients"]
    assert aggregate[0]["derived_gallery_id"] == created.json()["id"]
    assert aggregate[0]["available_count"] == 1
    assert aggregate[0]["selected_count"] == 0


def test_cover_font_uses_controlled_tokens_and_safe_legacy_fallback(client: TestClient) -> None:
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento", cover_title_font="fonte-legada-desconhecida")
        db.add(parent)
        db.commit()
        parent_id = parent.id

    details = client.get(f"/admin/parent-galleries/{parent_id}/details")
    assert details.status_code == 200
    assert details.json()["settings"]["cover_title_font"] == "system-sans"
    assert len(details.json()["font_options"]) >= 8
    assert sum(
        option["category"] == "handwritten"
        for option in details.json()["font_options"]
    ) >= 3
    accepted = client.patch(
        f"/admin/parent-galleries/{parent_id}/settings",
        json={"cover_title_font": "handwritten-caveat"},
    )
    assert accepted.status_code == 200
    third_handwritten = client.patch(
        f"/admin/parent-galleries/{parent_id}/settings",
        json={"cover_title_font": "handwritten-personal"},
    )
    assert third_handwritten.status_code == 200
    rejected = client.patch(
        f"/admin/parent-galleries/{parent_id}/settings",
        json={"cover_title_font": "url(https://example.test/font.woff2)"},
    )
    assert rejected.status_code == 422


def test_dedicated_cover_upload_reuses_technical_folder_and_media_pipeline(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    authenticate_admin(client)
    with SessionLocal() as db:
        parent = ParentGallery(name="Evento")
        db.add(parent)
        db.commit()
        parent_id = parent.id

    payload = {
        "filename": "capa.jpg",
        "display_name": "Capa principal",
        "idempotency_key": "cover-upload-key-0001",
    }
    first = client.post(f"/admin/parent-galleries/{parent_id}/cover-photos", json=payload)
    second = client.post(f"/admin/parent-galleries/{parent_id}/cover-photos", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    photo_id = UUID(first.json()["id"])

    invalid_mime = client.put(
        first.json()["upload_url"],
        content=jpeg_bytes(),
        headers={"content-type": "image/png"},
    )
    assert invalid_mime.status_code == 415
    queued = client.put(
        first.json()["upload_url"],
        content=jpeg_bytes(),
        headers={"content-type": "image/jpeg"},
    )
    assert queued.status_code == 202
    with SessionLocal() as db:
        photo = db.get(PhotoAsset, photo_id)
        assert photo is not None and photo.available is False
        generate_derivatives(db, photo)
        assert (
            len(
                list(
                    db.scalars(
                        select(PhotoFolder).where(
                            PhotoFolder.parent_gallery_id == parent_id,
                            PhotoFolder.purpose == "cover_assets",
                        )
                    )
                )
            )
            == 1
        )

    selected = client.put(
        f"/admin/parent-galleries/{parent_id}/cover", json={"photo_id": str(photo_id)}
    )
    assert selected.status_code == 200
    details = client.get(f"/admin/parent-galleries/{parent_id}/details").json()
    assert details["settings"]["cover_photo_id"] == str(photo_id)
    assert details["cover_options"][0]["status"] == "ready"
    assert details["cover_options"][0]["source"] == "cover_assets"
    assert client.get(f"/admin/parent-galleries/{parent_id}/folders").json()["total"] == 0
    assert (
        client.get(f"/admin/parent-galleries/{parent_id}/available-photos").json()["photos"] == []
    )
