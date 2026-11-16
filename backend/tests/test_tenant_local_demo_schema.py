"""A revisão nomeada dos runners precisa sustentar os modelos do runtime atual."""

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.auth import PhotographerSignup, TenantClosureRequest, now
from tests.test_photographer_onboarding_migration import _config
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema
SCRIPTS = Path(__file__).parents[2] / "scripts"


@pytest.mark.parametrize("runner", ["local_photographer_demo", "local_tenant_closure_demo"])
def test_named_demo_revision_supports_current_models(runner, postgres_schema, monkeypatch):
    # A fixture confere loopback/porta/banco e cria somente um schema aleatório.
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(f"schema_test_{runner}", SCRIPTS / f"{runner}.py")
    assert spec and spec.loader
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    signup_demo = demo if runner == "local_photographer_demo" else demo.signup_demo

    with patch.dict(os.environ):
        signup_demo.configure_synthetic_environment()
        config, url = _config(monkeypatch, postgres_schema)
        command.upgrade(config, "20261026_0090")
        signup_demo.create_synthetic_owner(url)
        command.upgrade(config, demo.REVISION)

        if runner == "local_photographer_demo":
            with Session(postgres_schema) as db:
                signup = PhotographerSignup(
                    photographer_name="Fotógrafo sintético",
                    email=f"schema-{uuid4().hex}@example.test",
                    state="email_pending",
                    otp_expires_at=now(),
                    adult_attested_at=now(),
                )
                db.add(signup)
                db.commit()
                assert db.get(PhotographerSignup, signup.id).adult_attested_at is not None
            signup_demo.require_current_schema(url)
        else:
            os.environ["PYP_CLOSURE_DEMO_PASSWORD"] = "SyntheticLocalDemo#83"
            os.environ["PYP_CLOSURE_DEMO_TOTP"] = "JBSWY3DPEHPK3PXP"
            os.environ["PHOTOGRAPHER_CPF_FINGERPRINT_KEYS_JSON"] = ""
            os.environ["PHOTOGRAPHER_CPF_FINGERPRINT_ACTIVE_KEY_VERSION"] = "legacy-v0"
            demo.seed_accounts(url)
            with Session(postgres_schema) as db:
                closure = db.scalar(select(TenantClosureRequest))
                assert closure is not None and closure.state == "closed"

        inspector = inspect(postgres_schema)
        for model in (PhotographerSignup, TenantClosureRequest):
            actual = {column["name"] for column in inspector.get_columns(model.__tablename__)}
            assert set(model.__table__.columns.keys()) <= actual
