"""Ensaios locais da re-cifragem; usam somente valores e chaves sintéticos."""

import json
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.app_env_transition import (
    APP_ENV_CONSUMER_SERVICES,
    EncryptedTransitionBackup,
    EnvironmentTransitionError,
    _execute_mercadopago_transition,
    create_encrypted_transition_backup,
    create_mercadopago_transition_plan,
    execute_approved_mercadopago_transition,
    restore_mercadopago_transition_backup,
)
from app.auth import (
    Client,
    MercadoPagoAccount,
    MercadoPagoPayment,
    PaymentPreferences,
    Tenant,
)
from app.environment_transition_inventory import (
    BIOMETRIC_COUNTERS,
    CONFIG_DIGEST_NAMES,
    CREDENTIAL_COUNTERS,
    EXPECTED_SERVICES,
    RETIRED_SERVICES,
    build_environment_inventory,
)
from app.integration_secrets import IntegrationCipher, SecretEnvelope


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    for model in (Tenant, Client, MercadoPagoAccount, PaymentPreferences, MercadoPagoPayment):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory, engine
    engine.dispose()


@pytest.fixture
def isolated_postgres_database():
    raw_url = os.getenv("APP_ENV_TRANSITION_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Requer APP_ENV_TRANSITION_TEST_DATABASE_URL explicitamente configurada")
    try:
        url = make_url(raw_url)
    except (TypeError, ValueError):
        pytest.fail("APP_ENV_TRANSITION_TEST_DATABASE_URL inválida")
    if (url.get_backend_name() != "postgresql"
            or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.database != "app_env_transition_test"):
        pytest.fail("O teste PostgreSQL exige banco local app_env_transition_test")

    engine = create_engine(url)
    schema = "app_env_transition_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        for model in (Tenant, Client, MercadoPagoAccount, PaymentPreferences, MercadoPagoPayment):
            model.__table__.create(scoped)
        factory = sessionmaker(bind=scoped, expire_on_commit=False)
        yield factory
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture
def cipher_pair():
    source = IntegrationCipher.from_explicit_context(
        environment="staging", secret_environment="staging", active_key_id="test-key",
        keys={"test-key": b"s" * 32},
    )
    return source, source.for_environment("production")


def _seed_account(db: Session, source: IntegrationCipher, *, number: int):
    tenant = Tenant(id=UUID(int=100 + number), status="active")
    client = Client(tenant_id=tenant.id, full_name=f"Synthetic {number}",
                    phone_e164=f"+55119999999{number:02d}")
    account = MercadoPagoAccount(
        id=UUID(int=number), tenant_id=tenant.id, seller_id=str(1000 + number),
        public_key=f"APP_USR-synthetic-public-{number}", test_account=True,
        status="active",
        access_token_envelope=source.encrypt(
            f"synthetic-token-{number}", tenant_id=tenant.id, credential_id=UUID(int=number)).payload(),
        webhook_secret_envelope=source.encrypt(
            f"synthetic-webhook-{number}", tenant_id=tenant.id, credential_id=UUID(int=number)).payload(),
    )
    db.add_all([tenant, client, account])
    db.flush()
    preference = PaymentPreferences(
        tenant_id=tenant.id, account_id=account.id, pix_enabled=True,
        mercadopago_enabled=True, version=7,
    )
    payment = MercadoPagoPayment(
        id=UUID(int=200 + number), tenant_id=tenant.id, client_id=client.id,
        account_id=account.id, checkout_key=str(uuid4()), cart_revision=f"{number:064x}",
        total_cents=1234 + number, method="credit_card", state="processing",
        provider_order_id=f"synthetic-order-{number}",
    )
    db.add_all([preference, payment])
    return tenant, client, account, preference, payment


def _contexts_match(row: MercadoPagoAccount, cipher: IntegrationCipher) -> tuple[str, str]:
    return (
        cipher.decrypt(SecretEnvelope.from_payload(row.access_token_envelope),
                       tenant_id=row.tenant_id, credential_id=row.id),
        cipher.decrypt(SecretEnvelope.from_payload(row.webhook_secret_envelope),
                       tenant_id=row.tenant_id, credential_id=row.id),
    )


