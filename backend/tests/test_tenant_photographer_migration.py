"""Cadeia Alembic e rollback da transição, somente em bancos sintéticos próprios."""

import importlib.util
import os
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import auth
from app.ownership_schema import SHARED_TABLES
from tests.tenant_fixtures import FIXTURE_TENANT_ID
from tests.tenant_fixtures import insert_legacy_model as insert_model
from tests.test_integration_secrets import secret_keyring  # noqa: F401

BACKEND = Path(__file__).resolve().parents[1]
FOUNDATION = "20260929_0069"
TRANSITION = "20260930_0070"
CURRENT_SCHEMA = "20261025_0089"
POST_TRANSITION_TABLES = frozenset({
    "installation_operator", "platform_owner", "system_monitor_grant",
    "system_monitor_activity", "system_monitor_bucket", "system_monitor_sample",
    "system_monitor_worker", "system_monitor_incident", "system_monitor_transition",
    "facial_embedding_experiment_setting",
    "provider_payment", "provider_payment_attempt", "provider_payment_receipt",
    "provider_payment_correction", "raw_development_settings", "raw_development_job",
    "mercadopago_account", "mercadopago_payment", "mercadopago_webhook", "payment_preferences",
})


def migrate(url, revision, *, downgrade=False, succeeds=True):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade" if downgrade else "upgrade", revision],
        cwd=BACKEND, env={**os.environ, "DATABASE_URL": url}, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == succeeds, result.stderr
    return result


