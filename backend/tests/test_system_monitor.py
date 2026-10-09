"""Contratos sintéticos: ORM em memória e funções, sem servidor/TestClient/rede."""
import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth import AdminUser, AuthSession, Base, Client, Tenant, TenantAdmin
from app.system_monitor import activity, telemetry
from app.system_monitor.access import require_permission
from app.system_monitor.config import Settings
from app.system_monitor.host import read_host
from app.system_monitor.incidents import evaluate
from app.system_monitor.models import (
    MonitorActivity,
    MonitorBucket,
    MonitorGrant,
    MonitorIncident,
    MonitorSample,
    MonitorTransition,
    PlatformOwner,
)
from app.system_monitor.report import build_report, export_report, safe_sample
from app.system_monitor.store import operation_summary, prune, save_buckets

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLED", "true")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def user(db, role="client", tenant=None, *, owner=True):
    tenant = tenant or Tenant(id=uuid4(), status="active")
    db.add(tenant)
    if role == "client":
        subject = Client(id=uuid4(), tenant_id=tenant.id, full_name="Cliente sintético", phone_e164="+5511999990000")
    else:
        subject = AdminUser(id=uuid4(), email=f"{uuid4()}@example.invalid", password_hash="synthetic", totp_secret="synthetic", email_verified=True)
        db.add(TenantAdmin(tenant_id=tenant.id, admin_user_id=subject.id, active=True))
        if owner:
            db.add(PlatformOwner(singleton=1, admin_user_id=subject.id, authorization_reference="synthetic-test"))
    db.add(subject)
    session = AuthSession(id=uuid4(), tenant_id=tenant.id, subject_id=subject.id,
        role=role, token_hash=str(uuid4()), expires_at=NOW + timedelta(hours=1),
        client_subject_id=subject.id if role == "client" else None,
        admin_subject_id=subject.id if role == "admin" else None)
    db.add(session)
    db.flush()
    return tenant, subject, session


def test_permissions_are_explicit_and_independent(db):
    _tenant, admin, _session = user(db, "admin")
    with pytest.raises(HTTPException) as denied:
        require_permission(db, admin.id, "tree")
    assert denied.value.status_code == 403
    db.add(MonitorGrant(admin_user_id=admin.id, permission="metrics", active=True,
                        authorization_reference="synthetic-test"))
    db.flush()
    require_permission(db, admin.id, "metrics")
    with pytest.raises(HTTPException):
        require_permission(db, admin.id, "export")
    db.get(MonitorGrant, (admin.id, "metrics")).active = False
    db.flush()
    with pytest.raises(HTTPException):
        require_permission(db, admin.id, "metrics")


def test_histogram_merges_counts_and_never_averages_percentiles(db):
    for _ in range(2):
        save_buckets(db, {(NOW - timedelta(minutes=1), "http.gallery", 2): [10, 1, 2, 1000]})
    result = operation_summary(db, NOW - timedelta(minutes=5), NOW)[0]
    assert result["count"] == 20 and result["errors"] == 2 and result["rejected"] == 4
    assert result["latency"] == {"samples": 20, "method": "histogram_upper_bound_ms", "p50": 100, "p95": 100, "p99": None}
    assert telemetry.percentiles({11: 100})["p99"] is None  # overflow has no finite upper bound


def test_activity_does_not_confuse_sessions_and_presence(db):
    tenant, _client, session = user(db)
    db.add(MonitorSample(minute=NOW, payload={}))
    db.flush()
    assert activity.page(db, NOW, tenant_id=tenant.id)["items"][0]["state"] == "valid_session"
    activity.signal(db, session.id, NOW)
    activity.signal(db, session.id, NOW + timedelta(seconds=20))
    assert db.get(MonitorActivity, session.id).last_activity.replace(tzinfo=UTC) == NOW
    assert activity.page(db, NOW, tenant_id=tenant.id)["items"][0]["state"] == "active"
    session.revoked_at = NOW
    db.flush()
    assert activity.page(db, NOW, tenant_id=tenant.id)["items"][0]["state"] == "inactive"
    assert activity.page(db, NOW + timedelta(minutes=5), tenant_id=tenant.id)["items"][0]["state"] == "unknown"


