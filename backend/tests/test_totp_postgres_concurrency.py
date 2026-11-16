"""Concorrência real de replay TOTP em schema sintético PostgreSQL isolado."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import main
from app.admin_security import issue_admin_action_token
from app.auth import (
    AdminTotpRecoveryCode,
    AdminUser,
    AuthChallenge,
    AuthSession,
    PhotographerSignup,
    Tenant,
    TenantAdmin,
    now,
    password_hasher,
)
from app.totp_recovery import create_recovery_codes, hash_recovery_code, recovery_code_selector
from tests.schema_fixtures import create_test_schema


def test_postgresql_accepts_same_totp_step_at_most_once_concurrently(monkeypatch):
    raw_url = os.environ.get("ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer PostgreSQL sintético exclusivo em ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    url = make_url(raw_url)
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "totp_migration_test"):
        pytest.fail("O teste TOTP exige o banco local isolado totp_migration_test")

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    engine = create_engine(url)
    schema = "totp_replay_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        create_test_schema(scoped)
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        tenant_id = uuid4()
        admin_id = uuid4()
        secret = pyotp.random_base32()
        with factory.begin() as db:
            db.add(Tenant(id=tenant_id, status="active"))
            db.flush()
            admin = AdminUser(
                id=admin_id, email="totp-concurrency@example.test",
                password_hash=password_hasher.hash("synthetic-password"),
                email_verified=True, totp_secret=secret,
            )
            admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant_id))
            db.add(admin)
            db.flush()
            challenge_ids = [uuid4(), uuid4()]
            db.add_all([
                AuthChallenge(
                    id=challenge_id, kind="admin_totp", subject=str(admin_id),
                    tenant_id=tenant_id, secret_hash="synthetic-unused",
                    expires_at=now() + timedelta(minutes=5),
                ) for challenge_id in challenge_ids
            ])
        code = pyotp.TOTP(secret).now()
        gate = Barrier(2)

        def attempt(challenge_id):
            with factory() as db:
                gate.wait(timeout=10)
                request = Request({"type": "http", "method": "POST", "path": "/auth/admin/totp",
                                   "headers": [], "client": ("127.0.0.1", 49000)})
                try:
                    main.admin_totp(
                        main.AdminTotpVerification(challenge_id=challenge_id, code=code),
                        request, Response(), db,
                    )
                    return 200
                except HTTPException as exc:
                    return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, challenge_ids))
        assert sorted(results) == [200, 401]
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(AuthSession).where(
                AuthSession.subject_id == admin_id
            )) == 1
            assert db.get(AdminUser, admin_id).totp_last_used_step is not None
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_postgresql_consumes_same_recovery_code_at_most_once_concurrently(monkeypatch):
    raw_url = os.environ.get("ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer PostgreSQL sintético exclusivo em ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    url = make_url(raw_url)
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "totp_migration_test"):
        pytest.fail("O teste TOTP exige o banco local isolado totp_migration_test")

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    engine = create_engine(url)
    schema = "totp_recovery_replay_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        create_test_schema(scoped)
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        tenant_id, admin_id = uuid4(), uuid4()
        secret = pyotp.random_base32()
        code = create_recovery_codes(1)[0]
        with factory.begin() as db:
            db.add(Tenant(id=tenant_id, status="active"))
            db.flush()
            admin = AdminUser(
                id=admin_id, email="totp-recovery-concurrency@example.test",
                password_hash=password_hasher.hash("synthetic-password"),
                email_verified=True, totp_secret=secret,
            )
            admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant_id))
            db.add(admin)
            db.flush()
            db.add(AdminTotpRecoveryCode(
                admin_user_id=admin_id,
                code_selector=recovery_code_selector(code),
                code_hash=hash_recovery_code(code),
            ))
            challenge_ids = [uuid4(), uuid4()]
            db.add_all([
                AuthChallenge(
                    id=challenge_id, kind="admin_totp", subject=str(admin_id),
                    tenant_id=tenant_id, secret_hash="synthetic-unused",
                    expires_at=now() + timedelta(minutes=5),
                ) for challenge_id in challenge_ids
            ])
        gate = Barrier(2)

        def attempt(challenge_id):
            with factory() as db:
                gate.wait(timeout=10)
                request = Request({"type": "http", "method": "POST", "path": "/auth/admin/totp",
                                   "headers": [], "client": ("127.0.0.1", 49001)})
                try:
                    main.admin_totp(
                        main.AdminTotpVerification(challenge_id=challenge_id, code=code),
                        request, Response(), db,
                    )
                    return 200
                except HTTPException as exc:
                    return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, challenge_ids))
        assert sorted(results) == [200, 401]
        with factory() as db:
            recovery = db.scalar(select(AdminTotpRecoveryCode).where(
                AdminTotpRecoveryCode.admin_user_id == admin_id
            ))
            assert recovery is not None and recovery.used_at is not None
            assert db.scalar(select(func.count()).select_from(AuthSession).where(
                AuthSession.subject_id == admin_id
            )) == 1
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_postgresql_website_reset_link_and_totp_are_consumed_once_concurrently(monkeypatch):
    raw_url = os.environ.get("ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer PostgreSQL sintético exclusivo em ADMIN_TOTP_POSTGRES_TEST_DATABASE_URL")
    url = make_url(raw_url)
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "totp_migration_test"):
        pytest.fail("O teste TOTP exige o banco local isolado totp_migration_test")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    engine = create_engine(url)
    schema = "totp_website_reset_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        create_test_schema(scoped)
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        tenant_id, admin_id = uuid4(), uuid4()
        secret = pyotp.random_base32()
        with factory.begin() as db:
            db.add(Tenant(id=tenant_id, status="active"))
            db.flush()
            admin = AdminUser(id=admin_id, email="website-reset@example.test",
                              password_hash=password_hasher.hash("Atual-forte-2026"),
                              email_verified=True, totp_secret=secret)
            admin.tenant_memberships.append(TenantAdmin(tenant_id=tenant_id))
            db.add(admin)
            db.add(PhotographerSignup(photographer_name="Web", email=admin.email, state="active",
                                      otp_expires_at=now(), reserved_admin_id=admin_id,
                                      activated_tenant_id=tenant_id, activated_at=now()))
            db.flush()
            _item, raw_token = issue_admin_action_token(db, admin_id=admin_id, purpose="password_reset")
        code = pyotp.TOTP(secret).now()
        gate = Barrier(2)

        def attempt(_):
            with factory() as db:
                gate.wait(timeout=10)
                request = Request({"type": "http", "method": "POST", "path": "/auth/admin/recovery/reset",
                                   "headers": [], "client": ("127.0.0.1", 49002)})
                try:
                    main.admin_recovery_reset(main.AdminPasswordResetInput(
                        token=raw_token, new_password='test-password-for-unit-tests-new', second_factor_code=code,
                    ), request, Response(), db)
                    return 200
                except HTTPException as exc:
                    return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, range(2)))
        assert results.count(200) == 1 and set(results) <= {200, 400, 401}
        with factory() as db:
            admin = db.get(AdminUser, admin_id)
            assert password_hasher.verify(admin.password_hash, 'test-password-for-unit-tests-new')
            assert admin.totp_last_used_step is not None
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
