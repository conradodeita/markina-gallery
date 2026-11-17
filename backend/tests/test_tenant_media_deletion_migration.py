"""Migration de exclusão fria em PostgreSQL sintético descartável."""

from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import MetaData, Table, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.auth import (
    MediaArchiveCycle,
    MediaArchiveObject,
    MediaArchiveOperation,
    ParentGallery,
    PhotoFolder,
    Tenant,
    TenantClosureMediaDeletionBatch,
    TenantClosureMediaDeletionItem,
    now,
)
from tests.test_photographer_onboarding_migration import _config, _demo_helpers
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


def _upgrade_with_owner(monkeypatch, engine, target):
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, url = _config(monkeypatch, engine)
    command.upgrade(config, "20261026_0090")
    demo.create_synthetic_owner(url)
    command.upgrade(config, target)
    return config


def test_downgrade_fails_before_ddl_when_a_writer_holds_a_guarded_table(
    monkeypatch, postgres_schema,
):
    engine = postgres_schema
    config = _upgrade_with_owner(monkeypatch, engine, "20261110_0122")
    writer = engine.connect()
    writer_tx = writer.begin()
    try:
        writer.exec_driver_sql(
            "LOCK TABLE platform_admin_event IN ROW EXCLUSIVE MODE"
        )
        with pytest.raises(OperationalError):
            command.downgrade(config, "20261110_0121")
    finally:
        writer_tx.rollback()
        writer.close()

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0122"
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='media_archive_object' "
            "AND column_name='remote_deleted_at'"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema=current_schema() "
            "AND table_name='tenant_closure_media_deletion_batch'"
        )) == 1


def test_audited_media_deletion_migration_is_additive_and_protects_receipts(
    monkeypatch, postgres_schema,
):
    engine = postgres_schema
    config = _upgrade_with_owner(monkeypatch, engine, "20261110_0121")

    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        admin_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner LIMIT 1"))
        profile_id = uuid4()
        connection.execute(text(
            "INSERT INTO photographer_business_profile "
            "(id,admin_user_id,tenant_id,full_name,cpf_envelope,cpf_fingerprint,"
            "cpf_fingerprint_key_version,created_at,updated_at) "
            "VALUES (:id,:admin,:tenant,'Synthetic profile','synthetic-envelope',:fingerprint,"
            "'legacy-v0',now(),now())"
        ), {"id": profile_id, "admin": admin_id, "tenant": tenant_id,
            "fingerprint": "f" * 64})

    command.upgrade(config, "20261110_0122")
    with engine.begin() as connection:
        row = connection.execute(text(
            "SELECT cpf_fingerprint,cpf_fingerprint_key_version FROM photographer_business_profile"
        )).one()
        assert row.cpf_fingerprint == "f" * 64
        assert row.cpf_fingerprint_key_version == "legacy-v0"
        assert connection.scalar(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema=current_schema() AND table_name='media_archive_object' "
            "AND column_name='remote_deleted_at'"
        )) == "YES"
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema=current_schema() AND table_name IN "
            "('tenant_closure_media_deletion_batch','tenant_closure_media_deletion_item')"
        )) == 2
        assert connection.scalar(text(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema=current_schema() "
            "AND table_name='platform_admin_event' AND column_name IN ('previous_status','next_status') "
            "AND character_maximum_length=32"
        )) == 2

    command.downgrade(config, "20261110_0121")
    command.upgrade(config, "20261110_0122")

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(
            "UPDATE photographer_business_profile SET cpf_fingerprint=NULL WHERE id=:id"
        ), {"id": profile_id})

    with engine.begin() as connection:
        tenant_id = connection.scalar(text("SELECT id FROM tenant LIMIT 1"))
        admin_id = connection.scalar(text("SELECT admin_user_id FROM platform_owner LIMIT 1"))
        closure_id = uuid4()
        connection.execute(text(
            "INSERT INTO tenant_closure_request "
            "(id,tenant_id,request_id,requested_by,state,requested_at,closed_at,terms_version,"
            "terms_sha256,balance_snapshot,balance_acknowledged) "
            "VALUES (:id,:tenant,:request,:owner,'closed',now(),now(),'synthetic',:digest,0,true)"
        ), {"id": closure_id, "tenant": tenant_id, "request": uuid4(),
            "owner": admin_id, "digest": "a" * 64})
        batch_id = uuid4()
        connection.execute(text(
            "INSERT INTO tenant_closure_media_deletion_batch "
            "(id,tenant_id,closure_request_id,requested_by_owner_admin_id,request_id,state,"
            "inventory_sha256,object_count,verified_deleted_object_count,total_bytes,requested_at,updated_at) "
            "VALUES (:id,:tenant,:closure,:owner,:request,'completed',:digest,0,0,0,now(),now())"
        ), {"id": batch_id, "tenant": tenant_id, "closure": closure_id, "owner": admin_id,
            "request": uuid4(), "digest": "b" * 64})

    with pytest.raises(RuntimeError, match="recibos de exclusão fria"):
        command.downgrade(config, "20261110_0121")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM tenant_closure_media_deletion_batch"
        )) == 1
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0122"

    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM tenant_closure_media_deletion_batch WHERE id=:id"
        ), {"id": batch_id})
        connection.execute(text(
            "UPDATE photographer_business_profile "
            "SET cpf_fingerprint=NULL,cpf_fingerprint_key_version=NULL WHERE id=:id"
        ), {"id": profile_id})
        assert connection.scalar(text(
            "SELECT cpf_fingerprint IS NULL AND cpf_fingerprint_key_version IS NULL "
            "FROM photographer_business_profile WHERE id=:id"
        ), {"id": profile_id}) is True

    with pytest.raises(RuntimeError, match="perfis sem verificador CPF"):
        command.downgrade(config, "20261110_0121")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0122"