def test_tree_pages_isolate_tenants_and_filter_before_limit(db):
    tenant, client, _session = user(db)
    _other, other_client, _session2 = user(db)
    db.add(MonitorSample(minute=NOW, payload={}))
    db.flush()
    data = activity.page(db, NOW, tenant_id=tenant.id, query="sintético")
    assert [row["id"] for row in data["items"]] == [str(client.id)]
    assert str(other_client.id) not in json.dumps(data)
    assert activity.page(db, NOW, tenant_id=tenant.id, state="active")["items"] == []
    first = activity.page(db, NOW, limit=1)
    from uuid import UUID
    second = activity.page(db, NOW, cursor=UUID(first["next_cursor"]), limit=1)
    assert first["items"][0]["id"] != second["items"][0]["id"]


def test_incidents_require_persistence_deduplicate_and_recover(db):
    settings = Settings()
    for seconds in (0, 60, 120, 180):
        evaluate(db, {"errors.http.gallery": (10, 5)}, NOW + timedelta(seconds=seconds), settings)
        db.flush()
    assert db.get(MonitorIncident, "errors.http.gallery").state == "active"
    assert len(db.scalars(select(MonitorTransition)).all()) == 1
    evaluate(db, {"errors.http.gallery": (None, 5)}, NOW + timedelta(seconds=200), settings)
    assert db.get(MonitorIncident, "errors.http.gallery").state == "active"
    evaluate(db, {"errors.http.gallery": (0, 5)}, NOW + timedelta(seconds=240), settings)
    db.flush()
    assert db.get(MonitorIncident, "errors.http.gallery").state == "resolved"
    assert len(db.scalars(select(MonitorTransition)).all()) == 2


def test_absent_stale_and_private_data_are_not_success_or_exported(db):
    assert build_report(db, NOW)["state"] == "unknown"
    db.add(MonitorSample(minute=NOW - timedelta(minutes=10), payload={"token": "PRIVATE", "client": "NAME"}))
    db.flush()
    result = build_report(db, NOW)
    assert result["state"] == "stale"
    assert result["latest"]["host"]["data"] is None
    assert "PRIVATE" not in export_report(result)
    assert "NAME" not in export_report(result)
    assert safe_sample({"storage": {"registered_file_bytes": "SECRET"}})["storage"]["registered_file_bytes"] is None
    with pytest.raises(ValueError):
        export_report({"large": "x" * 1048576})


def test_host_contract_rejects_unknown_fields_future_and_marks_stale(tmp_path):
    path = tmp_path / "host.json"
    payload = {"schema_version": 1, "source": "linux_procfs", "scope": "host", "collected_at": NOW.isoformat(), "cpu_percent": 20.0}
    path.write_text(json.dumps(payload))
    assert read_host(NOW, str(path))["status"] == "observed"
    assert read_host(NOW + timedelta(minutes=4), str(path))["status"] == "stale"
    assert read_host(NOW - timedelta(minutes=4), str(path))["status"] == "unavailable"
    payload["token"] = "PRIVATE"
    path.write_text(json.dumps(payload))
    assert read_host(NOW, str(path))["data"] is None


def test_retention_only_deletes_monitor_records(db):
    tenant, client, session = user(db)
    db.add(MonitorActivity(session_id=session.id, last_activity=NOW - timedelta(days=2)))
    db.add(MonitorSample(minute=NOW - timedelta(days=8), payload={}))
    db.flush()
    prune(db, NOW, Settings())
    assert db.get(Client, client.id) and db.get(Tenant, tenant.id)
    assert db.get(AuthSession, session.id)
    assert db.get(MonitorActivity, session.id) is None
    assert db.scalars(select(MonitorSample)).all() == []


