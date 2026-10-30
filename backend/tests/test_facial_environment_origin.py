"""Projeções sintéticas dos metadados; nenhum payload facial participa do ensaio."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, event, update

from app.auth import (
    FacialRollout,
    GalleryFacialPolicy,
    ParentGallery,
    PhotoAsset,
    PhotoFaceEmbedding,
)
from app.facial.environment_origin import inspect_embedding_origins


@pytest.fixture
def metadata_database():
    metadata = MetaData()
    fields = {
        PhotoFaceEmbedding: "id tenant_id photo_asset_id parent_gallery_id model_version quality_version",
        PhotoAsset: "id tenant_id parent_gallery_id",
        ParentGallery: "id tenant_id",
        GalleryFacialPolicy: (
            "id tenant_id parent_gallery_id status suspended_at model_version quality_version "
            "legal_notice_version legal_basis_reference retention_policy_version"
        ),
        FacialRollout: (
            "id tenant_id parent_gallery_id environment status revoked_at suspended_at "
            "approved_at approved_by_admin_id approval_reference model_version quality_version "
            "legal_notice_version legal_basis_reference retention_policy_version"
        ),
    }
    tables = {
        model: Table(model.__tablename__, metadata, *[
            Column(name, model.__table__.c[name].type) for name in names.split()
        ]) for model, names in fields.items()
    }
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    now = datetime(2026, 10, 29, tzinfo=UTC)
    base = {"tenant_id": UUID(int=1), "parent_gallery_id": UUID(int=2)}
    versions = {
        "model_version": "synthetic-model", "quality_version": "synthetic-quality",
    }
    legal = {
        "legal_notice_version": "synthetic-notice", "legal_basis_reference": "synthetic-basis",
        "retention_policy_version": "synthetic-retention",
    }
    with engine.begin() as connection:
        connection.execute(tables[ParentGallery].insert(), {"id": UUID(int=2), "tenant_id": UUID(int=1)})
        connection.execute(tables[PhotoAsset].insert(), {**base, "id": UUID(int=3)})
        connection.execute(tables[PhotoFaceEmbedding].insert(), {
            **base, **versions, "id": UUID(int=4), "photo_asset_id": UUID(int=3),
        })
        connection.execute(tables[GalleryFacialPolicy].insert(), {
            **base, **versions, **legal, "id": UUID(int=5), "status": "active",
        })
        connection.execute(tables[FacialRollout].insert(), {
            **base, **versions, **legal, "id": UUID(int=6), "environment": "staging",
            "status": "active", "approved_at": now, "approved_by_admin_id": UUID(int=7),
            "approval_reference": "synthetic-approval",
        })
    yield engine, tables
    engine.dispose()


def test_origin_inspection_returns_only_counts_and_never_selects_payload(metadata_database):
    engine, _ = metadata_database
    statements = []
    event.listen(engine, "before_cursor_execute", lambda conn, cursor, sql, *args: statements.append(sql))
    with engine.connect() as connection:
        result = inspect_embedding_origins(connection, source_environment="staging")
    assert result == {
        "total": 1, "binding_verified": 1, "policy_verified": 1,
        "source_rollout_verified": 1, "all_metadata_verified": 1,
    }
    assert len(statements) == 1
    assert statements[0].lstrip().upper().startswith("SELECT")
    assert "payload" not in statements[0]
    assert "ciphertext" not in statements[0]


@pytest.mark.parametrize(("model", "changes"), [
    (PhotoAsset, {"tenant_id": UUID(int=99)}),
    (ParentGallery, {"tenant_id": UUID(int=99)}),
    (GalleryFacialPolicy, {"status": "suspended"}),
    (GalleryFacialPolicy, {"retention_policy_version": ""}),
    (FacialRollout, {"tenant_id": UUID(int=99)}),
    (FacialRollout, {"environment": "production"}),
    (FacialRollout, {"approved_at": None}),
    (FacialRollout, {"approved_by_admin_id": None}),
    (FacialRollout, {"approval_reference": " "}),
    (FacialRollout, {"revoked_at": datetime(2026, 10, 29, tzinfo=UTC)}),
    (FacialRollout, {"model_version": "other-model"}),
    (FacialRollout, {"retention_policy_version": "other-policy"}),
])
def test_divergent_metadata_does_not_prove_origin(metadata_database, model, changes):
    engine, tables = metadata_database
    with engine.begin() as connection:
        connection.execute(update(tables[model]).values(**changes))
        result = inspect_embedding_origins(connection, source_environment="staging")
    assert result["total"] == 1
    assert result["all_metadata_verified"] == 0


def test_invalid_environment_aborts_before_sql(metadata_database):
    engine, _ = metadata_database
    with engine.connect() as connection, pytest.raises(ValueError, match="Contexto de origem"):
        inspect_embedding_origins(connection, source_environment="unknown")
