from uuid import uuid4

import pyotp
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth import AdminUser
from app.totp_crypto import TotpSecretCipher


def test_admin_totp_is_encrypted_in_database_and_transparent_to_authentication(monkeypatch):
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "false")
    engine = create_engine("sqlite://")
    AdminUser.__table__.create(engine)
    admin_id = uuid4()
    plaintext = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    try:
        with Session(engine) as db:
            db.add(AdminUser(id=admin_id, email="synthetic@example.test",
                             password_hash="synthetic-hash", totp_secret=plaintext))
            db.commit()
            stored = db.execute(
                text("SELECT totp_secret, totp_secret_envelope FROM admin_user WHERE email = :email"),
                {"email": "synthetic@example.test"},
            ).one()
            assert stored.totp_secret is None
            assert stored.totp_secret_envelope.startswith("totp:v1:")
            assert plaintext not in stored.totp_secret_envelope

        with Session(engine) as db:
            restored = db.get(AdminUser, admin_id)
            assert restored is not None
            assert restored.totp_secret == plaintext
    finally:
        AdminUser.__table__.drop(engine)
        engine.dispose()


def test_dual_write_keeps_legacy_reader_working_and_reconciles_legacy_writes(monkeypatch):
    monkeypatch.setenv("ADMIN_TOTP_LEGACY_DUAL_WRITE", "true")
    engine = create_engine("sqlite://")
    AdminUser.__table__.create(engine)
    admin_id = uuid4()
    original = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    updated_by_legacy = "MFRGGZDFMZTWQ2LKMFRGGZDFMZTWQ2LK"
    try:
        with Session(engine) as db:
            db.add(AdminUser(
                id=admin_id, email="dual@example.test", password_hash="synthetic",
                totp_secret=original,
            ))
            db.commit()

        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE admin_user SET totp_secret = :secret WHERE id = :admin_id"
            ), {"secret": updated_by_legacy, "admin_id": admin_id.hex})

        with Session(engine) as db:
            admin = db.get(AdminUser, admin_id)
            assert admin is not None and admin.totp_secret == updated_by_legacy
            db.flush()
            stored = db.execute(text(
                "SELECT totp_secret, totp_secret_envelope FROM admin_user WHERE id = :admin_id"
            ), {"admin_id": admin_id.hex}).one()
            assert stored.totp_secret == updated_by_legacy
            assert TotpSecretCipher.from_environment().decrypt(
                stored.totp_secret_envelope, admin_id=admin_id
            ) == updated_by_legacy

        # A legacy ORM selects only the old column, as the deployed API does.
        with engine.connect() as connection:
            legacy_secret = connection.scalar(text(
                "SELECT totp_secret FROM admin_user WHERE id = :admin_id"
            ), {"admin_id": admin_id.hex})
        code = pyotp.TOTP(legacy_secret).now()
        assert pyotp.TOTP(legacy_secret).verify(code, valid_window=1)
    finally:
        AdminUser.__table__.drop(engine)
        engine.dispose()