def _approved_inventory(*, account_count: int, **overrides):
    services = []
    for name in sorted(EXPECTED_SERVICES):
        retired = name in RETIRED_SERVICES
        services.append({
            "name": name,
            "status": "missing" if retired else "running",
            "health": "unknown" if retired else "healthy",
            "image_digest": None if retired else "sha256:" + "1" * 64,
            "revision": None if retired else "a" * 40,
            "ports": ([{"host_ip": "127.0.0.1", "host_port": 8080}] if name == "nginx" else []),
        })
    evidence = {
        name: {"enabled": False, "credential_matches_target": None,
               "provider_validated_for_target": None}
        for name in ("facial", "smtp", "whatsapp")
    }
    values = {
        "source_environment": "staging",
        "target_environment": "production",
        "code_revision": "a" * 40,
        "schema_revision": "20261028_0090",
        "services": services,
        "configuration_digests": {name: "b" * 64 for name in CONFIG_DIGEST_NAMES},
        "credential_counts": {name: account_count for name in CREDENTIAL_COUNTERS},
        "biometric_counts": {name: 0 for name in BIOMETRIC_COUNTERS},
        "integration_evidence": evidence,
        "live_payment_gate": False,
        "unknown_consumer_count": 0,
    }
    values.update(overrides)
    return build_environment_inventory(**values)


def test_transition_preserves_tenants_preferences_and_payment_snapshots(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
        _seed_account(db, source, number=2)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        before_preferences = list(db.scalars(select(PaymentPreferences).order_by(
            PaymentPreferences.tenant_id)).all())
        before_payments = list(db.scalars(select(MercadoPagoPayment).order_by(
            MercadoPagoPayment.id)).all())
        preference_snapshot = [(item.tenant_id, item.account_id, item.pix_enabled,
                                item.mercadopago_enabled, item.version) for item in before_preferences]
        payment_snapshot = [(
            item.id, item.tenant_id, item.client_id, item.account_id, item.checkout_key,
            item.cart_revision, item.total_cents, item.method, item.state, item.provider_order_id,
        ) for item in before_payments]

    with factory() as db:
        result = _execute_mercadopago_transition(db, plan, source=source, target=target)
    with factory() as db:
        accounts = list(db.scalars(select(MercadoPagoAccount).order_by(MercadoPagoAccount.id)).all())
        assert len(accounts) == 2
        assert [_contexts_match(account, target) for account in accounts] == [
            ("synthetic-token-1", "synthetic-webhook-1"),
            ("synthetic-token-2", "synthetic-webhook-2"),
        ]
        assert all(SecretEnvelope.from_payload(account.access_token_envelope).environment == "production"
                   for account in accounts)
        assert all(SecretEnvelope.from_payload(account.webhook_secret_envelope).environment == "production"
                   for account in accounts)
        after_preferences = list(db.scalars(select(PaymentPreferences).order_by(
            PaymentPreferences.tenant_id)).all())
        after_payments = list(db.scalars(select(MercadoPagoPayment).order_by(
            MercadoPagoPayment.id)).all())
        assert [(item.tenant_id, item.account_id, item.pix_enabled,
                 item.mercadopago_enabled, item.version) for item in after_preferences] == preference_snapshot
        assert [(
            item.id, item.tenant_id, item.client_id, item.account_id, item.checkout_key,
            item.cart_revision, item.total_cents, item.method, item.state, item.provider_order_id,
        ) for item in after_payments] == payment_snapshot
    assert result.account_count == 2
    assert result.source_category == "outro_ambiente_conhecido"
    assert result.target_category == "production"
    assert result.before_fingerprint == plan.fingerprint
    assert result.after_fingerprint != plan.fingerprint
    assert "synthetic-token" not in repr(result)


def test_transition_revalidates_fingerprint_before_first_write(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _, _, seeded, _, _ = _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory.begin() as db:
        account = db.get(MercadoPagoAccount, seeded.id)
        account.public_key = "APP_USR-synthetic-changed-after-plan"
    with factory() as db, pytest.raises(EnvironmentTransitionError):
        _execute_mercadopago_transition(db, plan, source=source, target=target)
    with factory() as db:
        account = db.get(MercadoPagoAccount, seeded.id)
        assert SecretEnvelope.from_payload(account.access_token_envelope).environment == "staging"
        assert _contexts_match(account, source) == ("synthetic-token-1", "synthetic-webhook-1")


def test_transition_rolls_back_all_accounts_if_later_update_fails(database, cipher_pair):
    factory, engine = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
        _seed_account(db, source, number=2)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TRIGGER fail_second_mp_envelope BEFORE UPDATE OF access_token_envelope "
            "ON mercadopago_account WHEN NEW.seller_id = '1002' "
            "BEGIN SELECT RAISE(ABORT, 'synthetic update failure'); END"
        ))
    with factory() as db, pytest.raises(EnvironmentTransitionError):
        _execute_mercadopago_transition(db, plan, source=source, target=target)
    with factory() as db:
        accounts = list(db.scalars(select(MercadoPagoAccount).order_by(MercadoPagoAccount.id)).all())
        assert len(accounts) == 2
        assert all(SecretEnvelope.from_payload(account.access_token_envelope).environment == "staging"
                   for account in accounts)
        assert all(SecretEnvelope.from_payload(account.webhook_secret_envelope).environment == "staging"
                   for account in accounts)
        assert [_contexts_match(account, source) for account in accounts] == [
            ("synthetic-token-1", "synthetic-webhook-1"),
            ("synthetic-token-2", "synthetic-webhook-2"),
        ]


