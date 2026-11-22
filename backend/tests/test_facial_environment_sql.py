import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.app_env_transition import (
    create_encrypted_transition_backup,
    create_mercadopago_transition_plan,
)
from app.auth import MercadoPagoAccount, PhotoFaceEmbedding, WhatsAppChannelSettings
from app.combined_environment_transition import (
    CombinedTransitionError,
    apply_combined_transition,
    recover_combined_transition,
)
from app.facial.crypto import FacialCryptoContext, FacialCryptoContextPair, FacialScope
from app.facial.environment_migration_guard import BiometricWritePreflight
from app.facial.environment_sql import (
    BiometricSqlError,
    EmbeddingSnapshot,
    lock_embedding_snapshot,
    prepare_embedding_destination,
    replace_embedding_envelopes,
)
from app.facial.environment_sql_backup import (
    SqlBackupError,
    SqlTransitionArchive,
    apply_sql_transition,
    inspect_sql_destination,
    open_sql_transition,
    seal_sql_transition,
)
from app.integration_secrets import IntegrationCipher


def valid_preflight(contexts, count):
    return BiometricWritePreflight(
        contexts, "a"*64, "a"*64, "a"*64, True, True, count, count,
        "b"*64, "b"*64, True, f'APPLY_BIOMETRIC_CONTEXT:{"a"*64}:{"b"*64}',
        frozenset({"api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker"}),
        0, False, False, "staging", "staging", 0, 0, 0, 0,
    )


def test_archive_authenticates_plan_context_and_envelopes(tmp_path):
    import json
    from dataclasses import replace

    source, contexts = fixture_snapshot()
    target = prepare_embedding_destination((source,), contexts=contexts)
    preflight = valid_preflight(contexts, 1)
    key = b"k" * 32
    archive = seal_sql_transition((source,), target, preflight=preflight, backup_key=key)
    path = tmp_path / "synthetic-encrypted-package.json"
    path.write_text(json.dumps(archive.payload()))
    assert str(source.values["id"]) not in path.read_text()
    assert "historical-synthetic" not in path.read_text()
    reopened = SqlTransitionArchive.from_payload(json.loads(path.read_text()))
    assert open_sql_transition(reopened, preflight=preflight, backup_key=key) == ((source,), target)
    for changed, altered_preflight, altered_key in (
        (replace(archive, ciphertext=archive.ciphertext[:-1]+bytes([archive.ciphertext[-1]^1])), preflight, key),
        (archive, replace(preflight, operation_plan_fingerprint="c"*64), key),
        (archive, preflight, b"x"*32),
    ):
        with pytest.raises(SqlBackupError):
            open_sql_transition(changed, preflight=altered_preflight, backup_key=altered_key)
    bad_target = (EmbeddingSnapshot({**target[0].values, "tenant_id": uuid4()}),)
    with pytest.raises(SqlBackupError):
        seal_sql_transition((source,), bad_target, preflight=preflight, backup_key=key)


def test_unverified_archive_and_bad_count_prevent_write():
    from dataclasses import replace
    source, contexts = fixture_snapshot()
    target = prepare_embedding_destination((source,), contexts=contexts)
    preflight = valid_preflight(contexts, 1)
    key = b"k"*32
    archive = seal_sql_transition((source,), target, preflight=preflight, backup_key=key)
    with pytest.raises(SqlBackupError, match="persistido"):
        apply_sql_transition(None, archive, preflight=preflight, backup_key=key,
                             persisted_archive_reopened=False)
    with pytest.raises(SqlBackupError, match="Contagem"):
        apply_sql_transition(None, archive,
            preflight=replace(preflight, expected_record_count=2, backup_record_count=2),
            backup_key=key, persisted_archive_reopened=True)


