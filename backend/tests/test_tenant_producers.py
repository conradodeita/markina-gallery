"""Propriedade resolvida no servidor; dados e sessões exclusivamente sintéticos."""

from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import auth, main
from app.auth import (
    AdminUser,
    AuthSession,
    Client,
    DerivedGallery,
    GalleryClientState,
    MediaJob,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
)
from app.client_identity import ClientIdentityConflict
from app.photographer_credits import grant_credits
from app.private_membership import ensure_private_membership
from app.system_monitor.models import PlatformOwner
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


def test_validation_summary_aggregates_only_current_tenant(tenant_db, admin_api, monkeypatch):
    from app.storage_metrics import PhotoStorageMeasurement

    api, owner, _ = admin_api
    other = Tenant()
    tenant_db.add(other)
    tenant_db.flush()
    first = ParentGallery(tenant_id=owner.id, name="Atual")
    hidden = ParentGallery(tenant_id=owner.id, name="Removida", lifecycle_status="deleted")
    second = ParentGallery(tenant_id=other.id, name="Outra conta")
    tenant_db.add_all([first, hidden, second])
    tenant_db.flush()
    folders = [
        PhotoFolder(tenant_id=owner.id, parent_gallery_id=first.id, name="Preparando",
                    purpose="content", status="preparing"),
        PhotoFolder(tenant_id=other.id, parent_gallery_id=second.id, name="Liberada",
                    purpose="content", status="released"),
    ]
    tenant_db.add_all(folders)
    for account in (owner, other):
        tenant_db.add(Client(tenant_id=account.id, full_name="Sintética",
                             phone_e164="+5511999999999"))
    tenant_db.flush()
    for folder, status in zip(folders, ("failed", "queued")):
        photo = PhotoAsset(tenant_id=folder.tenant_id, parent_gallery_id=folder.parent_gallery_id,
                           folder_id=folder.id, filename="synthetic.jpg",
                           storage_key=f"tenants/{folder.tenant_id}/synthetic.jpg")
        tenant_db.add(photo)
        tenant_db.flush()
        tenant_db.add(MediaJob(tenant_id=folder.tenant_id, photo_asset_id=photo.id, status=status))
    tenant_db.commit()
    monkeypatch.setattr(main, "measure_owned_photo_storage",
                        lambda db, *, tenant_id: PhotoStorageMeasurement(bytes=0, available=True))
    response = api.get("/admin/validation-summary")
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["counts"]["clients"] == summary["counts"]["parent_galleries"] == 1
    assert summary["counts"]["imports"] == {"failed": 1}
    assert summary["counts"]["folders_preparing"] == 1
    assert summary["counts"]["folders_released"] == 0
    assert summary["counts"]["folders_with_active_imports"] == 0
    assert summary["storage"]["photo_count"] == 1
    assert [g["id"] for g in summary["recent_galleries"]] == [str(first.id)]