def test_deletion_schema_isolates_tenants_and_protects_checkpoints_and_audit(
    monkeypatch, postgres_schema,
):
    engine = postgres_schema
    config = _upgrade_with_owner(monkeypatch, engine, "20261110_0122")
    with Session(engine) as db:
        owner_id = db.scalar(text("SELECT admin_user_id FROM platform_owner"))
        tenant_a = db.scalar(text("SELECT tenant_id FROM tenant_admin WHERE admin_user_id=:owner"),
                             {"owner": owner_id})
        tenant_b = Tenant()
        db.add(tenant_b)
        db.flush()
        tenant_b_id = tenant_b.id
        gallery = ParentGallery(tenant_id=tenant_b_id, name="Synthetic archive")
        db.add(gallery)
        db.flush()
        folder = PhotoFolder(tenant_id=tenant_b_id, parent_gallery_id=gallery.id, name="Synthetic")
        db.add(folder)
        db.flush()
        cycle = MediaArchiveCycle(tenant_id=tenant_b_id, parent_gallery_id=gallery.id,
                                  folder_id=folder.id, cycle_number=1, state="archived")
        db.add(cycle)
        db.flush()
        operation = MediaArchiveOperation(
            tenant_id=tenant_b_id, cycle_id=cycle.id, operation_type="delete_remote",
            status="completed", idempotency_key="synthetic-deletion", actor_type="system",
        )
        remote = MediaArchiveObject(
            tenant_id=tenant_b_id, cycle_id=cycle.id, source_ref="manifest:v1",
            object_type="manifest", mime_type="application/json", size_bytes=2,
            sha256="a" * 64, remote_object_id="synthetic-remote-id",
        )
        # Esta prova permanece em 0122; o ORM atual também inclui campos de 0125.
        closure_table = Table("tenant_closure_request", MetaData(), autoload_with=db.connection())
        closures = [{
            "id": uuid4(), "tenant_id": tenant, "request_id": uuid4(),
            "requested_by": owner_id, "state": "closed", "requested_at": now(), "closed_at": now(),
            "terms_version": "synthetic", "terms_sha256": "b" * 64,
            "balance_snapshot": 0, "balance_acknowledged": True,
        } for tenant in (tenant_a, tenant_b_id)]
        db.add_all([operation, remote])
        db.flush()
        db.execute(closure_table.insert(), closures)
        closure_a_id, closure_b_id = [row["id"] for row in closures]
        cycle_id, operation_id, object_id = cycle.id, operation.id, remote.id
        batch_a = TenantClosureMediaDeletionBatch(
            tenant_id=tenant_a, closure_request_id=closure_a_id,
            requested_by_owner_admin_id=owner_id, request_id=uuid4(), state="queued",
            inventory_sha256="c" * 64, object_count=1, total_bytes=2,
        )
        db.add(batch_a)
        db.flush()
        batch_a_id = batch_a.id
        db.commit()

    with pytest.raises(IntegrityError) as cross_closure, Session(engine) as db:
        db.add(TenantClosureMediaDeletionBatch(
            tenant_id=tenant_a, closure_request_id=closure_b_id,
            requested_by_owner_admin_id=owner_id, request_id=uuid4(), state="queued",
            inventory_sha256="d" * 64, object_count=1, total_bytes=2,
        ))
        db.flush()
    assert cross_closure.value.orig.diag.constraint_name == "fk_closure_media_deletion_batch_closure"

    with pytest.raises(IntegrityError) as cross_operation, Session(engine) as db:
        db.add(TenantClosureMediaDeletionItem(
            tenant_id=tenant_a, batch_id=batch_a_id, cycle_id=cycle_id, operation_id=operation_id,
        ))
        db.flush()
    assert cross_operation.value.orig.diag.constraint_name == "fk_closure_media_deletion_item_operation"

    with pytest.raises(IntegrityError) as invalid_count, engine.begin() as connection:
        connection.execute(text(
            "UPDATE tenant_closure_media_deletion_batch SET verified_deleted_object_count=2"
        ))
    assert invalid_count.value.orig.diag.constraint_name == "ck_closure_media_deletion_batch_deleted_objects"

    with Session(engine) as db:
        batch_b = TenantClosureMediaDeletionBatch(
            tenant_id=tenant_b_id, closure_request_id=closure_b_id,
            requested_by_owner_admin_id=owner_id, request_id=uuid4(), state="queued",
            inventory_sha256="e" * 64, object_count=1, total_bytes=2,
        )
        db.add(batch_b)
        db.flush()
        db.add(TenantClosureMediaDeletionItem(
            tenant_id=tenant_b_id, batch_id=batch_b.id, cycle_id=cycle_id, operation_id=operation_id,
        ))
        db.commit()

    # Limpa somente as linhas sintéticas de lote para testar cada proteção isoladamente.
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM tenant_closure_media_deletion_item"))
        connection.execute(text("DELETE FROM tenant_closure_media_deletion_batch"))
        connection.execute(text("UPDATE media_archive_object SET remote_deleted_at=now() WHERE id=:id"),
                           {"id": object_id})
    with pytest.raises(RuntimeError, match="checkpoints de remoção remota"):
        command.downgrade(config, "20261110_0121")
    with engine.begin() as connection:
        connection.execute(text("UPDATE media_archive_object SET remote_deleted_at=NULL WHERE id=:id"),
                           {"id": object_id})
        connection.execute(text(
            "INSERT INTO platform_admin_event "
            "(id,request_id,actor_admin_id,object_id,tenant_id,action,previous_status,next_status,result,origin,created_at) "
            "VALUES (:id,:request,:owner,:object,:tenant,'tenant.media_deletion_retry',"
            "'attention_required','queued','success','web_console',now())"
        ), {"id": uuid4(), "request": uuid4(), "owner": owner_id,
            "object": uuid4(), "tenant": tenant_a})
    with pytest.raises(RuntimeError, match="auditorias de exclusão fria"):
        command.downgrade(config, "20261110_0121")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261110_0122"
        assert connection.scalar(text(
            "SELECT count(*) FROM platform_admin_event WHERE action='tenant.media_deletion_retry' "
            "AND previous_status='attention_required' AND next_status='queued'"
        )) == 1