def test_plan_fails_closed_for_envelope_from_another_context(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _, _, account, _, _ = _seed_account(db, source, number=1)
        wrong_context = source.for_environment("homolog")
        account.webhook_secret_envelope = wrong_context.encrypt(
            "synthetic-wrong-context", tenant_id=account.tenant_id,
            credential_id=account.id).payload()
    with factory() as db, pytest.raises(EnvironmentTransitionError):
        create_mercadopago_transition_plan(db, source=source, target=target)


def test_encrypted_backup_restores_context_without_exposing_plaintext(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)
    serialized = str(backup.payload())
    assert "synthetic-token-1" not in serialized
    assert "synthetic-webhook-1" not in serialized
    assert "synthetic-token-1" not in repr(backup)

    with factory() as db:
        _execute_mercadopago_transition(db, plan, source=source, target=target)
    with factory() as db:
        restored = restore_mercadopago_transition_backup(
            db, EncryptedTransitionBackup.from_payload(backup.payload()),
            source=source, target=target,
        )
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        assert _contexts_match(account, source) == ("synthetic-token-1", "synthetic-webhook-1")
        assert SecretEnvelope.from_payload(account.access_token_envelope).environment == "staging"
    assert restored.account_count == 1
    assert restored.restored_fingerprint == plan.fingerprint
    assert restored.configuration_context.app_environment == "staging"
    assert restored.configuration_context.integration_secret_environment == "staging"
    assert restored.configuration_context.active_key_id == "test-key"
    assert "staging" not in repr(restored)


def test_corrupt_encrypted_backup_aborts_before_recovery_write(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)
    with factory() as db:
        _execute_mercadopago_transition(db, plan, source=source, target=target)
    corrupt = backup.payload()
    corrupt["ciphertext"] = ("A" if corrupt["ciphertext"][0] != "A" else "B") + corrupt["ciphertext"][1:]
    with factory() as db, pytest.raises(EnvironmentTransitionError):
        restore_mercadopago_transition_backup(
            db, EncryptedTransitionBackup.from_payload(corrupt), source=source, target=target,
        )
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        assert SecretEnvelope.from_payload(account.access_token_envelope).environment == "production"
        assert _contexts_match(account, target) == ("synthetic-token-1", "synthetic-webhook-1")


def test_recovery_rolls_back_if_a_later_account_update_fails(database, cipher_pair):
    factory, engine = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
        _seed_account(db, source, number=2)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)
    with factory() as db:
        _execute_mercadopago_transition(db, plan, source=source, target=target)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TRIGGER fail_second_recovery BEFORE UPDATE OF access_token_envelope "
            "ON mercadopago_account WHEN NEW.seller_id = '1002' "
            "BEGIN SELECT RAISE(ABORT, 'synthetic recovery failure'); END"
        ))
    with factory() as db, pytest.raises(EnvironmentTransitionError):
        restore_mercadopago_transition_backup(db, backup, source=source, target=target)
    with factory() as db:
        accounts = list(db.scalars(select(MercadoPagoAccount).order_by(MercadoPagoAccount.id)).all())
        assert all(SecretEnvelope.from_payload(account.access_token_envelope).environment == "production"
                   for account in accounts)
        assert [_contexts_match(account, target) for account in accounts] == [
            ("synthetic-token-1", "synthetic-webhook-1"),
            ("synthetic-token-2", "synthetic-webhook-2"),
        ]


def test_postgresql_transition_locks_and_preserves_financial_rows(
    isolated_postgres_database, cipher_pair,
):
    factory = isolated_postgres_database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        result = _execute_mercadopago_transition(db, plan, source=source, target=target)
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        payment = db.get(MercadoPagoPayment, UUID(int=201))
        assert _contexts_match(account, target) == ("synthetic-token-1", "synthetic-webhook-1")
        assert payment.total_cents == 1235
        assert payment.cart_revision == f"{1:064x}"
        assert payment.state == "processing"
        assert payment.provider_order_id == "synthetic-order-1"
    assert result.account_count == 1


