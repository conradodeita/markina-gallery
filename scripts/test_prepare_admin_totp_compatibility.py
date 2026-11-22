import base64
import importlib.util
import json
import sys
from pathlib import Path
from uuid import uuid4

import pyotp
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from scripts.prepare_admin_totp_compatibility import (
    compatibility_source,
    prepare_package,
    sha256,
)

LEGACY = b'''"""Synthetic legacy module; no production settings."""
from __future__ import annotations
from uuid import UUID, uuid4
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import TypeDecorator

# Preserve PostgreSQL UUID text semantics for SQL migration helpers on SQLite.
class LegacyUuid(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, _dialect):
        return UUID(value) if value is not None else None

class Base(DeclarativeBase):
    pass

class AdminUser(Base):
    __tablename__ = "admin_user"
    id: Mapped[UUID] = mapped_column(LegacyUuid(), primary_key=True, default=uuid4)
    totp_secret: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(320))

# downstream-contract: preserve this text and the function bytes
def unrelated_contract():
    return "totp_secret: Mapped[str] = mapped_column(String(128))"
'''
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
UPDATED = "MFRGGZDFMZTWQ2LKMFRGGZDFMZTWQ2LK"
BASE_IMAGE = "sha256:" + "a" * 64


@pytest.fixture
def compatible_module(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "backend"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "test")
    monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "synthetic")
    monkeypatch.setenv("ADMIN_TOTP_KEYS", json.dumps({
        "synthetic": base64.b64encode(b"k" * 32).decode(),
    }))
    path = tmp_path / "compatibility.py"
    path.write_bytes(compatibility_source(LEGACY, expected_sha256=sha256(LEGACY)))
    spec = importlib.util.spec_from_file_location("_pyp_compat_" + uuid4().hex, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    try:
        yield module
    finally:
        event.remove(Session, "before_flush", module._totp_bridge_flush)
        module.Base.registry.dispose()
        sys.modules.pop(module.__name__)


def test_transform_preserves_unrelated_source_and_handles_crlf():
    tail = LEGACY[LEGACY.index(b"# downstream-contract"):]
    for source in (LEGACY, LEGACY.replace(b"\n", b"\r\n")):
        result = compatibility_source(source, expected_sha256=sha256(source))
        expected_tail = tail if b"\r\n" not in source else tail.replace(b"\n", b"\r\n")
        assert expected_tail in result
        assert result.startswith(source.split(b"from uuid", 1)[0])
        compile(result, "compatibility.py", "exec")


@pytest.mark.parametrize("source", [
    LEGACY.replace(b"String(128))", b"String(128), nullable=False)", 1),
    LEGACY.replace(b"class AdminUser(Base):", b"class OtherUser(Base):"),
    LEGACY + b"\nclass AdminUser:\n    pass\n",
])
def test_unknown_or_ambiguous_legacy_model_is_rejected(source):
    with pytest.raises(ValueError):
        compatibility_source(source, expected_sha256=sha256(source))


def test_hash_mismatch_does_not_create_output_or_change_source(tmp_path):
    source = tmp_path / "legacy.py"
    source.write_bytes(LEGACY)
    output = tmp_path / "package"
    with pytest.raises(ValueError, match="hash"):
        prepare_package(source, output, expected_sha256="0" * 64, baseline_image=BASE_IMAGE)
    assert not output.exists()
    assert source.read_bytes() == LEGACY


def test_existing_output_is_preserved_and_artifact_records_immutable_inputs(tmp_path):
    source = tmp_path / "legacy.py"
    source.write_bytes(LEGACY)
    output = tmp_path / "package"
    manifest = prepare_package(source, output, expected_sha256=sha256(LEGACY),
                               baseline_image=BASE_IMAGE)
    assert manifest["baseline_image_id"] == BASE_IMAGE
    assert manifest["auth_sha256"] == sha256((output / "auth.py").read_bytes())
    assert manifest["cipher_sha256"] == sha256((output / "totp_crypto.py").read_bytes())
    assert manifest["external_operations_performed"] is False
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match="novo"):
        prepare_package(source, output, expected_sha256=sha256(LEGACY), baseline_image=BASE_IMAGE)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert source.read_bytes() == LEGACY


def test_legacy_write_and_contract_keep_same_authentication_factor(compatible_module, monkeypatch):
    from app.totp_crypto import TotpSecretCipher
    from app.totp_migration import contract_legacy_totp

    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    engine = create_engine("sqlite://")
    model = compatible_module.AdminUser
    compatible_module.Base.metadata.create_all(engine)
    admin_id = uuid4()
    try:
        with Session(engine) as db:
            db.add(model(id=admin_id, email="synthetic@example.test", totp_secret=SECRET))
            db.commit()
        with engine.begin() as connection:
            stored = connection.execute(text(
                "SELECT totp_secret,totp_secret_envelope FROM admin_user"
            )).one()
            assert stored.totp_secret == SECRET and SECRET not in stored.totp_secret_envelope
            connection.execute(text("UPDATE admin_user SET totp_secret=:value"), {"value": UPDATED})
        with Session(engine) as db:
            admin = db.get(model, admin_id)
            assert admin.totp_secret == UPDATED
            db.commit()
        monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "false")
        with engine.begin() as connection:
            assert contract_legacy_totp(connection, TotpSecretCipher.from_environment()) == 1
            assert connection.scalar(text("SELECT totp_secret FROM admin_user")) is None
        with Session(engine) as db:
            admin = db.get(model, admin_id)
            assert admin.totp_secret == UPDATED
            code = pyotp.TOTP(UPDATED).now()
            assert pyotp.TOTP(admin.totp_secret).verify(code, valid_window=1)
            db.expire(admin)
            assert admin.totp_secret == UPDATED
    finally:
        engine.dispose()


def test_invalid_envelope_fails_closed_even_with_legacy_plaintext(compatible_module, monkeypatch):
    from app.totp_crypto import TotpSecretError

    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    engine = create_engine("sqlite://")
    compatible_module.Base.metadata.create_all(engine)
    admin_id = uuid4()
    try:
        with Session(engine) as db:
            db.add(compatible_module.AdminUser(id=admin_id, email="synthetic@example.test",
                                             totp_secret=SECRET))
            db.commit()
        with engine.begin() as connection:
            connection.execute(text("UPDATE admin_user SET totp_secret_envelope='invalid'"))
        with Session(engine) as db, pytest.raises(TotpSecretError) as denied:
            db.get(compatible_module.AdminUser, admin_id)
        assert SECRET not in str(denied.value)
    finally:
        engine.dispose()
