"""Renovação coletiva de prazo sem contornar isolamento ou arquivo frio."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app import main
from app.auth import (
    AuditEvent,
    Base,
    Client,
    GalleryClientState,
    GalleryReopeningRequest,
    MediaArchiveCycle,
    MediaArchiveNotice,
    ParentGallery,
    PhotoAsset,
    PhotoFolder,
    PhotoSelection,
    Tenant,
    now,
)
from app.folder_access import (
    folder_archive_eligible_at,
    folder_browsing_clause,
    folder_effective_expiry,
)
from tests.tenant_fixtures import FIXTURE_TENANT_ID

pytest_plugins = ["tests.test_preview_adjustment"]


@pytest.mark.parametrize("model,fields", [
    (main.PhotoFolderInput, {"name": "Pasta sintética"}),
    (main.PhotoFolderDeadlineInput, {}),
    (main.GalleryReopeningDecisionInput, {"decision": "approved"}),
])
def test_folder_duration_inputs_reject_unrepresentable_deadlines(monkeypatch, model, fields):
    from pydantic import ValidationError

    from app import folder_deadlines

    instant = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)  # noqa: UP017
    monkeypatch.setattr(folder_deadlines, "now", lambda: instant)
    latest_duration = (datetime.max.replace(tzinfo=timezone.utc) - instant - timedelta(days=30)).days  # noqa: UP017
    assert model(**fields, access_duration_days=14).access_duration_days == 14
    assert model(**fields, access_duration_days=latest_duration).access_duration_days == latest_duration
    for days in (latest_duration + 1, 999999999, 2**63):
        with pytest.raises(ValidationError, match="duração"):
            model(**fields, access_duration_days=days)


def test_legacy_deadline_rejects_overflow_before_persisting(api_client):
    client, factory, _, _, (folder_id, _, _) = expired_folder(api_client)
    with factory() as db:
        folder = db.get(PhotoFolder, folder_id)
        folder.access_duration_days = None
        folder.access_expires_at = None
        db.commit()
        previous_audits = db.scalar(select(func.count(AuditEvent.id)))
    response = client.patch(
        f"/admin/photo-folders/{folder_id}/deadline",
        json={"access_duration_days": 999999999},
    )
    assert response.status_code == 422
    with factory() as db:
        folder = db.get(PhotoFolder, folder_id)
        assert folder.access_duration_days is None and folder.access_expires_at is None
        assert db.scalar(select(func.count(AuditEvent.id))) == previous_audits


def expired_folder(api_client, *, age=2, scope="all", media_state=None):
    client, factory, photo_id = api_client
    instant = now()
    with factory() as db:
        photo = db.get(PhotoAsset, photo_id)
        folder = db.get(PhotoFolder, photo.folder_id)
        folder.status = "released"
        folder.audience_scope = scope
        folder.released_at = instant - timedelta(days=60)
        folder.access_duration_days = 30
        folder.access_expires_at = instant - timedelta(days=age)
        if media_state:
            db.add(MediaArchiveCycle(
                tenant_id=folder.tenant_id, parent_gallery_id=folder.parent_gallery_id,
                folder_id=folder.id, cycle_number=1, state=media_state,
            ))
        db.commit()
        identifiers = folder.id, folder.parent_gallery_id, folder.released_at
    client.cookies.set("markina_session", "adjustment-admin")
    return client, factory, photo_id, instant, identifiers


def test_public_renewal_starts_now_preserves_selection_and_supersedes_old_notice(api_client, monkeypatch):
    client, factory, photo_id, instant, (folder_id, gallery_id, released_at) = expired_folder(api_client)
    monkeypatch.setattr(main, "now", lambda: instant)
    with factory() as db:
        folder = db.get(PhotoFolder, folder_id)
        first = db.scalar(select(Client))
        second = Client(tenant_id=FIXTURE_TENANT_ID, full_name="Segunda cliente",
                        phone_e164="+5511999999941")
        db.add(second)
        db.flush()
        for person in (first, second):
            db.add(GalleryClientState(
                tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id, client_id=person.id,
            ))
        db.flush()
        selection = PhotoSelection(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id,
            client_id=first.id, photo_asset_id=photo_id,
            created_at=instant - timedelta(days=3),
        )
        cycle = MediaArchiveCycle(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id,
            folder_id=folder_id, cycle_number=1, state="local",
        )
        db.add_all((selection, cycle))
        db.flush()
        notice = MediaArchiveNotice(
            tenant_id=FIXTURE_TENANT_ID, cycle_id=cycle.id, notice_type="window_7_days",
            idempotency_key="synthetic-old-window", title="Aviso de teste",
            body="Prazo anterior", deadline_at=folder.access_expires_at + timedelta(days=30),
        )
        db.add(notice)
        db.commit()
        client_ids, selection_id, notice_id = (first.id, second.id), selection.id, notice.id
    with factory() as db:
        for client_id in client_ids:
            assert db.scalar(select(PhotoFolder.id).where(
                PhotoFolder.id == folder_id, folder_browsing_clause(client_id, at=instant),
            )) is None
    listed = client.get(f"/admin/parent-galleries/{gallery_id}/folders").json()
    assert next(row for row in listed["folders"] if row["id"] == str(folder_id))["can_renew_deadline"]
    endpoint = f"/admin/photo-folders/{folder_id}/renew-deadline"
    response = client.patch(endpoint, json={"access_duration_days": 7})
    assert response.status_code == 200, response.text
    assert response.json()["can_renew_deadline"] is False
    with factory() as db:
        folder = db.get(PhotoFolder, folder_id)
        expected = instant + timedelta(days=7)
        assert folder.access_expires_at.replace(tzinfo=instant.tzinfo) == expected
        assert folder.released_at.replace(tzinfo=instant.tzinfo) == released_at.replace(tzinfo=instant.tzinfo)
        assert folder.access_duration_days == 7
        assert all(folder_effective_expiry(db, folder, client_id=cid) == expected for cid in client_ids)
        for client_id in client_ids:
            assert db.scalar(select(PhotoFolder.id).where(
                PhotoFolder.id == folder_id, folder_browsing_clause(client_id, at=instant),
            )) == folder_id
        assert folder_archive_eligible_at(db, folder) == expected + timedelta(days=30)
        assert db.get(PhotoSelection, selection_id) is not None
        assert db.get(MediaArchiveNotice, notice_id).superseded_at is not None
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.tenant_id == FIXTURE_TENANT_ID,
            AuditEvent.event == "photo_folder.deadline_renewed",
            AuditEvent.subject == str(folder_id),
        )) == 1
    assert client.patch(endpoint, json={"access_duration_days": 14}).status_code == 409
    with factory() as db:
        assert db.get(PhotoFolder, folder_id).access_expires_at.replace(tzinfo=instant.tzinfo) == expected


@pytest.mark.parametrize(("age", "scope", "media_state"), [
    (-1, "all", None), (31, "all", None), (2, "selected", None),
    (2, "all", "archived"), (2, "all", "archiving"),
    (2, "all", "restoring"), (2, "all", "reconciliation_required"),
])
def test_renewal_rejects_ineligible_folder_without_changing_expiry(api_client, age, scope, media_state):
    client, factory, _, _, (folder_id, _, _) = expired_folder(
        api_client, age=age, scope=scope, media_state=media_state,
    )
    with factory() as db:
        previous = db.get(PhotoFolder, folder_id).access_expires_at
    response = client.patch(f"/admin/photo-folders/{folder_id}/renew-deadline",
                            json={"access_duration_days": 7})
    assert response.status_code == 409, response.text
    with factory() as db:
        assert db.get(PhotoFolder, folder_id).access_expires_at == previous


def test_renewal_window_includes_expiry_and_exactly_thirty_days(api_client, monkeypatch):
    client, factory, _, instant, (folder_id, _, _) = expired_folder(api_client)
    monkeypatch.setattr(main, "now", lambda: instant)
    endpoint = f"/admin/photo-folders/{folder_id}/renew-deadline"
    for elapsed, expected_status in (
        (timedelta(microseconds=-1), 409),
        (timedelta(0), 200),
        (timedelta(days=30), 200),
        (timedelta(days=30, microseconds=1), 409),
    ):
        previous = instant - elapsed
        with factory() as db:
            db.get(PhotoFolder, folder_id).access_expires_at = previous
            db.commit()
        response = client.patch(endpoint, json={"access_duration_days": 7})
        assert response.status_code == expected_status, (elapsed, response.text)
        with factory() as db:
            expiry = db.get(PhotoFolder, folder_id).access_expires_at.replace(tzinfo=instant.tzinfo)
            assert expiry == (instant + timedelta(days=7) if expected_status == 200 else previous)


def test_renewal_rechecks_effective_public_reopening_and_rejects_closing_account(api_client):
    client, factory, _, instant, (folder_id, gallery_id, _) = expired_folder(api_client, age=40)
    with factory() as db:
        person = db.scalar(select(Client))
        db.add(GalleryClientState(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id, client_id=person.id,
        ))
        db.flush()
        reopening = GalleryReopeningRequest(
            tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery_id,
            photo_folder_id=folder_id, requested_by_client_id=person.id,
            idempotency_key="synthetic-reopening", status="approved",
            approved_duration_days=5, approved_until=instant + timedelta(days=1),
        )
        db.add(reopening)
        db.commit()
        reopening_id = reopening.id
    endpoint = f"/admin/photo-folders/{folder_id}/renew-deadline"
    assert client.patch(endpoint, json={"access_duration_days": 7}).status_code == 409
    with factory() as db:
        db.get(GalleryReopeningRequest, reopening_id).approved_until = instant - timedelta(days=1)
        db.get(Tenant, FIXTURE_TENANT_ID).lifecycle = "closing"
        db.commit()
    assert client.patch(endpoint, json={"access_duration_days": 7}).status_code == 409
    with factory() as db:
        db.get(Tenant, FIXTURE_TENANT_ID).lifecycle = "open"
        db.commit()
    assert client.patch(endpoint, json={"access_duration_days": 7}).status_code == 200


def test_renewal_keeps_tenant_role_and_duration_guards(api_client):
    client, factory, _, _, (folder_id, _, _) = expired_folder(api_client)
    endpoint = f"/admin/photo-folders/{folder_id}/renew-deadline"
    client.cookies.set("markina_session", "adjustment-client")
    assert client.patch(endpoint, json={"access_duration_days": 7}).status_code == 403
    client.cookies.set("markina_session", "adjustment-admin")
    for days in (0, -1, 1.5, 999999999):
        assert client.patch(endpoint, json={"access_duration_days": days}).status_code == 422
    with factory() as db:
        foreign = Tenant()
        db.add(foreign)
        db.flush()
        gallery = ParentGallery(tenant_id=foreign.id, name="Outra conta")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(
            tenant_id=foreign.id, parent_gallery_id=gallery.id,
            name="Pasta alheia", purpose="content", position=0,
        )
        db.add(folder)
        db.commit()
        foreign_id = folder.id
    assert client.patch(f"/admin/photo-folders/{foreign_id}/renew-deadline",
                        json={"access_duration_days": 7}).status_code == 404
    assert client.patch(f"/admin/photo-folders/{uuid4()}/renew-deadline",
                        json={"access_duration_days": 7}).status_code == 404


@pytest.fixture
def renewal_postgres(monkeypatch):
    raw = os.getenv("PUBLIC_FOLDER_RENEWAL_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Requer PostgreSQL descartável exclusivo para renovação.")
    url = make_url(raw)
    if (url.get_backend_name() != "postgresql" or url.host != "127.0.0.1"
            or url.port != 15483 or url.database != "pyp_public_renewal_test"):
        pytest.fail("Prova limitada ao PostgreSQL descartável em loopback:15483.")
    admin_engine = create_engine(url)
    schema = "renewal_" + uuid4().hex
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema} -clock_timeout=15s"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            tenant = Tenant()
            db.add(tenant)
            db.flush()
            gallery = ParentGallery(tenant_id=tenant.id, name="Concorrência sintética")
            db.add(gallery)
            db.flush()
            folder = PhotoFolder(
                tenant_id=tenant.id, parent_gallery_id=gallery.id, purpose="content",
                name="Pública vencida", audience_scope="all", status="released", position=0,
                released_at=now() - timedelta(days=60), access_duration_days=30,
                access_expires_at=now() - timedelta(days=2),
            )
            db.add(folder)
            db.commit()
            tenant_id, gallery_id, folder_id = tenant.id, gallery.id, folder.id
        monkeypatch.setattr(main, "directory_tenant_id", lambda *_args: tenant_id)
        monkeypatch.setattr(main, "require_admin", lambda *_args: None)
        yield sessionmaker(engine, expire_on_commit=False), tenant_id, gallery_id, folder_id
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_concurrent_postgres_renewals_extend_once(renewal_postgres):
    factory, tenant_id, _, folder_id = renewal_postgres
    barrier = Barrier(2)

    def renew():
        with factory() as db:
            barrier.wait(timeout=30)
            try:
                result = main.renew_public_photo_folder_deadline(
                    folder_id, main.PhotoFolderDeadlineInput(access_duration_days=7), None, db,
                )
                return 200, result["access_expires_at"]
            except HTTPException as error:
                db.rollback()
                return error.status_code, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(renew) for _ in range(2)]
        results = [future.result(timeout=45) for future in futures]
    assert sorted(result[0] for result in results) == [200, 409]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.event == "photo_folder.deadline_renewed",
        )) == 1


def test_postgres_renewal_waits_for_archive_scope_and_rechecks_media(renewal_postgres, monkeypatch):
    from app import tenant_closure

    factory, tenant_id, gallery_id, folder_id = renewal_postgres
    ready_for_parent = Event()
    original_guard = tenant_closure.require_new_work

    def new_work_guard(*args, **kwargs):
        result = original_guard(*args, **kwargs)
        ready_for_parent.set()
        return result

    monkeypatch.setattr(tenant_closure, "require_new_work", new_work_guard)

    def renew():
        with factory() as db:
            try:
                main.renew_public_photo_folder_deadline(
                    folder_id, main.PhotoFolderDeadlineInput(access_duration_days=7), None, db,
                )
            except HTTPException as error:
                db.rollback()
                return error.status_code
        return 200

    with factory() as archive_db:
        archive_db.scalar(select(ParentGallery).where(ParentGallery.id == gallery_id).with_for_update())
        folder = archive_db.scalar(select(PhotoFolder).where(PhotoFolder.id == folder_id).with_for_update())
        previous = folder.access_expires_at
        archive_db.add(MediaArchiveCycle(
            tenant_id=tenant_id, parent_gallery_id=gallery_id, folder_id=folder_id,
            cycle_number=1, state="archiving",
        ))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(renew)
            assert ready_for_parent.wait(timeout=30)
            assert not future.done()
            archive_db.commit()
            assert future.result(timeout=45) == 409
    with factory() as db:
        assert db.get(PhotoFolder, folder_id).access_expires_at == previous


def test_postgres_renewal_does_not_invert_cycle_scope_locks(renewal_postgres):
    factory, tenant_id, gallery_id, folder_id = renewal_postgres
    with factory() as db:
        cycle = MediaArchiveCycle(
            tenant_id=tenant_id, parent_gallery_id=gallery_id, folder_id=folder_id,
            cycle_number=1, state="local",
        )
        db.add(cycle)
        db.flush()
        notice = MediaArchiveNotice(
            tenant_id=tenant_id, cycle_id=cycle.id, notice_type="window_7_days",
            idempotency_key="concurrent-window", title="Prazo anterior",
            body="Aviso sintético", deadline_at=now() + timedelta(days=28),
        )
        db.add(notice)
        db.commit()
        cycle_id = cycle.id

    def renew():
        with factory() as db:
            return main.renew_public_photo_folder_deadline(
                folder_id, main.PhotoFolderDeadlineInput(access_duration_days=7), None, db,
            )

    with factory() as archive_db:
        archive_db.scalar(select(MediaArchiveCycle).where(
            MediaArchiveCycle.id == cycle_id,
        ).with_for_update())
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(renew).result(timeout=30)
        assert result["can_renew_deadline"] is False
        archive_db.scalar(select(ParentGallery).where(
            ParentGallery.id == gallery_id,
        ).with_for_update())
        folder = archive_db.scalar(select(PhotoFolder).where(
            PhotoFolder.id == folder_id,
        ).with_for_update().execution_options(populate_existing=True))
        assert folder_archive_eligible_at(archive_db, folder) > now()
