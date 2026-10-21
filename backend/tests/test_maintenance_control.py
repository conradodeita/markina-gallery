from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from starlette.requests import Request

from app import maintenance_control as barrier
from app.main import ControlledMaintenanceMiddleware


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.hashes = {}
        self.closed = False

    def ping(self):
        return True

    def close(self):
        self.closed = True

    def eval(self, script, key_count, *args):
        if script in {barrier._ENTER, barrier._ENTER_CRITICAL}:
            maintenance_key, active_key, token, service = args
            if script == barrier._ENTER and maintenance_key in self.values:
                return 0
            self.hashes.setdefault(active_key, {})[token] = service
            return 1
        if script == barrier._LEAVE:
            return int(self.hashes.get(args[0], {}).pop(args[1], None) is not None)
        if script == barrier._BEGIN_MAINTENANCE:
            maintenance_key, operation_id = args
            if maintenance_key in self.values:
                return 0
            self.values[maintenance_key] = f"{operation_id}:active"
            return 1
        if script == barrier._FINISH_MAINTENANCE:
            maintenance_key, active_key, operation_id = args
            if self.values.get(maintenance_key) != f"{operation_id}:active":
                return 0
            if self.hashes.get(active_key):
                return -1
            del self.values[maintenance_key]
            return 1
        raise AssertionError("script de barreira inesperado")

    def hlen(self, key):
        return len(self.hashes.get(key, {}))

    def get(self, key):
        return self.values.get(key)

    def exists(self, key):
        return int(key in self.values)


def postgres_marker():
    return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))


@pytest.fixture(autouse=True)
def maintenance_enabled(monkeypatch):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "true")


def test_sqlite_mode_is_only_a_test_noop():
    engine = create_engine("sqlite://")
    with barrier.shared_operation(engine, service="unit-test"):
        pass


def test_maintenance_is_disabled_by_default_without_touching_redis(monkeypatch):
    monkeypatch.delenv(barrier.MAINTENANCE_ENABLED_ENV, raising=False)
    with patch.object(barrier, "redis_client", side_effect=AssertionError("Redis must not be accessed")):
        active = barrier.try_enter(postgres_marker(), service="api")
        assert active is not None and active.client is None
        with pytest.raises(barrier.MaintenanceUnavailable):
            barrier.begin_maintenance("disabled")


def test_default_mode_preserves_http_without_redis(monkeypatch):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "false")
    app = FastAPI()

    @app.get("/regular")
    def regular():
        return {"status": "normal"}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    with (
        patch.object(barrier, "redis_client", side_effect=AssertionError("Redis must not be accessed")),
        TestClient(app) as http,
    ):
        assert http.get("/regular").json() == {"status": "normal"}


def test_invalid_maintenance_flag_fails_closed(monkeypatch):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "maybe")
    with pytest.raises(barrier.MaintenanceUnavailable):
        barrier.try_enter(postgres_marker(), service="api")


def test_unsupported_database_fails_closed():
    engine = SimpleNamespace(dialect=SimpleNamespace(name="mysql"))
    with pytest.raises(barrier.MaintenanceUnavailable):
        barrier.try_enter(engine, service="api")


def test_maintenance_rejects_new_work_and_opens_only_after_active_ack():
    redis = FakeRedis()
    with patch.object(barrier, "redis_client", return_value=redis):
        operation = barrier.begin_maintenance("maintenance-001")
        active = barrier.try_enter(postgres_marker(), service="worker")
        assert active is None
        barrier.finish_maintenance("maintenance-001", client=operation)
        active = barrier.try_enter(postgres_marker(), service="worker")
        assert active is not None
        active.release()
        operation.close()


def test_worker_cycles_do_not_enter_during_maintenance_and_resume_afterward():
    redis = FakeRedis()
    engine = postgres_marker()
    claimed = []
    with patch.object(barrier, "redis_client", return_value=redis):
        operation = barrier.begin_maintenance("maintenance-worker", client=redis)
        with pytest.raises(barrier.MaintenanceBusy), barrier.shared_operation(
            engine, service="face-index-worker"
        ):
            claimed.append("new claim")
        assert claimed == []
        barrier.finish_maintenance("maintenance-worker", client=operation)
        with barrier.shared_operation(engine, service="face-index-worker"):
            claimed.append("resumed claim")
        assert claimed == ["resumed claim"]


def test_general_worker_integration_blocks_claim_and_resumes(monkeypatch):
    from app import worker as general_worker

    redis = FakeRedis()
    claims = []
    engine = postgres_marker()
    monkeypatch.setattr(general_worker, "SessionLocal", SimpleNamespace(kw={"bind": engine}))
    monkeypatch.setattr(general_worker, "_run_cycle_guarded", lambda: claims.append("claim") or True)
    monkeypatch.setattr(barrier, "redis_client", lambda: redis)

    gate = barrier.begin_maintenance("maintenance-general-worker", client=redis)
    assert general_worker.run_cycle() is False
    assert claims == []

    barrier.finish_maintenance("maintenance-general-worker", client=gate)
    assert general_worker.run_cycle() is True
    assert claims == ["claim"]


def test_rejected_duplicate_maintenance_closes_owned_redis_client():
    redis = FakeRedis()
    redis.values[barrier.MAINTENANCE_KEY] = "maintenance-existing:active"
    with patch.object(barrier, "redis_client", return_value=redis), pytest.raises(barrier.MaintenanceBusy):
        barrier.begin_maintenance("maintenance-new")
    assert redis.closed


