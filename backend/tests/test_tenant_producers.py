"""Propriedade resolvida no servidor; dados e sessões exclusivamente sintéticos."""

from datetime import timedelta
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
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    Tenant,
    TenantAdmin,
)
from app.private_membership import ensure_private_membership
from app.tenancy import TenantContextError
from tests.test_tenant_foundation import tenant_db as foundation_tenant_db

tenant_db = foundation_tenant_db


@pytest.fixture
def admin_api(tenant_db, monkeypatch):
    tenant = Tenant()
    tenant_db.add(tenant)
    tenant_db.flush()
    admin = AdminUser(email="admin@example.test", password_hash="synthetic", totp_secret="synthetic")
    admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    tenant_db.add(admin)
    tenant_db.flush()
    tenant_db.add(AuthSession(role="admin", subject_id=admin.id,
                             token_hash=auth.token_hash("synthetic-session"),
                             expires_at=auth.now() + timedelta(days=1)))
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
    members = [Client(full_name=f"Cliente {i}", phone_e164=f"+551199999999{i}") for i in range(2)]
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
    with pytest.raises(TenantContextError):
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
        member = Client(full_name="Cliente", phone_e164="+5511999999999")
        tenant_db.add(member)
        tenant_db.flush()
        gallery = ensure_private_membership(tenant_db, parent=parent, client=member).gallery
    folder = PhotoFolder(name="Lote", parent_gallery_id=parent.id,
                         derived_gallery_id=gallery.id if gallery else None)
    tenant_db.add(folder)
    tenant_db.commit()
    key = f"private/{gallery.id}/fake.jpg" if gallery else "synthetic/fake.jpg"
    payload = {"filename": "fake.jpg", "storage_key": key, "tenant_id": str(uuid4())}
    route = f"/admin/photo-folders/{folder.id}/photos"
    first, retry = client.post(route, json=payload), client.post(route, json=payload)
    assert first.status_code == retry.status_code == 201, (first.text, retry.text)
    assert first.json()["id"] == retry.json()["id"]
    photo = tenant_db.get(PhotoAsset, UUID(first.json()["id"]))
    assert photo.tenant_id == tenant.id and photo.parent_gallery_id == parent.id
    assert photo.storage_key == key and photo.derived_gallery_id == (gallery.id if gallery else None)


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
