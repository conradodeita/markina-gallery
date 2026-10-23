"""Migration cirúrgica: remove operação e mantém os registros financeiros."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20261022_0087_retire_infinitepay.py"
SPEC = importlib.util.spec_from_file_location("retire_infinitepay_migration", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_removes_secrets_and_checkout_url_preserving_history():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE infinitepay_credential (id TEXT PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE infinitepay_settings (id TEXT PRIMARY KEY)")
        connection.exec_driver_sql("""CREATE TABLE provider_payment (
            id TEXT PRIMARY KEY, credential_id TEXT,
            checkout_url TEXT, state TEXT NOT NULL, total_cents INTEGER NOT NULL,
            CONSTRAINT fk_provider_payment_credential_owner
            FOREIGN KEY(credential_id) REFERENCES infinitepay_credential(id))""")
        connection.exec_driver_sql("CREATE TABLE provider_payment_attempt (id TEXT PRIMARY KEY, payment_id TEXT)")
        connection.exec_driver_sql("CREATE TABLE provider_payment_receipt (id TEXT PRIMARY KEY, payment_id TEXT)")
        connection.exec_driver_sql("CREATE TABLE provider_payment_correction (id TEXT PRIMARY KEY, payment_id TEXT)")
        connection.exec_driver_sql("""CREATE TABLE admin_security_challenge (
            id TEXT PRIMARY KEY, purpose TEXT NOT NULL,
            CONSTRAINT ck_admin_security_purpose CHECK (purpose IN (
              'password_recovery_otp', 'change_password_otp', 'change_email_otp',
              'change_pix_otp', 'change_infinitepay_otp')),
            CONSTRAINT ck_admin_challenge_infinitepay_context CHECK (
              purpose != 'change_infinitepay_otp' OR id IS NOT NULL))""")
        connection.exec_driver_sql("INSERT INTO infinitepay_credential VALUES ('cred-1')")
        connection.exec_driver_sql("INSERT INTO infinitepay_settings VALUES ('settings-1')")
        connection.exec_driver_sql("INSERT INTO provider_payment VALUES ('payment-1', 'cred-1', 'https://old.invalid', 'confirmed', 1000)")
        connection.exec_driver_sql("INSERT INTO provider_payment_attempt VALUES ('attempt-1', 'payment-1')")
        connection.exec_driver_sql("INSERT INTO provider_payment_receipt VALUES ('receipt-1', 'payment-1')")
        connection.exec_driver_sql("INSERT INTO provider_payment_correction VALUES ('correction-1', 'payment-1')")
        connection.exec_driver_sql("INSERT INTO admin_security_challenge VALUES ('otp-old', 'change_infinitepay_otp')")
        connection.exec_driver_sql("INSERT INTO admin_security_challenge VALUES ('otp-pix', 'change_pix_otp')")

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            MIGRATION.upgrade()

        inspector = sa.inspect(connection)
        assert not inspector.has_table("infinitepay_settings")
        assert not inspector.has_table("infinitepay_credential")
        assert {column["name"] for column in inspector.get_columns("provider_payment")} == {
            "id", "state", "total_cents",
        }
        assert connection.exec_driver_sql("SELECT id, state, total_cents FROM provider_payment").all() == [
            ("payment-1", "confirmed", 1000),
        ]
        for table, expected in (("provider_payment_attempt", "attempt-1"),
                                ("provider_payment_receipt", "receipt-1"),
                                ("provider_payment_correction", "correction-1")):
            assert connection.exec_driver_sql(f"SELECT id FROM {table}").scalar_one() == expected
        assert connection.exec_driver_sql("SELECT id FROM admin_security_challenge").all() == [("otp-pix",)]
    engine.dispose()


def test_downgrade_recusa_recriar_segredos_e_links_removidos():
    try:
        MIGRATION.downgrade()
    except RuntimeError as error:
        assert "irreversível" in str(error)
    else:
        raise AssertionError("A migration deve registrar que a reversão precisa de backup.")
