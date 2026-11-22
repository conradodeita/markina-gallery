"""Testes sintéticos de ledger, origem FIFO e autorização global."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
from threading import Barrier
from types import SimpleNamespace
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app import photographer_credits as credits
from app.auth import (
    AdminUser,
    AuditEvent,
    Client,
    InstallationOperator,
    ParentGallery,
    PhotoAsset,
    PhotoCreditOperation,
    PhotoCreditOperationEvent,
    PhotoFolder,
    PhotographerCreditAllocationEvent,
    PhotographerCreditEntry,
    PhotographerCreditPackage,
    Tenant,
    TenantAdmin,
    TenantCreditWallet,
    now,
)
from app.system_monitor.models import MonitorGrant, PlatformOwner
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db


def create_accounts(db):
    owner_tenant, tenant = Tenant(), Tenant()
    db.add_all([owner_tenant, tenant])
    db.flush()
    owner = AdminUser(
        email="platform-owner@example.test", password_hash="synthetic", totp_secret="synthetic",
        email_verified=True,
    )
    photographer = AdminUser(
        email="photographer@example.test", password_hash="synthetic", totp_secret="synthetic",
        email_verified=True,
    )
    owner.tenant_memberships.append(TenantAdmin(tenant_id=owner_tenant.id))
    photographer.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    db.add_all([owner, photographer])
    db.flush()
    db.add_all([
        PlatformOwner(singleton=1, admin_user_id=owner.id, authorization_reference="synthetic"),
        TenantCreditWallet(tenant_id=owner_tenant.id, mode="unmetered"),
        TenantCreditWallet(tenant_id=tenant.id, mode="finite"),
    ])
    db.flush()
    return owner_tenant, tenant, owner, photographer


def create_photo(db, tenant_id, *, purpose="content"):
    gallery = ParentGallery(tenant_id=tenant_id, name="Galeria sintética", payment_required=False)
    db.add(gallery)
    db.flush()
    folder = PhotoFolder(
        tenant_id=tenant_id,
        parent_gallery_id=gallery.id,
        name="Conteúdo sintético",
        purpose=purpose,
        status="preparing",
    )
    db.add(folder)
    db.flush()
    photo = PhotoAsset(
        tenant_id=tenant_id,
        parent_gallery_id=gallery.id,
        folder_id=folder.id,
        filename="synthetic.jpg",
        storage_key=(
            f"tenants/{tenant_id}/{gallery.id}/{folder.id}/"
            f"{sha256(jpeg_payload()).hexdigest()}.jpg"
        ),
    )
    db.add(photo)
    db.flush()
    return photo


def jpeg_payload():
    payload = BytesIO()
    Image.new("RGB", (1200, 800), (12, 34, 56)).save(payload, "JPEG")
    return payload.getvalue()


def upload_request(payload, *, facial_reindex=False):
    from starlette.requests import Request

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request({
        "type": "http",
        "method": "PUT",
        "path": "/admin/photo-assets/source",
        "headers": [
            (b"content-type", b"image/jpeg"),
            *([(b"x-facial-reindex", b"true")] if facial_reindex else []),
        ],
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test", 1234),
    }, receive)


def configure_upload_route(monkeypatch, tenant_id, tmp_path):
    from app import main
    from app.facial import lifecycle

    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "false")
    monkeypatch.setattr(main, "directory_tenant_id", lambda _db, _request: tenant_id)
    monkeypatch.setattr(main, "require_admin", lambda _request: None)
    monkeypatch.setattr(main, "require_parent_gallery_mutable", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "enqueue_derivatives", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lifecycle, "admit_source", lambda *_args, **_kwargs: None)
    return main, lifecycle


def test_only_platform_owner_can_manage_packages_and_grant(client_db):
    owner_tenant, _, owner, photographer = create_accounts(client_db)
    package = credits.create_package(
        client_db, owner.id, name="Pacote explícito", description=None, credit_quantity=10,
        price_cents=None, currency_code=None, active=False,
    )
    client_db.commit()
    assert package.active is False and package.price_cents is None
    assert credits.list_packages(client_db, owner.id)[0]["id"] == str(package.id)
    with pytest.raises(HTTPException) as denied:
        credits.create_package(
            client_db, photographer.id, name="Negado", description=None, credit_quantity=1,
            price_cents=None, currency_code=None, active=False,
        )
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as unmetered:
        credits.grant_credits(client_db, owner.id, owner_tenant.id, 1, "grant-owner", "synthetic")
    assert unmetered.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry)) == 0
    owner_wallet = credits.wallet_snapshot(client_db, owner_tenant.id)
    assert owner_wallet["mode"] == "unmetered"
    assert owner_wallet["available_credits"] is None
    assert owner_wallet["can_upload_content"] is True


def test_photographer_catalog_returns_only_active_priced_packages(client_db, monkeypatch):
    _, tenant, owner, photographer = create_accounts(client_db)
    active = credits.create_package(
        client_db, owner.id, name="Pacote ativo", description="Descrição configurada",
        credit_quantity=20, price_cents=2500, currency_code="BRL", active=True,
    )
    credits.create_package(
        client_db, owner.id, name="Pacote inativo", description=None,
        credit_quantity=5, price_cents=None, currency_code=None, active=False,
    )
    client_db.commit()

    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from app import main

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(
        subject_id=photographer.id, tenant_id=tenant.id,
    ))
    request = Request({
        "type": "http", "method": "GET", "path": "/admin/credits/packages",
        "headers": [], "query_string": b"", "scheme": "http", "server": ("test", 80),
        "client": ("test", 1234),
    })

    response = Response()
    result = main.admin_active_credit_packages(request, response, client_db)

    assert response.headers["Cache-Control"] == "private, no-store"
    assert [item["id"] for item in result["items"]] == [str(active.id)]
    assert result["items"][0]["price_cents"] == 2500
    assert result["items"][0]["currency_code"] == "BRL"


def test_photographer_catalog_denies_owner_and_inactive_tenant(client_db, monkeypatch):
    owner_tenant, tenant, owner, photographer = create_accounts(client_db)

    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from app import main

    request = Request({
        "type": "http", "method": "GET", "path": "/admin/credits/packages",
        "headers": [], "query_string": b"", "scheme": "http", "server": ("test", 80),
        "client": ("test", 1234),
    })
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(
        subject_id=owner.id, tenant_id=owner_tenant.id,
    ))
    with pytest.raises(HTTPException) as owner_denied:
        main.admin_active_credit_packages(request, Response(), client_db)
    assert owner_denied.value.status_code == 403

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(
        subject_id=photographer.id, tenant_id=owner_tenant.id,
    ))
    with pytest.raises(HTTPException) as tenant_mismatch:
        main.admin_active_credit_packages(request, Response(), client_db)
    assert tenant_mismatch.value.status_code == 403

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(
        subject_id=photographer.id, tenant_id=tenant.id,
    ))
    client_db.get(Tenant, tenant.id).status = "suspended"
    client_db.commit()
    with pytest.raises(HTTPException) as inactive_denied:
        main.admin_active_credit_packages(request, Response(), client_db)
    assert inactive_denied.value.status_code == 403


def test_grant_idempotency_fifo_consumption_and_grant_specific_revocation(client_db):
    _, tenant, owner, photographer = create_accounts(client_db)
    first = credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-a", "synthetic-a")
    first.created_at = now() - timedelta(days=1)
    client_db.commit()
    replay = credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-a", "synthetic-a")
    assert replay.id == first.id
    second = credits.grant_credits(client_db, owner.id, tenant.id, 2, "grant-b", "synthetic-b")
    client_db.commit()

    photo = create_photo(client_db, tenant.id)
    fingerprint = "a" * 64
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    assert operation is not None and operation.status == "reserved"
    repeated = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    assert repeated is not None and repeated.id == operation.id
    client_db.commit()

    consumption = credits.consume_photo_credit(
        client_db, tenant.id, photo.id, fingerprint, actor_admin_id=photographer.id,
    )
    repeated_consumption = credits.consume_photo_credit(
        client_db, tenant.id, photo.id, fingerprint, actor_admin_id=photographer.id,
    )
    assert consumption is not None and repeated_consumption is not None
    assert consumption.id == repeated_consumption.id
    assert consumption.source_entry_id == first.id
    client_db.commit()
    operation_events = list(client_db.scalars(select(PhotoCreditOperationEvent.event_type).where(
        PhotoCreditOperationEvent.operation_id == operation.id,
    )))
    assert operation_events.count("source_durable") == 1
    assert operation_events.count("consumed") == 1
    snapshot = credits.wallet_snapshot(client_db, tenant.id)
    assert snapshot["available_credits"] == 3
    assert snapshot["recent_consumed_credits"] == 1
    assert snapshot["recent_period_days"] == 30
    assert snapshot["can_upload_content"] is True

    revoked = credits.revoke_grant(
        client_db, owner.id, tenant.id, first.id, 1, "revoke-a", "synthetic-revoke",
    )
    client_db.commit()
    assert revoked.source_entry_id == first.id and revoked.delta == -1
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 2
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] != credits.wallet_snapshot(
        client_db, owner.tenant_memberships[0].tenant_id,
    )["available_credits"]
    with pytest.raises(HTTPException) as too_much:
        credits.revoke_grant(
            client_db, owner.id, tenant.id, first.id, 1, "revoke-a-again", "synthetic-revoke",
        )
    assert too_much.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditAllocationEvent).where(
        PhotographerCreditAllocationEvent.source_entry_id == second.id,
    )) == 0


def test_snapshot_recent_consumption_uses_rolling_thirty_day_window(client_db):
    _, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "recent-window", "synthetic")

    recent_photo = create_photo(client_db, tenant.id)
    credits.reserve_photo_credit(client_db, tenant.id, recent_photo.id, recent_photo.storage_key, "a" * 64)
    credits.consume_photo_credit(
        client_db, tenant.id, recent_photo.id, "a" * 64, actor_admin_id=photographer.id,
    )
    client_db.commit()

    old_photo = create_photo(client_db, tenant.id)
    old_time = now() - timedelta(days=31)
    old_operation = credits.reserve_photo_credit(
        client_db, tenant.id, old_photo.id, old_photo.storage_key, "b" * 64,
    )

    def age_old_consumption(session, _flush_context, _instances):
        for entry in session.new:
            if isinstance(entry, PhotographerCreditEntry) and entry.operation_id == old_operation.id:
                entry.created_at = old_time

    event.listen(client_db, "before_flush", age_old_consumption)
    try:
        credits.consume_photo_credit(
            client_db, tenant.id, old_photo.id, "b" * 64, actor_admin_id=photographer.id,
        )
        client_db.commit()
    finally:
        event.remove(client_db, "before_flush", age_old_consumption)

    snapshot = credits.wallet_snapshot(client_db, tenant.id)
    assert snapshot["available_credits"] == 0
    assert snapshot["recent_consumed_credits"] == 1
    assert snapshot["recent_period_days"] == 30
    assert snapshot["can_upload_content"] is False


def test_pre_durable_failure_releases_only_its_fifo_reservation(client_db):
    _, tenant, owner, _photographer = create_accounts(client_db)
    grant = credits.grant_credits(client_db, owner.id, tenant.id, 1, "grant-release", "synthetic")
    client_db.commit()
    photo = create_photo(client_db, tenant.id)
    fingerprint = "b" * 64
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    client_db.commit()
    released = credits.release_photo_credit(
        client_db, tenant.id, photo.id, proven_pre_durable_failure=True,
    )
    assert released.status == "released"
    client_db.commit()
    assert credits._source_available(client_db, grant) == 1
    replay = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    assert replay is not None and replay.id == operation.id and replay.status == "reserved"
    with pytest.raises(HTTPException) as mismatch:
        credits.reserve_photo_credit(
            client_db, tenant.id, photo.id, photo.storage_key, "c" * 64,
        )
    assert mismatch.value.status_code == 409


def test_partial_upload_batch_consumes_only_the_stored_photo(client_db):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "partial-batch", "synthetic")
    stored_photo, blocked_photo = create_photo(client_db, tenant.id), create_photo(client_db, tenant.id)
    fingerprint = "e" * 64
    credits.reserve_photo_credit(
        client_db, tenant.id, stored_photo.id, stored_photo.storage_key, fingerprint,
    )
    client_db.commit()
    credits.consume_photo_credit(client_db, tenant.id, stored_photo.id, fingerprint)
    client_db.commit()

    with pytest.raises(HTTPException) as insufficient:
        credits.reserve_photo_credit(
            client_db, tenant.id, blocked_photo.id, blocked_photo.storage_key, "f" * 64,
        )
    assert insufficient.value.status_code == 409
    snapshot = credits.wallet_snapshot(client_db, tenant.id)
    assert snapshot["available_credits"] == 0
    assert snapshot["can_upload_content"] is False
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation)) == 1


def test_concurrent_reservations_cannot_use_the_same_credit(client_db):
    if client_db.get_bind().dialect.name != "postgresql":
        pytest.skip("concorrência de carteira requer PostgreSQL descartável")
    _, tenant, owner, _ = create_accounts(client_db)
    tenant_id = tenant.id
    credits.grant_credits(client_db, owner.id, tenant_id, 1, "concurrent-reserve", "synthetic")
    photos = [create_photo(client_db, tenant_id), create_photo(client_db, tenant_id)]
    identities = [(photo.id, photo.storage_key) for photo in photos]
    client_db.commit()
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    rendezvous = Barrier(2)

    def reserve_one(identity, fingerprint):
        with factory() as db:
            rendezvous.wait(timeout=10)
            try:
                operation = credits.reserve_photo_credit(
                    db, tenant_id, identity[0], identity[1], fingerprint,
                )
                db.commit()
                return operation.status
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda pair: reserve_one(*pair),
            [(identities[0], "1" * 64), (identities[1], "2" * 64)],
        ))

    assert outcomes.count("reserved") == 1
    assert outcomes.count(409) == 1
    client_db.expire_all()
    assert credits.wallet_snapshot(client_db, tenant_id)["available_credits"] == 0
    assert credits.wallet_snapshot(client_db, tenant_id)["reserved_credits"] == 1
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant_id,
        PhotoCreditOperation.status == "reserved",
    )) == 1


def test_upload_route_releases_only_when_storage_proves_source_absent(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    grant = credits.grant_credits(client_db, owner.id, tenant.id, 1, "upload-release", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)

    def fail_before_rename(*_args, **_kwargs):
        raise OSError("synthetic storage failure before rename")

    monkeypatch.setattr(lifecycle, "write_source", fail_before_rename)
    with pytest.raises(HTTPException) as failed:
        asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db))

    assert failed.value.status_code == 503
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "released"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    assert credits._source_available(client_db, grant) == 1
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 0


def test_upload_cancelled_while_receiving_body_releases_credit_reservation(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "cancelled-upload", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)

    from starlette.requests import Request

    async def cancelled_receive():
        raise asyncio.CancelledError()

    request = Request({
        "type": "http", "method": "PUT", "path": f"/admin/photo-assets/{photo.id}/source",
        "headers": [(b"content-type", b"image/jpeg")], "query_string": b"", "scheme": "http",
        "server": ("test", 80), "client": ("test", 1234),
    }, cancelled_receive)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main.import_photo_source(photo.id, request, client_db))

    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "released"
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditAllocationEvent).where(
        PhotographerCreditAllocationEvent.operation_id == operation.id,
        PhotographerCreditAllocationEvent.event_type == "released",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 0


def test_upload_body_must_match_content_addressed_photo_identity(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "upload-fingerprint", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    different = BytesIO()
    Image.new("RGB", (1200, 800), (80, 4, 120)).save(different, "JPEG")

    with pytest.raises(HTTPException) as mismatch:
        asyncio.run(main.import_photo_source(photo.id, upload_request(different.getvalue()), client_db))

    assert mismatch.value.status_code == 409
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "released"
    assert not main.safe_source_path(photo).exists()
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 0


def test_unmetered_content_upload_still_matches_registered_fingerprint(
    client_db, monkeypatch, tmp_path,
):
    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    photo = create_photo(client_db, owner_tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, owner_tenant.id, tmp_path)
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=owner.id))
    different = BytesIO()
    Image.new("RGB", (1200, 800), (80, 4, 120)).save(different, "JPEG")

    with pytest.raises(HTTPException) as mismatch:
        asyncio.run(main.import_photo_source(photo.id, upload_request(different.getvalue()), client_db))

    assert mismatch.value.status_code == 409
    assert not main.safe_source_path(photo).exists()
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation)) == 0
    assert asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db)) == {
        "status": "queued",
    }
    assert main.safe_source_path(photo).read_bytes() == jpeg_payload()
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation)) == 0


def test_upload_rechecks_archive_state_after_body_before_durable_write(
    client_db, monkeypatch, tmp_path,
):
    from app.auth import MediaArchiveCycle

    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "archive-race-upload", "synthetic")
    photo = create_photo(client_db, tenant.id)
    parent_id, folder_id = photo.parent_gallery_id, photo.folder_id
    client_db.commit()
    main, lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    real_reader = main.read_bounded_body

    async def archive_while_body_is_read(request, **kwargs):
        client_db.add(MediaArchiveCycle(
            tenant_id=tenant.id,
            parent_gallery_id=parent_id,
            folder_id=folder_id,
            cycle_number=1,
            state="archived",
        ))
        client_db.commit()
        return await real_reader(request, **kwargs)

    def forbidden_write(*_args, **_kwargs):
        pytest.fail("A fonte não pode ser gravada após o arquivo da pasta.")

    monkeypatch.setattr(main, "read_bounded_body", archive_while_body_is_read)
    monkeypatch.setattr(lifecycle, "write_source", forbidden_write)
    lock_order = []

    def record_gallery_folder_locks(execute_state):
        statement = execute_state.statement
        if not execute_state.is_select or getattr(statement, "_for_update_arg", None) is None:
            return
        sql = str(statement).lower()
        if "from parent_gallery" in sql:
            lock_order.append("parent")
        elif "from photo_folder" in sql:
            lock_order.append("folder")

    event.listen(client_db, "do_orm_execute", record_gallery_folder_locks)
    try:
        with pytest.raises(HTTPException) as blocked:
            asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db))
    finally:
        event.remove(client_db, "do_orm_execute", record_gallery_folder_locks)

    assert blocked.value.status_code == 409
    assert "entrou em uma etapa de arquivo" in blocked.value.detail
    assert lock_order[:2] == ["parent", "folder"]
    assert not main.safe_source_path(photo).exists()
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "released"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1


@pytest.mark.parametrize(("pix_ready", "whatsapp_ready"), [(False, False), (False, True), (True, False)])
def test_new_website_upload_is_blocked_when_operational_channels_are_unavailable(
    client_db, monkeypatch, tmp_path, pix_ready, whatsapp_ready,
):
    _, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "blocked-upload", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
    monkeypatch.setitem(main.app.dependency_overrides, main.db_session, lambda: client_db)

    from app import photographer_onboarding

    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: object())
    monkeypatch.setattr(photographer_onboarding, "onboarding_status", lambda *_args, **_kwargs: {
        "email_verified": True, "profile_complete": True, "terms_accepted": True,
        "pix_configured": pix_ready, "whatsapp_configured": whatsapp_ready, "credits_available": True,
    })

    browser = TestClient(main.app)
    response = browser.put(
        f"/admin/photo-assets/{photo.id}/source",
        content=jpeg_payload(),
        headers={"content-type": "image/jpeg"},
    )
    browser.close()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "photographer_onboarding_required"
    assert response.json()["detail"]["pix_configured"] is pix_ready
    assert response.json()["detail"]["whatsapp_configured"] is whatsapp_ready
    assert client_db.scalar(select(PhotoCreditOperation.id).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    )) is None
    assert not main.safe_source_path(photo).exists()


def test_existing_upload_reservation_can_finish_after_onboarding_channels_change(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "accepted-upload", "synthetic")
    photo = create_photo(client_db, tenant.id)
    payload = jpeg_payload()
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, sha256(payload).hexdigest(),
    )
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))

    from app import photographer_onboarding

    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: object())
    monkeypatch.setattr(photographer_onboarding, "onboarding_status", lambda *_args, **_kwargs: {
        "email_verified": False, "profile_complete": False, "terms_accepted": False,
        "pix_configured": False, "whatsapp_configured": False, "credits_available": False,
    })

    assert asyncio.run(main.import_photo_source(photo.id, upload_request(payload), client_db)) == {
        "status": "queued",
    }

    client_db.refresh(operation)
    assert operation.status == "consumed"
    assert main.safe_source_path(photo).read_bytes() == payload
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    monkeypatch.setattr(
        main, "require_parent_gallery_mutable",
        lambda *_args, **_kwargs: client_db.get(ParentGallery, photo.parent_gallery_id),
    )
    replay = main.register_folder_photo_asset(
        photo.folder_id,
        main.PhotoAssetInput(filename=photo.filename, storage_key=photo.storage_key),
        upload_request(b""),
        client_db,
    )
    assert replay == {"id": str(photo.id), "duplicate": "true"}


def test_cross_tenant_source_upload_is_rejected_before_onboarding_exception(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, _owner, _photographer = create_accounts(client_db)
    foreign_tenant = Tenant()
    client_db.add(foreign_tenant)
    client_db.flush()
    foreign_wallet = TenantCreditWallet(tenant_id=foreign_tenant.id, mode="finite")
    client_db.add(foreign_wallet)
    photo = create_photo(client_db, foreign_tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)

    from app import photographer_onboarding

    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: object())
    monkeypatch.setattr(photographer_onboarding, "onboarding_status", lambda *_args, **_kwargs: {})

    with pytest.raises(HTTPException) as denied:
        asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db))

    assert denied.value.status_code == 404
    assert client_db.scalar(select(PhotoCreditOperation.id).where(
        PhotoCreditOperation.tenant_id == foreign_tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    )) is None


def test_new_photo_registration_gates_onboarding_and_credit_before_reservation(
    client_db, monkeypatch,
):
    _, tenant, owner, photographer = create_accounts(client_db)
    gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética", payment_required=False)
    client_db.add(gallery)
    client_db.flush()
    folder = PhotoFolder(
        tenant_id=tenant.id, parent_gallery_id=gallery.id,
        name="Conteúdo sintético", purpose="content", status="preparing",
    )
    client_db.add(folder)
    client_db.commit()

    from app import main

    monkeypatch.setattr(main, "directory_tenant_id", lambda *_args: tenant.id)
    monkeypatch.setattr(
        main, "require_admin",
        lambda *_args: SimpleNamespace(subject_id=photographer.id),
    )
    monkeypatch.setattr(main, "require_parent_gallery_mutable", lambda *_args, **_kwargs: gallery)
    fingerprint = sha256(jpeg_payload()).hexdigest()
    payload = main.PhotoAssetInput(
        filename="synthetic.jpg",
        storage_key=f"{gallery.id}/{folder.id}/{fingerprint}.jpg",
    )

    from app import photographer_onboarding

    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: object())
    monkeypatch.setattr(photographer_onboarding, "onboarding_status", lambda *_args, **_kwargs: {
        "email_verified": True,
        "profile_complete": False,
        "terms_accepted": False,
        "pix_configured": True,
        "whatsapp_configured": True,
        "credits_available": True,
    })
    with pytest.raises(HTTPException) as onboarding_blocked:
        main.register_folder_photo_asset(folder.id, payload, upload_request(b""), client_db)
    assert onboarding_blocked.value.status_code == 409
    assert onboarding_blocked.value.detail["code"] == "photographer_onboarding_required"
    assert onboarding_blocked.value.detail["profile_complete"] is False
    assert onboarding_blocked.value.detail["terms_accepted"] is False
    assert client_db.scalar(select(func.count()).select_from(PhotoAsset).where(
        PhotoAsset.tenant_id == tenant.id,
        PhotoAsset.folder_id == folder.id,
    )) == 0
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
    )) == 0

    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: None)

    with pytest.raises(HTTPException) as insufficient:
        main.register_folder_photo_asset(folder.id, payload, upload_request(b""), client_db)
    assert insufficient.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PhotoAsset).where(
        PhotoAsset.tenant_id == tenant.id,
        PhotoAsset.folder_id == folder.id,
    )) == 0
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
    )) == 0

    credits.grant_credits(client_db, owner.id, tenant.id, 1, "register-before-upload", "synthetic")
    registered = main.register_folder_photo_asset(folder.id, payload, upload_request(b""), client_db)
    photo_id = UUID(registered["id"])
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo_id,
    ))
    assert operation is not None and operation.status == "reserved"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    assert credits.wallet_snapshot(client_db, tenant.id)["reserved_credits"] == 1


def test_folder_photo_registration_rolls_back_after_credit_reservation_failure(
    client_db, monkeypatch,
):
    _, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "rollback-registration", "synthetic")
    gallery = ParentGallery(tenant_id=tenant.id, name="Galeria sintética", payment_required=False)
    client_db.add(gallery)
    client_db.flush()
    folder = PhotoFolder(
        tenant_id=tenant.id, parent_gallery_id=gallery.id,
        name="Conteúdo sintético", purpose="content", status="preparing",
    )
    client_db.add(folder)
    client_db.commit()

    from app import main, photographer_onboarding

    monkeypatch.setattr(main, "directory_tenant_id", lambda *_args: tenant.id)
    monkeypatch.setattr(
        main, "require_admin",
        lambda *_args: SimpleNamespace(subject_id=photographer.id),
    )
    monkeypatch.setattr(main, "require_parent_gallery_mutable", lambda *_args, **_kwargs: gallery)
    monkeypatch.setattr(photographer_onboarding, "_signup_identity", lambda *_args: None)
    reached_after_flush = []

    def fail_credit_reservation(db, tenant_id, photo_asset_id, *_args, **_kwargs):
        assert tenant_id == tenant.id
        assert db.get(PhotoAsset, photo_asset_id) is not None
        reached_after_flush.append(photo_asset_id)
        raise RuntimeError("synthetic credit reservation failure")

    monkeypatch.setattr(credits, "reserve_photo_credit", fail_credit_reservation)
    fingerprint = sha256(b"synthetic rollback photo").hexdigest()
    payload = main.PhotoAssetInput(
        filename="rollback.jpg",
        storage_key=f"{gallery.id}/{folder.id}/{fingerprint}.jpg",
    )

    with pytest.raises(RuntimeError, match="synthetic credit reservation failure"):
        main.register_folder_photo_asset(folder.id, payload, upload_request(b""), client_db)

    client_db.expire_all()
    assert len(reached_after_flush) == 1
    assert client_db.scalar(select(func.count()).select_from(PhotoAsset).where(
        PhotoAsset.tenant_id == tenant.id,
        PhotoAsset.folder_id == folder.id,
    )) == 0
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
    )) == 0
    wallet = credits.wallet_snapshot(client_db, tenant.id)
    assert wallet["available_credits"] == 1
    assert wallet["reserved_credits"] == 0


def test_upload_route_reconciles_durable_rename_and_replay_consumes_once(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "upload-durable", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    real_write = lifecycle.write_source

    def rename_then_interrupt(path, payload, **context):
        real_write(path, payload, **context)
        raise OSError("synthetic response interruption after rename")

    monkeypatch.setattr(lifecycle, "write_source", rename_then_interrupt)
    payload = jpeg_payload()
    with pytest.raises(HTTPException) as interrupted:
        asyncio.run(main.import_photo_source(photo.id, upload_request(payload), client_db))

    assert interrupted.value.status_code == 503
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "consumed"
    assert main.safe_source_path(photo).read_bytes() == payload
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0

    monkeypatch.setattr(lifecycle, "write_source", real_write)
    assert asyncio.run(main.import_photo_source(photo.id, upload_request(payload), client_db)) == {
        "status": "queued",
    }
    assert asyncio.run(main.import_photo_source(
        photo.id, upload_request(payload, facial_reindex=True), client_db,
    )) == {"status": "queued"}
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 1
    event_types = list(client_db.scalars(select(PhotoCreditOperationEvent.event_type).where(
        PhotoCreditOperationEvent.operation_id == operation.id,
    )))
    assert event_types.count("source_durable") == 1
    assert event_types.count("consumed") == 1
    assert event_types.count("upload_attempted") == 3


def test_upload_route_reconciles_when_credit_commit_fails_after_rename(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "upload-commit-failure", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)
    real_consume = credits.consume_photo_credit
    calls = 0

    def fail_first_confirmation(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SQLAlchemyError("synthetic credit commit failure")
        return real_consume(*args, **kwargs)

    monkeypatch.setattr(credits, "consume_photo_credit", fail_first_confirmation)
    payload = jpeg_payload()
    with pytest.raises(HTTPException) as interrupted:
        asyncio.run(main.import_photo_source(photo.id, upload_request(payload), client_db))

    assert interrupted.value.status_code == 503
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "reconciliation_required"
    assert main.safe_source_path(photo).read_bytes() == payload
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0

    monkeypatch.setattr(credits, "consume_photo_credit", real_consume)
    lock_order = []

    def record_financial_row_lock(execute_state):
        statement = execute_state.statement
        if not execute_state.is_select or getattr(statement, "_for_update_arg", None) is None:
            return
        sql = str(statement).lower()
        if "tenant_credit_wallet" in sql:
            lock_order.append("wallet")
        elif "photo_credit_operation" in sql:
            lock_order.append("operation")

    event.listen(client_db, "do_orm_execute", record_financial_row_lock)
    try:
        retried = asyncio.run(main.import_photo_source(photo.id, upload_request(payload), client_db))
    finally:
        event.remove(client_db, "do_orm_execute", record_financial_row_lock)
    assert retried == {"status": "queued"}
    assert lock_order[:2] == ["wallet", "operation"]
    assert operation.status == "consumed"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 1
    event_types = list(client_db.scalars(select(PhotoCreditOperationEvent.event_type).where(
        PhotoCreditOperationEvent.operation_id == operation.id,
    )))
    assert event_types.count("source_durable") == 1
    assert event_types.count("reconciled_consumed") == 1


def test_mismatched_stored_source_keeps_credit_reserved(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "upload-mismatch", "synthetic")
    photo = create_photo(client_db, tenant.id)
    client_db.commit()
    main, lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)

    def publish_conflicting_file(path, _payload, **_context):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"different durable content")
        raise OSError("synthetic conflicting source")

    monkeypatch.setattr(lifecycle, "write_source", publish_conflicting_file)
    with pytest.raises(HTTPException) as interrupted:
        asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db))

    assert interrupted.value.status_code == 503
    operation = client_db.scalar(select(PhotoCreditOperation).where(
        PhotoCreditOperation.tenant_id == tenant.id,
        PhotoCreditOperation.photo_asset_id_snapshot == photo.id,
    ))
    assert operation is not None and operation.status == "reconciliation_required"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0
    assert credits.wallet_snapshot(client_db, tenant.id)["reserved_credits"] == 1
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 0


def test_worker_reconciles_old_uploads_only_with_fingerprint_proof(
    client_db, monkeypatch, tmp_path,
):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 3, "worker-reconcile", "synthetic")
    photos = [create_photo(client_db, tenant.id) for _ in range(3)]
    expected = [b"durable JPEG content", b"absent JPEG content", b"expected JPEG content"]
    operations = []
    for index, (photo, body) in enumerate(zip(photos, expected, strict=True)):
        operations.append(credits.reserve_photo_credit(
            client_db, tenant.id, photo.id, photo.storage_key, sha256(body).hexdigest(),
        ))
        if index != 1:
            path = tmp_path / "source" / photo.storage_key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body if index == 0 else b"different content")
    client_db.flush()
    for operation in operations:
        operation.updated_at = now() - timedelta(hours=1)
    client_db.commit()
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))

    lock_order = []
    def record_financial_row_lock(execute_state):
        statement = execute_state.statement
        if not execute_state.is_select or getattr(statement, "_for_update_arg", None) is None:
            return
        sql = str(statement).lower()
        if "tenant_credit_wallet" in sql:
            lock_order.append("wallet")
        elif "photo_credit_operation" in sql:
            lock_order.append("operation")

    processed = 0
    event.listen(client_db, "do_orm_execute", record_financial_row_lock)
    try:
        while True:
            transaction_locks_start = len(lock_order)
            worked = credits.reconcile_next_stale_photo_credit_operation(client_db)
            if not worked:
                break
            assert lock_order[transaction_locks_start:transaction_locks_start + 2] == [
                "wallet", "operation",
            ]
            client_db.commit()
            processed += 1
    finally:
        event.remove(client_db, "do_orm_execute", record_financial_row_lock)

    client_db.expire_all()
    assert processed == 3
    assert [
        client_db.scalar(select(PhotoCreditOperation.status).where(
            PhotoCreditOperation.id == operation.id,
        ))
        for operation in operations
    ] == ["consumed", "released", "reconciliation_required"]
    snapshot = credits.wallet_snapshot(client_db, tenant.id)
    assert snapshot["available_credits"] == 1
    assert snapshot["reserved_credits"] == 1
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.entry_type == "upload_consumption",
    )) == 1


def test_cover_upload_does_not_open_or_consume_credit_operation(client_db, monkeypatch, tmp_path):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "cover-excluded", "synthetic")
    photo = create_photo(client_db, tenant.id, purpose="cover_assets")
    client_db.commit()
    main, _lifecycle = configure_upload_route(monkeypatch, tenant.id, tmp_path)

    assert asyncio.run(main.import_photo_source(photo.id, upload_request(jpeg_payload()), client_db)) == {
        "status": "queued",
    }
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 1
    assert client_db.scalar(select(func.count()).select_from(PhotoCreditOperation)) == 0


def test_deleting_photo_preserves_consumption_history_without_refund(client_db):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "delete-history", "synthetic")
    photo = create_photo(client_db, tenant.id)
    fingerprint = "d" * 64
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, fingerprint,
    )
    client_db.commit()
    credits.consume_photo_credit(client_db, tenant.id, photo.id, fingerprint)
    client_db.commit()

    from app import main

    main._delete_photo_records(client_db, photo, tenant_id=tenant.id)
    client_db.flush()
    client_db.expire_all()
    preserved = client_db.get(PhotoCreditOperation, operation.id)
    assert preserved is not None
    assert preserved.photo_asset_id is None
    assert preserved.photo_asset_id_snapshot == photo.id
    assert preserved.status == "consumed"
    assert credits.wallet_snapshot(client_db, tenant.id)["available_credits"] == 0


def test_deleting_photo_waits_for_credit_operation_reconciliation(client_db):
    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "delete-pending", "synthetic")
    photo = create_photo(client_db, tenant.id)
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, "9" * 64,
    )
    client_db.commit()

    from app import main

    with pytest.raises(HTTPException) as pending:
        main._delete_photo_records(client_db, photo, tenant_id=tenant.id)

    assert pending.value.status_code == 409
    assert client_db.get(PhotoAsset, photo.id) is not None
    assert client_db.get(PhotoCreditOperation, operation.id).status == "reserved"


def test_delete_private_gallery_waits_for_credit_operation_reconciliation(client_db, monkeypatch):
    from app import main
    from app.auth import DerivedGallery

    _, tenant, owner, _ = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 1, "delete-private-pending", "synthetic")
    client = Client(tenant_id=tenant.id, full_name="Cliente sintético", phone_e164="+5511555598801")
    parent = ParentGallery(tenant_id=tenant.id, name="Galeria pai sintética")
    client_db.add_all([client, parent])
    client_db.flush()
    gallery = DerivedGallery(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        client_id=client.id,
        name="Galeria privada sintética",
    )
    client_db.add(gallery)
    client_db.flush()
    folder = PhotoFolder(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        derived_gallery_id=gallery.id,
        name="Pasta privada sintética",
        purpose="content",
    )
    client_db.add(folder)
    client_db.flush()
    photo = PhotoAsset(
        tenant_id=tenant.id,
        parent_gallery_id=parent.id,
        folder_id=folder.id,
        derived_gallery_id=gallery.id,
        filename="privada.jpg",
        storage_key=f"synthetic/{gallery.id}/{folder.id}/privada.jpg",
    )
    client_db.add(photo)
    client_db.flush()
    operation = credits.reserve_photo_credit(
        client_db, tenant.id, photo.id, photo.storage_key, "e" * 64,
        actor_admin_id=None,
    )
    client_db.commit()
    monkeypatch.setattr(main, "directory_tenant_id", lambda *_args: tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda *_args: None)

    with pytest.raises(HTTPException) as pending:
        main.delete_derived_gallery(gallery.id, upload_request(b""), client_db)

    assert pending.value.status_code == 409
    assert "aguarda reconciliação do upload" in pending.value.detail
    client_db.expire_all()
    assert client_db.get(DerivedGallery, gallery.id) is not None
    assert client_db.get(PhotoAsset, photo.id) is not None
    assert client_db.get(PhotoCreditOperation, operation.id).status == "reserved"


def test_package_database_checks_reject_active_package_without_price(client_db):
    _, _, owner, _ = create_accounts(client_db)
    invalid = PhotographerCreditPackage(
        name="Ativo sem preço", credit_quantity=10, active=True,
        created_by_admin_id=owner.id, updated_by_admin_id=owner.id,
    )
    client_db.add(invalid)
    with pytest.raises(IntegrityError):
        client_db.flush()
    client_db.rollback()


def test_credit_capability_endpoint_is_private_and_owner_scoped(client_db, monkeypatch):
    _, _, owner, photographer = create_accounts(client_db)
    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main

    request = object()
    response = Response()
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=owner.id))
    assert main.admin_credit_capabilities(request, response, client_db) == {
        "manage_packages": True,
    }
    assert response.headers["Cache-Control"] == "private, no-store"

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
    assert main.admin_credit_capabilities(request, Response(), client_db) == {
        "manage_packages": False,
    }


def test_wallet_endpoint_returns_authoritative_recent_usage_without_shared_cache(client_db, monkeypatch):
    _, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "wallet-api-grant", "synthetic")
    photo = create_photo(client_db, tenant.id)
    credits.reserve_photo_credit(client_db, tenant.id, photo.id, photo.storage_key, "e" * 64)
    credits.consume_photo_credit(
        client_db, tenant.id, photo.id, "e" * 64, actor_admin_id=photographer.id,
    )

    from starlette.responses import Response

    from app import main

    monkeypatch.setattr(main, "directory_tenant_id", lambda _db, _request: tenant.id)
    response = Response()
    result = main.admin_credit_wallet(object(), response, client_db)

    assert response.headers["Cache-Control"] == "private, no-store"
    assert result["wallet"]["available_credits"] == 1
    assert result["wallet"]["recent_consumed_credits"] == 1
    assert result["wallet"]["recent_period_days"] == 30
    assert result["wallet"]["can_upload_content"] is True
    assert result["entries"][0]["type"] == "upload_consumption"


def test_photo_credit_operation_endpoint_returns_server_state_and_hides_other_tenants(client_db, monkeypatch):
    owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    credits.grant_credits(client_db, owner.id, tenant.id, 2, "photo-status-grant", "synthetic")
    photo = create_photo(client_db, tenant.id)
    credits.reserve_photo_credit(client_db, tenant.id, photo.id, photo.storage_key, "a" * 64)

    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main

    tenant_context = [tenant.id]
    monkeypatch.setattr(main, "directory_tenant_id", lambda _db, _request: tenant_context[0])
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
    response = Response()
    result = main.admin_photo_credit_operation(photo.id, object(), response, client_db)
    assert response.headers["Cache-Control"] == "private, no-store"
    assert result["applicable"] is True
    assert result["operation"]["status"] == "reserved"
    assert result["operation"]["quantity"] == 1
    assert result["wallet"]["available_credits"] == 1
    assert result["wallet"]["reserved_credits"] == 1

    credits.consume_photo_credit(client_db, tenant.id, photo.id, "a" * 64)
    consumed = main.admin_photo_credit_operation(photo.id, object(), Response(), client_db)
    assert consumed["operation"]["status"] == "consumed"
    assert consumed["wallet"]["reserved_credits"] == 0

    tenant_context[0] = owner_tenant.id
    with pytest.raises(HTTPException) as hidden:
        main.admin_photo_credit_operation(photo.id, object(), Response(), client_db)
    assert hidden.value.status_code == 404


def test_platform_owner_can_select_tenants_and_audit_revocable_grant_sources(client_db, monkeypatch):
    owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    grant = credits.grant_credits(client_db, owner.id, tenant.id, 2, "owner-ui-grant", "synthetic-reference")
    photo = create_photo(client_db, tenant.id)
    credits.reserve_photo_credit(client_db, tenant.id, photo.id, photo.storage_key, "f" * 64)
    credits.consume_photo_credit(
        client_db, tenant.id, photo.id, "f" * 64, actor_admin_id=photographer.id,
    )

    summaries = credits.list_credit_tenants(client_db, owner.id)
    owner_summary = next(item for item in summaries if item["tenant_id"] == str(owner_tenant.id))
    photographer_summary = next(item for item in summaries if item["tenant_id"] == str(tenant.id))
    assert owner_summary["wallet"]["mode"] == "unmetered"
    assert owner_summary["admin_emails"] == ["platform-owner@example.test"]
    assert photographer_summary["wallet"]["available_credits"] == 1
    assert photographer_summary["wallet"]["recent_consumed_credits"] == 1
    assert photographer_summary["admin_emails"] == ["photographer@example.test"]

    detail = credits.credit_tenant_detail(client_db, owner.id, tenant.id)
    assert detail["entries"][0]["type"] == "upload_consumption"
    grant_source = next(item for item in detail["revocable_grants"] if item["id"] == str(grant.id))
    assert grant_source["revocable_quantity"] == 1
    with pytest.raises(HTTPException) as denied:
        credits.list_credit_tenants(client_db, photographer.id)
    assert denied.value.status_code == 403

    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=owner.id))
    response = Response()
    route_result = main.admin_credit_tenants(object(), response, client_db)
    assert response.headers["Cache-Control"] == "private, no-store"
    assert len(route_result["items"]) == 2
    detail_response = Response()
    route_detail = main.admin_credit_tenant_detail(tenant.id, object(), detail_response, client_db)
    assert detail_response.headers["Cache-Control"] == "private, no-store"
    assert route_detail["wallet"]["available_credits"] == 1
    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
    with pytest.raises(HTTPException) as denied_route:
        main.admin_credit_tenants(object(), Response(), client_db)
    assert denied_route.value.status_code == 403


def test_owner_credit_grant_requires_step_up_audits_and_replays_without_totp(client_db, monkeypatch):
    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main, platform_console
    from app.auth import PlatformAdminEvent, password_hasher

    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = secret
    client_db.commit()
    owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(platform_console, "require_console_owner", lambda _db, _session: None)
    monkeypatch.setattr(platform_console, "revalidate_owner_before_commit", lambda *_: None)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    from app.main import PhotographerCreditGrantInput, PhotographerCreditRevocationInput

    payload = PhotographerCreditGrantInput(
        request_id=UUID("4316c671-8efb-44ba-83d7-b4db07c6ad9e"),
        tenant_id=tenant.id,
        quantity=3,
        idempotency_key="owner-grant-step-up",
        reference="synthetic step-up grant",
        current_password="SyntheticOwnerPassword!2026",
        totp_code=pyotp.TOTP(secret).now(),
    )
    result = main.admin_grant_photographer_credits(
        payload, request, Response(), client_db,
    )
    client_db.expire_all()
    assert result["entry"]["delta"] == 3
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "owner_grant",
    )) == 1
    event = client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == payload.request_id,
    ))
    assert event.action == "credit.granted"
    assert event.result == "success" and event.evidence_sha256

    replay = main.admin_grant_photographer_credits(payload, request, Response(), client_db)
    assert replay["entry"]["id"] == result["entry"]["id"]
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "credit.granted",
    )) == 1

    other_tenant = Tenant()
    client_db.add(other_tenant)
    client_db.flush()
    client_db.add(TenantCreditWallet(tenant_id=other_tenant.id, mode="finite"))
    client_db.commit()
    reused_tenant = payload.model_copy(update={"tenant_id": other_tenant.id})
    with pytest.raises(HTTPException) as tenant_conflict:
        main.admin_grant_photographer_credits(reused_tenant, request, Response(), client_db)
    assert tenant_conflict.value.status_code == 409

    reused = payload.model_copy(update={"reference": "different intent"})
    with pytest.raises(HTTPException) as conflict:
        main.admin_grant_photographer_credits(reused, request, Response(), client_db)
    assert conflict.value.status_code == 409
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "owner_grant",
    )) == 1

    current_step = pyotp.TOTP(secret).timecode(now())
    revoke = PhotographerCreditRevocationInput(
        request_id=uuid4(), tenant_id=tenant.id, quantity=1,
        idempotency_key="owner-revoke-step-up", reference="synthetic step-up revoke",
        current_password="SyntheticOwnerPassword!2026",
        totp_code=pyotp.TOTP(secret).at((current_step + 1) * pyotp.TOTP(secret).interval),
    )
    revoked = main.admin_revoke_photographer_credits(
        UUID(result["entry"]["id"]), revoke, request, Response(), client_db,
    )
    assert revoked["entry"]["delta"] == -1
    replayed_revoke = main.admin_revoke_photographer_credits(
        UUID(result["entry"]["id"]), revoke, request, Response(), client_db,
    )
    assert replayed_revoke["entry"]["id"] == revoked["entry"]["id"]

    invalid = PhotographerCreditGrantInput(
        request_id=uuid4(), tenant_id=tenant.id, quantity=2,
        idempotency_key="owner-grant-invalid-step-up", reference="synthetic denied",
        current_password="incorrect synthetic password", totp_code=pyotp.TOTP(secret).now(),
    )
    with pytest.raises(HTTPException) as denied:
        main.admin_grant_photographer_credits(invalid, request, Response(), client_db)
    assert denied.value.status_code == 403
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "owner_grant",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "console.access_denied",
    )) >= 2


@pytest.mark.parametrize("replay", [False, True])
@pytest.mark.parametrize("operation", ["grant", "package"])
def test_owner_financial_response_revalidates_session_after_loading_result(
    client_db, monkeypatch, replay, operation,
):
    from starlette.responses import Response

    from app import main, platform_console
    from app.auth import PlatformAdminEvent, password_hasher

    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = secret
    client_db.commit()
    owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(platform_console, "current_session", lambda *_args, **_kwargs: owner_session)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    if operation == "grant":
        payload = main.PhotographerCreditGrantInput(
            request_id=uuid4(), tenant_id=tenant.id, quantity=2,
            idempotency_key="response-session-grant", reference="synthetic grant",
            current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
        )
        def invoke():
            return main.admin_grant_photographer_credits(payload, request, Response(), client_db)
        serialize_name = "entry_payload"
        action = "credit.granted"
    else:
        payload = main.PhotographerCreditPackageInput(
            request_id=uuid4(), name="Pacote sintético", description=None,
            credit_quantity=2, price_cents=200, currency_code="BRL", active=False,
            current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
        )
        def invoke():
            return main.admin_create_credit_package(payload, request, Response(), client_db)
        serialize_name = "package_payload"
        action = "credit.package_created"

    if replay:
        invoke()

    serialize = getattr(credits, serialize_name)

    def serialize_then_revoke(*args, **kwargs):
        result = serialize(*args, **kwargs)
        def revoked(*_args, **_kwargs):
            raise HTTPException(403, "Acesso negado.")
        monkeypatch.setattr(platform_console, "current_session", revoked)
        return result

    monkeypatch.setattr(credits, serialize_name, serialize_then_revoke)
    with pytest.raises(HTTPException) as denied:
        invoke()
    assert denied.value.status_code == 403
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == payload.request_id,
        PlatformAdminEvent.action == action,
    )) == 1
    if operation == "grant":
        assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
            PhotographerCreditEntry.tenant_id == tenant.id,
            PhotographerCreditEntry.entry_type == "owner_grant",
        )) == 1


@pytest.mark.parametrize("method,path", [
    ("POST", "/admin/platform/credit-grants"),
    ("POST", f"/admin/platform/credit-grants/{UUID(int=1)}/revoke"),
    ("POST", "/admin/platform/credit-packages"),
    ("PUT", f"/admin/platform/credit-packages/{UUID(int=1)}"),
    ("POST", f"/admin/platform/credit-purchases/{UUID(int=1)}/review"),
])
def test_owner_financial_validation_never_echoes_credentials(monkeypatch, method, path):
    from app import main

    # Validação HTTP não deve tocar banco nem precisar de uma sessão real.
    monkeypatch.setitem(main.app.dependency_overrides, main.db_session, lambda: None)
    marker = "SyntheticSensitiveInputOnly"
    with TestClient(main.app) as http:
        response = http.request(method, path, json={
            "current_password": {"submitted_password": marker},
            "totp_code": {"submitted_code": marker},
        })
    assert response.status_code == 422
    assert marker not in response.text
    assert response.json() == {"detail": "Confira os dados da solicitação."}
    assert response.headers["Cache-Control"] == "private, no-store"


def test_owner_credit_revocation_rolls_back_if_session_changes_before_commit(client_db, monkeypatch):
    from types import SimpleNamespace

    from fastapi import HTTPException
    from starlette.responses import Response

    from app import main, platform_console
    from app.auth import PlatformAdminEvent, password_hasher

    owner_tenant, tenant, owner, _photographer = create_accounts(client_db)
    grant = credits.grant_credits(
        client_db, owner.id, tenant.id, 3, "session-revoke-grant", "synthetic seed",
    )
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = secret
    client_db.commit()
    owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(platform_console, "require_console_owner", lambda _db, _session: None)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    monkeypatch.setattr(
        platform_console, "current_session",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id,
        ),
    )

    from app.main import PhotographerCreditRevocationInput

    payload = PhotographerCreditRevocationInput(
        request_id=uuid4(), tenant_id=tenant.id, quantity=1,
        idempotency_key="session-revoke-at-commit", reference="synthetic revoke",
        current_password="SyntheticOwnerPassword!2026",
        totp_code=pyotp.TOTP(secret).now(),
    )
    with pytest.raises(HTTPException) as denied:
        main.admin_revoke_photographer_credits(
            grant.id, payload, request, Response(), client_db,
        )
    assert denied.value.status_code == 403
    client_db.expire_all()
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditEntry).where(
        PhotographerCreditEntry.tenant_id == tenant.id,
        PhotographerCreditEntry.entry_type == "grant_revocation",
    )) == 0
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == payload.request_id,
    )) == 0


def test_owner_credit_package_mutation_requires_step_up_and_replays_safely(client_db, monkeypatch):
    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main, platform_console
    from app.auth import PlatformAdminEvent, password_hasher

    owner_tenant, _tenant, owner, _photographer = create_accounts(client_db)
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = secret
    client_db.commit()
    owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(platform_console, "require_console_owner", lambda _db, _session: None)
    monkeypatch.setattr(platform_console, "revalidate_owner_before_commit", lambda *_: None)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    from app.main import PhotographerCreditPackageInput

    payload = PhotographerCreditPackageInput(
        request_id=uuid4(), name="Pacote sintético", description="Apenas teste",
        credit_quantity=20, price_cents=2500, currency_code="BRL", active=False,
        current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
    )
    created = main.admin_create_credit_package(payload, request, Response(), client_db)
    replayed = main.admin_create_credit_package(payload, request, Response(), client_db)
    assert created["id"] == replayed["id"]
    assert created["replayed"] is False and replayed["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(PhotographerCreditPackage).where(
        PhotographerCreditPackage.name == "Pacote sintético",
    )) == 1
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "credit.package_created",
    )) == 1

    current_step = pyotp.TOTP(secret).timecode(now())
    update = PhotographerCreditPackageInput(
        request_id=uuid4(), name="Pacote sintético revisado", description="Apenas teste",
        credit_quantity=25, price_cents=2500, currency_code="BRL", active=False,
        current_password="SyntheticOwnerPassword!2026",
        totp_code=pyotp.TOTP(secret).at((current_step + 1) * pyotp.TOTP(secret).interval),
    )
    updated = main.admin_update_credit_package(
        UUID(created["id"]), update, request, Response(), client_db,
    )
    assert updated["name"] == "Pacote sintético revisado" and updated["credit_quantity"] == 25
    update_replay = main.admin_update_credit_package(
        UUID(created["id"]), update, request, Response(), client_db,
    )
    assert update_replay["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "credit.package_updated",
    )) == 1

    conflict = payload.model_copy(update={"name": "Outro pacote"})
    with pytest.raises(HTTPException) as reused:
        main.admin_create_credit_package(conflict, request, Response(), client_db)
    assert reused.value.status_code == 409


def test_owner_credit_purchase_review_requires_step_up_and_replays(client_db, monkeypatch):
    from types import SimpleNamespace

    from starlette.responses import Response

    from app import main, platform_console
    from app.auth import MercadoPagoCreditPurchase, PlatformAdminEvent, password_hasher
    from tests.test_mercadopago_credit_purchases import create_purchase_context, prepare

    owner_tenant, buyer_tenant, owner, buyer, package, _account_id = create_purchase_context(client_db)
    purchase = prepare(client_db, buyer_tenant, buyer, package, "owner-review-step-up")
    purchase.state = "charged_back"
    purchase.review_status = "pending"
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = secret
    client_db.commit()
    owner_session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(main, "require_admin", lambda _request: owner_session)
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(platform_console, "require_console_owner", lambda _db, _session: None)
    monkeypatch.setattr(platform_console, "revalidate_owner_before_commit", lambda *_: None)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    from app.main import PhotographerCreditReviewInput

    payload = PhotographerCreditReviewInput(
        request_id=uuid4(), decision="release", reason="Revisão sintética",
        current_password="SyntheticOwnerPassword!2026", totp_code=pyotp.TOTP(secret).now(),
    )
    result = main.admin_review_credit_purchase(
        purchase.id, payload, request, Response(), client_db,
    )
    assert result["replayed"] is False
    replay = main.admin_review_credit_purchase(
        purchase.id, payload, request, Response(), client_db,
    )
    assert replay["replayed"] is True
    assert client_db.get(MercadoPagoCreditPurchase, purchase.id).review_status == "released"
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "credit.purchase_reviewed",
    )) == 1

    reused = payload.model_copy(update={"reason": "Conteúdo diferente"})
    with pytest.raises(HTTPException) as conflict:
        main.admin_review_credit_purchase(
            purchase.id, reused, request, Response(), client_db,
        )
    assert conflict.value.status_code == 409

    restricted_purchase = prepare(
        client_db, buyer_tenant, buyer, package, "owner-review-restrict-step-up",
    )
    restricted_purchase.state = "partially_refunded"
    restricted_purchase.review_status = "pending"
    client_db.commit()
    current_step = pyotp.TOTP(secret).timecode(now())
    restriction = PhotographerCreditReviewInput(
        request_id=uuid4(), decision="restrict", reason="Manter bloqueio sintético",
        current_password="SyntheticOwnerPassword!2026",
        totp_code=pyotp.TOTP(secret).at((current_step + 1) * pyotp.TOTP(secret).interval),
    )
    restricted = main.admin_review_credit_purchase(
        restricted_purchase.id, restriction, request, Response(), client_db,
    )
    assert restricted["replayed"] is False
    assert client_db.get(MercadoPagoCreditPurchase, restricted_purchase.id).review_status == "restricted"
    restriction_replay = main.admin_review_credit_purchase(
        restricted_purchase.id, restriction, request, Response(), client_db,
    )
    assert restriction_replay["replayed"] is True
    assert client_db.scalar(select(func.count()).select_from(PlatformAdminEvent).where(
        PlatformAdminEvent.action == "credit.purchase_reviewed",
    )) == 2


def test_global_route_audits_denied_commercial_access(client_db, monkeypatch):
    _, _, _, photographer = create_accounts(client_db)
    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from app import main

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=photographer.id))
    request = Request({
        "type": "http", "method": "GET", "path": "/admin/platform/credit-packages",
        "headers": [], "query_string": b"", "scheme": "http", "server": ("test", 80),
        "client": ("test", 1234),
    })
    with pytest.raises(HTTPException) as denied:
        main._require_credit_owner(request, client_db, Response())
    assert denied.value.status_code == 403
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == "credit.owner_access_denied",
        AuditEvent.subject == str(photographer.id),
    )) == 1


def test_owner_credit_tenant_search_matches_name_and_email_and_returns_minimal_suggestions(client_db, monkeypatch):
    _, tenant, owner, photographer = create_accounts(client_db)
    tenant.photographer_name = "Zeta Studio"
    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from app import main

    monkeypatch.setattr(main, "require_admin", lambda _request: SimpleNamespace(subject_id=owner.id))
    request = Request({
        "type": "http", "method": "GET", "path": "/admin/platform/credit-tenants/search",
        "headers": [], "query_string": b"query=zeta&limit=10", "scheme": "http", "server": ("test", 80),
        "client": ("test", 1234),
    })
    response = Response()
    result = main.admin_search_credit_tenants(
        request, response, query="zeta", limit=10, offset=0, db=client_db,
    )

    assert response.headers["Cache-Control"] == "private, no-store"
    assert result["items"] == [{
        "tenant_id": str(tenant.id),
        "status": "active",
        "canonical_host": None,
        "photographer_name": "Zeta Studio",
        "admin_email": photographer.email,
    }]
    email_result = main.admin_search_credit_tenants(
        request, Response(), query="GRAPH", limit=10, offset=0, db=client_db,
    )
    assert email_result["items"] == result["items"]
    assert set(result["items"][0]) == {
        "tenant_id", "status", "canonical_host", "photographer_name", "admin_email",
    }
    assert credits.search_credit_tenants(client_db, owner.id, "x") == []
    with pytest.raises(HTTPException) as denied:
        credits.search_credit_tenants(client_db, photographer.id, "zeta")
    assert denied.value.status_code == 403


def test_credit_tenant_search_sorts_by_name_and_hides_ambiguous_email(client_db):
    owner_tenant, zeta, owner, _ = create_accounts(client_db)
    zeta.photographer_name = "Zeta Studio"
    alpha = Tenant(photographer_name="Alpha Studio")
    client_db.add(alpha)
    client_db.flush()
    alpha_user = AdminUser(
        email="alpha@example.test", password_hash="synthetic", totp_secret="synthetic",
        email_verified=True,
    )
    alpha_user.tenant_memberships.append(TenantAdmin(tenant_id=alpha.id))
    client_db.add_all([alpha_user, TenantCreditWallet(tenant_id=alpha.id, mode="finite")])
    client_db.commit()

    page = credits.browse_credit_tenants(client_db, owner.id, query="studio", mode="alphabetical")
    assert [item["photographer_name"] for item in page["items"]] == ["Alpha Studio", "Zeta Studio"]
    assert [item["tenant_id"] for item in page["items"]] == [str(alpha.id), str(zeta.id)]
    all_ordered = credits.browse_credit_tenants(client_db, owner.id, mode="alphabetical")["items"]
    assert [item["tenant_id"] for item in all_ordered] == [str(alpha.id), str(owner_tenant.id), str(zeta.id)]

    ambiguous_admin = AdminUser(
        email="second-admin@example.test", password_hash="synthetic", totp_secret="synthetic",
        email_verified=True,
    )
    ambiguous_admin.tenant_memberships.append(TenantAdmin(tenant_id=zeta.id))
    client_db.add(ambiguous_admin)
    client_db.commit()
    result = credits.browse_credit_tenants(client_db, owner.id, query="zeta")
    assert result["items"] == [{
        "tenant_id": str(zeta.id),
        "status": "active",
        "canonical_host": None,
        "photographer_name": "Zeta Studio",
        "admin_email": None,
    }]


def test_credit_tenant_search_denies_photographer_client_and_technical_operator(client_db, monkeypatch):
    _, tenant, _owner, photographer = create_accounts(client_db)
    operator = AdminUser(
        email="operator@example.test", password_hash="synthetic", totp_secret="synthetic",
        email_verified=True,
    )
    operator.tenant_memberships.append(TenantAdmin(tenant_id=tenant.id))
    client_db.add(operator)
    client_db.flush()
    client_identity = Client(
        tenant_id=tenant.id, full_name="Synthetic client", phone_e164="+5511999998888",
    )
    client_db.add_all([
        client_identity,
        InstallationOperator(
            admin_user_id=operator.id, active=True, authorization_reference="synthetic",
            granted_at=now(), updated_at=now(),
        ),
        MonitorGrant(
            admin_user_id=operator.id, permission="metrics", active=True,
            authorization_reference="synthetic",
        ),
    ])
    client_db.commit()

    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from app import main

    request = Request({
        "type": "http", "method": "GET", "path": "/admin/platform/credit-tenants/search",
        "headers": [], "query_string": b"query=synthetic", "scheme": "http", "server": ("test", 80),
        "client": ("test", 1234),
    })
    for actor_id in (photographer.id, client_identity.id, operator.id):
        monkeypatch.setattr(main, "require_admin", lambda _request, identity=actor_id: SimpleNamespace(subject_id=identity))
        with pytest.raises(HTTPException) as denied:
            main.admin_search_credit_tenants(
                request, Response(), query="synthetic", limit=10, offset=0, db=client_db,
            )
        assert denied.value.status_code == 403
def test_sensitive_payload_schemas_enforce_bounds_and_forbid_extras():
    from pydantic import ValidationError

    from app import main

    package = {
        "request_id": uuid4(),
        "name": "Pacote sintético",
        "description": None,
        "credit_quantity": 2,
        "price_cents": 500,
        "currency_code": "BRL",
        "active": False,
        "current_password": "synthetic-password",
        "totp_code": "123456",
    }
    assert main.PhotographerCreditPackageInput(**package).price_cents == 500
    for invalid_package in (
        {**package, "price_cents": 500, "currency_code": None},
        {**package, "price_cents": None, "currency_code": "BRL"},
        {**package, "price_cents": None, "currency_code": None, "active": True},
        {**package, "unexpected": "value"},
    ):
        with pytest.raises(ValidationError):
            main.PhotographerCreditPackageInput(**invalid_package)

    for duration_days in (7, 14, 30):
        payload = main.MediaArchiveRecoveryInput(
            duration_days=duration_days, idempotency_key="synthetic-recovery",
        )
        assert payload.duration_days == duration_days
    for invalid_recovery in (
        {"duration_days": 8, "idempotency_key": "synthetic-recovery"},
        {"duration_days": 7, "idempotency_key": ""},
        {"duration_days": 7, "idempotency_key": "synthetic-recovery", "unexpected": True},
    ):
        with pytest.raises(ValidationError):
            main.MediaArchiveRecoveryInput(**invalid_recovery)

    credit_fields = {
        "request_id": uuid4(),
        "tenant_id": uuid4(),
        "quantity": 1,
        "idempotency_key": "synthetic-credit-operation",
        "reference": "synthetic test",
        "current_password": "synthetic-password",
        "totp_code": "123456",
    }
    for input_model in (
        main.PhotographerCreditGrantInput,
        main.PhotographerCreditRevocationInput,
    ):
        assert input_model(**credit_fields).quantity == 1
        for invalid_fields in (
            {**credit_fields, "quantity": 0},
            {**credit_fields, "idempotency_key": ""},
            {**credit_fields, "unexpected": True},
        ):
            with pytest.raises(ValidationError):
                input_model(**invalid_fields)

    review = {
        "request_id": uuid4(),
        "decision": "release",
        "reason": "Revisão sintética",
        "current_password": "synthetic-password",
        "totp_code": "123456",
    }
    assert main.PhotographerCreditReviewInput(**review).decision == "release"
    for invalid_review in (
        {**review, "decision": "approve"},
        {**review, "reason": ""},
        {**review, "unexpected": True},
    ):
        with pytest.raises(ValidationError):
            main.PhotographerCreditReviewInput(**invalid_review)

    reopening_request = {
        "idempotency_key": "synthetic-reopen-01",
        "folder_id": uuid4(),
    }
    assert main.GalleryReopeningRequestInput(**reopening_request).folder_id == reopening_request["folder_id"]
    with pytest.raises(ValidationError):
        main.GalleryReopeningRequestInput(
            idempotency_key="synthetic-reopen-01",
            unexpected=True,
            folder_id=uuid4(),
        )

    assert main.GalleryReopeningDecisionInput(
        decision="approved", access_duration_days=7,
    ).decision == "approved"
    assert main.GalleryReopeningDecisionInput(decision="refused").decision == "refused"
    for invalid_decision in (
        {"decision": "approved"},
        {"decision": "refused", "access_duration_days": 7},
        {"decision": "approved", "access_duration_days": 7, "unexpected": True},
    ):
        with pytest.raises(ValidationError):
            main.GalleryReopeningDecisionInput(**invalid_decision)

    with pytest.raises(ValidationError):
        main.PhotoFolderInput(
            name="Pasta sintética",
            access_duration_days=7,
            unexpected="must be rejected",
        )