@pytest.mark.parametrize("source_change", [None, "fingerprint", "deleted", "expiry", "pipeline"])
def test_gemma_inference_does_not_lock_primary_source_processing(
    migration_db, tmp_path, monkeypatch, source_change,
):
    from dataclasses import replace

    from app.facial.crypto import FacialCipher
    from app.facial.engine import FacialEngineError
    from app.facial.gemma_provider import GEMMA_MODEL_ID, GEMMA_MODEL_VERSION
    from app.facial.jobs import FacialJobRepository
    from app.facial.lifecycle import admit_source, finalize_source, media_can_proceed
    from app.facial.worker import process_claimed_index_job
    from app.media import safe_source_path
    from tests.test_facial_engine import _face, _settings
    from tests.test_highres_pipeline import HighresProvider, jpeg

    url, _name = migration_db
    migrate(url, CURRENT_SCHEMA)
    engine = sa.create_engine(url, poolclass=NullPool)
    monkeypatch.setenv("MEDIA_SOURCE_ROOT", str(tmp_path / "source"))
    monkeypatch.setenv("MEDIA_DERIVATIVES_ROOT", str(tmp_path / "derivatives"))
    monkeypatch.setenv("FACIAL_HIGHRES_ENABLED", "true")
    monkeypatch.setattr("app.facial.lifecycle.shutil.disk_usage", lambda _path: Mock(
        free=80_000_000_000, total=100_000_000_000,
    ))
    settings = _settings(tmp_path)
    repository = FacialJobRepository()
    cipher = FacialCipher(active_key_id="test", keys={"test": b"k" * 32})
    try:
        with Session(engine) as db, Session(engine) as primary:
            if db.get(auth.Tenant, FIXTURE_TENANT_ID) is None:
                db.execute(sa.insert(auth.Tenant).values(id=FIXTURE_TENANT_ID, status="active"))
            parent_id, folder_id, photo_id = uuid4(), uuid4(), uuid4()
            db.execute(sa.insert(auth.ParentGallery).values(
                id=parent_id, tenant_id=FIXTURE_TENANT_ID, name="Concorrência sintética",
            ))
            db.execute(sa.insert(auth.PhotoFolder).values(
                id=folder_id, tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent_id,
                name="Fotos", status="released", purpose="content",
            ))
            policy_values = {
                "tenant_id": FIXTURE_TENANT_ID, "parent_gallery_id": parent_id, "status": "active",
                "model_version": "model-v1", "quality_version": "quality-v1",
                "calibration_version": "calibration-v1", "legal_notice_version": "notice-v1",
                "legal_basis_reference": "synthetic-only", "retention_policy_version": "retention-v1",
            }
            db.execute(sa.insert(auth.GalleryFacialPolicy).values(
                **policy_values, minor_policy_version="minor-disabled-v1",
            ))
            db.execute(sa.insert(auth.FacialRollout).values(
                **policy_values, environment="test", stage="canary", consent_version="consent-v1",
            ))
            db.execute(sa.insert(auth.PhotoAsset).values(
                id=photo_id, tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=parent_id,
                folder_id=folder_id, filename="synthetic.jpg", available=True,
                storage_key=f"tenants/{FIXTURE_TENANT_ID}/{parent_id}/{folder_id}/synthetic.jpg",
            ))
            photo = db.get(auth.PhotoAsset, photo_id)
            db.execute(sa.insert(auth.MediaDerivative).values(
                tenant_id=FIXTURE_TENANT_ID, photo_asset_id=photo_id,
                variant="client_preview", status="ready", width=640, height=480,
                relative_path=f"tenants/{FIXTURE_TENANT_ID}/{photo_id}/client_preview.jpg",
            ))
            db.add(auth.FacialEmbeddingExperimentSetting(
                singleton=1, enabled=True, enabled_since=auth.now() - timedelta(days=1),
            ))
            admit_source(db, photo, jpeg(), settings=settings)
            path = safe_source_path(photo)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(jpeg())
            finalize_source(db, photo, settings=settings)
            db.commit()
            sface_claim = repository.claim_next(primary, job_class="index", lease_seconds=120)
            gemma_claim = repository.claim_next(db, job_class="gemma", lease_seconds=900)
            assert sface_claim and gemma_claim

            class ConcurrentGemmaProvider:
                model_id = GEMMA_MODEL_ID
                model_version = GEMMA_MODEL_VERSION
                embedding_dimension = 768
                @property
                def last_metrics(self):
                    return {}

                def observe_highres_path(self, _path):
                    # Simula SFace concorrente enquanto Gemma calcula; timeout
                    # curto do PostgreSQL detecta lock no fluxo principal.
                    primary.execute(sa.text("SET LOCAL lock_timeout='300ms'"))
                    done = process_claimed_index_job(
                        primary, sface_claim, repository=repository,
                        provider=HighresProvider(), cipher=cipher, settings=settings,
                        derivatives_root=tmp_path / "derivatives",
                    )
                    assert done.status == "completed"
                    assert media_can_proceed(primary, photo.id, tenant_id=FIXTURE_TENANT_ID)
                    changed = {
                        "fingerprint": {"source_fingerprint": "f" * 64},
                        "deleted": {"deleted_at": auth.now()},
                        "expiry": {"expires_at": auth.now() + timedelta(days=2)},
                        "pipeline": {"pipeline_version": "another-synthetic-pipeline"},
                    }.get(source_change)
                    if changed:
                        primary.execute(sa.update(auth.PhotoAnalysis).where(
                            auth.PhotoAnalysis.photo_asset_id == photo.id,
                        ).values(**changed))
                    primary.commit()
                    return [replace(_face((1.0,) + (0.0,) * 767),
                                    image_width=2400, image_height=1600)]

            def run_gemma():
                return process_claimed_index_job(
                    db, gemma_claim, repository=repository, provider=ConcurrentGemmaProvider(),
                    cipher=cipher, settings=settings, derivatives_root=tmp_path / "derivatives",
                )

            expected = {("opencv-yunet-sface", 128)}
            if source_change:
                with pytest.raises(FacialEngineError, match="alterada ou excluída"):
                    run_gemma()
            else:
                assert run_gemma().status == "completed"
                expected.add((GEMMA_MODEL_ID, 768))
            assert set(db.execute(sa.select(
                auth.PhotoFaceEmbedding.model_id, auth.PhotoFaceEmbedding.embedding_dimension,
            ))) == expected
            assert db.scalar(sa.select(auth.PhotoAnalysis.state)) == "ready"
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def baseline_template():
    url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PHOTOGRAPHER_TEST_DATABASE_URL não configurada")
    parsed = sa.engine.make_url(url)
    assert parsed.host == "127.0.0.1" and parsed.port == 15470
    assert parsed.database == "pyp_photographer_test"
    control = sa.create_engine(parsed, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    name = f"pilot_template_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    try:
        migrate(parsed.set(database=name).render_as_string(hide_password=False), FOUNDATION)
        yield parsed, name, control
    finally:
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}"'))
        control.dispose()