def test_validation_summary_projects_recent_open_selections_per_tenant(
    tenant_db, admin_api, monkeypatch
):
    from app.storage_metrics import PhotoStorageMeasurement

    api, current_tenant, _admin = admin_api
    other_tenant = Tenant()
    tenant_db.add(other_tenant)
    tenant_db.flush()
    reference = auth.now()
    expected_started_at = None
    for index in range(6):
        parent = ParentGallery(tenant_id=current_tenant.id, name=f"Evento {index}")
        client = Client(
            tenant_id=current_tenant.id,
            full_name=f"Cliente {index}",
            phone_e164=f"+5511999000{index:04d}",
        )
        tenant_db.add_all([parent, client])
        tenant_db.flush()
        started_at = reference - timedelta(hours=index + 1)
        tenant_db.add(GalleryClientState(
            tenant_id=current_tenant.id,
            parent_gallery_id=parent.id,
            client_id=client.id,
            selection_started_at=started_at,
        ))
        folder = PhotoFolder(
            tenant_id=current_tenant.id,
            parent_gallery_id=parent.id,
            name="Pasta",
            purpose="content",
            status="released",
        )
        tenant_db.add(folder)
        tenant_db.flush()
        selection_count = 2 if index == 0 else 1
        if index == 0:
            expected_started_at = started_at
        for photo_index in range(selection_count):
            photo = PhotoAsset(
                tenant_id=current_tenant.id,
                parent_gallery_id=parent.id,
                folder_id=folder.id,
                filename=f"foto-{photo_index}.jpg",
                storage_key=f"current/{index}/{photo_index}.jpg",
            )
            tenant_db.add(photo)
            tenant_db.flush()
            tenant_db.add(PhotoSelection(
                tenant_id=current_tenant.id,
                parent_gallery_id=parent.id,
                client_id=client.id,
                photo_asset_id=photo.id,
                created_at=reference - timedelta(minutes=index * 10 + photo_index + 1),
            ))

    other_parent = ParentGallery(tenant_id=other_tenant.id, name="Galeria secreta")
    other_client = Client(
        tenant_id=other_tenant.id,
        full_name="Cliente de outro tenant",
        phone_e164="+5511888000000",
    )
    tenant_db.add_all([other_parent, other_client])
    tenant_db.flush()
    other_folder = PhotoFolder(
        tenant_id=other_tenant.id,
        parent_gallery_id=other_parent.id,
        name="Pasta secreta",
        purpose="content",
        status="released",
    )
    tenant_db.add(other_folder)
    tenant_db.flush()
    other_photo = PhotoAsset(
        tenant_id=other_tenant.id,
        parent_gallery_id=other_parent.id,
        folder_id=other_folder.id,
        filename="segredo.jpg",
        storage_key="other/secret.jpg",
    )
    tenant_db.add(other_photo)
    tenant_db.flush()
    tenant_db.add(PhotoSelection(
        tenant_id=other_tenant.id,
        parent_gallery_id=other_parent.id,
        client_id=other_client.id,
        photo_asset_id=other_photo.id,
    ))
    tenant_db.commit()

    monkeypatch.setattr(
        main, "measure_owned_photo_storage",
        lambda db, *, tenant_id: PhotoStorageMeasurement(bytes=0, available=True),
    )
    response = api.get("/admin/validation-summary")
    assert response.status_code == 200, response.text
    selections = response.json()["recent_selections"]
    assert len(selections) == 5
    assert [item["client"]["name"] for item in selections] == [
        "Cliente 0", "Cliente 1", "Cliente 2", "Cliente 3", "Cliente 4",
    ]
    assert selections[0]["selected_count"] == 2
    assert selections[0]["selection_started_at"] == expected_started_at.isoformat()
    assert "Cliente de outro tenant" not in response.text
    assert "Galeria secreta" not in response.text


