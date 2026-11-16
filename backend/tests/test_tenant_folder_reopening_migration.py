"""Reabertura conserva o escopo de pasta no schema migrado e no ORM."""

from importlib import import_module

import pytest
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    Client,
    DerivedGallery,
    GalleryClientState,
    GalleryReopeningRequest,
    ParentGallery,
    PhotoFolder,
    Tenant,
)
from tests.test_photographer_onboarding_migration import _config, _demo_helpers
from tests.test_tenant_credit_purchase_postgres import postgres_schema as _postgres_schema

postgres_schema = _postgres_schema


@pytest.mark.parametrize("foreign_folder", [1, 2, None], ids=["other-gallery", "other-tenant", "derived-with-folder"])
@pytest.mark.parametrize("schema_source", ["migrations", "metadata"])
def test_migrated_reopening_rejects_foreign_folder_and_preserves_legacy(monkeypatch, postgres_schema, foreign_folder, schema_source):
    engine = postgres_schema
    demo = _demo_helpers()
    demo.configure_synthetic_environment()
    config, scoped_url = _config(monkeypatch, engine)
    if schema_source == "migrations":
        command.upgrade(config, "20261026_0090")
        demo.create_synthetic_owner(scoped_url)
        command.upgrade(config, "head")
    else:
        Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as db:
        tenant_a, tenant_b = Tenant(), Tenant()
        db.add_all([tenant_a, tenant_b])
        db.flush()
        parent_a = ParentGallery(tenant_id=tenant_a.id, name="Galeria A")
        parent_other = ParentGallery(tenant_id=tenant_a.id, name="Outra galeria A")
        parent_b = ParentGallery(tenant_id=tenant_b.id, name="Galeria B")
        db.add_all([parent_a, parent_other, parent_b])
        db.flush()
        folders = [
            PhotoFolder(tenant_id=parent.tenant_id, parent_gallery_id=parent.id, name="Pasta", position=0)
            for parent in (parent_a, parent_other, parent_b)
        ]
        client = Client(tenant_id=tenant_a.id, full_name="Cliente sintética", phone_e164="+5511999990001")
        db.add_all([*folders, client])
        db.flush()
        db.add(GalleryClientState(tenant_id=tenant_a.id, parent_gallery_id=parent_a.id, client_id=client.id))
        derived = DerivedGallery(tenant_id=tenant_a.id, parent_gallery_id=parent_a.id, client_id=client.id, name="Legado")
        db.add(derived)
        db.flush()
        derived_folder = PhotoFolder(
            tenant_id=tenant_a.id, parent_gallery_id=parent_a.id,
            derived_gallery_id=derived.id, name="Pasta privada legada", position=0,
        )
        db.add(derived_folder)
        db.commit()

        def request(folder_id, key, *, legacy_derived=False):
            return GalleryReopeningRequest(
                tenant_id=tenant_a.id,
                parent_gallery_id=None if legacy_derived else parent_a.id,
                derived_gallery_id=derived.id if legacy_derived else None,
                requested_by_client_id=client.id,
                photo_folder_id=folder_id,
                idempotency_key=key,
            )

        with pytest.raises(IntegrityError) as error, db.begin_nested():
            db.add(request(
                folders[foreign_folder or 0].id, "wrong-scope",
                legacy_derived=foreign_folder is None,
            ))
            db.flush()
        assert error.value.orig.diag.constraint_name == (
            "fk_gallery_reopening_derived_folder_scope" if foreign_folder is None
            else "fk_gallery_reopening_folder_scope"
        )
        db.add_all([
            request(folders[0].id, "same-scope"), request(None, "legacy"),
            request(None, "legacy-derived", legacy_derived=True),
            request(derived_folder.id, "same-derived-scope", legacy_derived=True),
        ])
        db.commit()
        assert db.scalar(select(func.count()).select_from(GalleryReopeningRequest)) == 4

    # O downgrade não pode apagar a associação válida nem os pedidos legados.
    if schema_source == "migrations":
        with pytest.raises(RuntimeError, match="Preserve reaberturas por pasta"):
            command.downgrade(config, "20261108_0112")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(GalleryReopeningRequest)) == 4


def test_folder_reopening_empty_migration_round_trip(postgres_schema, monkeypatch):
    # Esquema mínimo imediatamente anterior à 0113, com a chave composta da 0112.
    with postgres_schema.begin() as connection:
        connection.execute(text(
            "CREATE TABLE photo_folder (id uuid PRIMARY KEY, parent_gallery_id uuid, derived_gallery_id uuid, "
            "tenant_id uuid NOT NULL, UNIQUE(id,parent_gallery_id,tenant_id))"
        ))
        connection.execute(text(
            "CREATE TABLE gallery_reopening_request (id uuid PRIMARY KEY, tenant_id uuid NOT NULL, "
            "derived_gallery_id uuid, parent_gallery_id uuid, requested_by_client_id uuid, "
            "idempotency_key varchar(128), status varchar(16), approved_until timestamptz)"
        ))
        for index, columns in (
            ("uq_gallery_reopening_request_pending", "tenant_id,derived_gallery_id"),
            ("uq_gallery_reopening_canonical_pending", "tenant_id,parent_gallery_id,requested_by_client_id"),
        ):
            connection.execute(text(f"CREATE UNIQUE INDEX {index} ON gallery_reopening_request ({columns}) WHERE status='pending'"))
        migration = import_module("migrations.versions.20261109_0113_folder_scoped_reopening")
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.upgrade()
        migration.downgrade()
        assert "photo_folder_id" not in {
            column["name"] for column in inspect(connection).get_columns("gallery_reopening_request")
        }
