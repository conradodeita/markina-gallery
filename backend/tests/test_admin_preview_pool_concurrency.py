from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app import auth, main
from app.auth import AuditEvent, AuthSession, MediaDerivative, Role, TenantAdmin, now, token_hash
from tests.test_tenant_acervo import client_db as _client_db
from tests.test_tenant_acervo import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_auth import request
from tests.test_tenant_client_navigation import cookie

client_db = _client_db
graph = _graph
links = _links

PREVIEWS = [
    ("admin_photo_preview", "admin_preview", "media_preview.admin_viewed"),
    ("admin_watermarked_photo_preview", "client_preview", "media_preview.admin_watermarked_viewed"),
]


@pytest.fixture
def preview_records(client_db, graph, links, tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path))
    records = []
    for account in graph:
        photo = account["photo"]
        for variant in ("admin_preview", "client_preview"):
            relative_path = f"legacy/{account['tenant'].id}/{variant}.jpg"
            path = tmp_path / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"synthetic-{account['tenant'].id}-{variant}".encode())
            client_db.add(MediaDerivative(
                tenant_id=photo.tenant_id, photo_asset_id=photo.id,
                variant=variant, status="ready", relative_path=relative_path,
            ))
        client_db.commit()
        admin_cookie = cookie(client_db, account, Role.ADMIN)
        records.append({"tenant_id": account["tenant"].id, "photo_id": photo.id,
                        "cookie": admin_cookie, "root": tmp_path})
    client_db.commit()
    return records


@pytest.fixture
def preview_pool(client_db, preview_records, monkeypatch):
    sqlite = client_db.bind.dialect.name == "sqlite"
    engine = create_engine(
        client_db.bind.url, poolclass=QueuePool, pool_size=2, max_overflow=0,
        pool_timeout=0.3, connect_args={"check_same_thread": False} if sqlite else {},
    )
    if sqlite:
        @event.listens_for(engine, "connect")
        def sqlite_contract(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    engine = engine.execution_options(**client_db.bind.get_execution_options())
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(main, "SessionLocal", factory)
    try:
        yield engine, factory
    finally:
        engine.dispose()


@pytest.mark.parametrize("endpoint,variant,audit_event", PREVIEWS)
def test_concurrent_own_previews_finish_without_nested_pool_acquisition(
    client_db, preview_records, preview_pool, monkeypatch, endpoint, variant, audit_event,
):
    engine, factory = preview_pool
    rendezvous = Barrier(2)
    resolve_owner = main.directory_tenant_id

    def simultaneous_owners(db, incoming):
        owner = resolve_owner(db, incoming)
        rendezvous.wait(timeout=5)
        return owner

    monkeypatch.setattr(main, "directory_tenant_id", simultaneous_owners)

    def retrieve(record):
        with main.domain_session(factory) as db:
            response = getattr(main, endpoint)(record["photo_id"], request(record["cookie"]), db)
            return response, Path(response.path).read_bytes()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(retrieve, record) for record in preview_records]
        responses = [future.result(timeout=10) for future in futures]
    for record, (response, content) in zip(preview_records, responses, strict=True):
        assert content == f"synthetic-{record['tenant_id']}-{variant}".encode()
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.tenant_id == record["tenant_id"], AuditEvent.event == audit_event,
            AuditEvent.subject == str(record["photo_id"]),
        )) == 1
    assert engine.pool.checkedout() == 0


@pytest.mark.parametrize("endpoint,_variant,_audit_event", PREVIEWS)
@pytest.mark.parametrize("invalid", ["revoked", "expired", "inactive_membership", "suspended", "unverified"])
def test_invalid_administrator_is_denied_before_preview_or_audit(
    client_db, graph, preview_records, preview_pool, endpoint, _variant, _audit_event, invalid,
):
    record = preview_records[0]
    session = client_db.scalar(select(AuthSession).where(
        AuthSession.token_hash == token_hash(record["cookie"]),
    ))
    if invalid == "revoked":
        session.revoked_at = now()
    elif invalid == "expired":
        session.expires_at = now() - timedelta(seconds=1)
    elif invalid == "inactive_membership":
        membership = client_db.scalar(select(TenantAdmin).where(
            TenantAdmin.tenant_id == record["tenant_id"],
        ))
        membership.active = False
    elif invalid == "suspended":
        graph[0]["tenant"].status = "suspended"
    else:
        graph[0]["admin"].email_verified = False
    client_db.commit()
    _engine, factory = preview_pool
    with factory() as db, pytest.raises(HTTPException) as captured:
        getattr(main, endpoint)(record["photo_id"], request(record["cookie"]), db)
    assert captured.value.status_code == 403
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == _audit_event,
    )) == 0


@pytest.mark.parametrize("endpoint,_variant,audit_event", PREVIEWS)
@pytest.mark.parametrize("foreign", [True, False])
def test_foreign_and_absent_previews_are_indistinguishable_without_audit(
    client_db, preview_records, preview_pool, endpoint, _variant, audit_event, foreign,
):
    _engine, factory = preview_pool
    photo_id = preview_records[1]["photo_id"] if foreign else uuid4()
    with factory() as db, pytest.raises(HTTPException) as captured:
        getattr(main, endpoint)(photo_id, request(preview_records[0]["cookie"]), db)
    assert captured.value.status_code == 404
    assert captured.value.detail == "Foto não encontrada."
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == audit_event,
    )) == 0


@pytest.mark.parametrize("endpoint,_variant,audit_event", PREVIEWS)
@pytest.mark.parametrize("visitor", [True, False])
def test_visitor_and_client_cannot_use_administrative_previews(
    client_db, graph, preview_records, preview_pool, endpoint, _variant, audit_event, visitor,
):
    incoming = request() if visitor else request(cookie(client_db, graph[0], Role.CLIENT))
    _engine, factory = preview_pool
    with factory() as db, pytest.raises(HTTPException) as captured:
        getattr(main, endpoint)(preview_records[0]["photo_id"], incoming, db)
    assert captured.value.status_code == 403
    assert client_db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.event == audit_event,
    )) == 0