@pytest.fixture
def admin_api(tenant_db, monkeypatch):
    owner_tenant, tenant = Tenant(), Tenant()
    tenant_db.add_all([owner_tenant, tenant])
    tenant_db.flush()
    platform_owner = AdminUser(
        email="platform-owner@example.test",
        password_hash="synthetic",
        totp_secret="synthetic",
        email_verified=True,
    )
    platform_owner.tenant_memberships.append(TenantAdmin(tenant_id=owner_tenant.id))
    tenant_db.add(platform_owner)
    tenant_db.flush()
    tenant_db.add(PlatformOwner(
        singleton=1,
        admin_user_id=platform_owner.id,
        authorization_reference="synthetic-producer-test",
    ))
    tenant_db.add_all([
        TenantCreditWallet(tenant_id=owner_tenant.id, mode="unmetered"),
        TenantCreditWallet(tenant_id=tenant.id, mode="finite"),
    ])
    admin = AdminUser(email="admin@example.test", password_hash="synthetic", totp_secret="synthetic", email_verified=True)
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    tenant_db.add(admin)
    tenant_db.flush()
    tenant_db.add(AuthSession(role="admin", subject_id=admin.id, tenant_id=tenant.id, admin_subject_id=admin.id,
                             token_hash=auth.token_hash("synthetic-session"),
                             expires_at=auth.now() + timedelta(days=1)))
    tenant_db.commit()
    grant_credits(
        tenant_db, platform_owner.id, tenant.id, 10,
        "synthetic-producer-test", "synthetic upload allowance",
    )
    tenant_db.commit()
    factory = sessionmaker(bind=tenant_db.bind, expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    with TestClient(main.app) as client:
        client.cookies.set("markina_session", "synthetic-session")
        yield client, tenant, admin


def test_origem_recebe_contexto_e_edicao_preserva_proprietario(tenant_db, admin_api):
    client, tenant, admin = admin_api
    response = client.post("/admin/parent-galleries", json={"name": "Origem",
                           "tenant_id": str(uuid4())}, headers={"X-Tenant-ID": str(uuid4())})
    assert response.status_code == 201, response.text
    parent_id = UUID(response.json()["id"])
    parent = tenant_db.get(ParentGallery, parent_id)
    assert parent.tenant_id == tenant.id
    response = client.patch(f"/admin/parent-galleries/{parent_id}/settings",
                            json={"name": "Editada", "tenant_id": str(uuid4())})
    assert response.status_code == 422
    tenant_db.refresh(parent)
    assert parent.name == "Origem" and parent.tenant_id == tenant.id
    response = client.patch(f"/admin/parent-galleries/{parent_id}/settings", json={"name": "Editada"})
    assert response.status_code == 200, response.text
    tenant_db.refresh(parent)
    assert parent.id == parent_id and parent.tenant_id == tenant.id and parent.name == "Editada"
    admin.tenant_memberships[0].active = False
    tenant_db.commit()
    assert client.patch(f"/admin/parent-galleries/{parent_id}/settings",
                        json={"name": "Recusada"}).status_code == 403
    tenant_db.refresh(parent)
    assert parent.name == "Editada" and parent.tenant_id == tenant.id


def test_privada_herda_origem_e_reusa_membros(tenant_db, admin_api):
    _, tenant, admin = admin_api
    parent = ParentGallery(name="Origem", tenant_id=tenant.id)
    members = [Client(tenant_id=tenant.id, full_name=f"Cliente {i}", phone_e164=f"+551199999999{i}") for i in range(2)]
    tenant_db.add_all([parent, *members])
    tenant_db.commit()
    first = ensure_private_membership(tenant_db, parent=parent, client=members[0], actor_admin_id=admin.id)
    shared = ensure_private_membership(tenant_db, parent=parent, client=members[1], gallery=first.gallery)
    retry = ensure_private_membership(tenant_db, parent=parent, client=members[0])
    tenant_db.commit()
    assert shared.gallery.id == first.gallery.id == retry.gallery.id
    assert first.gallery.tenant_id == parent.tenant_id == tenant.id
    assert not retry.gallery_created and not retry.membership_created
    tenant.status = "suspended"
    tenant_db.commit()
    with pytest.raises(ClientIdentityConflict):
        ensure_private_membership(tenant_db, parent=parent, client=members[0])
    assert tenant_db.get(DerivedGallery, first.gallery.id).tenant_id == tenant.id


@pytest.mark.parametrize("private", [False, True])
def test_foto_de_pasta_herda_origem_e_retry_preserva_id(tenant_db, admin_api, private):
    client, tenant, _ = admin_api
    parent = ParentGallery(name="Upload", tenant_id=tenant.id)
    tenant_db.add(parent)
    tenant_db.flush()
    gallery = None
    if private:
        member = Client(tenant_id=tenant.id, full_name="Cliente", phone_e164="+5511999999999")
        tenant_db.add(member)
        tenant_db.flush()
        gallery = ensure_private_membership(tenant_db, parent=parent, client=member).gallery
    folder = PhotoFolder(tenant_id=tenant.id, name="Lote", parent_gallery_id=parent.id,
                         derived_gallery_id=gallery.id if gallery else None)
    tenant_db.add(folder)
    tenant_db.commit()
    fingerprint = sha256(b"synthetic test JPEG identity").hexdigest()
    key = (
        f"private/{gallery.id}/{folder.id}/{fingerprint}.jpg"
        if gallery else f"{parent.id}/{folder.id}/{fingerprint}.jpg"
    )
    payload = {"filename": "fake.jpg", "storage_key": key, "tenant_id": str(uuid4())}
    route = f"/admin/photo-folders/{folder.id}/photos"
    first, retry = client.post(route, json=payload), client.post(route, json=payload)
    assert first.status_code == retry.status_code == 201, (first.text, retry.text)
    assert first.json()["id"] == retry.json()["id"]
    photo = tenant_db.get(PhotoAsset, UUID(first.json()["id"]))
    assert photo.tenant_id == tenant.id and photo.parent_gallery_id == parent.id
    assert photo.storage_key == f"tenants/{tenant.id}/{key}" and photo.derived_gallery_id == (gallery.id if gallery else None)


def test_capa_herda_origem_e_idempotencia(tenant_db, admin_api):
    client, tenant, _ = admin_api
    parent = ParentGallery(name="Capa", tenant_id=tenant.id)
    tenant_db.add(parent)
    tenant_db.commit()
    route = f"/admin/parent-galleries/{parent.id}/cover-photos"
    payload = {"filename": "cover.jpg", "idempotency_key": "synthetic-cover-key"}
    assert client.post(route, json={**payload, "tenant_id": str(uuid4())}).status_code == 422
    first, retry = client.post(route, json=payload), client.post(route, json=payload)
    assert first.status_code == retry.status_code == 201, (first.text, retry.text)
    assert first.json()["id"] == retry.json()["id"]
    photo = tenant_db.get(PhotoAsset, UUID(first.json()["id"]))
    assert photo.tenant_id == tenant.id and photo.parent_gallery_id == parent.id