def test_http_instrumentation_finishes_stream_without_storing_url(monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLED", "true")
    telemetry.drain()
    async def app(scope, receive, send):
        scope["route"] = SimpleNamespace(path="/gallery/{gallery_id}")
        await send({"type": "http.response.start", "status": 500, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
    async def send(message):
        return None
    asyncio.run(telemetry.MonitorMiddleware(app)({"type": "http", "path": "/gallery/PRIVATE"}, None, send))
    buckets, _, _ = telemetry.drain()
    assert len(buckets) == 1
    assert next(iter(buckets))[1] == "http.gallery"
    assert next(iter(buckets.values()))[1] == 1
    assert "PRIVATE" not in str(buckets)


def test_disabled_monitor_denials_are_not_cacheable(monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLED", "false")
    messages = []
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 403, "headers": []})
        await send({"type": "http.response.body", "body": b""})
    async def send(message):
        messages.append(message)
    asyncio.run(telemetry.MonitorMiddleware(app)({"type": "http", "path": "/admin/system-monitor/tree"}, None, send))
    assert (b"cache-control", b"private, no-store") in messages[0]["headers"]


def route_context(db, monkeypatch, role="admin", *, owner=True):
    from app import auth
    from app.system_monitor import routes
    tenant, subject, session = user(db, role, owner=owner)
    session.token_hash = auth.token_hash("synthetic-cookie")
    db.commit()
    monkeypatch.setattr(auth, "now", lambda: NOW)
    factory = lambda: Session(db.bind)
    monkeypatch.setattr(auth, "SessionLocal", factory)
    monkeypatch.setattr(routes, "SessionLocal", factory)
    request = Request({"type": "http", "headers": [(b"cookie", b"markina_session=synthetic-cookie")]})
    return routes, request, tenant, subject, session


@pytest.mark.parametrize("role", ["client", "admin"])
def test_every_sensitive_route_denies_without_explicit_grants(db, monkeypatch, role):
    routes, request, *_ = route_context(db, monkeypatch, role)
    calls = [lambda: routes.summary(request, Response(), 60),
             lambda: routes.tree(request, Response(), None, None, 25, "", "all"),
             lambda: routes.incidents(request, Response(), 60),
             lambda: routes.report(request, 60, "json")]
    for call in calls:
        with pytest.raises(HTTPException) as error:
            call()
        assert error.value.status_code == 403


def test_export_needs_two_grants_excludes_tree_and_optional_incidents(db, monkeypatch):
    from app.system_monitor.grants import change_grants
    routes, request, _tenant, admin, _session = route_context(db, monkeypatch)
    change_grants(db, admin.id, ["export"], "synthetic-test")
    db.commit()
    with pytest.raises(HTTPException):
        routes.report(request, 60, "json")
    change_grants(db, admin.id, ["metrics"], "synthetic-test")
    db.commit()
    result = routes.report(request, 60, "json")
    body = json.loads(result.body)
    assert body["incidents"] is None and "Cliente sintético" not in result.body.decode()
    assert "synthetic-cookie" not in result.body.decode()
    assert result.headers["cache-control"] == "private, no-store"
    change_grants(db, admin.id, ["metrics"], "synthetic-test", revoke=True)
    db.commit()
    with pytest.raises(HTTPException):
        routes.report(request, 60, "text")


def test_permissions_are_rechecked_after_read_and_revoked_session_is_denied(db, monkeypatch):
    from app.system_monitor.grants import change_grants
    routes, request, _tenant, admin, session = route_context(db, monkeypatch)
    change_grants(db, admin.id, ["metrics"], "synthetic-test")
    db.commit()
    def revoke_during_read(*_args):
        change_grants(db, admin.id, ["metrics"], "synthetic-test", revoke=True)
        db.commit()
        return {}
    monkeypatch.setattr(routes, "build_report", revoke_during_read)
    with pytest.raises(HTTPException):
        routes.summary(request, Response(), 60)
    session.revoked_at = NOW
    db.commit()
    with pytest.raises(HTTPException):
        routes.capabilities(request, Response())


def test_collector_failure_is_sanitized_and_next_flush_recovers(db, monkeypatch, caplog):
    from app.system_monitor import runtime
    telemetry.drain()
    telemetry.record("http.auth", 100, 500)
    def failed_factory():
        raise RuntimeError("SECRET")
    assert runtime.flush(failed_factory) is False
    runtime.collect(failed_factory, NOW)
    assert "SECRET" not in caplog.text
    telemetry.record("http.auth", 100)
    assert runtime.flush(lambda: Session(db.bind)) is True
    assert db.scalar(select(MonitorBucket.count)) == 1


def test_pool_timeout_and_work_exception_are_counted_without_changing_exception(monkeypatch):
    from sqlalchemy.exc import TimeoutError
    from sqlalchemy.pool import QueuePool

    from app.system_monitor.pool import MonitoredQueuePool
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLED", "true")
    telemetry.drain()
    def fail(_self):
        raise TimeoutError("private")
    monkeypatch.setattr(QueuePool, "_do_get", fail)
    with pytest.raises(TimeoutError):
        MonitoredQueuePool(lambda: None)._do_get()
    @telemetry.observe_work("media")
    def work():
        raise ValueError("original-error")
    with pytest.raises(ValueError, match="original-error"):
        work()
    buckets, _, _ = telemetry.drain()
    assert {key[1] for key in buckets} == {"pool.acquire", "work.media"}
    assert all(value[1] == 1 for value in buckets.values())
    assert next(value[4] for key, value in buckets.items() if key[1] == "pool.acquire") == 1
    assert next(value[4] for key, value in buckets.items() if key[1] == "work.media") == 0


def test_export_strips_injected_worker_and_incident_fields(db):
    from app.system_monitor.incidents import incident_rows
    payload = safe_sample({"workers": [{"kind": "media", "status": "SECRET", "last_cycle_at": "NAME", "recent_instances": "PHONE"}]})
    db.add(MonitorIncident(code="errors.http.auth", state="active", first_seen=NOW, updated_at=NOW,
        evidence={"observed": 5, "threshold": 5, "cookie": "SECRET"}))
    db.add(MonitorIncident(code="private@example.invalid", state="active", first_seen=NOW, updated_at=NOW, evidence={}))
    db.flush()
    result = json.dumps([payload, incident_rows(db, NOW, NOW + timedelta(seconds=1))])
    assert all(value not in result for value in ("SECRET", "NAME", "PHONE", "private@example.invalid"))


def test_tree_limits_queries_and_disabled_or_future_activity_is_unknown(db, monkeypatch):
    from sqlalchemy import event
    tenant, _client, session = user(db)
    db.add(MonitorSample(minute=NOW, payload={}))
    activity.signal(db, session.id, NOW + timedelta(hours=1))
    db.flush()
    statements = []
    def count(*args):
        statements.append(args[2])
    event.listen(db.bind, "before_cursor_execute", count)
    assert activity.page(db, NOW, tenant_id=tenant.id)["items"][0]["state"] == "valid_session"
    assert len(statements) == 2
    event.remove(db.bind, "before_cursor_execute", count)
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLED", "false")
    assert activity.page(db, NOW, tenant_id=tenant.id)["items"][0]["state"] == "unknown"


def test_host_rates_do_not_fabricate_missing_interfaces_and_write_atomically(tmp_path):
    from app.system_monitor.host_collect import atomic_write, rates
    result = rates({"cpu_total": 100, "cpu_idle": 20}, {"cpu_total": 200, "cpu_idle": 80}, 1)
    assert result["cpu_percent"] == 40
    assert result["network_in_bytes_per_second"] is None
    path = tmp_path / "host.json"
    atomic_write(path, {"schema_version": 1})
    assert json.loads(path.read_text()) == {"schema_version": 1}
    assert not list(tmp_path.glob(".monitor-*"))


def test_migration_compiles_postgresql_without_database():
    import importlib.util
    import io
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    spec = importlib.util.spec_from_file_location("monitor_migration", Path(__file__).parents[1] / "migrations/versions/20261009_0072_system_monitor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output})
    module.op = Operations(context)
    module.upgrade()
    sql = output.getvalue()
    assert sql.count("CREATE TABLE") == 8
    assert all(not line.startswith(("INSERT", "DELETE", "DROP", "UPDATE ")) for line in sql.splitlines())
    assert "ON DELETE CASCADE" in sql
    with pytest.raises(RuntimeError):
        module.downgrade()


def test_storage_inventory_is_bounded_private_and_does_not_read_contents(tmp_path, monkeypatch):
    from app.system_monitor import storage
    monkeypatch.setattr(storage, "_cached", None)
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path))
    tenant_id = uuid4()
    relative = f"tenants/{tenant_id}/photo.jpg"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(b"synthetic-bytes")
    class Rows:
        def __init__(self, rows):
            self.rows = rows
        def all(self):
            return self.rows
    class Database:
        def execute(self, statement):
            assert "LIMIT" in str(statement)
            return Rows([("source", tenant_id, relative)])
    result = storage.file_inventory(Database())
    assert result["registered_file_bytes"] == 15 and result["inventory_complete"]
    assert str(tenant_id) not in json.dumps(result)
    monkeypatch.setattr(storage, "_cached", None)
    target.unlink()  # disposable synthetic fixture only
    result = storage.file_inventory(Database())
    assert result["registered_file_bytes"] is None and not result["inventory_complete"]


def test_sources_use_existing_schema_and_isolate_a_failed_source(db, monkeypatch):
    from app.system_monitor import sources, storage
    monkeypatch.setattr(storage, "_cached", None)
    def unavailable(_db):
        raise RuntimeError("sensitive-provider-error")
    monkeypatch.setattr(sources, "database_waits", unavailable)
    result = sources.collect_sections(lambda: Session(db.bind), NOW)
    assert result["jobs"]["counts"] == [] and result["uploads"] == []
    assert result["database_waits"]["status"] == "unavailable"
    assert result["storage"]["registered_photos"] == 0
    assert "sensitive-provider-error" not in json.dumps(result)


def test_host_collector_parses_fixture_and_does_not_sum_interfaces(tmp_path, monkeypatch):
    from app.system_monitor import host_collect
    (tmp_path / "net").mkdir()
    (tmp_path / "stat").write_text("cpu 10 0 10 80 0 0 0 0 0 0\n")
    (tmp_path / "net/dev").write_text("eth0: 100 0 0 0 0 0 0 0 200 0 0 0 0 0 0 0\nveth0: 999 0 0 0 0 0 0 0 999 0 0 0 0 0 0 0\n")
    (tmp_path / "diskstats").write_text("8 0 sda 0 0 10 0 0 0 20 0 0 5 0\n")
    result = host_collect.counters(tmp_path, "eth0", "sda")
    assert result["net_in"] == 100 and result["net_out"] == 200
    assert result["io_read"] == 5120 and result["io_write"] == 10240


def test_export_interval_validation_is_declared_in_route_contract():
    from app.system_monitor.routes import router
    for route in router.routes:
        if route.path in {"/admin/system-monitor", "/admin/system-monitor/report", "/admin/system-monitor/incidents"}:
            field = next(f for f in route.dependant.query_params if f.name == "minutes")
            assert field.validate(4, {}, loc=("query", "minutes"))[1]
            assert field.validate(1441, {}, loc=("query", "minutes"))[1]
            assert not field.validate(60, {}, loc=("query", "minutes"))[1]


def test_nonowner_with_all_grants_cannot_read_any_monitor_or_legacy_diagnostic(db, monkeypatch):
    from app import main
    from app.auth import InstallationOperator
    routes, request, _tenant, admin, _session = route_context(db, monkeypatch, owner=False)
    user(db, "admin", owner=True)
    for permission in ("metrics", "tree", "incidents", "export"):
        db.add(MonitorGrant(admin_user_id=admin.id, permission=permission, active=True, authorization_reference="synthetic"))
    db.add(InstallationOperator(admin_user_id=admin.id, active=True, authorization_reference="synthetic", granted_at=NOW, updated_at=NOW))
    db.commit()
    monkeypatch.setattr(main, "SessionLocal", lambda: Session(db.bind))
    assert not any(routes.capabilities(request, Response()).values())
    assert main.admin_installation_capabilities(request, Response()) == {"capacity_diagnostics": False}
    for call in (lambda: routes.summary(request, Response(), 60),
                 lambda: routes.tree(request, Response(), None, None, 25, "", "all"),
                 lambda: routes.incidents(request, Response(), 60),
                 lambda: routes.report(request, 60, "json"),
                 lambda: main.admin_capacity_observability(request, Response()),
                 lambda: main.require_installation_operator(request)):
        with pytest.raises(HTTPException) as error:
            call()
        assert error.value.status_code == 403


def test_owner_uuid_survives_email_change_and_old_email_does_not_transfer_access(db):
    from app.system_monitor.access import is_owner
    from app.system_monitor.grants import change_grants, establish_owner
    _tenant, owner, _session = user(db, "admin")
    old_email = owner.email
    change_grants(db, owner.id, ["metrics"], "synthetic")
    owner.email = "new-owner@example.invalid"
    db.flush()
    assert is_owner(db, owner.id)
    require_permission(db, owner.id, "metrics")
    _tenant2, other, _session2 = user(db, "admin", owner=False)
    other.email = old_email
    db.flush()
    assert not is_owner(db, other.id)
    with pytest.raises(HTTPException):
        change_grants(db, other.id, ["metrics"], "synthetic")
    with pytest.raises(ValueError, match="Transferência"):
        establish_owner(db, other.id, old_email, "synthetic")
    owner.email_verified = False
    db.flush()
    assert not is_owner(db, owner.id)


def test_initial_owner_nomination_requires_confirmation_and_is_singleton(db):
    from app.system_monitor.access import is_owner
    from app.system_monitor.grants import establish_owner
    _tenant, admin, _session = user(db, "admin", owner=False)
    assert not is_owner(db, admin.id)
    with pytest.raises(ValueError):
        establish_owner(db, admin.id, "wrong@example.invalid", "synthetic")
    assert db.get(PlatformOwner, 1) is None
    establish_owner(db, admin.id, admin.email, "synthetic")
    establish_owner(db, admin.id, admin.email, "synthetic")
    assert is_owner(db, admin.id)
    assert len(db.scalars(select(PlatformOwner)).all()) == 1


def test_incident_permission_revoked_during_export_prevents_delivery(db, monkeypatch):
    from app.system_monitor.grants import change_grants
    routes, request, _tenant, admin, _session = route_context(db, monkeypatch)
    change_grants(db, admin.id, ["metrics", "export", "incidents"], "synthetic")
    db.commit()
    original = routes.build_report
    def revoke_during_report(*args, **kwargs):
        assert kwargs["include_incidents"]
        result = original(*args, **kwargs)
        change_grants(db, admin.id, ["incidents"], "synthetic", revoke=True)
        db.commit()
        return result
    monkeypatch.setattr(routes, "build_report", revoke_during_report)
    with pytest.raises(HTTPException) as denied:
        routes.report(request, 60, "json")
    assert denied.value.status_code == 403


def test_cleanup_inventory_preserves_monitor_and_security_audit(db, monkeypatch, tmp_path):
    from app import homolog_cleanup
    from app.auth import audit
    tenant, admin, session = user(db, "admin")
    db.add(MonitorGrant(admin_user_id=admin.id, permission="metrics", active=True,
                        authorization_reference="synthetic"))
    db.add(MonitorBucket(minute=NOW, operation="http.read", latency_bin=100, count=1))
    db.add(MonitorActivity(session_id=session.id, last_activity=NOW))
    audit(db, "system_monitor.grants_granted", str(admin.id), tenant_id=tenant.id)
    db.commit()
    monkeypatch.setenv("APP_ENV", "homolog")
    monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: {"synthetic": tmp_path})
    expected = {"platform_owner", "system_monitor_grant", "system_monitor_activity",
                "system_monitor_bucket", "system_monitor_sample", "system_monitor_worker",
                "system_monitor_incident", "system_monitor_transition"}
    assert expected <= homolog_cleanup.PRESERVED_TABLES
    assert not expected & homolog_cleanup.OPERATIONAL_TABLES
    result = homolog_cleanup.inventory(db)
    assert all(name in result["preserved"] for name in expected)
    assert not expected & result["database"].keys()
    for name in ("platform_owner", "system_monitor_grant", "system_monitor_activity", "system_monitor_bucket"):
        assert result["preserved"][name] == 1
    assert result["preserved"]["admin_security_audit_events"] == 1
    assert result["database"]["client_gallery_audit_events"] == 0
    assert str(admin.id) not in str(result)
