import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pyotp
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base

from app.auth import AdminUser
from app.totp_crypto import TotpSecretCipher, TotpSecretError
from app.totp_migration import (
    contract_legacy_totp,
    encrypt_existing_totp,
    restore_legacy_totp,
    rotate_admin_totp_envelopes,
)


def cipher(key_id="active", keys=None):
    return TotpSecretCipher(environment="test", active_key_id=key_id,
                            keys=keys or {key_id: b"k" * 32})


def test_expand_preserves_legacy_value_and_contract_downgrade_restores_it():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE admin_user (id CHAR(36) PRIMARY KEY, totp_secret VARCHAR(128), "
            "totp_secret_envelope VARCHAR(768))"
        ))
        admin_id = uuid4()
        connection.execute(text(
            "INSERT INTO admin_user (id,totp_secret) VALUES (:id,:secret)"
        ),
                           {"id": str(admin_id), "secret": "JBSWY3DPEHPK3PXP"})
        assert encrypt_existing_totp(connection, cipher()) == 1
        row = connection.execute(text(
            "SELECT totp_secret, totp_secret_envelope FROM admin_user"
        )).one()
        assert row.totp_secret == "JBSWY3DPEHPK3PXP"
        first = row.totp_secret_envelope
        assert first.startswith("totp:v1:")
        assert cipher().decrypt(first, admin_id=admin_id) == row.totp_secret
        assert encrypt_existing_totp(connection, cipher()) == 0
        assert connection.scalar(text(
            "SELECT totp_secret_envelope FROM admin_user"
        )) == first
        assert contract_legacy_totp(connection, cipher()) == 1
        assert connection.scalar(text("SELECT totp_secret FROM admin_user")) is None
        assert restore_legacy_totp(connection, cipher()) == 1
        assert connection.scalar(text("SELECT totp_secret FROM admin_user")) == "JBSWY3DPEHPK3PXP"
    engine.dispose()


def test_migration_validates_every_row_before_writing_any_plaintext():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE admin_user (id CHAR(36) PRIMARY KEY, totp_secret VARCHAR(128), "
            "totp_secret_envelope VARCHAR(768))"
        ))
        ids = [uuid4(), uuid4()]
        connection.execute(text(
            "INSERT INTO admin_user (id,totp_secret) VALUES (:id,:secret)"
        ),
                           {"id": str(ids[0]), "secret": "valid-secret"})
        connection.execute(text(
            "INSERT INTO admin_user (id,totp_secret) VALUES (:id,:secret)"
        ),
                           {"id": str(ids[1]), "secret": ""})
        with pytest.raises(TotpSecretError):
            encrypt_existing_totp(connection, cipher())
        rows = connection.execute(text(
            "SELECT totp_secret, totp_secret_envelope FROM admin_user ORDER BY id"
        )).all()
        assert {(row.totp_secret, row.totp_secret_envelope) for row in rows} == {
            ("valid-secret", None), ("", None),
        }
    engine.dispose()


def test_contract_reconciles_legacy_write_and_refuses_to_run_during_dual_write(monkeypatch):
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE admin_user (id CHAR(36) PRIMARY KEY, totp_secret VARCHAR(128), "
            "totp_secret_envelope VARCHAR(768))"
        ))
        admin_id = uuid4()
        connection.execute(text(
            "INSERT INTO admin_user (id,totp_secret,totp_secret_envelope) "
            "VALUES (:id,:legacy,:envelope)"
        ), {
            "id": str(admin_id),
            "legacy": "MFRGGZDFMZTWQ2LK",
            "envelope": cipher().encrypt("JBSWY3DPEHPK3PXP", admin_id=admin_id),
        })
        with pytest.raises(TotpSecretError):
            contract_legacy_totp(connection, cipher())
        assert connection.scalar(text("SELECT totp_secret FROM admin_user")) == "MFRGGZDFMZTWQ2LK"

        monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "false")
        assert contract_legacy_totp(connection, cipher()) == 1
        row = connection.execute(text(
            "SELECT totp_secret,totp_secret_envelope FROM admin_user"
        )).one()
        assert row.totp_secret is None
        assert cipher().decrypt(row.totp_secret_envelope, admin_id=admin_id) == "MFRGGZDFMZTWQ2LK"
    engine.dispose()


