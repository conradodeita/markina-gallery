from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import (
    Client,
    DerivedGallery,
    DerivedGalleryMembership,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    SessionLocal,
    Tenant,
)
from app.main import app
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.test_notification_settings import authenticated, isolated_schema  # noqa: F401


def make_overview():
    with SessionLocal() as db:
        parent = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Origem sintética")
        other = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Outra origem")
        owner = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Ana Principal", phone_e164="+5511999999001")
        shared = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Bruna Compartilhada", phone_e164="+5511999999002")
        blocked = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Carla Bloqueada", phone_e164="+5511999999003")
        unlinked = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Dora Desvinculada", phone_e164="+5511999999004")
        db.add_all([parent, other, owner, shared, blocked, unlinked])
        db.flush()
        private = DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, client_id=owner.id, name="Ensaio Ana")
        other_private = DerivedGallery(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=other.id, client_id=owner.id, name="Ensaio de outra origem"
        )
        db.add_all([private, other_private])
        db.flush()
        public_folder = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, name="Pública", position=0)
        cover_folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, name="Capas", purpose="cover_assets", position=1
        )
        private_folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, derived_gallery_id=private.id,
            name="Retratos privados", status="released", position=0,
        )
        other_folder = PhotoFolder(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=other.id, derived_gallery_id=other_private.id,
            name="Privada de outra origem", position=0,
        )
        db.add_all([public_folder, cover_folder, private_folder, other_folder])
        for person, state in [(owner, "active"), (shared, "active"),
                              (blocked, "blocked"), (unlinked, "unlinked")]:
            db.add(DerivedGalleryMembership(
                tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, derived_gallery_id=private.id,
                client_id=person.id, status=state,
            ))
        db.flush()
        db.add(PhotoAsset(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent.id, derived_gallery_id=private.id,
            folder_id=private_folder.id, filename="sintetica.jpg",
            storage_key=f"private/{private.id}/sintetica.jpg", available=False,
        ))
        db.commit()
        return parent.id, other.id, private.id, owner.id, shared.id, private_folder.id


def test_overview_is_admin_only_and_limited_to_requested_origin():
    parent, other, private, owner, shared, folder = make_overview()
    path = f"/admin/parent-galleries/{parent}/private-folders"
    assert TestClient(app).get(path).status_code == 403
    assert authenticated("client").get(path).status_code == 403
    browser = authenticated()
    response = browser.get(path)
    assert response.status_code == 200
    assert response.json() == {"galleries": [{
        "id": str(private), "name": "Ensaio Ana",
        "owner": {"id": str(owner), "name": "Ana Principal"},
        "active_members": [
            {"id": str(owner), "name": "Ana Principal"},
            {"id": str(shared), "name": "Bruna Compartilhada"},
        ],
        "folders": [{"id": str(folder), "name": "Retratos privados", "status": "released",
                     "position": 0, "photo_count": 1}],
    }]}
    # A consulta da outra origem não inclui os nomes/pastas desta origem.
    other_response = browser.get(f"/admin/parent-galleries/{other}/private-folders")
    assert other_response.status_code == 200
    assert "Retratos privados" not in other_response.text
    assert "Bruna Compartilhada" not in other_response.text
    with SessionLocal() as db:
        foreign_tenant_id = uuid4()
        db.add(Tenant(id=foreign_tenant_id, status="active"))
        db.flush()
        foreign_tenant_parent = ParentGallery(tenant_id=foreign_tenant_id, name="Galeria de outro tenant")
        db.add(foreign_tenant_parent)
        db.commit()
        foreign_tenant_parent_id = foreign_tenant_parent.id
    assert browser.get(
        f"/admin/parent-galleries/{foreign_tenant_parent_id}/private-folders"
    ).status_code == 404
    assert browser.get(f"/admin/parent-galleries/{uuid4()}/private-folders").status_code == 404
    # A lista pública não recebe pastas privadas em consequência desta leitura.
    public = browser.get(f"/admin/parent-galleries/{parent}/folders")
    assert [item["name"] for item in public.json()["folders"]] == ["Pública"]


def test_overview_keeps_owner_without_active_members_and_omits_empty_galleries():
    parent, _, private, _, _, _ = make_overview()
    with SessionLocal() as db:
        for member in db.scalars(select(DerivedGalleryMembership)):
            member.status = "blocked"
        empty_origin = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Sem privadas")
        empty_owner = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Sem pasta", phone_e164="+5511999999005")
        db.add_all([empty_origin, empty_owner])
        db.flush()
        db.add(DerivedGallery(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent, client_id=empty_owner.id, name="Sem pasta"))
        db.commit()
        empty_id = empty_origin.id
    browser = authenticated()
    result = browser.get(f"/admin/parent-galleries/{parent}/private-folders").json()["galleries"]
    assert len(result) == 1
    assert result[0]["id"] == str(private)
    assert result[0]["owner"]["name"] == "Ana Principal"
    assert result[0]["active_members"] == []
    assert browser.get(f"/admin/parent-galleries/{empty_id}/private-folders").json() == {
        "galleries": []
    }
