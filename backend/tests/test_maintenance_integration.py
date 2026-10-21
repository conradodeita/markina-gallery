"""Testes contra Redis descartável real; não apontar para instância operacional."""

from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import create_engine, text

from app import maintenance_control as barrier
from app.main import ControlledMaintenanceMiddleware

URL = os.getenv("PYPPIC_TEST_REDIS_URL")
DATABASE_URL = os.getenv("PYPPIC_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requer Redis isolado descartável")


@pytest.fixture(autouse=True)
def redis_url_for_barrier(monkeypatch):
    monkeypatch.setenv("FACIAL_REDIS_URL", URL or "")
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "true")


def postgres_marker():
    return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))


def test_real_redis_maintenance_closes_admission_waits_for_ack_and_reopens():
    client = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-" + uuid4().hex
    active = None
    try:
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        active = barrier.try_enter(postgres_marker(), service="worker")
        assert active is not None
        gate = barrier.begin_maintenance(operation_id, client=client)
        assert barrier.try_enter(postgres_marker(), service="api") is None
        assert not barrier.wait_for_drain(gate, timeout_seconds=0)
        active.release()
        active = None
        assert barrier.wait_for_drain(gate, timeout_seconds=1)
        barrier.finish_maintenance(operation_id, client=gate)
        assert client.get(barrier.MAINTENANCE_KEY) is None
        assert client.hlen(barrier.ACTIVE_KEY) == 0
    finally:
        if active is not None and active.client is not None:
            active.client.close()
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        client.close()


def test_real_redis_keeps_maintenance_after_unacknowledged_process():
    client = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-stale-" + uuid4().hex
    operation = None
    try:
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        active = barrier.try_enter(postgres_marker(), service="raw-development-worker")
        assert active is not None
        active.client.close()  # falha do processo: não executa HDEL
        operation = barrier.begin_maintenance(operation_id, client=client)
        assert not barrier.wait_for_drain(operation, timeout_seconds=0)
        assert client.hlen(barrier.ACTIVE_KEY) == 1
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance(operation_id, client=operation)
        assert client.get(barrier.MAINTENANCE_KEY) == f"{operation_id}:active"
    finally:
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        client.close()


def test_real_redis_maintenance_rejects_api_write_before_handler():
    client = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-http-" + uuid4().hex
    app = FastAPI()
    calls = []

    @app.post("/admit")
    def admit():
        calls.append("executed")
        return {"accepted": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=postgres_marker())
    try:
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        gate = barrier.begin_maintenance(operation_id, client=client)
        with TestClient(app) as http:
            rejected = http.post("/admit")
            assert rejected.status_code == 503
            assert rejected.headers["Retry-After"] == "5"
            assert calls == []
            assert http.get("/health").status_code == 200
        barrier.finish_maintenance(operation_id, client=gate)
        with TestClient(app) as http:
            assert http.post("/admit").status_code == 200
        assert calls == ["executed"]
    finally:
        client.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        client.close()


