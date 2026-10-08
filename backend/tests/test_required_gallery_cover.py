"""Contrato de prontidão e salvamento de Detalhes, em banco descartável."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth import (
    AuditEvent,
    Client,
    GalleryClientState,
    MediaDerivative,
    ParentGallery,
    ParentGalleryRegistration,
    PhotoAsset,
    PhotoFolder,
    SessionLocal,
    Tenant,
)
from app.gallery_cover_readiness import gallery_cover_readiness
from tests import test_gallery_workflow_remediation as workflow
from tests.tenant_fixtures import FIXTURE_TENANT_ID

clean_database = workflow.clean_database
client = workflow.client
authenticate_admin = workflow.authenticate_admin
ready_photo = workflow.ready_photo


def gallery_with_cover(db, tenant_id=FIXTURE_TENANT_ID):
    gallery = ParentGallery(tenant_id=tenant_id, name="Galeria sintética")
    db.add(gallery)
    db.flush()
    folder = PhotoFolder(tenant_id=tenant_id, parent_gallery_id=gallery.id, name="Fotos")
    db.add(folder)
    db.flush()
    photo = ready_photo(db, parent=gallery, folder=folder)
    gallery.cover_photo_id = photo.id
    db.flush()
    return gallery, photo


@pytest.mark.parametrize("state", ["missing", "processing", "failed", "ready", "unsafe_path"])
def test_only_configured_owned_ready_cover_completes_details(client, state):
    authenticate_admin(client)
    with SessionLocal() as db:
        gallery, photo = gallery_with_cover(db)
        derivative = db.scalar(select(MediaDerivative).where(MediaDerivative.photo_asset_id == photo.id, MediaDerivative.variant == "admin_preview"))
        if state == "missing":
            gallery.cover_photo_id = None
        elif state == "processing":
            derivative.status = "queued"
        elif state == "failed":
            derivative.status = "failed"
        elif state == "unsafe_path":
            derivative.relative_path = "../outside.jpg"
        gallery_id = gallery.id
        db.commit()
        expected = "failed" if state == "unsafe_path" else state
        assert gallery_cover_readiness(db, gallery)["status"] == expected
    editor = client.get(f"/admin/parent-galleries/{gallery_id}/editor").json()
    details = client.get(f"/admin/parent-galleries/{gallery_id}/details").json()
    assert details["cover_readiness"] == editor["cover_readiness"]
    assert editor["cover_readiness"]["status"] == expected
    assert editor["actions"]["can_complete"] is (expected == "ready")
    assert next(step for step in editor["steps"] if step["id"] == "detalhes")["status"] == ("complete" if expected == "ready" else "pending")


@pytest.mark.parametrize("reference", ["removed", "other_gallery", "other_tenant"])
def test_missing_or_incompatible_cover_reference_is_not_ready(reference):
    with SessionLocal() as db:
        gallery, _ = gallery_with_cover(db)
        other = Tenant()
        db.add(other)
        db.flush()
        target = ParentGallery(tenant_id=other.id if reference == "other_tenant" else FIXTURE_TENANT_ID, name="Outra")
        db.add(target)
        db.flush()
        folder = PhotoFolder(tenant_id=target.tenant_id, parent_gallery_id=target.id, name="Fotos")
        db.add(folder)
        db.flush()
        photo = PhotoAsset(tenant_id=target.tenant_id, parent_gallery_id=target.id, folder_id=folder.id, filename="outra.jpg", storage_key="tests/other.jpg")
        db.add(photo)
        db.flush()
        db.commit()
        # Projeção defensiva de referência antiga/incompatível; não força violação de FK.
        view = ParentGallery(id=gallery.id, tenant_id=gallery.tenant_id, cover_photo_id=uuid4() if reference == "removed" else photo.id)
        assert gallery_cover_readiness(db, view)["status"] == "missing"


@pytest.mark.parametrize("state", ["missing", "processing", "failed", "ready"])
def test_visual_patch_is_atomic_and_requires_ready_cover(client, state):
    authenticate_admin(client)
    with SessionLocal() as db:
        gallery, photo = gallery_with_cover(db)
        if state == "missing":
            gallery.cover_photo_id = None
        elif state != "ready":
            derivative = db.scalar(select(MediaDerivative).where(MediaDerivative.photo_asset_id == photo.id, MediaDerivative.variant == "admin_preview"))
            derivative.status = "queued" if state == "processing" else "failed"
        gallery_id = gallery.id
        original_name, original_size = gallery.name, gallery.cover_title_size
        db.commit()
        audits_before = db.scalar(select(func.count()).select_from(AuditEvent))
    result = client.patch(f"/admin/parent-galleries/{gallery_id}/settings", json={"name": "Novo nome", "cover_title_size": 40})
    assert result.status_code == (200 if state == "ready" else 409)
    with SessionLocal() as db:
        gallery = db.get(ParentGallery, gallery_id)
        assert gallery.name == ("Novo nome" if state == "ready" else original_name)
        assert gallery.cover_title_size == (40 if state == "ready" else original_size)
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == audits_before + (1 if state == "ready" else 0)


def test_initial_creation_settings_and_cover_upload_remain_available(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    authenticate_admin(client)
    created = client.post("/admin/parent-galleries", json={"name": "Cadastro sem capa"})
    assert created.status_code == 201
    gallery_id = created.json()["id"]
    result = client.patch(f"/admin/parent-galleries/{gallery_id}/settings", json={"name": "Nome atualizado", "folder_display_mode": "sequential", "sales_message": "Seleção externa"})
    assert result.status_code == 200
    editor = client.get(f"/admin/parent-galleries/{gallery_id}/editor").json()
    assert editor["actions"]["can_upload"] is True
    assert editor["actions"]["can_create_folder"] is True
    assert editor["gallery"]["name"] == "Nome atualizado"
    uploaded = client.post(f"/admin/parent-galleries/{gallery_id}/cover-photos", json={"filename": "capa.jpg", "idempotency_key": "cover-required-test-0001"})
    assert uploaded.status_code == 201
    assert client.put(uploaded.json()["upload_url"], content=workflow.jpeg_bytes(), headers={"content-type": "image/jpeg"}).status_code == 202
    assert client.get(f"/admin/parent-galleries/{gallery_id}/editor").json()["cover_readiness"]["status"] == "processing"


def test_replacing_cover_returns_existing_gallery_to_pending_without_removing_content(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    authenticate_admin(client)
    with SessionLocal() as db:
        gallery, photo = gallery_with_cover(db)
        gallery_id, photo_id = gallery.id, photo.id
        person = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Cliente sintética", phone_e164="+5511999988009")
        db.add(person)
        db.flush()
        state = GalleryClientState(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, client_id=person.id)
        registration = ParentGalleryRegistration(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, client_id=person.id, status="active")
        db.add_all([state, registration])
        db.commit()
        state_id, registration_id = state.id, registration.id
    assert client.get(f"/admin/parent-galleries/{gallery_id}/editor").json()["actions"]["can_complete"] is True
    uploaded = client.post(f"/admin/parent-galleries/{gallery_id}/cover-photos", json={"filename": "nova.jpg", "idempotency_key": "cover-required-test-0002"})
    assert uploaded.status_code == 201
    assert client.put(uploaded.json()["upload_url"], content=workflow.jpeg_bytes(), headers={"content-type": "image/jpeg"}).status_code == 202
    editor = client.get(f"/admin/parent-galleries/{gallery_id}/editor").json()
    assert editor["cover_readiness"]["status"] == "processing"
    assert editor["actions"]["can_complete"] is False
    with SessionLocal() as db:
        assert db.get(PhotoAsset, photo_id) is not None
        assert db.get(ParentGallery, gallery_id).active is True
        assert db.get(GalleryClientState, state_id).status == "active"
        assert db.get(ParentGalleryRegistration, registration_id).status == "active"