@pytest.fixture
def migration_db(baseline_template):
    parsed, template, control = baseline_template
    name = f"pilot_migration_{uuid4().hex}"
    with control.connect() as connection:
        connection.execute(sa.text(f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
    url = parsed.set(database=name).render_as_string(hide_password=False)
    engine = sa.create_engine(url, poolclass=NullPool)
    try:
        yield url, engine
    finally:
        engine.dispose()
        with control.connect() as connection:
            connection.execute(sa.text(f'DROP DATABASE "{name}"'))


def snapshot(connection):
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return metadata, {
        name: sorted((tuple(row) for row in connection.execute(table.select())), key=repr)
        for name, table in metadata.tables.items()
    }


def assert_preserved(connection, before):
    metadata, rows = before
    for name, old in rows.items():
        if name == "alembic_version":
            continue
        after = sorted((tuple(row) for row in connection.execute(metadata.tables[name].select())), key=repr)
        assert after == old, name


def assert_catalog(connection):
    inspector = sa.inspect(connection)
    assert not POST_TRANSITION_TABLES & set(inspector.get_table_names())
    for name, target in auth.Base.metadata.tables.items():
        # Contrato histórico 0070: tabelas/colunas de revisions posteriores ainda não existem.
        if name in POST_TRANSITION_TABLES:
            continue
        actual_columns = {column["name"]: column for column in inspector.get_columns(name)}
        future_columns = {
            "facial_search_request": {"search_engine"},
            "private_upload_batch": {"folder_id", "parent_gallery_id"},
            "sale_order": {"provider_payment_id", "mercadopago_payment_id"},
            "tenant": {"canonical_host"},
        }
        future_nullability = {
            "private_upload_batch": {"derived_gallery_id": False},
        }
        historical_columns = [column for column in target.c if column.name not in future_columns.get(name, set())]
        assert set(actual_columns) == {column.name for column in historical_columns}, name
        assert all(
            actual_columns[column.name]["nullable"]
            == future_nullability.get(name, {}).get(column.name, column.nullable)
            for column in historical_columns
        ), name
        actual_fk = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(name)
        }
        expected_fk = {
            (tuple(e.parent.name for e in f.elements), f.referred_table.name, tuple(e.column.name for e in f.elements))
            for f in target.foreign_key_constraints
            if not any(e.parent.name in future_columns.get(name, set()) for e in f.elements)
        }
        assert actual_fk == expected_fk, name
        assert set(inspector.get_pk_constraint(name)["constrained_columns"]) == set(target.primary_key.columns.keys())
        actual_unique = {tuple(u["column_names"]) for u in inspector.get_unique_constraints(name)}
        expected_unique = {
            tuple(column.name for column in u.columns)
            for u in target.constraints
            if isinstance(u, sa.UniqueConstraint) and u.name != "uq_tenant_canonical_host"
        }
        expected_unique |= {
            ("tenant_id", "photo_asset_id"),
        } if name == "private_upload_batch_asset" else set()
        assert actual_unique == expected_unique, name
        actual_indexes = {i["name"]: (tuple(i["column_names"]), i["unique"])
                          for i in inspector.get_indexes(name) if not i.get("duplicates_constraint")}
        expected_indexes = {i.name: (tuple(column.name for column in i.columns), i.unique) for i in target.indexes
                            if not any(column.name in future_columns.get(name, set()) for column in i.columns)}
        assert expected_indexes.items() <= actual_indexes.items(), name
        # Índices legados não únicos podem ser preservados mesmo quando não
        # declarados no ORM; nenhuma unicidade global extra pode sobreviver.
        assert all(not unique for key, (_, unique) in actual_indexes.items() if key not in expected_indexes), name
        by_name = {i["name"]: i for i in inspector.get_indexes(name)}
        for index in target.indexes:
            expected_where = index.dialect_kwargs.get("postgresql_where")
            if expected_where is None:
                continue
            expression = str(expected_where.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
            actual_where = by_name[index.name].get("dialect_options", {}).get("postgresql_where")
            normalize = lambda sql: re.sub(r"[()\s]", "", str(sql).replace("::text", "")).lower()
            assert normalize(expression) == normalize(actual_where), index.name


def legacy(connection):
    owner = connection.scalar(sa.text("SELECT id FROM tenant"))
    admin, client, parent, gallery, folder, photo, order, event, session = (uuid4() for _ in range(9))
    insert_model(connection, auth.AdminUser, id=admin, email="synthetic@example.test",
                 password_hash="synthetic-hash", totp_secret="synthetic-totp", email_verified=True)
    insert_model(connection, auth.TenantAdmin, tenant_id=owner, admin_user_id=admin)
    insert_model(connection, auth.Client, id=client, full_name="Sintética", phone_e164="+5511999990001")
    insert_model(connection, auth.ClientPhone, client_id=client, phone_e164="+5511999990001",
                 verified_at=auth.now())
    insert_model(connection, auth.ParentGallery, id=parent, tenant_id=owner, name="Origem sintética")
    insert_model(connection, auth.DerivedGallery, id=gallery, tenant_id=owner, parent_gallery_id=parent,
                 client_id=client, name="Privada sintética")
    insert_model(connection, auth.PhotoFolder, id=folder, parent_gallery_id=parent, name="Lote sintético")
    insert_model(connection, auth.PhotoAsset, id=photo, tenant_id=owner, parent_gallery_id=parent,
                 folder_id=folder, filename="synthetic.jpg", storage_key="legacy/synthetic.jpg")
    connection.execute(sa.text("UPDATE parent_gallery SET cover_photo_id=:photo WHERE id=:parent"),
                       {"photo": photo, "parent": parent})
    insert_model(connection, auth.GalleryClientState, parent_gallery_id=parent, client_id=client)
    insert_model(connection, auth.PhotoSelection, parent_gallery_id=parent, client_id=client, photo_asset_id=photo)
    insert_model(connection, auth.GalleryAccess, gallery_id=parent, client_id=client)
    insert_model(connection, auth.GalleryAccess, gallery_id=gallery, client_id=client)
    old_capability = uuid4()
    insert_model(connection, auth.GalleryAccessCapability, id=old_capability, parent_gallery_id=parent,
                 scope="public_gallery", token_hash="a" * 64, status="revoked", actor_admin_id=admin)
    insert_model(connection, auth.GalleryAccessCapability, parent_gallery_id=parent,
                 scope="public_gallery", token_hash="b" * 64, rotated_from_id=old_capability, actor_admin_id=admin)
    insert_model(connection, auth.SaleOrder, id=order, client_id=client, parent_gallery_id=parent,
                 parent_gallery_id_snapshot=parent, parent_gallery_name_snapshot="Origem sintética",
                 derived_gallery_name_snapshot="Sintética", payment_status="confirmed", total_cents=12345)
    insert_model(connection, auth.SaleOrderItem, sale_order_id=order, photo_asset_id=photo,
                 photo_asset_id_snapshot=photo, filename_snapshot="synthetic.jpg", unit_price_cents=12345)
    insert_model(connection, auth.GlobalPixSettings, admin_user_id=admin, status="active", copy_paste="synthetic-pix")
    insert_model(connection, auth.BrandingSettings, login_title="Marca sintética", logo_key="legacy/synthetic-logo.png")
    connection.execute(sa.text("UPDATE preview_adjustment_settings SET generation=3, strength=25 WHERE id=1"))
    insert_model(connection, auth.AssetFileCleanup, paths=["legacy/synthetic.jpg"])
    insert_model(connection, auth.GalleryMembershipNotificationOutbox, parent_gallery_id=None,
                 event_key="synthetic-orphan-history", event_type="private_created",
                 parent_name_snapshot="Origem removida", derived_name_snapshot="Privada removida")
    insert_model(connection, auth.MediaJob, photo_asset_id=photo, kind="generate_derivatives")
    insert_model(connection, auth.FacialJob, parent_gallery_id=parent, photo_asset_id=photo,
                 kind="index", idempotency_key="synthetic-facial")
    setting = connection.scalar(sa.text("SELECT event_type FROM notification_setting LIMIT 1"))
    insert_model(connection, auth.NotificationEvent, id=event, event_type=setting, event_key="synthetic-event",
                 parent_gallery_id=parent, client_id=client, template_version=1, push_title="Sintética",
                 push_body="Sintética", whatsapp_body="Sintética", target_path="/library",
                 expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.NotificationDelivery, event_id=event, recipient_role="client", recipient_id=client,
                 channel="whatsapp")
    insert_model(connection, auth.PushSubscription, role="client", subject_id=client,
                 endpoint_fingerprint="synthetic", encrypted_subscription="unchanged-synthetic-envelope")
    insert_model(connection, auth.AuthSession, id=session, role="admin", subject_id=admin,
                 token_hash="synthetic-session-hash", expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.AuthSession, role="client", subject_id=client,
                 token_hash="synthetic-client-session", expires_at=auth.now() + timedelta(hours=1))
    insert_model(connection, auth.AdminSecurityChallenge, purpose="change_pix_otp", admin_id=admin, session_id=session,
                 subject_fingerprint="synthetic", secret_hash="synthetic-otp-hash",
                 expires_at=auth.now() + timedelta(minutes=1))
    insert_model(connection, auth.AuthChallenge, kind="client_otp", secret_hash="synthetic-hash",
                 expires_at=auth.now() + timedelta(minutes=1))
    return {"owner": owner, "admin": admin, "client": client, "parent": parent, "gallery": gallery, "photo": photo}


def test_gemma_postgres_upgrade_preserves_legacy_and_isolates_namespaces(migration_db):
    """0073/0074 preservam envelopes SFace e consultas antigas, sem downgrade destrutivo."""
    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
    migrate(url, "20261009_0072")
    embedding_id, policy_id, request_id = (uuid4() for _ in range(3))
    envelope = {"payload_ciphertext": b"synthetic-sface-envelope", "payload_nonce": b"x" * 12,
                "key_id": "synthetic-key"}
    embedding_scope = {"tenant_id": records["owner"], "parent_gallery_id": records["parent"],
                       "photo_asset_id": records["photo"], "face_ordinal": 0,
                       "quality_version": "synthetic-quality-v1", "preview_fingerprint": "f" * 64}
    with engine.begin() as connection:
        insert_model(connection, auth.PhotoFaceEmbedding, id=embedding_id,
                     model_id="opencv-yunet-sface", embedding_dimension=128,
                     model_version="synthetic-sface-v1", **embedding_scope, **envelope)
        insert_model(connection, auth.GalleryFacialPolicy, id=policy_id,
                     tenant_id=records["owner"], parent_gallery_id=records["parent"],
                     model_version="synthetic-sface-v1", quality_version="synthetic-quality-v1")
        insert_model(connection, auth.FacialSearchRequest, id=request_id,
                     tenant_id=records["owner"], parent_gallery_id=records["parent"],
                     client_id=records["client"], policy_id=policy_id,
                     consent_version="synthetic-consent-v1", legal_notice_version="synthetic-notice-v1",
                     subject_declaration="adult", model_version="synthetic-sface-v1",
                     quality_version="synthetic-quality-v1", index_generation=0,
                     expires_at=auth.now() + timedelta(hours=1))
        before = snapshot(connection)
    migrate(url, "20261011_0074")
    with engine.begin() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20261011_0074"
        assert connection.scalar(sa.text("SELECT search_engine FROM facial_search_request WHERE id=:id"),
                                 {"id": request_id}) == "opencv-yunet-sface"
        indexes = {item["name"] for item in sa.inspect(connection).get_indexes("photo_face_embedding")}
        assert "ix_face_embedding_gallery_engine" in indexes
        connection.execute(sa.text(
            "INSERT INTO facial_embedding_experiment_setting (singleton, updated_at) VALUES (1, :now)"
        ), {"now": auth.now()})
        setting = connection.execute(sa.text(
            "SELECT enabled, mode, model_revision FROM facial_embedding_experiment_setting"
        )).one()
        assert tuple(setting) == (False, "shadow", "914f7f89142e33e77833254d9c9b90c3cef7303b")
        insert_model(connection, auth.PhotoFaceEmbedding,
                     model_id="google-embeddinggemma-2", embedding_dimension=768,
                     model_version="synthetic-gemma-v1", **embedding_scope,
                     payload_ciphertext=b"synthetic-gemma-envelope", payload_nonce=b"y" * 12,
                     key_id="synthetic-key")
        for kind in ("index_gemma", "search_gemma"):
            insert_model(connection, auth.FacialJob, tenant_id=records["owner"],
                         parent_gallery_id=records["parent"], kind=kind,
                         idempotency_key=f"synthetic-{kind}")
        namespaces = connection.execute(sa.text(
            "SELECT model_id, embedding_dimension, payload_ciphertext FROM photo_face_embedding ORDER BY model_id"
        )).all()
        assert [tuple(row) for row in namespaces] == [
            ("google-embeddinggemma-2", 768, b"synthetic-gemma-envelope"),
            ("opencv-yunet-sface", 128, b"synthetic-sface-envelope"),
        ]
        with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
            connection.execute(sa.text(
                "UPDATE facial_search_request SET search_engine='unknown-engine' WHERE id=:id"
            ), {"id": request_id})
        connection.execute(sa.text(
            "UPDATE facial_search_request SET search_engine='google-embeddinggemma-2' WHERE id=:id"
        ), {"id": request_id})
        after_upgrade = snapshot(connection)
    migrate(url, "20261009_0072", downgrade=True, succeeds=False)
    with engine.connect() as connection:
        assert_preserved(connection, after_upgrade)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20261011_0074"


def test_upgrade_vazio_catalogo_e_defaults_preservados(migration_db):
    url, engine = migration_db
    with engine.connect() as connection:
        before = snapshot(connection)
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert_catalog(connection)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TRANSITION
        assert connection.scalar(sa.text("SELECT count(*) FROM tenant")) == 1


def test_upgrade_preserva_todas_colunas_legadas_e_owner_duravel(migration_db):
    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
        before = snapshot(connection)
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert_catalog(connection)
        for name in set(auth.Base.metadata.tables) - SHARED_TABLES - POST_TRANSITION_TABLES:
            assert connection.scalar(sa.text(f'SELECT count(*) FROM "{name}" WHERE tenant_id IS NULL')) == 0, name
            assert connection.scalar(sa.text(f'SELECT count(*) FROM "{name}" WHERE tenant_id != :owner'),
                                     {"owner": records["owner"]}) == 0, name
        assert connection.scalar(sa.text("SELECT client_subject_id FROM auth_session WHERE role='client'")) == records["client"]


@pytest.mark.parametrize("kind", ["orphan", "ambiguous_gallery", "two_tenants", "duplicate_phone", "missing_recipient", "missing_actor"])
def test_legado_inconsistente_abortado_sem_ddl_parcial(migration_db, kind):
    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
        connection.execute(sa.text("SET LOCAL session_replication_role=replica"))
        if kind == "orphan":
            connection.execute(sa.text("UPDATE photo_folder SET parent_gallery_id=:missing"), {"missing": uuid4()})
        elif kind == "ambiguous_gallery":
            another_client = uuid4()
            insert_model(connection, auth.Client, id=another_client, full_name="Sintética ambígua",
                         phone_e164="+5511999990050")
            insert_model(connection, auth.DerivedGallery, id=records["parent"], tenant_id=records["owner"],
                         parent_gallery_id=records["parent"], client_id=another_client, name="Ambígua")
        elif kind == "two_tenants":
            insert_model(connection, auth.Tenant)
        elif kind == "duplicate_phone":
            other = uuid4()
            insert_model(connection, auth.Client, id=other, full_name="Sintética B", phone_e164="+5511999990002")
            # O índice antigo protege só verificados; ambos não verificados reproduzem a ambiguidade.
            connection.execute(sa.text("UPDATE client_phone SET verified_at=NULL"))
            insert_model(connection, auth.ClientPhone, client_id=other, phone_e164="+5511999990001")
        elif kind == "missing_recipient":
            connection.execute(sa.text("UPDATE notification_delivery SET recipient_id=:missing"), {"missing": uuid4()})
        else:
            insert_model(connection, auth.GalleryLifecycleOperation, operation_type="delete_parent_gallery",
                         target_parent_gallery_id=records["parent"], actor_admin_id=uuid4(), idempotency_key="synthetic-missing-actor")
        before = snapshot(connection)
    failure = migrate(url, TRANSITION, succeeds=False)
    assert "Legado incompatível" in failure.stderr
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == FOUNDATION
        assert "tenant_id" not in {c["name"] for c in sa.inspect(connection).get_columns("client")}


def revision_module():
    path = BACKEND / "migrations/versions/20260930_0070_photographer_isolation_schema.py"
    spec = importlib.util.spec_from_file_location("schema0070_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_falha_apos_backfill_reverte_colunas_e_dados(migration_db, monkeypatch):
    _, engine = migration_db
    with engine.begin() as connection:
        legacy(connection)
        before = snapshot(connection)
    module = revision_module()

    def fail_after_backfill(bind):
        assert bind.scalar(sa.text("SELECT count(*) FROM client WHERE tenant_id IS NOT NULL")) == 1
        bind.execute(sa.text("ALTER TABLE client ADD CONSTRAINT synthetic_rollback_probe CHECK (false)"))

    monkeypatch.setattr(module, "_apply_schema", fail_after_backfill)
    with (
        pytest.raises(sa.exc.IntegrityError),
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        module.upgrade()
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert "tenant_id" not in {c["name"] for c in sa.inspect(connection).get_columns("client")}
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == FOUNDATION


def test_sessao_sem_sujeito_revogada_sem_apagar_hash(migration_db):
    url, engine = migration_db
    identifier, subject = uuid4(), uuid4()
    with engine.begin() as connection:
        insert_model(connection, auth.AuthSession, id=identifier, role="client", subject_id=subject,
                     token_hash="synthetic-unresolved-hash", expires_at=auth.now() + timedelta(hours=1))
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        row = connection.execute(sa.text("SELECT id, subject_id, token_hash, revoked_at, tenant_id FROM auth_session")).one()
        assert row.id == identifier and row.subject_id == subject and row.token_hash == "synthetic-unresolved-hash"
        assert row.revoked_at is not None and row.tenant_id is None


def test_downgrade_recusado_preserva_propriedade(migration_db):
    url, engine = migration_db
    migrate(url, TRANSITION)
    with engine.connect() as connection:
        before = snapshot(connection)
    failure = migrate(url, FOUNDATION, downgrade=True, succeeds=False)
    assert "Preserve o schema" in failure.stderr
    with engine.connect() as connection:
        assert_preserved(connection, before)
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == TRANSITION


def test_dialeto_nao_operacional_recusado_antes_de_alterar(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.sqlite').as_posix()}"
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        with (
            Operations.context(MigrationContext.configure(connection)),
            pytest.raises(RuntimeError, match="requer PostgreSQL"),
        ):
            revision_module().upgrade()
        assert sa.inspect(connection).get_table_names() == []
    engine.dispose()


def test_inventario_multitenant_agrega_contagens_sem_identificar_fotografos(
    migration_db, monkeypatch, tmp_path
):
    from app import homolog_cleanup
    from app.tenancy import TenantContextError

    url, engine = migration_db
    # O inventário exige o schema operacional completo usado em homologação.
    migrate(url, CURRENT_SCHEMA)
    roots = {name: tmp_path / name for name in homolog_cleanup.EXPECTED_MEDIA_ROOTS}
    for root in roots.values():
        root.mkdir()
    with Session(engine) as db:
        db.add(auth.Tenant())
        db.commit()
        monkeypatch.setenv("APP_ENV", "homolog")
        monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: roots)
        result = homolog_cleanup.inventory(db)
        assert result["photographer_count"] == 2
        assert result["destructive_cleanup"] == {
            "status": "unavailable_multiple_photographers"
        }
        assert all(type(value) is int for value in result["database"].values())
        assert all(type(value) is int for value in result["preserved"].values())
        rendered = str(result)
        assert str(FIXTURE_TENANT_ID) not in rendered
        assert "Tenant" not in rendered
        roots = Mock(side_effect=AssertionError("Mídia não pode ser acessada"))
        monkeypatch.setattr(homolog_cleanup, "media_roots", roots)
        with pytest.raises(TenantContextError):
            homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
        roots.assert_not_called()
        db.rollback()
        assert db.scalar(sa.select(sa.func.count()).select_from(auth.Tenant)) == 2


def test_limpeza_legado_completo_preserva_administracao(migration_db, monkeypatch, tmp_path, secret_keyring):  # noqa: F811
    from app import homolog_cleanup
    from app.provision_installation_operator import provision_operator
    from app.system_monitor.models import (
        MonitorActivity,
        MonitorBucket,
        MonitorGrant,
        PlatformOwner,
    )

    url, engine = migration_db
    with engine.begin() as connection:
        records = legacy(connection)
    # A rotina atual exige o catálogo completo, incluindo o monitor 0072.
    migrate(url, CURRENT_SCHEMA)
    monkeypatch.setenv("APP_ENV", "homolog")
    roots = {name: tmp_path / name for name in homolog_cleanup.EXPECTED_MEDIA_ROOTS}
    for root in roots.values():
        root.mkdir()
        (root / "synthetic.jpg").write_bytes(b"synthetic-test-only")
    monkeypatch.setattr(homolog_cleanup, "EXPECTED_MEDIA_ROOTS", roots)
    monkeypatch.setattr(homolog_cleanup, "media_roots", lambda: roots)
    with Session(engine) as db:
        provision_operator(db, admin_id=records["admin"], action="grant",
                           authorization_reference="synthetic-cleanup-proof", apply=True)
        provider_payment = auth.ProviderPayment(
            tenant_id=records["owner"], client_id=records["client"],
            checkout_key="synthetic-cleanup-payment", cart_revision="c" * 64,
            total_cents=12345, handle_snapshot="synthetic_handle",
            configuration_version=2, verification_profile="synthetic-only",
            state="awaiting_payment",
        )
        db.add(provider_payment)
        db.flush()
        db.add_all([
            auth.ProviderPaymentAttempt(tenant_id=records["owner"], client_id=records["client"],
                                        payment_id=provider_payment.id, state="accepted"),
            auth.ProviderPaymentReceipt(tenant_id=records["owner"], client_id=records["client"],
                                        payment_id=provider_payment.id, digest="d" * 64,
                                        transaction_nsu="synthetic-cleanup-nsu", slug="synthetic-slug",
                                        verification_profile="synthetic-only"),
            auth.ProviderPaymentCorrection(tenant_id=records["owner"], client_id=records["client"],
                                          payment_id=provider_payment.id, actor_admin_id=records["admin"],
                                          idempotency_key="synthetic-cleanup-correction",
                                          reason="Teste sintético de limpeza", previous_revision=1,
                                          previous_transaction_nsu="synthetic-cleanup-nsu"),
        ])
        provider_payment_id = provider_payment.id
        admin_session = db.scalar(sa.select(auth.AuthSession).where(auth.AuthSession.role == "admin"))
        minute = auth.now().replace(second=0, microsecond=0)
        db.add_all([
            PlatformOwner(singleton=1, admin_user_id=records["admin"], authorization_reference="synthetic"),
            MonitorGrant(admin_user_id=records["admin"], permission="metrics", active=True,
                         authorization_reference="synthetic"),
            MonitorBucket(minute=minute, operation="http.read", latency_bin=100, count=1),
            MonitorActivity(session_id=admin_session.id, last_activity=minute),
        ])
        auth.audit(db, "system_monitor.grants_granted", str(records["admin"]), tenant_id=records["owner"])
        db.commit()
        before = homolog_cleanup.inventory(db)
        result = homolog_cleanup.execute(db, homolog_cleanup.CONFIRMATION)
        assert result["preserved"] == before["preserved"]
        assert all(value == 0 for value in result["database"].values())
        assert all(value["files"] == 0 for value in result["media"].values())
        assert db.get(auth.InstallationOperator, records["admin"]).active
        assert db.get(PlatformOwner, 1).admin_user_id == records["admin"]
        assert db.get(auth.ProviderPayment, provider_payment_id) is None
        assert db.get(MonitorGrant, (records["admin"], "metrics")).active
        assert db.get(MonitorBucket, (minute, "http.read", 100)).count == 1
        assert db.get(MonitorActivity, admin_session.id) is not None
        assert db.scalar(sa.select(auth.AuditEvent.id).where(
            auth.AuditEvent.event == "system_monitor.grants_granted"))
        assert db.scalar(sa.select(auth.AuditEvent.id).where(
            auth.AuditEvent.event == "installation_operator.grant"))