@pytest.mark.parametrize("blocked_gate", [
    "confirmation", "inventory_fingerprint", "consumers", "backup", "facial", "integration",
])
def test_operational_gate_aborts_before_write(database, cipher_pair, blocked_gate):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)
    overrides = {}
    paused = APP_ENV_CONSUMER_SERVICES
    backup_verified = True
    if blocked_gate == "facial":
        from app.environment_transition_inventory import BIOMETRIC_COUNTERS

        overrides["biometric_counts"] = {**{name: 0 for name in BIOMETRIC_COUNTERS}, "photo_embeddings": 1}
    elif blocked_gate == "integration":
        overrides["integration_evidence"] = {
            "facial": {"enabled": False, "credential_matches_target": None,
                       "provider_validated_for_target": None},
            "smtp": {"enabled": True, "credential_matches_target": False,
                     "provider_validated_for_target": True},
            "whatsapp": {"enabled": False, "credential_matches_target": None,
                          "provider_validated_for_target": None},
        }
    elif blocked_gate == "consumers":
        paused = APP_ENV_CONSUMER_SERVICES - {"worker"}
    elif blocked_gate == "backup":
        backup_verified = False

    inventory = _approved_inventory(account_count=1, **overrides)
    expected = inventory["approval_fingerprint"]
    if blocked_gate == "inventory_fingerprint":
        expected = "0" * 64
    confirmation = (f"APLICAR_TRANSICAO_APP_ENV:{inventory['approval_fingerprint']}:{plan.fingerprint}"
                    if inventory["approval_fingerprint"] else "invalid")
    if blocked_gate == "confirmation":
        confirmation = "invalid"

    with factory() as db, pytest.raises(EnvironmentTransitionError):
        execute_approved_mercadopago_transition(
            db, plan, backup, source=source, target=target,
            inventory=inventory,
            approved_inventory_fingerprint=expected,
            operator_confirmation=confirmation,
            paused_consumers=paused,
            backup_storage_verified=backup_verified,
        )
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        assert _contexts_match(account, source) == ("synthetic-token-1", "synthetic-webhook-1")


def test_operational_gate_accepts_exact_inventory_backup_and_confirmation(database, cipher_pair):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)
    inventory = _approved_inventory(account_count=1)
    fingerprint = inventory["approval_fingerprint"]
    with factory() as db:
        result = execute_approved_mercadopago_transition(
            db, plan, backup, source=source, target=target,
            inventory=inventory,
            approved_inventory_fingerprint=fingerprint,
            operator_confirmation=f"APLICAR_TRANSICAO_APP_ENV:{fingerprint}:{plan.fingerprint}",
            paused_consumers=APP_ENV_CONSUMER_SERVICES,
            backup_storage_verified=True,
        )
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        assert _contexts_match(account, target) == ("synthetic-token-1", "synthetic-webhook-1")
    assert result.account_count == 1


def test_synthetic_runbook_roundtrip_has_no_secrets_or_external_calls(database, cipher_pair, tmp_path):
    factory, _ = database
    source, target = cipher_pair
    with factory.begin() as db:
        _seed_account(db, source, number=1)
    with factory() as db:
        plan = create_mercadopago_transition_plan(db, source=source, target=target)
    with factory() as db:
        backup = create_encrypted_transition_backup(db, plan, source=source, target=target)

    backup_path = tmp_path / "encrypted-transition-backup.json"
    backup_path.write_text(json.dumps(backup.payload()), encoding="utf-8")
    stored_backup = backup_path.read_text(encoding="utf-8")
    assert "synthetic-token-1" not in stored_backup
    assert "synthetic-webhook-1" not in stored_backup
    reloaded_backup = EncryptedTransitionBackup.from_payload(json.loads(stored_backup))
    inventory = _approved_inventory(account_count=1)
    fingerprint = inventory["approval_fingerprint"]

    with factory() as db:
        execute_approved_mercadopago_transition(
            db, plan, reloaded_backup, source=source, target=target,
            inventory=inventory,
            approved_inventory_fingerprint=fingerprint,
            operator_confirmation=f"APLICAR_TRANSICAO_APP_ENV:{fingerprint}:{plan.fingerprint}",
            paused_consumers=APP_ENV_CONSUMER_SERVICES,
            backup_storage_verified=True,
        )
    with factory() as db:
        restore_mercadopago_transition_backup(
            db, reloaded_backup, source=source, target=target,
        )
    with factory() as db:
        account = db.get(MercadoPagoAccount, UUID(int=1))
        assert _contexts_match(account, source) == ("synthetic-token-1", "synthetic-webhook-1")