def test_maintenance_waits_for_real_operation_ack_and_refuses_wrong_owner():
    redis = FakeRedis()
    with patch.object(barrier, "redis_client", return_value=redis):
        active = barrier.try_enter(postgres_marker(), service="raw-development-worker")
        operation = barrier.begin_maintenance("maintenance-002")
        assert not barrier.wait_for_drain(operation, timeout_seconds=0, poll_seconds=0)
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance("maintenance-other", client=operation)
        active.release()
        assert barrier.wait_for_drain(operation, timeout_seconds=0)
        barrier.finish_maintenance("maintenance-002", client=operation)
        operation.close()


def test_crashed_operation_has_no_ttl_and_keeps_maintenance_blocked():
    redis = FakeRedis()
    with patch.object(barrier, "redis_client", return_value=redis):
        active = barrier.try_enter(postgres_marker(), service="face-index-worker")
        active.client.close()  # simula a perda do processo sem ACK explícito
        operation = barrier.begin_maintenance("maintenance-003")
        assert not barrier.wait_for_drain(operation, timeout_seconds=0)
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance("maintenance-003", client=operation)
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        assert redis.values[barrier.MAINTENANCE_KEY] == "maintenance-003:active"
        operation.close()


def test_unacknowledged_exception_keeps_active_receipt():
    redis = FakeRedis()
    engine = postgres_marker()
    with patch.object(barrier, "redis_client", return_value=redis), pytest.raises(RuntimeError), barrier.shared_operation(
        engine, service="worker"
    ):
        raise RuntimeError("synthetic interruption")
    assert redis.hlen(barrier.ACTIVE_KEY) == 1


def test_maintenance_blocks_regular_http_but_tracks_exact_critical_callbacks():
    redis = FakeRedis()
    app = FastAPI()
    calls = []

    @app.post("/upload")
    def upload():
        # O marcador já existe antes da execução do handler, mesmo para uploads longos.
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        return {"status": "stored"}

    @app.get("/session")
    def session(request: Request):
        return {"session": request.headers.get("cookie", "")}

    @app.post("/admit")
    def admit():
        calls.append("regular")
        return {"accepted": True}

    @app.post("/internal/whatsapp/webhook")
    def whatsapp_callback():
        calls.append("whatsapp")
        return {"status": "persisted"}

    @app.get("/infinitepay/return")
    def payment_return():
        calls.append("payment")
        return {"status": "checked"}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    with patch.object(barrier, "redis_client", return_value=redis):
        gate = barrier.begin_maintenance("maintenance-001", client=redis)
        with TestClient(app) as http:
            http.cookies.set("session", "existing-auth-session")
            rejected = http.post("/admit")
            assert rejected.status_code == 503
            assert rejected.headers["Retry-After"] == "5"
            assert rejected.headers["Cache-Control"] == "no-store"
            blocked_session = http.get("/session")
            assert blocked_session.status_code == 503
            assert http.cookies.get("session") == "existing-auth-session"
            assert http.post("/upload").status_code == 503
            assert http.post("/internal/whatsapp/webhook").status_code == 200
            assert http.get("/infinitepay/return").status_code == 200
            assert http.post("/infinitepay/return").status_code == 503
        assert calls == ["whatsapp", "payment"]
        assert redis.hlen(barrier.ACTIVE_KEY) == 0
        barrier.finish_maintenance("maintenance-001", client=gate)
        with TestClient(app) as http:
            http.cookies.set("session", "existing-auth-session")
            assert http.get("/session").json() == {"session": "session=existing-auth-session"}
            assert http.post("/upload").json() == {"status": "stored"}


def test_critical_callbacks_are_admitted_and_tracked_during_maintenance():
    redis = FakeRedis()
    with patch.object(barrier, "redis_client", return_value=redis):
        gate = barrier.begin_maintenance("maintenance-callback", client=redis)
        active = barrier.try_enter_critical(postgres_marker(), service="api-critical-callback")
        assert active is not None
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        active.release()
        barrier.finish_maintenance("maintenance-callback", client=gate)


def test_maintenance_waits_for_request_admitted_before_gate():
    redis = FakeRedis()
    app = FastAPI()
    gate_holder = []

    @app.post("/long-upload")
    def long_upload():
        gate_holder.append(barrier.begin_maintenance("maintenance-upload", client=redis))
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        return {"status": "uploaded"}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    with patch.object(barrier, "redis_client", return_value=redis):
        with TestClient(app) as http:
            assert http.post("/long-upload").json() == {"status": "uploaded"}
        gate = gate_holder[0]
        assert redis.hlen(barrier.ACTIVE_KEY) == 0
        assert barrier.wait_for_drain(gate, timeout_seconds=0)
        barrier.finish_maintenance("maintenance-upload", client=gate)


def test_failed_critical_callback_keeps_maintenance_receipt_and_gate():
    redis = FakeRedis()
    app = FastAPI()

    @app.post("/internal/whatsapp/webhook")
    def failing_callback():
        raise RuntimeError("persist failed")

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    with patch.object(barrier, "redis_client", return_value=redis):
        gate = barrier.begin_maintenance("maintenance-002", client=redis)
        with TestClient(app, raise_server_exceptions=False) as http:
            assert http.post("/internal/whatsapp/webhook").status_code == 500
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance("maintenance-002", client=gate)


def test_callback_500_response_keeps_receipt_even_when_asgi_returns_normally():
    redis = FakeRedis()
    app = FastAPI()

    @app.post("/internal/whatsapp/webhook")
    def failed_response():
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "temporary persistence failure"}, status_code=500)

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    with patch.object(barrier, "redis_client", return_value=redis):
        gate = barrier.begin_maintenance("maintenance-500", client=redis)
        with TestClient(app) as http:
            response = http.post("/internal/whatsapp/webhook")
        assert response.status_code == 500
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance("maintenance-500", client=gate)