def fixture_snapshot():
    contexts = FacialCryptoContextPair(
        FacialCryptoContext.from_keyring(environment="staging", active_key_id="a", keys={"a": b"a"*32}),
        FacialCryptoContext.from_keyring(environment="production", active_key_id="b", keys={"b": b"b"*32}),
    )
    values = dict.fromkeys(PhotoFaceEmbedding.__table__.c.keys())
    values.update(id=uuid4(), tenant_id=uuid4(), parent_gallery_id=uuid4(), photo_asset_id=uuid4(),
                  model_version="historical-synthetic", quality_version="synthetic-quality",
                  created_at=datetime(2026, 10, 29, tzinfo=UTC),
                  updated_at=datetime(2026, 10, 29, tzinfo=UTC))
    scope = FacialScope("staging", values["parent_gallery_id"], "photo", values["photo_asset_id"],
                        "embedding", values["model_version"], values["quality_version"])
    envelope = contexts.source.cipher.encrypt(b"synthetic vector", scope=scope)
    values.update(payload_ciphertext=envelope.ciphertext, payload_nonce=envelope.nonce, key_id=envelope.key_id)
    return EmbeddingSnapshot(values), contexts


def test_preparation_preserves_historical_model_and_all_metadata():
    source, contexts = fixture_snapshot()
    target, = prepare_embedding_destination((source,), contexts=contexts)
    fields = {"payload_ciphertext", "payload_nonce", "key_id"}
    assert {k:v for k,v in target.values.items() if k not in fields} == {
        k:v for k,v in source.values.items() if k not in fields}
    assert target.values["payload_ciphertext"] != source.values["payload_ciphertext"]
    reverse = FacialCryptoContextPair(contexts.destination, contexts.source)
    restored, = prepare_embedding_destination((target,), contexts=reverse)
    assert restored.values["model_version"] == "historical-synthetic"
    assert repr(source) == "EmbeddingSnapshot(<redacted>)"


def test_corruption_or_duplicate_aborts_without_changing_source():
    source, contexts = fixture_snapshot()
    snapshot = dict(source.values)
    corrupt = EmbeddingSnapshot({**snapshot, "payload_ciphertext": b"corrupt"})
    for batch in ((source, corrupt), (source, source)):
        with pytest.raises(BiometricSqlError, match="Preparação"):
            prepare_embedding_destination(batch, contexts=contexts)
    assert dict(source.values) == snapshot


def test_sql_write_and_locks_refuse_sqlite_even_in_transaction():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            with pytest.raises(BiometricSqlError, match="PostgreSQL"):
                lock_embedding_snapshot(connection)
            with pytest.raises(BiometricSqlError, match="PostgreSQL"):
                replace_embedding_envelopes(connection, expected=(), replacement=())
    finally:
        engine.dispose()