def test_rollback_preserves_newer_plaintext_written_by_legacy_binary():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE admin_user (id CHAR(36) PRIMARY KEY, totp_secret VARCHAR(128), "
            "totp_secret_envelope VARCHAR(768))"
        ))
        admin_id = uuid4()
        connection.execute(text(
            "INSERT INTO admin_user (id,totp_secret,totp_secret_envelope) "
            "VALUES (:id,:legacy,:envelope)"
        ), {
            "id": str(admin_id),
            "legacy": "MFRGGZDFMZTWQ2LK",
            "envelope": cipher().encrypt("JBSWY3DPEHPK3PXP", admin_id=admin_id),
        })
        assert restore_legacy_totp(connection, cipher()) == 0
        assert connection.scalar(text("SELECT totp_secret FROM admin_user")) == "MFRGGZDFMZTWQ2LK"
    engine.dispose()


def test_rotation_dry_run_preserves_values_and_apply_uses_active_key(monkeypatch):
    old_key, active_key = b"o" * 32, b"n" * 32
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "active")
    monkeypatch.setenv("ADMIN_TOTP_KEYS", json.dumps({
        "old": base64.b64encode(old_key).decode(),
        "active": base64.b64encode(active_key).decode(),
    }))
    old_cipher = TotpSecretCipher(environment="development", active_key_id="old", keys={"old": old_key})
    active_cipher = TotpSecretCipher(
        environment="development", active_key_id="active", keys={"old": old_key, "active": active_key}
    )
    engine = create_engine("sqlite://")
    AdminUser.__table__.create(engine)
    admin_id = uuid4()
    secret = "synthetic-totp-secret"
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO admin_user "
            "(id,email,password_hash,email_verified,totp_secret_envelope) "
            "VALUES (:id,:email,:password,true,:secret)"
        ), {"id": admin_id.hex, "email": "rotation@example.test", "password": "synthetic",
             "secret": old_cipher.encrypt(secret, admin_id=admin_id)})
    try:
        with Session(engine) as db:
            before = db.execute(text("SELECT totp_secret_envelope FROM admin_user")).scalar_one()
            plan = rotate_admin_totp_envelopes(db, active_cipher, apply=False)
            after_dry_run = db.execute(text("SELECT totp_secret_envelope FROM admin_user")).scalar_one()
            assert before == after_dry_run
            assert plan == {"old": 1, "recifrados": 0, "pendentes": 1}
        with Session(engine) as db:
            result = rotate_admin_totp_envelopes(db, active_cipher, apply=True)
            db.commit()
        with Session(engine) as db:
            stored = db.execute(text("SELECT totp_secret_envelope FROM admin_user")).scalar_one()
            assert stored.startswith("totp:v1:active:")
            assert active_cipher.decrypt(stored, admin_id=admin_id) == secret
            assert db.get(AdminUser, admin_id).totp_secret == secret
        assert result == {"old": 1, "recifrados": 1, "pendentes": 1}
    finally:
        AdminUser.__table__.drop(engine)
        engine.dispose()


def test_rotation_dry_run_does_not_commit_legacy_reconciliation(monkeypatch):
    old_key, active_key = b"o" * 32, b"n" * 32
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "development")
    monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "active")
    monkeypatch.setenv("ADMIN_TOTP_KEYS", json.dumps({
        "old": base64.b64encode(old_key).decode(),
        "active": base64.b64encode(active_key).decode(),
    }))
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    old_cipher = TotpSecretCipher(environment="development", active_key_id="old", keys={"old": old_key})
    active_cipher = TotpSecretCipher(
        environment="development", active_key_id="active", keys={"old": old_key, "active": active_key}
    )
    engine = create_engine("sqlite://")
    AdminUser.__table__.create(engine)
    admin_id = uuid4()
    previous_secret, latest_legacy_secret = "old-totp-secret", "latest-legacy-secret"
    previous_envelope = old_cipher.encrypt(previous_secret, admin_id=admin_id)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO admin_user "
            "(id,email,password_hash,email_verified,totp_secret,totp_secret_envelope) "
            "VALUES (:id,:email,:password,true,:legacy,:envelope)"
        ), {"id": admin_id.hex, "email": "rotation-legacy@example.test", "password": "synthetic",
             "legacy": latest_legacy_secret, "envelope": previous_envelope})
    try:
        with Session(engine) as db, db.begin():
            plan = rotate_admin_totp_envelopes(db, active_cipher, apply=False)
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT totp_secret,totp_secret_envelope FROM admin_user"
            )).one()
        assert row.totp_secret == latest_legacy_secret
        assert row.totp_secret_envelope == previous_envelope
        assert plan == {"old": 1, "recifrados": 0, "pendentes": 1}

        with Session(engine) as db, db.begin():
            result = rotate_admin_totp_envelopes(db, active_cipher, apply=True)
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT totp_secret,totp_secret_envelope FROM admin_user"
            )).one()
        assert row.totp_secret == latest_legacy_secret
        assert row.totp_secret_envelope.startswith("totp:v1:active:")
        assert active_cipher.decrypt(row.totp_secret_envelope, admin_id=admin_id) == latest_legacy_secret
        assert result == {"old": 1, "recifrados": 1, "pendentes": 1}
    finally:
        AdminUser.__table__.drop(engine)
        engine.dispose()


