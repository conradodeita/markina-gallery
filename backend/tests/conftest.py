"""Configuração efêmera e exclusiva para testes locais; nunca use credenciais reais."""

import base64
import json
import os

import pytest

if os.environ.get("APP_ENV") not in {None, "development", "test"}:
    raise RuntimeError("A suíte não pode iniciar com APP_ENV protegido configurado.")

os.environ.setdefault("ADMIN_TOTP_SECRET_ENV", os.environ.get("APP_ENV", "development"))
os.environ.setdefault("ADMIN_TOTP_ACTIVE_KEY_ID", "pytest-only")
os.environ.setdefault(
    "ADMIN_TOTP_KEYS",
    json.dumps({"pytest-only": base64.b64encode(b"pyp-test-key-not-for-any-environment"[:32]).decode()}),
)

# Credenciais exclusivamente sintéticas para os testes que inicializam a aplicação
# fora do ambiente development. Cada finalidade mantém um valor independente.
os.environ.setdefault(
    "GALLERY_CAPABILITY_SIGNING_KEY",
    "pyp-test-gallery-capability-signing-key-only-0001",
)
os.environ.setdefault(
    "AUTH_PII_FINGERPRINT_SALT",
    "pyp-test-auth-pii-fingerprint-salt-only-0001",
)
os.environ.setdefault(
    "INTEGRATION_SECRET_ENV",
    os.environ.get("APP_ENV", "development"),
)
os.environ.setdefault("INTEGRATION_SECRET_ACTIVE_KEY_ID", "pytest-only")
os.environ.setdefault(
    "INTEGRATION_SECRET_KEYS",
    json.dumps({
        "pytest-only": base64.b64encode(b"pyp-test-integration-key-not-for-any-env"[:32]).decode(),
    }),
)


@pytest.fixture(autouse=True)
def isolate_shared_metadata_ddl_rules():
    from app.auth import Base

    # SQLAlchemy attaches DDL rules when PostgreSQL emits cyclic FKs through
    # ALTER TABLE. Restore the shared model state after every case so a later
    # SQLite schema cannot inherit another test's dialect-specific rules.
    rules = [(constraint, constraint._create_rule)
             for table in Base.metadata.tables.values() for constraint in table.constraints]
    try:
        yield
    finally:
        for constraint, rule in rules:
            constraint._create_rule = rule