@pytest.mark.skipif(not DATABASE_URL, reason="requer PostgreSQL isolado descartável")
def test_postgres_redis_gate_and_persisted_callback_ack():
    engine = create_engine(DATABASE_URL)
    redis = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-maintenance-" + uuid4().hex
    table = "maintenance_callback_" + uuid4().hex
    calls = []
    app = FastAPI()

    @app.post("/regular")
    def regular():
        calls.append("regular")
        return {"accepted": True}

    @app.post("/internal/whatsapp/webhook")
    def callback():
        with engine.begin() as connection:
            connection.execute(text(f'INSERT INTO "{table}" (event_id) VALUES (:event_id)'), {"event_id": operation_id})
        calls.append("callback")
        return {"status": "persisted"}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=engine)
    try:
        with engine.begin() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            connection.exec_driver_sql(f'CREATE TABLE "{table}" (event_id text PRIMARY KEY)')
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        gate = barrier.begin_maintenance(operation_id, client=redis)
        assert barrier.try_enter(engine, service="worker") is None
        with TestClient(app) as http:
            rejected = http.post("/regular")
            assert rejected.status_code == 503
            persisted = http.post("/internal/whatsapp/webhook")
            assert persisted.status_code == 200
            assert persisted.json() == {"status": "persisted"}
        assert calls == ["callback"]
        assert redis.hlen(barrier.ACTIVE_KEY) == 0
        with engine.connect() as connection:
            assert connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one() == 1
        barrier.finish_maintenance(operation_id, client=gate)
        with TestClient(app) as http:
            assert http.post("/regular").status_code == 200
    finally:
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}"')
        redis.close()
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="requer PostgreSQL isolado descartável")
def test_postgres_redis_worker_ack_preserves_queued_job_and_allows_resume():
    engine = create_engine(DATABASE_URL)
    redis = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-worker-" + uuid4().hex
    table = "maintenance_job_" + uuid4().hex
    active = None
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE TABLE "{table}" (job_id text PRIMARY KEY, status text NOT NULL)')
            connection.execute(
                text(f'INSERT INTO "{table}" (job_id, status) VALUES (:job_id, \'queued\')'),
                {"job_id": operation_id},
            )
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        active = barrier.try_enter(engine, service="face-index-worker")
        assert active is not None
        gate = barrier.begin_maintenance(operation_id, client=redis)
        assert barrier.try_enter(engine, service="face-index-worker") is None
        assert not barrier.wait_for_drain(gate, timeout_seconds=0)
        active.release()
        active = None
        assert barrier.wait_for_drain(gate, timeout_seconds=1)
        with engine.connect() as connection:
            assert connection.execute(text(f'SELECT status FROM "{table}" WHERE job_id=:job_id'),
                                      {"job_id": operation_id}).scalar_one() == "queued"
        barrier.finish_maintenance(operation_id, client=gate)
        resumed = barrier.try_enter(engine, service="face-index-worker")
        assert resumed is not None
        resumed.release()
    finally:
        if active is not None:
            active.abandon()
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}"')
        redis.close()
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="requer PostgreSQL isolado descartável")
def test_postgres_redis_unacknowledged_worker_keeps_maintenance_closed():
    engine = create_engine(DATABASE_URL)
    redis = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-no-ack-" + uuid4().hex
    active = None
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        active = barrier.try_enter(engine, service="raw-development-worker")
        assert active is not None
        gate = barrier.begin_maintenance(operation_id, client=redis)
        active.abandon()
        active = None
        assert not barrier.wait_for_drain(gate, timeout_seconds=0)
        with pytest.raises(barrier.MaintenanceBusy):
            barrier.finish_maintenance(operation_id, client=gate)
        assert redis.get(barrier.MAINTENANCE_KEY) == f"{operation_id}:active"
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
    finally:
        if active is not None:
            active.abandon()
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        redis.close()
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="requer PostgreSQL isolado descartável")
def test_postgres_redis_gate_waits_for_admitted_upload_before_ack():
    engine = create_engine(DATABASE_URL)
    redis = Redis.from_url(URL, decode_responses=True)
    operation_id = "pytest-upload-" + uuid4().hex
    gate_holder = []
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: Request):
        gate_holder.append(barrier.begin_maintenance(operation_id, client=redis))
        body = await request.body()
        assert redis.hlen(barrier.ACTIVE_KEY) == 1
        return {"bytes_received": len(body)}

    app.add_middleware(ControlledMaintenanceMiddleware, engine=engine)
    try:
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        with TestClient(app) as http:
            result = http.post("/upload", content=b"synthetic-upload-payload")
        assert result.status_code == 200
        assert result.json() == {"bytes_received": len(b"synthetic-upload-payload")}
        gate = gate_holder[0]
        assert redis.hlen(barrier.ACTIVE_KEY) == 0
        assert barrier.wait_for_drain(gate, timeout_seconds=0)
        barrier.finish_maintenance(operation_id, client=gate)
    finally:
        redis.delete(barrier.MAINTENANCE_KEY, barrier.ACTIVE_KEY)
        redis.close()
        engine.dispose()