def test_postgresql_upgrade_failure_rolls_back_schema_and_all_secret_rows(monkeypatch):
    raw_url = os.getenv("TOTP_MIGRATION_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer TOTP_MIGRATION_TEST_DATABASE_URL no PostgreSQL descartável")
    base_url = sa.engine.make_url(raw_url)
    if (base_url.host, base_url.port, base_url.database) != (
        "127.0.0.1", 53005, "totp_migration_test",
    ):
        pytest.fail("A migration TOTP exige o PostgreSQL descartável local dedicado")

    admin_url = base_url.set(drivername="postgresql+psycopg")
    control = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    database = f"totp_malformed_{uuid4().hex}"
    try:
        with control.connect() as connection:
            connection.execute(sa.text(f'CREATE DATABASE "{database}"'))
        migration_url = admin_url.set(database=database).render_as_string(hide_password=False)
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "test")
        monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "pytest-only")
        monkeypatch.setenv(
            "ADMIN_TOTP_KEYS",
            json.dumps({"pytest-only": base64.b64encode(b"pyp-test-key-not-for-any-environment"[:32]).decode()}),
        )

        def migrate(*arguments, succeeds=True):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", *arguments],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "DATABASE_URL": migration_url},
                capture_output=True,
                text=True,
                check=False,
            )
            assert (result.returncode == 0) == succeeds, result.stderr
            return result

        migrate("upgrade", "20261026_0090")
        engine = create_engine(migration_url)
        valid_id, malformed_id = UUID(int=1), UUID(int=2)
        valid_secret = "JBSWY3DPEHPK3PXP"
        with engine.begin() as connection:
            for admin_id, email, secret in (
                (valid_id, "valid@example.test", valid_secret),
                (malformed_id, "malformed@example.test", ""),
            ):
                connection.execute(text(
                    "INSERT INTO admin_user (id,email,password_hash,email_verified,totp_secret) "
                    "VALUES (:id,:email,'synthetic-hash',true,:secret)"
                ), {"id": admin_id, "email": email, "secret": secret})

        result = migrate("upgrade", "20261031_0091", succeeds=False)
        assert "Proteção do autenticador temporariamente indisponível." in result.stderr
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261026_0090"
            columns = {column["name"]: column for column in sa.inspect(connection).get_columns("admin_user")}
            assert "totp_last_used_step" not in columns
            assert "totp_secret_envelope" not in columns
            assert columns["totp_secret"]["type"].length == 128
            assert columns["totp_secret"]["nullable"] is False
            stored = connection.execute(text(
                "SELECT id,totp_secret FROM admin_user ORDER BY id"
            )).all()
            assert [(row.id, row.totp_secret) for row in stored] == [
                (valid_id, valid_secret), (malformed_id, ""),
            ]
        engine.dispose()
    finally:
        with control.connect() as connection:
            connection.execute(sa.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :database AND pid <> pg_backend_pid()"
            ), {"database": database})
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{database}"'))
        control.dispose()


