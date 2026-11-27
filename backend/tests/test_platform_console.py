"""Contratos de leitura mínima do console global (dados exclusivamente sintéticos)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import photographer_terms as terms
from app import platform_console as console
from app.auth import (
    AdminUser,
    GoogleDriveConnection,
    InstallationOperator,
    MediaArchiveCycle,
    MediaArchiveOperation,
    MediaArchiveRecoveryCreditReservation,
    MediaArchiveRecoveryPricing,
    MediaArchiveRecoveryRequest,
    ParentGallery,
    PhotoFolder,
    PhotographerTermsAcceptance,
    PlatformAdminEvent,
    Tenant,
    TenantAdmin,
    TenantClosureRecoveryBatch,
    TenantClosureRequest,
    now,
    password_hasher,
)
from app.photographer_credits import grant_credits
from app.system_monitor.models import MonitorGrant, PlatformOwner
from tests.test_photographer_credits import create_accounts, create_photo
from tests.test_tenant_client_isolation import client_db as _client_db

UTC = timezone.utc  # noqa: UP017 — compatibilidade com o Python 3.10 do runtime
client_db = _client_db


@pytest.fixture
def http(client_db, monkeypatch):
    owner_tenant, tenant, owner, photographer = create_accounts(client_db)
    client_db.commit()
    session = SimpleNamespace(id=uuid4(), subject_id=owner.id, tenant_id=owner_tenant.id)
    monkeypatch.setattr(console, "SessionLocal", lambda: client_db)
    monkeypatch.setattr(console, "current_session", lambda *_args, **_kwargs: session)
    app = FastAPI()
    app.include_router(console.router)
    app.include_router(terms.router)
    return TestClient(app), session, tenant.id, photographer.id


def test_explicit_directory_includes_no_wallet_suspended_and_ambiguous_accounts(client_db):
    create_accounts(client_db)
    empty = Tenant(status="suspended")
    ambiguous = Tenant()
    client_db.add_all([empty, ambiguous])
    client_db.flush()
    for email in ("hidden-a@example.test", "hidden-b@example.test"):
        admin = AdminUser(email=email, password_hash="synthetic", totp_secret="synthetic")
        admin.tenant_memberships.append(TenantAdmin(tenant_id=ambiguous.id))
        client_db.add(admin)
    client_db.commit()
    assert console.tenant_directory(client_db) == {"items": [], "has_more": False}
    rows = console.tenant_directory(client_db, mode="all")["items"]
    # A fixture mantém também o tenant legado sintético de UUID ...0001.
    assert len(rows) == 5
    assert next(row for row in rows if row["tenant_id"] == str(empty.id))["status"] == "suspended"
    assert next(row for row in rows if row["tenant_id"] == str(ambiguous.id))["admin_email"] is None
    assert all(set(row) == {"tenant_id", "status", "lifecycle", "canonical_host", "canonical_host_status", "photographer_name", "admin_email"} for row in rows)
    pages = [console.tenant_directory(client_db, mode="all", limit=1, offset=index) for index in range(6)]
    assert len({page["items"][0]["tenant_id"] for page in pages[:5]}) == 5
    assert [page["has_more"] for page in pages] == [True, True, True, True, False, False]


def test_directory_reports_lifecycle_separately_from_availability(client_db):
    _owner_tenant, closed_tenant, _owner, _photographer = create_accounts(client_db)
    closed_tenant.status = "suspended"
    closed_tenant.lifecycle = "closed"
    closing_tenant = Tenant(status="active", lifecycle="closing")
    client_db.add(closing_tenant)
    client_db.commit()

    rows = console.tenant_directory(client_db, mode="all")["items"]
    closed = next(item for item in rows if item["tenant_id"] == str(closed_tenant.id))
    closing = next(item for item in rows if item["tenant_id"] == str(closing_tenant.id))
    assert (closed["status"], closed["lifecycle"]) == ("suspended", "closed")
    assert (closing["status"], closing["lifecycle"]) == ("active", "closing")


def test_directory_email_filter_is_literal_and_bounds_are_enforced(client_db):
    _owner_tenant, _tenant, _owner, photographer = create_accounts(client_db)
    photographer.email = "Literal%_tag@example.test"
    client_db.commit()
    assert len(console.tenant_directory(client_db, query="%_", mode="all")["items"]) == 1
    for mode in ("all", "alphabetical", "recent"):
        assert console.tenant_directory(client_db, query="LITERAL%_", mode=mode)["items"][0]["admin_email"] == photographer.email
    for invalid in ({"limit": 21}, {"offset": -1}, {"mode": "unknown"}):
        with pytest.raises(HTTPException) as error:
            console.tenant_directory(client_db, **invalid)
        assert error.value.status_code == 422


def test_owner_http_summary_only_exposes_counts_of_selected_tenant(http, client_db):
    client, session, tenant_id, _ = http
    client_db.add_all([ParentGallery(tenant_id=tenant_id, name="Private target name"),
                       ParentGallery(tenant_id=session.tenant_id, name="Private other name")])
    client_db.commit()
    root = "/admin/platform/console"
    assert client.get(root + "/capabilities").json() == {"read_console": True}
    assert client.get(root + "/tenants").json()["items"] == []
    response = client.get(f"{root}/tenants/{tenant_id}")
    assert response.status_code == 200
    assert {"private", "no-store"} <= set(response.headers["cache-control"].split(", "))
    result = response.json()
    assert result["gallery_count"] == 1 and result["photo_count"] == 0
    assert set(result) == {"tenant_id", "status", "lifecycle", "canonical_host", "canonical_host_status", "photographer_name", "gallery_count", "photo_count", "source", "scope", "observed_at"}
    assert "Private" not in response.text
    assert client.get(f"{root}/tenants/{uuid4()}").status_code == 404


def test_terms_draft_is_owner_only_and_publish_is_explicit_and_reauthenticated(http, client_db, monkeypatch):
    client, session, _tenant_id, photographer_id = http
    root = "/admin/platform/terms"
    initial = client.get(root + "/draft")
    assert initial.status_code == 200 and initial.json()["revision"] is None
    assert "{{provider_legal_name}}" in initial.json()["template_text"]
    assert initial.json()["provider_legal_name"] == ""
    assert initial.json()["provider_contact_email"] == client_db.get(AdminUser, session.subject_id).email
    assert "### 14. Aviso de Privacidade do serviço" in initial.json()["template_text"]
    assert "CPF" in initial.json()["template_text"]
    assert "referência protegida e versionada" in initial.json()["template_text"]
    assert "Google Drive" not in initial.json()["template_text"]
    assert client.get(root + "/versions").json()["items"] == []

    saved = client.put(root + "/draft", json={
        "revision": None, "template_text": initial.json()["template_text"],
        "provider_legal_name": "Provedor sintético", "provider_contact_email": "support@example.test",
    })
    assert saved.status_code == 200
    assert saved.json()["revision"]
    assert client.get(root + "/versions").json()["items"] == []
    assert client.put(root + "/draft", json={
        "revision": None, "template_text": initial.json()["template_text"],
        "provider_legal_name": "Provedor sintético", "provider_contact_email": "support@example.test",
    }).status_code == 409

    reauthenticated = []
    monkeypatch.setattr(terms, "reauthenticate_console_owner",
                        lambda admin, payload: reauthenticated.append((admin.id, payload.current_password.get_secret_value())) or 12345)
    publish_payload = {
        "expected_revision": saved.json()["revision"], "confirm_publication": True,
        "current_password": "synthetic-password", "totp_code": "123456",
    }
    assert client.get(root + "/versions").json()["items"] == []
    published = client.post(root + "/publish", json=publish_payload)
    assert published.status_code == 200 and published.json()["version"] == "v1"
    assert reauthenticated == [(session.subject_id, "synthetic-password")]
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == 12345
    versions = client.get(root + "/versions").json()["items"]
    assert len(versions) == 1 and versions[0]["version"] == "v1"
    assert versions[0]["provider_legal_name"] == "Provedor sintético"
    assert "synthetic-password" not in published.text and "123456" not in published.text

    client_db.add(PhotographerTermsAcceptance(
        admin_user_id=photographer_id, tenant_id=_tenant_id, terms_version="v1",
        terms_text="Protocolo sintético integral", terms_sha256="a" * 64,
        provider_identity="Provedor sintético", photographer_identity="Fotógrafo sintético",
        accepted_at=now(), environment="test",
    ))
    client_db.commit()
    history = client.get(f"{root}/acceptances/{_tenant_id}")
    assert history.status_code == 200
    assert history.json()["items"][0]["text"] == "Protocolo sintético integral"
    assert history.json()["items"][0]["sha256"] == "a" * 64

    session.subject_id, session.tenant_id = photographer_id, _tenant_id
    assert client.get(root + "/draft").status_code == 403
    assert client.get(f"{root}/acceptances/{_tenant_id}").status_code == 403


@pytest.mark.parametrize("action", ["draft", "publish"])
def test_terms_session_revoked_before_commit_preserves_state(http, client_db, monkeypatch, action):
    from sqlalchemy import func

    from app.auth import AuditEvent, PhotographerTermsDraft, PhotographerTermsVersion

    client, session, _tenant_id, _photographer_id = http
    root = "/admin/platform/terms"
    initial = client.get(root + "/draft").json()
    draft_payload = {
        "revision": None, "template_text": initial["template_text"],
        "provider_legal_name": "Provedor sintético", "provider_contact_email": "support@example.test",
    }
    if action == "publish":
        saved = client.put(root + "/draft", json=draft_payload)
        assert saved.status_code == 200
        monkeypatch.setattr(terms, "reauthenticate_console_owner", lambda *_: 12345)
    before_step = client_db.get(AdminUser, session.subject_id).totp_last_used_step
    before_audit = client_db.scalar(select(func.count()).select_from(AuditEvent))
    client_db.commit()
    revoked = False
    real_audit = terms.audit

    def revoke_during_mutation(*args, **kwargs):
        nonlocal revoked
        real_audit(*args, **kwargs)
        revoked = True

    def current_session(*_args, **_kwargs):
        if revoked:
            raise HTTPException(403, "Sessão revogada.")
        return session

    monkeypatch.setattr(terms, "audit", revoke_during_mutation)
    monkeypatch.setattr(console, "current_session", current_session)
    if action == "draft":
        response = client.put(root + "/draft", json=draft_payload)
    else:
        response = client.post(root + "/publish", json={
            "expected_revision": saved.json()["revision"], "confirm_publication": True,
            "current_password": "synthetic-password", "totp_code": "123456",
        })
    assert revoked and response.status_code == 403
    client_db.expire_all()
    assert client_db.scalar(select(func.count()).select_from(PhotographerTermsVersion)) == 0
    assert client_db.scalar(select(func.count()).select_from(PhotographerTermsDraft)) == (action == "publish")
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == before_step
    assert client_db.scalar(select(func.count()).select_from(AuditEvent)) == before_audit


def test_archive_recovery_price_requires_owner_reauthentication_and_is_idempotent(http, client_db, monkeypatch):
    client, session, _tenant_id, photographer_id = http
    root = "/admin/platform/console/media-archive/recovery-pricing"
    initial = client.get(root)
    assert initial.status_code == 200
    assert initial.json()["configured"] is False

    reauthenticated = []
    monkeypatch.setattr(
        console, "reauthenticate_console_owner",
        lambda admin, payload: reauthenticated.append((admin.id, payload.current_password.get_secret_value())) or 12345,
    )
    request_id = str(uuid4())
    payload = {
        "request_id": request_id,
        "recovery_fee_credits": 9,
        "current_password": "synthetic-password",
        "totp_code": "123456",
    }
    saved = client.put(root, json=payload)
    assert saved.status_code == 200
    assert saved.json()["recovery_fee_credits"] == 9
    assert saved.json()["configured"] is True and saved.json()["replayed"] is False
    assert reauthenticated == [(session.subject_id, "synthetic-password")]
    assert client_db.get(MediaArchiveRecoveryPricing, 1).recovery_fee_credits == 9
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == 12345
    assert "synthetic-password" not in saved.text and "123456" not in saved.text

    replay = client.put(root, json=payload)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert replay.json()["recovery_fee_credits"] == 9
    assert len(reauthenticated) == 1

    session.subject_id = photographer_id
    denied = client.get(root)
    assert denied.status_code == 403


def test_owner_retry_route_reauthenticates_and_uses_original_fee_snapshot(http, client_db, monkeypatch):
    client, session, tenant_id, photographer_id = http
    photo = create_photo(client_db, tenant_id)
    folder = client_db.get(PhotoFolder, photo.folder_id)
    cycle = MediaArchiveCycle(
        tenant_id=tenant_id,
        parent_gallery_id=photo.parent_gallery_id,
        folder_id=folder.id,
        cycle_number=1,
        state="archived",
        manifest_sha256="a" * 64,
        object_count=1,
        total_bytes=1,
        archived_at=now(),
    )
    client_db.add(cycle)
    client_db.flush()
    failed = MediaArchiveOperation(
        tenant_id=tenant_id,
        cycle_id=cycle.id,
        operation_type="restore",
        status="failed",
        idempotency_key="synthetic-failed-recovery",
        actor_type="tenant",
        actor_admin_id=photographer_id,
        last_error_code="drive_unavailable",
        last_error="Falha comprovada na operação; mídia preservada.",
    )
    client_db.add(failed)
    client_db.flush()
    failed_operation_id = failed.id
    client_db.add_all([
        MediaArchiveRecoveryRequest(
            tenant_id=tenant_id,
            operation_id=failed.id,
            cycle_id=cycle.id,
            requester_type="tenant",
            requested_by_admin_id=photographer_id,
            requested_by_tenant_admin_id=photographer_id,
            duration_days=14,
            fee_credits_snapshot=2,
            owner_exempt=False,
        ),
        MediaArchiveRecoveryCreditReservation(
            tenant_id=tenant_id,
            operation_id=failed.id,
            reserved_credits=2,
            status="released",
        ),
        MediaArchiveRecoveryPricing(
            id=1,
            recovery_fee_credits=9,
            updated_by_admin_id=session.subject_id,
        ),
    ])
    grant_credits(
        client_db, session.subject_id, tenant_id, 5,
        "synthetic-owner-retry-grant", "synthetic-owner-retry",
    )
    client_db.commit()

    reauthenticated = []
    monkeypatch.setattr(
        console, "reauthenticate_console_owner",
        lambda admin, payload: reauthenticated.append((admin.id, payload.current_password.get_secret_value())) or 54321,
    )
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *args, **kwargs: None)
    route = (
        f"/admin/platform/console/credit-tenants/{tenant_id}/media-archive/"
        f"recoveries/{failed_operation_id}/retry"
    )
    payload = {
        "duration_days": 14,
        "idempotency_key": "synthetic-owner-retry",
        "current_password": "synthetic-password",
        "totp_code": "123456",
    }

    response = client.post(route, json=payload)
    assert response.status_code == 202
    assert response.json()["fee_credits"] == 2
    assert response.json()["duration_days"] == 14
    assert response.json()["retry_of_operation_id"] == str(failed_operation_id)
    assert reauthenticated == [(session.subject_id, "synthetic-password")]
    retry = client_db.scalar(select(MediaArchiveOperation).where(
        MediaArchiveOperation.tenant_id == tenant_id,
        MediaArchiveOperation.idempotency_key == "synthetic-owner-retry",
    ))
    request = client_db.scalar(select(MediaArchiveRecoveryRequest).where(
        MediaArchiveRecoveryRequest.tenant_id == tenant_id,
        MediaArchiveRecoveryRequest.operation_id == retry.id,
    ))
    reservation = client_db.scalar(select(MediaArchiveRecoveryCreditReservation).where(
        MediaArchiveRecoveryCreditReservation.tenant_id == tenant_id,
        MediaArchiveRecoveryCreditReservation.operation_id == retry.id,
    ))
    assert retry.actor_type == "owner" and retry.actor_admin_id == session.subject_id
    assert request.requester_type == "owner" and request.retry_of_operation_id == failed_operation_id
    assert request.fee_credits_snapshot == 2 and request.owner_exempt is False
    assert reservation.status == "reserved" and reservation.reserved_credits == 2
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == 54321
    assert "synthetic-password" not in response.text and "123456" not in response.text

    replay = client.post(route, json=payload)
    assert replay.status_code == 202
    assert replay.json()["operation_id"] == response.json()["operation_id"]
    assert len(reauthenticated) == 1


def test_technical_grants_never_authorize_console_or_reveal_target_existence(http, client_db):
    client, session, tenant_id, photographer_id = http
    client_db.add(InstallationOperator(admin_user_id=photographer_id, active=True,
        authorization_reference="synthetic", granted_at=now(), updated_at=now()))
    for permission in ("metrics", "tree", "incidents", "export"):
        client_db.add(MonitorGrant(admin_user_id=photographer_id, permission=permission,
            active=True, authorization_reference="synthetic"))
    client_db.commit()
    session.subject_id, session.tenant_id = photographer_id, tenant_id
    root = "/admin/platform/console"
    assert client.get(root + "/capabilities").json() == {"read_console": False}
    for path in ("/tenants?mode=all", f"/tenants/{tenant_id}", f"/tenants/{uuid4()}", "/sources"):
        response = client.get(root + path)
        assert response.status_code == 403
        assert {"private", "no-store"} <= set(response.headers["cache-control"].split(", "))
        assert response.json() == {"detail": "Acesso não autorizado."}


def test_revocation_during_read_prevents_response(http, client_db, monkeypatch):
    client, _session, _tenant_id, _ = http
    original = console.tenant_directory

    def revoke(db, **parameters):
        result = original(db, **parameters)
        db.delete(db.get(PlatformOwner, 1))
        db.commit()
        return result

    monkeypatch.setattr(console, "tenant_directory", revoke)
    response = client.get("/admin/platform/console/tenants?mode=all")
    assert response.status_code == 403
    assert "items" not in response.json()


def test_session_and_membership_are_revalidated_and_sources_do_not_claim_health(http, client_db, monkeypatch):
    client, session, _tenant_id, _ = http
    response = client.get("/admin/platform/console/sources")
    assert response.status_code == 200
    assert {item["key"] for item in response.json()["items"]} == {"backup", "drive", "archive", "restore"}
    sources = {item["key"]: item for item in response.json()["items"]}
    assert all(sources[key]["state"] == "unknown" and sources[key]["source"] is None
               and sources[key]["observed_at"] is None for key in ("backup", "archive", "restore"))
    assert sources["drive"]["state"] == sources["drive"]["availability"] == "unknown"
    assert sources["drive"]["source"] == "application_database.google_drive_connection"
    assert sources["drive"]["scope"] == "platform_owner"
    assert sources["drive"]["observed_at"] is not None
    assert sources["drive"]["quota_observed_at"] is None
    membership = client_db.scalar(select(TenantAdmin).where(TenantAdmin.admin_user_id == session.subject_id))
    membership.active = False
    client_db.commit()
    assert client.get("/admin/platform/console/tenants?mode=all").status_code == 403


def test_drive_source_exposes_only_persisted_owner_state_and_quota_without_claiming_health(http, client_db):
    client, session, _tenant_id, _ = http
    connection = GoogleDriveConnection(
        tenant_id=session.tenant_id, connected_by_admin_id=session.subject_id,
        refresh_token_envelope={"ciphertext": "synthetic-refresh-token"},
        scopes="https://www.googleapis.com/auth/drive.file", state="connected",
        connected_at=now(), updated_at=now(), quota_limit="109951162777600",
        quota_usage="54975581388800", quota_observed_at=now(),
    )
    client_db.add(connection)
    client_db.commit()

    result = client.get("/admin/platform/console/sources")
    assert result.status_code == 200
    drive = next(item for item in result.json()["items"] if item["key"] == "drive")
    assert drive["state"] == "connected"
    assert drive["availability"] == "authorization_recorded"
    assert drive["scope"] == "platform_owner"
    assert drive["source"] == "application_database.google_drive_connection"
    assert drive["quota_limit"] == "109951162777600"
    assert drive["quota_usage"] == "54975581388800"
    assert drive["quota_observed_at"] is not None
    assert "healthy" not in result.text.lower() and "availability atual" not in result.text.lower()
    assert "synthetic-refresh-token" not in result.text and "ciphertext" not in result.text

    connection = client_db.merge(connection)
    connection.state = "revoked"
    client_db.commit()
    drive = next(item for item in client.get("/admin/platform/console/sources").json()["items"] if item["key"] == "drive")
    assert drive["state"] == drive["availability"] == "revoked"
    assert drive["quota_limit"] is None and drive["quota_usage"] is None and drive["quota_observed_at"] is None

    connection = client_db.merge(connection)
    connection.state = "reauthorization_required"
    client_db.commit()
    drive = next(item for item in client.get("/admin/platform/console/sources").json()["items"] if item["key"] == "drive")
    assert drive["state"] == drive["availability"] == "reauthorization_required"


def test_session_change_after_collection_is_denied(http, monkeypatch):
    client, session, _tenant_id, _ = http
    calls = 0

    def renewed(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return session if calls == 1 else SimpleNamespace(id=uuid4(), subject_id=session.subject_id, tenant_id=session.tenant_id)

    monkeypatch.setattr(console, "current_session", renewed)
    assert client.get("/admin/platform/console/tenants?mode=all").status_code == 403


def test_console_never_provisions_or_approves_website_registration(http, client_db):
    client, _session, _tenant_id, _ = http
    from sqlalchemy import func
    before = client_db.scalar(select(func.count()).select_from(Tenant))
    for path in ("/tenants", "/onboarding", "/invitations", "/signups/approve"):
        response = client.post("/admin/platform/console" + path,
                               json={"name": "Synthetic applicant", "email": "new@example.test"})
        assert response.status_code in {404, 405}
    assert client_db.scalar(select(func.count()).select_from(Tenant)) == before


def test_hostname_activation_rejects_cross_origin_and_audits_owner_confirmation(http, client_db):
    from hashlib import sha256

    client, session, tenant_id, _ = http
    owner = client_db.get(AdminUser, session.subject_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    target = client_db.get(Tenant, tenant_id)
    target.canonical_host = "synthetic.pickyourpic.com.br"
    target.canonical_host_status = "reserved"
    client_db.commit()
    path = f"/admin/platform/console/tenants/{tenant_id}/hostname/activate"
    body = {"request_id": str(uuid4()), "expected_hostname": target.canonical_host,
            "expected_status": "reserved", "evidence_sha256": sha256(b"readiness").hexdigest(),
            "confirm_readiness": True, "current_password": "SyntheticOwnerPassword!2026",
            "totp_code": pyotp.TOTP("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP").now()}
    cross_origin = client.post(path, json=body, headers={"origin": "https://attacker.invalid"})
    assert cross_origin.status_code == 403
    assert client_db.get(Tenant, tenant_id).canonical_host_status == "reserved"

    response = client.post(path, json=body)
    assert response.status_code == 200
    assert response.json()["canonical_host_status"] == "ready"
    assert "SyntheticOwnerPassword!2026" not in response.text
    assert "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP" not in response.text
    event = client_db.scalar(select(PlatformAdminEvent).where(PlatformAdminEvent.action == "tenant.host_ready"))
    assert event.evidence_sha256 == body["evidence_sha256"]
    assert "SyntheticOwnerPassword!2026" not in str(event.__dict__)
    assert "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP" not in str(event.__dict__)


def test_hostname_activation_denies_installation_operator_even_with_console_grants(http, client_db):
    client, session, tenant_id, photographer_id = http
    target = client_db.get(Tenant, tenant_id)
    target.canonical_host = "operator-target.pickyourpic.com.br"
    target.canonical_host_status = "reserved"
    client_db.add(InstallationOperator(admin_user_id=photographer_id, active=True,
        authorization_reference="synthetic", granted_at=now(), updated_at=now()))
    client_db.add_all([MonitorGrant(admin_user_id=photographer_id, permission=permission, active=True,
        authorization_reference="synthetic") for permission in ("metrics", "tree", "incidents", "export")])
    client_db.commit()
    session.subject_id, session.tenant_id = photographer_id, tenant_id
    response = client.post(f"/admin/platform/console/tenants/{tenant_id}/hostname/activate", json={
        "request_id": str(uuid4()), "expected_hostname": target.canonical_host,
        "expected_status": "reserved", "evidence_sha256": "a" * 64, "confirm_readiness": True,
        "current_password": "synthetic", "totp_code": "123456",
    })
    assert response.status_code == 403
    assert client_db.get(Tenant, tenant_id).canonical_host_status == "reserved"


def test_owner_closure_recovery_batch_requires_reauth_and_replays_idempotently(
    http, client_db, monkeypatch,
):
    client, session, tenant_id, photographer_id = http
    import pyotp

    from app import main

    owner = client_db.get(AdminUser, session.subject_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    tenant = client_db.get(Tenant, tenant_id)
    tenant.status = "suspended"
    tenant.lifecycle = "closed"
    client_db.add(TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=now(),
        closed_at=now(),
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    ))
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *args, **kwargs: None)

    request_id = uuid4()
    body = {
        "request_id": str(request_id),
        "duration_days": 14,
        "current_password": "SyntheticOwnerPassword!2026",
        "totp_code": pyotp.TOTP(owner.totp_secret).now(),
    }
    path = f"/admin/platform/console/tenants/{tenant_id}/closure/recovery-batches"
    response = client.post(path, json=body)
    assert response.status_code == 202, response.text
    result = response.json()
    assert result["state"] == "completed" and result["operations"] == []
    assert result["replayed"] is False
    assert "SyntheticOwnerPassword!2026" not in response.text
    assert body["totp_code"] not in response.text
    batch = client_db.scalar(select(TenantClosureRecoveryBatch).where(
        TenantClosureRecoveryBatch.tenant_id == tenant_id,
        TenantClosureRecoveryBatch.request_id == request_id,
    ))
    assert batch is not None and batch.duration_days == 14
    used_step = client_db.get(AdminUser, session.subject_id).totp_last_used_step

    replay = client.post(path, json=body)
    assert replay.status_code == 202, replay.text
    assert replay.json()["batch_id"] == result["batch_id"]
    assert replay.json()["replayed"] is True
    assert client_db.get(AdminUser, session.subject_id).totp_last_used_step == used_step

    status = client.get(path + f"/{result['batch_id']}")
    assert status.status_code == 200
    assert status.json()["batch_id"] == result["batch_id"]
    assert {"private", "no-store"} <= set(status.headers["cache-control"].split(", "))


def test_owner_closure_recovery_batch_rechecks_idempotency_after_admin_lock(
    http, client_db, monkeypatch,
):
    client, session, tenant_id, photographer_id = http
    from app import main, tenant_closure_recovery

    owner_id = session.subject_id
    owner = client_db.get(AdminUser, owner_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    client_db.get(Tenant, tenant_id).lifecycle = "closed"
    closed_at = now() - timedelta(days=1)
    closure = TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=closed_at,
        closed_at=closed_at,
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    )
    client_db.add(closure)
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)

    def unexpected(*_args, **_kwargs):
        raise AssertionError("a concurrent replay must not repeat rate limiting or TOTP")

    monkeypatch.setattr(console, "enforce_rate_limit", unexpected)
    monkeypatch.setattr(console, "reauthenticate_console_owner", unexpected)
    request_id = uuid4()
    batch_id = uuid4()
    response_payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "state": "completed",
        "duration_days": 14,
        "created_at": now().isoformat(),
        "operations": [],
        "replayed": True,
    }
    calls = []

    def replay_existing_batch(db, **kwargs):
        calls.append(kwargs)
        return response_payload

    monkeypatch.setattr(tenant_closure_recovery, "request_batch", replay_existing_batch)
    scalar = client_db.scalar
    injected = False

    def inject_completed_batch_after_admin_lock(statement, *args, **kwargs):
        nonlocal injected
        result = scalar(statement, *args, **kwargs)
        if (
            not injected
            and getattr(statement, "_for_update_arg", None) is not None
            and "admin_user" in str(statement).lower()
        ):
            client_db.add(TenantClosureRecoveryBatch(
                id=batch_id,
                tenant_id=tenant_id,
                closure_request_id=closure.id,
                requested_by_owner_admin_id=owner_id,
                request_id=request_id,
                duration_days=14,
            ))
            client_db.commit()
            injected = True
        return result

    monkeypatch.setattr(client_db, "scalar", inject_completed_batch_after_admin_lock)
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/recovery-batches",
        json={
            "request_id": str(request_id),
            "duration_days": 14,
            "current_password": "SyntheticOwnerPassword!2026",
            "totp_code": pyotp.TOTP(owner.totp_secret).now(),
        },
    )

    assert injected is True
    assert response.status_code == 202, response.text
    assert response.json()["replayed"] is True
    assert calls == [{
        "owner_id": owner_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "duration_days": 14,
    }]


def test_owner_closure_recovery_batch_rolls_back_when_session_changes_before_commit(
    http, client_db, monkeypatch,
):
    client, session, tenant_id, photographer_id = http
    from app import main

    owner = client_db.get(AdminUser, session.subject_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    tenant = client_db.get(Tenant, tenant_id)
    tenant.lifecycle = "closed"
    request_id = uuid4()
    client_db.add(TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=now(),
        closed_at=now(),
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    ))
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *args, **kwargs: None)

    calls = 0

    def changed_session(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return SimpleNamespace(id=uuid4(), subject_id=session.subject_id, tenant_id=session.tenant_id)
        return session

    monkeypatch.setattr(console, "current_session", changed_session)
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/recovery-batches",
        json={
            "request_id": str(request_id),
            "duration_days": 14,
            "current_password": "SyntheticOwnerPassword!2026",
            "totp_code": pyotp.TOTP(owner.totp_secret).now(),
        },
    )

    assert response.status_code == 403
    assert calls == 2
    assert client_db.scalar(select(TenantClosureRecoveryBatch).where(
        TenantClosureRecoveryBatch.tenant_id == tenant_id,
        TenantClosureRecoveryBatch.request_id == request_id,
    )) is None
    assert client_db.get(AdminUser, session.subject_id, populate_existing=True).totp_last_used_step is None


def test_owner_reopens_only_after_explicit_reauthenticated_action_and_preserves_suspension(
    http, client_db, monkeypatch,
):
    client, session, tenant_id, photographer_id = http
    import pyotp

    from app import main

    owner = client_db.get(AdminUser, session.subject_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    tenant = client_db.get(Tenant, tenant_id)
    tenant.status = "suspended"
    tenant.lifecycle = "closed"
    client_db.add(TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=now(),
        closed_at=now(),
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    ))
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *args, **kwargs: None)

    body = {
        "request_id": str(uuid4()),
        "current_password": "SyntheticOwnerPassword!2026",
        "totp_code": pyotp.TOTP(owner.totp_secret).now(),
    }
    path = f"/admin/platform/console/tenants/{tenant_id}/closure/reopen"
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["lifecycle"] == "open"
    assert response.json()["availability"] == "suspended"
    tenant_after = client_db.get(Tenant, tenant_id, populate_existing=True)
    assert tenant_after.lifecycle == "open" and tenant_after.status == "suspended"
    event = client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == UUID(body["request_id"]),
    ))
    assert event.action == "tenant.reopened" and event.result == "success"

    replay = client.post(path, json=body)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert "SyntheticOwnerPassword!2026" not in replay.text
    assert body["totp_code"] not in replay.text


def test_owner_reopen_rolls_back_when_session_changes_before_commit(http, client_db, monkeypatch):
    client, session, tenant_id, photographer_id = http
    from app import main

    owner = client_db.get(AdminUser, session.subject_id)
    owner.password_hash = password_hasher.hash("SyntheticOwnerPassword!2026")
    owner.totp_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    tenant = client_db.get(Tenant, tenant_id)
    tenant.lifecycle = "closed"
    closure = TenantClosureRequest(
        tenant_id=tenant_id,
        request_id=uuid4(),
        requested_by=photographer_id,
        state="closed",
        requested_at=now(),
        closed_at=now(),
        terms_version="synthetic-closure",
        terms_sha256="a" * 64,
        balance_snapshot=0,
        balance_acknowledged=True,
    )
    client_db.add(closure)
    client_db.flush()
    closure_id = closure.id
    client_db.commit()
    monkeypatch.setattr(main, "require_same_origin", lambda _request: None)
    monkeypatch.setattr(console, "enforce_rate_limit", lambda *args, **kwargs: None)

    calls = 0

    def changed_session(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return SimpleNamespace(id=uuid4(), subject_id=session.subject_id, tenant_id=session.tenant_id)
        return session

    monkeypatch.setattr(console, "current_session", changed_session)
    request_id = uuid4()
    response = client.post(
        f"/admin/platform/console/tenants/{tenant_id}/closure/reopen",
        json={
            "request_id": str(request_id),
            "current_password": "SyntheticOwnerPassword!2026",
            "totp_code": pyotp.TOTP(owner.totp_secret).now(),
        },
    )

    assert response.status_code == 403
    assert calls == 2
    assert client_db.get(Tenant, tenant_id, populate_existing=True).lifecycle == "closed"
    assert client_db.get(TenantClosureRequest, closure_id, populate_existing=True).state == "closed"
    assert client_db.scalar(select(PlatformAdminEvent).where(
        PlatformAdminEvent.request_id == request_id,
    )) is None
    assert client_db.get(AdminUser, session.subject_id, populate_existing=True).totp_last_used_step is None


def test_owner_closure_status_uses_current_cycle_utc_anniversary_and_hides_identity(
    http, client_db, monkeypatch,
):
    from app import tenant_closure_recovery

    client, _session, tenant_id, photographer_id = http
    tenant = client_db.get(Tenant, tenant_id)
    tenant.status = "suspended"
    tenant.lifecycle = "closed"
    previous_closed = datetime(2010, 1, 1, 9, 0, tzinfo=UTC)
    previous_reopened = datetime(2010, 2, 1, 9, 0, tzinfo=UTC)
    local_closed = datetime(2024, 2, 29, 8, 30, tzinfo=timezone(timedelta(hours=-3)))
    current_closed = datetime(2024, 2, 29, 11, 30, tzinfo=UTC)
    assert tenant_closure_recovery._as_utc(local_closed) == current_closed
    client_db.add_all([
        TenantClosureRequest(
            tenant_id=tenant_id, request_id=uuid4(), requested_by=photographer_id,
            state="reopened", requested_at=previous_closed, closed_at=previous_closed,
            reopened_at=previous_reopened, terms_version="synthetic-old",
            terms_sha256="b" * 64, balance_snapshot=0, balance_acknowledged=True,
        ),
        TenantClosureRequest(
            tenant_id=tenant_id, request_id=uuid4(), requested_by=photographer_id,
            state="closed", requested_at=current_closed, closed_at=current_closed,
            terms_version="synthetic-current", terms_sha256="a" * 64,
            balance_snapshot=0, balance_acknowledged=True,
        ),
    ])
    client_db.commit()

    monkeypatch.setattr(tenant_closure_recovery, "now", lambda: datetime(2034, 2, 28, 11, 29, tzinfo=UTC))
    path = f"/admin/platform/console/tenants/{tenant_id}/closure"
    before = client.get(path)
    assert before.status_code == 200, before.text
    assert {"private", "no-store"} <= set(before.headers["cache-control"].split(", "))
    assert before.json()["lifecycle"] == "closed"
    assert before.json()["availability"] == "suspended"
    assert before.json()["closed_at"] == datetime(2024, 2, 29, 11, 30, tzinfo=UTC).isoformat()
    assert before.json()["review_at"] == datetime(2034, 2, 28, 11, 30, tzinfo=UTC).isoformat()
    assert before.json()["review_due"] is False
    assert before.json()["reopen_blocker"] is None
    # A frase de confirmação pode citar CPF; valores/campos pessoais continuam ausentes.
    assert '"cpf"' not in before.text.lower() and "fingerprint" not in before.text.lower()
    assert "cpf_envelope" not in before.text and "address_envelope" not in before.text
    assert set(before.json()["profile_retention"]) == {
        "state", "eligible", "blocker", "confirmation_phrase", "reduced_at",
    }
    assert "terms_sha256" not in before.text and "balance_snapshot" not in before.text

    monkeypatch.setattr(tenant_closure_recovery, "now", lambda: datetime(2034, 2, 28, 11, 30, tzinfo=UTC))
    at_anniversary = client.get(path)
    assert at_anniversary.status_code == 200, at_anniversary.text
    assert at_anniversary.json()["review_due"] is True
    assert at_anniversary.json()["reopen_blocker"] == "identity_confirmation_required"
    assert at_anniversary.json()["closed_at"] == datetime(2024, 2, 29, 11, 30, tzinfo=UTC).isoformat()


def test_closed_tenant_cannot_be_activated_through_availability_control(http, client_db):
    _client, session, tenant_id, _photographer_id = http
    target = client_db.get(Tenant, tenant_id)
    target.status = "suspended"
    target.lifecycle = "closed"
    client_db.commit()
    payload = console.StatusInput(
        request_id=uuid4(), expected_status="suspended", status="active",
        current_password="SyntheticOwnerPassword!2026", totp_code="123456",
    )
    with pytest.raises(HTTPException) as error:
        console.change_tenant_status(client_db, session, tenant_id, payload)
    assert error.value.status_code == 409
    assert "fluxo próprio" in error.value.detail
    client_db.refresh(target)
    assert target.lifecycle == "closed" and target.status == "suspended"


def test_closure_console_requires_platform_owner(http):
    client, session, tenant_id, photographer_id = http
    session.subject_id = photographer_id
    response = client.get(f"/admin/platform/console/tenants/{tenant_id}/closure")
    assert response.status_code == 403
    assert "closed_at" not in response.text and "fingerprint" not in response.text.lower()


def test_closed_lifecycle_without_matching_latest_cycle_fails_closed(http, client_db):
    client, _session, tenant_id, photographer_id = http
    tenant = client_db.get(Tenant, tenant_id)
    tenant.lifecycle = "closed"
    client_db.add(TenantClosureRequest(
        tenant_id=tenant_id, request_id=uuid4(), requested_by=photographer_id,
        state="reopened", requested_at=now(), closed_at=now(), reopened_at=now(),
        terms_version="synthetic-previous", terms_sha256="c" * 64,
        balance_snapshot=0, balance_acknowledged=True,
    ))
    client_db.commit()
    response = client.get(f"/admin/platform/console/tenants/{tenant_id}/closure")
    assert response.status_code == 200, response.text
    assert response.json()["history_state"] == "unavailable"
    assert response.json()["closed_at"] is None
    assert response.json()["review_due"] is None
    assert response.json()["reopen_blocker"] == "closure_history_unavailable"


def test_hostname_activation_validation_never_echoes_credentials():
    from fastapi.exceptions import RequestValidationError

    from app.main import protect_credential_validation_input

    app = FastAPI()
    app.add_exception_handler(RequestValidationError, protect_credential_validation_input)
    app.include_router(console.router)
    client = TestClient(app)
    payload = {"request_id": str(uuid4()), "expected_hostname": "synthetic.pickyourpic.com.br",
               "expected_status": "reserved", "evidence_sha256": "a" * 64, "confirm_readiness": True,
               "current_password": "SyntheticValidationPassword!2026", "totp_code": "111222"}
    missing_hash = {key: value for key, value in payload.items() if key != "evidence_sha256"}
    for invalid in (missing_hash, {**payload, "evidence_sha256": "invalid"},
                    {**payload, "confirm_readiness": False}):
        response = client.post(f"/admin/platform/console/tenants/{uuid4()}/hostname/activate", json=invalid)
        assert response.status_code == 422
        assert response.json() == {"detail": "Confira os dados da solicitação."}
        assert "no-store" in response.headers["cache-control"]
        assert payload["current_password"] not in response.text and payload["totp_code"] not in response.text
