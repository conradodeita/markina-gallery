"""Histórico por pasta em contas sintéticas; nenhum arquivo ou provedor real."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import photographer_credits as credits
from app.auth import (
    ParentGallery,
    PhotoAsset,
    PhotoCreditOperationEvent,
    PhotoFolder,
    PhotographerCreditEntry,
)
from app.credit_history import folder_entry_page, history_page, photo_history_context
from tests.test_photographer_credits import create_accounts, create_photo
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def test_proveniencia_da_reserva_preserva_pasta_apos_retry_rename_e_remocao(client_db):
    owner_tenant, tenant, owner, _ = create_accounts(client_db)
    photo = create_photo(client_db, tenant.id)
    folder = client_db.get(PhotoFolder, photo.folder_id)
    gallery = client_db.get(ParentGallery, photo.parent_gallery_id)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "history-grant", "synthetic")
    fingerprint = credits.fingerprint_from_storage_key(photo.storage_key)
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    client_db.commit()
    reserved = client_db.scalar(select(PhotoCreditOperationEvent).where(
        PhotoCreditOperationEvent.operation_id == operation.id,
        PhotoCreditOperationEvent.event_type == "reserved",
    ))
    original = dict(reserved.details)
    assert original["folder_id_snapshot"] == str(folder.id)
    assert original["folder_name_snapshot"] == folder.name
    assert original["parent_gallery_id_snapshot"] == str(gallery.id)
    assert original["parent_gallery_name_snapshot"] == gallery.name
    assert original["source_entry_id"]
    assert photo_history_context(client_db, owner_tenant.id, photo.id) == {}

    folder.name = "Pasta renomeada"
    client_db.commit()
    retry = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    assert retry.id == operation.id
    assert len(list(client_db.scalars(select(PhotoCreditOperationEvent).where(
        PhotoCreditOperationEvent.operation_id == operation.id,
        PhotoCreditOperationEvent.event_type == "reserved",
    )))) == 1
    credits.consume_photo_credit(client_db, tenant.id, photo.id, fingerprint)
    client_db.commit()
    assert reserved.details == original

    operation.photo_asset_id = None
    client_db.flush()
    client_db.delete(photo)
    client_db.flush()
    client_db.delete(folder)
    client_db.commit()
    assert reserved.details == original
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    summary = next(item for item in history_page(client_db, tenant.id)["items"] if item["type"] == "folder_upload")
    assert summary["photo_count"] == 1 and summary["delta"] == -1
    assert summary["source_reference"] == original["folder_id_snapshot"]
    assert summary["description"] == original["folder_name_snapshot"]
    assert len(folder_entry_page(client_db, tenant.id, folder.id)["items"]) == 1


def consume(db, tenant_id, photo):
    fingerprint = credits.fingerprint_from_storage_key(photo.storage_key)
    credits.reserve_photo_credit(db, tenant_id, photo.id, photo.storage_key, fingerprint)
    credits.consume_photo_credit(db, tenant_id, photo.id, fingerprint)
    db.flush()


def next_photo(db, photo):
    duplicate = PhotoAsset(
        tenant_id=photo.tenant_id, parent_gallery_id=photo.parent_gallery_id, folder_id=photo.folder_id,
        filename="synthetic.jpg", storage_key=photo.storage_key[:-4] + f"-{uuid4()}.jpg",
    )
    db.add(duplicate)
    db.flush()
    return duplicate


def test_resume_pasta_com_mais_de_30_fotos_sem_truncar_e_pagina_snapshot(client_db):
    owner_tenant, tenant, owner, _ = create_accounts(client_db)
    first = create_photo(client_db, tenant.id)
    second = create_photo(client_db, tenant.id)  # pasta homônima, outra galeria
    credits.grant_credits(client_db, owner.id, tenant.id, 50, "history-main", "synthetic")
    credits.grant_credits(client_db, owner.id, tenant.id, 5, "history-extra", "synthetic-extra")
    consume(client_db, tenant.id, first)
    for _ in range(35):
        consume(client_db, tenant.id, next_photo(client_db, first))
    consume(client_db, tenant.id, second)
    consume(client_db, tenant.id, next_photo(client_db, second))
    client_db.commit()
    assert len(credits.list_entries(client_db, tenant.id)) == 30
    full = history_page(client_db, tenant.id)
    folders = {item["folder_id"]: item for item in full["items"] if item["type"] == "folder_upload"}
    assert len(full["items"]) == 4 and len(folders) == 2
    assert folders[str(first.folder_id)]["photo_count"] == 36
    assert folders[str(first.folder_id)]["delta"] == -36
    assert folders[str(second.folder_id)]["photo_count"] == 2
    assert sum(item["delta"] for item in full["items"]) == 17
    page = history_page(client_db, tenant.id, limit=1)
    assert page["has_more"]
    consume(client_db, tenant.id, next_photo(client_db, first))
    client_db.commit()
    pages = page["items"][:]
    for offset in range(1, 4):
        pages.extend(history_page(client_db, tenant.id, limit=1, offset=offset, as_of=page["as_of"])["items"])
    assert len({item["id"] for item in pages}) == 4
    assert next(item for item in pages if item["folder_id"] == str(first.folder_id))["photo_count"] == 36
    refreshed = history_page(client_db, tenant.id)
    assert next(item for item in refreshed["items"] if item["folder_id"] == str(first.folder_id))["photo_count"] == 37
    detail = folder_entry_page(client_db, tenant.id, first.folder_id, as_of=page["as_of"])
    assert len(detail["items"]) == 20 and detail["has_more"]
    rest = folder_entry_page(client_db, tenant.id, first.folder_id, offset=20, as_of=detail["as_of"])
    assert len(rest["items"]) == 16 and not rest["has_more"]
    assert len({item["id"] for item in detail["items"] + rest["items"]}) == 36
    assert history_page(client_db, owner_tenant.id)["items"] == []
    with pytest.raises(HTTPException) as denied:
        folder_entry_page(client_db, owner_tenant.id, first.folder_id)
    assert denied.value.status_code == 404


def test_legado_sem_proveniencia_fica_individual_sem_inferir_storage_key(client_db, monkeypatch):
    _, tenant, owner, _ = create_accounts(client_db)
    photo = create_photo(client_db, tenant.id)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "legacy-history", "synthetic")
    monkeypatch.setattr(credits, "photo_history_context", lambda *args: {})
    consume(client_db, tenant.id, photo)
    client_db.commit()
    assert any(item["type"] == "folder_upload" for item in history_page(client_db, tenant.id)["items"])
    operation = client_db.scalar(select(credits.PhotoCreditOperation).where(
        credits.PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    operation.photo_asset_id = None
    client_db.flush()
    client_db.delete(photo)
    client_db.commit()
    items = history_page(client_db, tenant.id)["items"]
    unknown = next(item for item in items if item["type"] == "upload_consumption")
    assert unknown["folder_unidentified"] and unknown["folder_id"] is None
    assert unknown["photo_count"] == 1 and unknown["delta"] == -1


def test_duas_compras_do_mesmo_pacote_continuam_individualizadas(client_db):
    _, tenant, owner, photographer = create_accounts(client_db)
    package = credits.create_package(
        client_db, owner.id, name="Pacote sintético", description=None, credit_quantity=12,
        price_cents=1500, currency_code="BRL", active=True,
    )
    references = {str(uuid4()), str(uuid4())}
    for reference in references:
        client_db.add(PhotographerCreditEntry(
            tenant_id=tenant.id, entry_type="purchase", delta=12,
            idempotency_key="history-purchase:" + reference, source_reference=reference,
            package_id=package.id, actor_admin_id=photographer.id,
            description="Compra sintética, sem provedor",
        ))
    client_db.commit()
    page = history_page(client_db, tenant.id)
    assert len(page["items"]) == 2
    assert {item["source_reference"] for item in page["items"]} == references
    assert all(item["type"] == "purchase" and item["photo_count"] == 0 for item in page["items"])


def test_history_http_limites_contexto_e_owner_only(client_db, monkeypatch):
    owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    photo = create_photo(client_db, tenant.id)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "history-api", "synthetic")
    consume(client_db, tenant.id, photo)
    client_db.commit()
    from app import main

    def db_override():
        yield client_db

    main.app.dependency_overrides[main.db_session] = db_override
    monkeypatch.setattr(main, "directory_tenant_id", lambda *args: tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda *args: SimpleNamespace(subject_id=photographer.id))
    try:
        client = TestClient(main.app)
        path = f"/admin/credits/history/folders/{photo.folder_id}"
        assert client.get(path).status_code == 200
        page = client.get("/admin/credits/history", params={"limit": 1})
        assert page.status_code == 200 and page.json()["has_more"]
        assert page.headers["cache-control"] == "private, no-store"
        assert client.get(path, params={"limit": 31}).status_code == 422
        assert client.get(path, params={"offset": -1}).status_code == 422
        assert client.get(path, params={"as_of": "invalid"}).status_code == 422
        owner_path = f"/admin/platform/credit-tenants/{tenant.id}/history"
        assert client.get(owner_path).status_code == 403
        monkeypatch.setattr(main, "require_admin", lambda *args: SimpleNamespace(subject_id=owner.id))
        assert client.get(owner_path).status_code == 200
        assert client.get(owner_path + f"/folders/{photo.folder_id}").status_code == 200
        monkeypatch.setattr(main, "directory_tenant_id", lambda *args: owner_tenant.id)
        for offset in (0, 20):
            assert client.get(path, params={"offset": offset}).status_code == 404
    finally:
        main.app.dependency_overrides.pop(main.db_session, None)
