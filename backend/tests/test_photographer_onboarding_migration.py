"""Migration 0099 conserves existing accounts and scopes WhatsApp per tenant."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def _config(monkeypatch, engine):
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    url = engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    return config, url.render_as_string(hide_password=False)


def _demo_helpers():
    path = Path(__file__).parents[2] / "scripts" / "local_photographer_demo.py"
    spec = importlib.util.spec_from_file_location("local_photographer_demo_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_0099_preserves_legacy_owner_and_allows_one_channel_per_tenant(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, scoped_url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(scoped_url)
    command.upgrade(config, "20261104_0099")

    with engine.begin() as connection:
        owner_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner"))
        before_email = connection.scalar(text("SELECT email FROM admin_user WHERE id = :owner"), {"owner": owner_id})
    command.downgrade(config, "20261103_0098")
    command.upgrade(config, "20261104_0099")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT email FROM admin_user WHERE id = :owner"), {"owner": owner_id}) == before_email
        assert connection.scalar(text("SELECT totp_enabled FROM admin_user WHERE id = :owner"), {"owner": owner_id}) is True

    tenant_a = uuid4()
    tenant_b = uuid4()
    with engine.begin() as connection:
        owner_tenant = connection.scalar(text("SELECT tenant_id FROM tenant_admin WHERE admin_user_id = :owner"), {"owner": owner_id})
        assert connection.scalar(text("SELECT totp_enabled FROM admin_user WHERE id = :owner"), {"owner": owner_id}) is True
        connection.execute(text("INSERT INTO tenant(id, status, created_at) VALUES (:tenant, 'active', CURRENT_TIMESTAMP)"), {"tenant": tenant_a})
        connection.execute(text("INSERT INTO tenant(id, status, created_at) VALUES (:tenant, 'active', CURRENT_TIMESTAMP)"), {"tenant": tenant_b})
        connection.execute(text(
                "INSERT INTO whatsapp_channel_settings(id,tenant_id,environment,status,updated_at) "
                "VALUES (:id,:tenant,'development','sandbox',CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "tenant": tenant_a})
        connection.execute(text(
                "INSERT INTO whatsapp_channel_settings(id,tenant_id,environment,status,updated_at) "
                "VALUES (:id,:tenant,'development','sandbox',CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "tenant": tenant_b})
        assert owner_tenant is not None

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
                "INSERT INTO whatsapp_channel_settings(id,tenant_id,environment,status,updated_at) "
                "VALUES (:id,:tenant,'development','sandbox',CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "tenant": tenant_a})

    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO photographer_terms_acceptance "
            "(id,admin_user_id,tenant_id,terms_version,terms_text,terms_sha256,provider_identity, "
            "photographer_identity,accepted_at,environment) VALUES "
            "(:id,:admin,:tenant,'synthetic-v1','synthetic terms',:digest,'synthetic provider', "
            "'synthetic photographer',CURRENT_TIMESTAMP,'test')"
        ), {"id": uuid4(), "admin": owner_id, "tenant": owner_tenant, "digest": "a" * 64})
    with pytest.raises(RuntimeError, match="Preserve dados de photographer_terms_acceptance"):
        command.downgrade(config, "20261103_0098")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM photographer_terms_acceptance")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261104_0099"
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("UPDATE photographer_terms_acceptance SET terms_text='changed'"))
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("TRUNCATE photographer_terms_acceptance"))

    command.upgrade(config, "20261104_0100")
    command.downgrade(config, "20261104_0099")
    command.upgrade(config, "20261104_0100")
    session_id = uuid4()
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT admin_user_id FROM platform_owner")) == owner_id
        connection.execute(text(
            "INSERT INTO auth_session(id,token_hash,role,subject_id,admin_subject_id,tenant_id,expires_at) "
            "VALUES (:id,:hash,'admin',:owner,:owner,:tenant,CURRENT_TIMESTAMP+INTERVAL '5 minutes')"
        ), {"id": session_id, "hash": uuid4().hex, "owner": owner_id, "tenant": owner_tenant})
        connection.execute(text(
            "INSERT INTO admin_totp_enrollment(id,admin_user_id,tenant_id,session_id,secret_envelope,expires_at) "
            "VALUES (:id,:owner,:tenant,:session,'synthetic-envelope',CURRENT_TIMESTAMP+INTERVAL '5 minutes')"
        ), {"id": uuid4(), "owner": owner_id, "tenant": owner_tenant, "session": session_id})
    with pytest.raises(RuntimeError, match="Preserve tentativas de autenticador"):
        command.downgrade(config, "20261104_0099")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM admin_totp_enrollment")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261104_0100"
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO admin_totp_enrollment(id,admin_user_id,tenant_id,session_id,secret_envelope,expires_at) "
            "VALUES (:id,:owner,:tenant,:session,'synthetic-cross-tenant',CURRENT_TIMESTAMP+INTERVAL '5 minutes')"
        ), {"id": uuid4(), "owner": owner_id, "tenant": tenant_a, "session": session_id})

    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO photographer_business_profile(id,admin_user_id,tenant_id,full_name,cpf_envelope,cpf_fingerprint,created_at,updated_at) "
            "VALUES (:id,:owner,:tenant,'synthetic','synthetic-envelope',:fingerprint,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
        ), {"id": uuid4(), "owner": owner_id, "tenant": tenant_a, "fingerprint": "c"*64})
    with pytest.raises(RuntimeError, match="vínculo incompatível"):
        command.upgrade(config, "20261104_0101")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM photographer_business_profile")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261104_0100"
        # Somente a fixture descartável resolve seu vínculo propositalmente inválido.
        connection.execute(text("DELETE FROM photographer_business_profile"))
    command.upgrade(config, "20261104_0101")
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO photographer_terms_acceptance "
            "(id,admin_user_id,tenant_id,terms_version,terms_text,terms_sha256,provider_identity,photographer_identity,accepted_at,environment) "
            "VALUES (:id,:admin,:tenant,'cross-tenant','synthetic terms',:digest,'synthetic','synthetic',CURRENT_TIMESTAMP,'test')"
        ), {"id": uuid4(), "admin": owner_id, "tenant": tenant_a, "digest": "b"*64})
    command.downgrade(config, "20261104_0100")
    command.upgrade(config, "20261104_0101")
    command.upgrade(config, "20261104_0102")
    command.downgrade(config, "20261104_0101")
    command.upgrade(config, "20261104_0102")
    command.upgrade(config, "20261104_0103")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema=current_schema() AND table_name='whatsapp_tenant_credential'"
        )) == 1
    with pytest.raises(RuntimeError, match="Preserve credenciais WhatsApp"):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO whatsapp_tenant_credential "
                "(id,tenant_id,environment,instance_name,webhook_secret_envelope,created_at,updated_at) "
                "VALUES (:id,:tenant,'development','pyp-synthetic','{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            ), {"id": uuid4(), "tenant": tenant_a})
        command.downgrade(config, "20261104_0102")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM whatsapp_tenant_credential")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261104_0103"
    with engine.begin() as connection:
        # Remoção somente da credencial sintética da fixture descartável.
        connection.execute(text("DELETE FROM whatsapp_tenant_credential WHERE instance_name='pyp-synthetic'"))
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO platform_admin_event(id,actor_admin_id,tenant_id,object_id,action,result,origin,created_at,reason_code,target_version) "
            "VALUES (:id,:owner,:tenant,:object,'photographer.totp_revoked','success','web_console',CURRENT_TIMESTAMP,'lost_device',:version)"
        ), {"id": uuid4(), "owner": owner_id, "tenant": tenant_a, "object": uuid4(), "version": "d"*64})
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("UPDATE platform_admin_event SET reason_code='assisted_recovery'"))
    with pytest.raises(RuntimeError, match="histórico de recuperação assistida"):
        command.downgrade(config, "20261104_0101")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM platform_admin_event")) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261104_0103"
    command.upgrade(config, "20261105_0104")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='photographer_business_profile' "
            "AND column_name='address_envelope' AND is_nullable='YES'"
        )) == 1
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO photographer_business_profile "
            "(id,admin_user_id,tenant_id,full_name,cpf_envelope,cpf_fingerprint,created_at,updated_at,address_envelope) "
            "VALUES (:id,:owner,:tenant,'Synthetic owner','synthetic-envelope',:fingerprint,"
            "CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'private:v1:synthetic')"
        ), {"id": uuid4(), "owner": owner_id, "tenant": owner_tenant, "fingerprint": "e" * 64})
    with pytest.raises(RuntimeError, match="Preserve endereços cadastrados"):
        command.downgrade(config, "20261104_0103")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261105_0104"


def test_linear_migration_chain_from_0090_reaches_0116_with_owner_data(monkeypatch, postgres_schema):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, scoped_url = _config(monkeypatch, engine)

    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(scoped_url)
    command.upgrade(config, "20261105_0106")

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261105_0106"
        owner = connection.execute(text(
            "SELECT id, totp_secret, totp_secret_envelope, totp_enabled "
            "FROM admin_user WHERE email='owner.local-demo@example.test'"
        )).one()
        assert owner.totp_secret is None
        assert owner.totp_secret_envelope.startswith("totp:v1:local-demo:")
        assert owner.totp_enabled is True

        tenant_id = connection.scalar(text(
            "SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:owner"
        ), {"owner": owner.id})
        assert tenant_id is not None
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_credit_wallet WHERE tenant_id=:tenant"
        ), {"tenant": tenant_id}) == 1

        columns = connection.scalar(text("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema=current_schema() AND (
                (table_name='photographer_business_profile' AND column_name='address_envelope') OR
                (table_name='tenant' AND column_name='canonical_host_status') OR
                (table_name='gallery_client_state' AND column_name='selection_started_at')
            )
        """))
        assert columns == 3

    # Mantém o checkpoint anterior e prova a extensão de auditoria do ingresso.
    command.upgrade(config, "20261107_0107")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261107_0107"
        assert connection.scalar(text(
            "SELECT totp_secret_envelope FROM admin_user WHERE id=:owner"
        ), {"owner": owner.id}) == owner.totp_secret_envelope
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_credit_wallet WHERE tenant_id=:tenant"
        ), {"tenant": tenant_id}) == 1
        assert connection.scalar(text("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema=current_schema() AND table_name='platform_admin_event'
              AND column_name='evidence_sha256'
        """)) == 1

    # Estende a prova de onboarding até a revisão atual do catálogo de arquivo frio.
    command.upgrade(config, "20261109_0116")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261109_0116"
        current_owner = connection.execute(text(
            "SELECT id, totp_secret, totp_secret_envelope, totp_enabled "
            "FROM admin_user WHERE email='owner.local-demo@example.test'"
        )).one()
        assert current_owner.id == owner.id
        assert current_owner.totp_secret is None
        assert current_owner.totp_secret_envelope == owner.totp_secret_envelope
        assert current_owner.totp_enabled is True
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_credit_wallet WHERE tenant_id=:tenant"
        ), {"tenant": tenant_id}) == 1
        assert connection.scalar(text(
            "SELECT recovery_fee_credits FROM media_archive_recovery_pricing WHERE id=1"
        )) is None
        archive_tables = connection.execute(text("""
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema=current_schema() AND table_name IN (
                'media_archive_cycle', 'media_archive_object', 'media_archive_operation',
                'media_archive_event', 'media_archive_space_reservation',
                'media_archive_coordinator', 'media_archive_notice',
                'media_archive_recovery_request', 'media_archive_recovery_pricing',
                'media_archive_recovery_credit_reservation',
                'media_archive_recovery_credit_allocation_event'
            )
        """)).scalar_one()
        assert archive_tables == 11
        assert connection.scalar(text(
            "SELECT count(*) FROM media_archive_cycle WHERE tenant_id=:tenant"
        ), {"tenant": tenant_id}) == 0
