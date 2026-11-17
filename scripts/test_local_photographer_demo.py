"""Guards for the opt-in, isolated photographer UI demo."""

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text

path = Path(__file__).with_name("local_photographer_demo.py")
spec = importlib.util.spec_from_file_location("local_photographer_demo", path)
assert spec and spec.loader
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_demo_target_is_exact_local_disposable_database() -> None:
    environment = {
        "APP_ENV": "development",
        "PUBLIC_APP_ORIGIN": "http://127.0.0.1:3039",
        "DATABASE_URL": "postgresql+psycopg://demo:synthetic@127.0.0.1:15472/pyp_ui_demo",
    }
    assert demo.validate_target(environment) == environment["DATABASE_URL"]
    for field, value in (
        ("APP_ENV", "production"),
        ("PUBLIC_APP_ORIGIN", "https://pickyourpic.com.br"),
        ("DATABASE_URL", "postgresql+psycopg://demo:synthetic@127.0.0.1:5432/pyp_ui_demo"),
        ("DATABASE_URL", "postgresql+psycopg://demo:synthetic@132.145.193.169:15472/pyp_ui_demo"),
        ("DATABASE_URL", "postgresql+psycopg://demo:synthetic@127.0.0.1:15472/pyp_ui_demo?hostaddr=132.145.193.169"),
        ("PGHOSTADDR", "132.145.193.169"),
        ("PGSERVICE", "production"),
    ):
        with pytest.raises(ValueError):
            demo.validate_target({**environment, field: value})


@pytest.mark.parametrize("old_revision", ["older", "20261105_0105"])
def test_resume_requires_exact_schema_without_upgrading(tmp_path, old_revision) -> None:
    url = f"sqlite:///{tmp_path / 'demo.sqlite'}"
    engine = create_engine(url)
    try:
        with pytest.raises(ValueError):
            demo.require_current_schema(url)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": old_revision})
        with pytest.raises(ValueError):
            demo.require_current_schema(url)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == old_revision
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = :revision"), {"revision": demo.REVISION})
        demo.require_current_schema(url)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == demo.REVISION
    finally:
        engine.dispose()


def test_demo_keys_survive_restart_and_are_separated_by_purpose() -> None:
    names = ("SECRET_KEY", "AUTH_PII_FINGERPRINT_SALT", "ADMIN_PRIVATE_FIELD_KEY", "ADMIN_TOTP_KEYS", "INTEGRATION_SECRET_KEYS")
    with patch.dict(os.environ):
        demo.configure_synthetic_environment(seed=b"synthetic-demo-seed")
        first = {name: os.environ[name] for name in names}
        assert len(set(first.values())) == len(first)
        demo.configure_synthetic_environment(seed=b"synthetic-demo-seed")
        assert first == {name: os.environ[name] for name in names}
        demo.configure_synthetic_environment(seed=b"another-synthetic-seed")
        assert all(first[name] != os.environ[name] for name in names)


@pytest.mark.skipif(os.getenv("PYP_RUN_LOCAL_DEMO_SMOKE") != "1", reason="Requer demo local ativa")
def test_local_demo_signup_and_tenant_access() -> None:
    origin = demo.ORIGIN
    email = f"smoke-{uuid4().hex[:12]}@example.test"
    with httpx.Client(base_url=origin, headers={"Origin": origin}, timeout=10) as client:
        started = client.post("/api/auth/photographer-signup", json={
            "photographer_name": "Fotógrafo Sintético",
            "email": email,
            "adult_attested": True,
            "anti_bot_proof": "",
        })
        assert started.status_code == 202, started.status_code
        code = client.get("/api/local-demo/mailbox").json()["synthetic_codes"][email]
        verified = client.post("/api/auth/photographer-signup/verify-email", json={
            "request_id": started.json()["request_id"], "code": code,
        })
        assert verified.status_code == 200, verified.status_code
        setup = client.get("/api/auth/photographer-signup/setup")
        assert setup.status_code == 200, setup.status_code
        completed = client.post("/api/auth/photographer-signup/complete", json={
            "password": "SyntheticDemo#47Alpha",
        })
        assert completed.status_code == 200, completed.status_code
        assert client.get("/api/admin/credits/wallet").status_code == 200
        assert client.get("/api/admin/platform/console/tenants?mode=all").status_code == 403