def test_postgres_roundtrip_drift_and_failure_rollback(monkeypatch, tmp_path):
    url = os.getenv("APP_ENV_TRANSITION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL sintético local não configurado")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost", "::1"}
    assert parsed.database == "app_env_transition_test"
    engine = create_engine(url)
    schema = "biometric_test_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    metadata = MetaData()
    table = Table("photo_face_embedding", metadata, *[
        Column(c.name, c.type, primary_key=c.name == "id", nullable=c.name != "id")
        for c in PhotoFaceEmbedding.__table__.c
    ])
    try:
        first, contexts = fixture_snapshot()
        second, _ = fixture_snapshot()
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            metadata.create_all(connection)
            connection.execute(table.insert(), [dict(first.values), dict(second.values)])
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            source = lock_embedding_snapshot(connection)
            with scoped.connect() as competing:
                transaction = competing.begin()
                try:
                    competing.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                    competing.execute(text("SET LOCAL lock_timeout='100ms'"))
                    with pytest.raises(DBAPIError):
                        competing.execute(table.update().where(
                            table.c.id == source[0].values["id"]
                        ).values(key_id="synthetic-concurrent"))
                finally:
                    transaction.rollback()
            target = prepare_embedding_destination(source, contexts=contexts)
            preflight = valid_preflight(contexts, 2)
            key = b"k"*32
            archive = seal_sql_transition(source, target, preflight=preflight, backup_key=key)
            archive = SqlTransitionArchive.from_payload(archive.payload())
            assert apply_sql_transition(connection, archive, preflight=preflight, backup_key=key,
                                        persisted_archive_reopened=True) == 2
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            with monkeypatch.context() as patch:
                def prohibit_payload_decryption(*args, **kwargs):
                    raise AssertionError("Não abrir payload durante inspeção")
                patch.setattr(type(contexts.source.cipher), "decrypt", prohibit_payload_decryption)
                assert inspect_sql_destination(connection, archive, preflight=preflight,
                    backup_key=key) == {"record_count": 2, "destination_verified": True,
                                       "source_verified": False}
            nested = connection.begin_nested()
            connection.execute(table.update().where(table.c.id == source[0].values["id"]).values(
                payload_ciphertext=b"synthetic drift"))
            assert inspect_sql_destination(connection, archive, preflight=preflight,
                backup_key=key)["destination_verified"] is False
            nested.rollback()
            with pytest.raises(BiometricSqlError, match="divergente"):
                replace_embedding_envelopes(connection, expected=source, replacement=target)
            assert apply_sql_transition(connection, archive, preflight=preflight, backup_key=key,
                                        persisted_archive_reopened=True, recovery=True) == 2
            assert inspect_sql_destination(connection, archive, preflight=preflight,
                backup_key=key) == {"record_count": 2, "destination_verified": False,
                                   "source_verified": True}
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            blocked_id = str(source[1].values["id"])
            connection.execute(text(f"""CREATE FUNCTION interrupt_update() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                IF NEW.id = '{blocked_id}'::uuid THEN
                    RAISE EXCEPTION 'synthetic interruption';
                END IF; RETURN NEW; END $$"""))
            connection.execute(text("""CREATE TRIGGER interrupt_update BEFORE UPDATE
                ON photo_face_embedding FOR EACH ROW EXECUTE FUNCTION interrupt_update()"""))
            with pytest.raises(BiometricSqlError, match="revertida"):
                replace_embedding_envelopes(connection, expected=source, replacement=target)
            observed = tuple(EmbeddingSnapshot(r) for r in connection.execute(
                select(table).order_by(table.c.id)).mappings())
            assert observed == source
            connection.execute(text("DROP TRIGGER interrupt_update ON photo_face_embedding"))
        account_table = Table("mercadopago_account", MetaData(), *[
            Column(c.name, c.type, primary_key=c.name == "id", nullable=c.name != "id")
            for c in MercadoPagoAccount.__table__.c
        ])
        channel_table = Table("whatsapp_channel_settings", MetaData(), *[
            Column(c.name, c.type, primary_key=c.name == "id", nullable=c.name != "id")
            for c in WhatsAppChannelSettings.__table__.c
        ])
        financial_source = IntegrationCipher.from_explicit_context(
            environment="staging", secret_environment="staging", active_key_id="k",
            keys={"k": b"z"*32})
        financial_target = financial_source.for_environment("production")
        tenant, account = uuid4(), uuid4()
        account_values = {"id": account, "tenant_id": tenant, "seller_id": "synthetic",
            "public_key": "synthetic-public", "test_account": True, "status": "active",
            "created_at": datetime(2026, 10, 29, tzinfo=UTC),
            "access_token_envelope": financial_source.encrypt("synthetic-token",
                tenant_id=tenant, credential_id=account).payload(),
            "webhook_secret_envelope": financial_source.encrypt("synthetic-webhook",
                tenant_id=tenant, credential_id=account).payload()}
        with scoped.begin() as connection:
            account_table.create(connection)
            connection.execute(account_table.insert(), account_values)
            channel_table.create(connection)
            channel = dict.fromkeys(channel_table.c.keys())
            channel.update(id=uuid4(), tenant_id=tenant, environment="staging", status="ready",
                           updated_at=datetime(2026, 10, 29, tzinfo=UTC))
            connection.execute(channel_table.insert(), channel)
        with Session(scoped) as session:
            account_plan = create_mercadopago_transition_plan(session,
                source=financial_source, target=financial_target)
            account_backup = create_encrypted_transition_backup(session, account_plan,
                source=financial_source, target=financial_target)
        with scoped.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            connection.execute(text("""CREATE FUNCTION interrupt_account() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic account failure'; END $$"""))
            connection.execute(text("""CREATE TRIGGER interrupt_account BEFORE UPDATE ON
                mercadopago_account FOR EACH ROW EXECUTE FUNCTION interrupt_account()"""))
            arguments = {"biometric_archive": archive, "biometric_preflight": preflight,
                "biometric_backup_key": key, "account_plan": account_plan,
                "account_backup": account_backup, "source_cipher": financial_source,
                "target_cipher": financial_target, "persisted_backups_reopened": True,
                "channel_source": (channel,)}
            with pytest.raises(CombinedTransitionError):
                apply_combined_transition(connection, **arguments)
            assert tuple(EmbeddingSnapshot(r) for r in connection.execute(
                select(table).order_by(table.c.id)).mappings()) == source
            connection.execute(text("DROP TRIGGER interrupt_account ON mercadopago_account"))
            result = apply_combined_transition(connection, **arguments)
            assert result["embedding_count"] == 2 and result["account_count"] == 1
            assert result["channel_count"] == 1
            assert connection.execute(select(channel_table.c.environment)).scalar_one() == "production"
            assert inspect_sql_destination(connection, archive,
                preflight=preflight, backup_key=key)["destination_verified"] is True
            assert connection.execute(select(account_table.c.access_token_envelope)).scalar_one()[
                "environment"] == "production"
            recovery_arguments = {k:v for k,v in arguments.items() if k != "account_plan"}
            recovery_arguments["account_destination_fingerprint"] = "f"*64
            with pytest.raises(CombinedTransitionError):
                recover_combined_transition(connection, **recovery_arguments)
            recovery_arguments["account_destination_fingerprint"] = result["account_fingerprint"]
            assert recover_combined_transition(connection, **recovery_arguments) == {
                "embedding_count": 2, "account_count": 1, "channel_count": 1}
            assert connection.execute(select(channel_table.c.environment)).scalar_one() == "staging"
            result = apply_combined_transition(connection, **arguments)
            transaction.rollback()
        with scoped.connect() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            assert tuple(EmbeddingSnapshot(r) for r in connection.execute(
                select(table).order_by(table.c.id)).mappings()) == source
            assert connection.execute(select(account_table.c.access_token_envelope)).scalar_one()[
                "environment"] == "staging"
        if os.name == "posix":
            from app.auth import FacialJob, FacialSearchNotificationOutbox, FacialSearchRequest
            from app.environment_transition_bundle import (
                FINANCIAL_TABLES,
                apply_bundle,
                inspect_bundle,
                persist_profile,
                prepare_bundle,
                recover_bundle,
            )
            from app.facial.environment_package_store import PackageStorageError
            projections = (
                (FacialJob, ("id", "status")),
                (FacialSearchRequest, ("id", "reference_locator_ciphertext")),
                (FacialSearchNotificationOutbox, ("id", "payload_ciphertext")),
            )
            with scoped.begin() as connection:
                for model, columns in projections:
                    projection = Table(model.__tablename__, MetaData(), *[
                        Column(name, model.__table__.c[name].type) for name in columns])
                    projection.create(connection)
                for name in FINANCIAL_TABLES:
                    if name == "mercadopago_account":
                        continue
                    projection = Table(name, MetaData(), Column("id", account_table.c.id.type),
                                       Column("state", account_table.c.status.type))
                    projection.create(connection)
                    connection.execute(projection.insert(), {"id": uuid4(), "state": "synthetic-preserved"})
            packages, keys = tmp_path / "packages", tmp_path / "keys"
            packages.mkdir(mode=0o700)
            keys.mkdir(mode=0o700)
            operation = "synthetic-complete-cutover"
            common = {"contexts": contexts, "source_cipher": financial_source,
                "target_cipher": financial_target, "package_root": packages, "key_root": keys,
                "operation": operation}
            with scoped.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                connection.execute(text("SET TRANSACTION READ ONLY"))
                persist_profile(connection, package_root=packages, key_root=keys, operation=operation,
                    continuity={"synthetic": True}, inventory="a"*64, plan="b"*64)
                assert prepare_bundle(connection, **common, inventory="a"*64, plan="b"*64,
                    continuity={"synthetic": True}) == {
                        "embedding_count": 2, "account_count": 1, "channel_count": 1}
            common["app_environment"] = "staging"
            with scoped.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                assert apply_bundle(connection, **common) == {
                    "embedding_count": 2, "account_count": 1, "channel_count": 1}
            with scoped.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                connection.execute(text("SET TRANSACTION READ ONLY"))
                status = inspect_bundle(connection, **common)
                assert status["destination_verified"] is True and status["source_verified"] is False
            with scoped.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                assert recover_bundle(connection, **common) == {
                    "embedding_count": 2, "account_count": 1, "channel_count": 1}
            with scoped.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                assert recover_bundle(connection, **common)["already_recovered"] is True
                with pytest.raises(PackageStorageError):
                    apply_bundle(connection, **common)
                assert inspect_bundle(connection, **common)["source_verified"] is True
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