def test_postgresql_expand_keeps_legacy_orm_live_and_contract_is_reversible(monkeypatch):
    raw_url = os.getenv("TOTP_MIGRATION_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer TOTP_MIGRATION_TEST_DATABASE_URL no PostgreSQL descartável")
    base_url = sa.engine.make_url(raw_url)
    if (base_url.host, base_url.port, base_url.database) != (
        "127.0.0.1", 53005, "totp_migration_test",
    ):
        pytest.fail("A migration TOTP exige o PostgreSQL descartável local dedicado")

    admin_url = base_url.set(drivername="postgresql+psycopg")
    control = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    database = f"totp_expand_{uuid4().hex}"
    try:
        with control.connect() as connection:
            connection.execute(sa.text(f'CREATE DATABASE "{database}"'))
        migration_url = admin_url.set(database=database).render_as_string(hide_password=False)
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("ADMIN_TOTP_SECRET_ENV", "test")
        monkeypatch.setenv("ADMIN_TOTP_ACTIVE_KEY_ID", "pytest-only")
        monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
        monkeypatch.setenv(
            "ADMIN_TOTP_KEYS",
            json.dumps({"pytest-only": base64.b64encode(b"pyp-test-key-not-for-any-environment"[:32]).decode()}),
        )

        def migrate(*arguments):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", *arguments],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "DATABASE_URL": migration_url},
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr

        migrate("upgrade", "20261031_0092")
        engine = create_engine(migration_url)
        admin_id = UUID(int=4101)
        original_secret = "JBSWY3DPEHPK3PXP"
        legacy_updated_secret = "MFRGGZDFMZTWQ2LK"
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO admin_user "
                "(id,email,password_hash,email_verified,totp_secret) "
                "VALUES (:id,:email,'synthetic-hash',true,:secret)"
            ), {"id": admin_id, "email": "legacy@example.test", "secret": original_secret})

        legacy_base = declarative_base()

        class LegacyAdmin(legacy_base):
            __tablename__ = "admin_user"
            id = sa.Column(sa.Uuid(), primary_key=True)
            totp_secret = sa.Column(sa.String(128), nullable=False)

        # The old binary maps only totp_secret and verifies the same factor after 0091.
        with Session(engine) as db:
            legacy = db.get(LegacyAdmin, admin_id)
            assert legacy is not None and legacy.totp_secret == original_secret
            code = pyotp.TOTP(legacy.totp_secret).now()
            assert pyotp.TOTP(legacy.totp_secret).verify(code, valid_window=1)

        # Simulate an old binary updating the legacy field during coexistence.
        with Session(engine) as db:
            legacy = db.get(LegacyAdmin, admin_id)
            assert legacy is not None
            legacy.totp_secret = legacy_updated_secret
            db.commit()
        # A prova histórica usa o reconciliador real de 0091/0093. O ORM atual
        # também exige totp_enabled (0099) e não representa o binário de 0092.
        with engine.begin() as connection:
            active_cipher = TotpSecretCipher.from_environment()
            assert encrypt_existing_totp(connection, active_cipher) == 1
            values = connection.execute(text(
                "SELECT totp_secret,totp_secret_envelope FROM admin_user WHERE id=:id"
            ), {"id": admin_id}).one()
            assert values.totp_secret == legacy_updated_secret
            decrypted = active_cipher.decrypt(
                values.totp_secret_envelope, admin_id=admin_id
            )
            assert decrypted == legacy_updated_secret
            code = pyotp.TOTP(decrypted).now()
            assert pyotp.TOTP(decrypted).verify(code, valid_window=1)

        monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "false")
        migrate("upgrade", "20261031_0093")
        with engine.connect() as connection:
            values = connection.execute(text(
                "SELECT totp_secret,totp_secret_envelope FROM admin_user WHERE id=:id"
            ), {"id": admin_id}).one()
            assert values.totp_secret is None
            assert TotpSecretCipher.from_environment().decrypt(
                values.totp_secret_envelope, admin_id=admin_id
            ) == legacy_updated_secret

        migrate("downgrade", "20261031_0092")
        with Session(engine) as db:
            legacy = db.get(LegacyAdmin, admin_id)
            assert legacy is not None and legacy.totp_secret == legacy_updated_secret
            code = pyotp.TOTP(legacy.totp_secret).now()
            assert pyotp.TOTP(legacy.totp_secret).verify(code, valid_window=1)

        migrate("downgrade", "20261026_0090")
        with engine.connect() as connection:
            columns = {column["name"] for column in sa.inspect(connection).get_columns("admin_user")}
            assert "totp_secret_envelope" not in columns
            assert "totp_last_used_step" not in columns
            assert connection.scalar(text(
                "SELECT totp_secret FROM admin_user WHERE id=:id"
            ), {"id": admin_id}) == legacy_updated_secret
        engine.dispose()
    finally:
        with control.connect() as connection:
            connection.execute(sa.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :database AND pid <> pg_backend_pid()"
            ), {"database": database})
            connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{database}"'))
        control.dispose()
