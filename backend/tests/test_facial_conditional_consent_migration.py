"""Migração aditiva do recibo de consentimento condicional em PostgreSQL."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, text

from app.auth import Client, FacialSearchRequest, GalleryFacialPolicy, ParentGallery, now
from tests.tenant_fixtures import insert_legacy_model


def test_conditional_consent_migration_preserves_existing_declarations():
    base_url = os.getenv("PHOTOGRAPHER_TEST_DATABASE_URL") or os.getenv("TENANT_TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("Banco PostgreSQL isolado do CI não configurado")

    parsed_url = sa.engine.make_url(base_url)
    assert parsed_url.host == "127.0.0.1"
    assert (parsed_url.port, parsed_url.database) in (
        (55469, "pyp_tenant_test"), (15470, "pyp_photographer_test"),
    )
    control_engine = create_engine(parsed_url, isolation_level="AUTOCOMMIT")
    database_name = f"facial_consent_migration_{uuid4().hex}"
    migration_url = parsed_url.set(database=database_name).render_as_string(hide_password=False)
    migration_engine = None
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": migration_url}

    def migrate(revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=root, env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    try:
        with control_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))

        migrate("20261014_0081")
        migration_engine = create_engine(migration_url)
        with migration_engine.begin() as connection:
            gallery_id = insert_legacy_model(connection, ParentGallery, name="Galeria sintética")
            client_id = insert_legacy_model(
                connection, Client, full_name="Cliente sintético", phone_e164="+5511999999900",
            )
            policy_id = insert_legacy_model(
                connection, GalleryFacialPolicy, parent_gallery_id=gallery_id,
                model_version="synthetic-v1", quality_version="synthetic-v1",
            )
            for declaration in ("adult", "minor"):
                insert_legacy_model(
                    connection,
                    FacialSearchRequest,
                    parent_gallery_id=gallery_id,
                    client_id=client_id,
                    policy_id=policy_id,
                    status="queued",
                    consent_version=f"historical-{declaration}-v1",
                    subject_declaration=declaration,
                    legal_notice_version="historical-notice-v1",
                    model_version="synthetic-v1",
                    quality_version="synthetic-v1",
                    index_generation=1,
                    expires_at=now(),
                )

        migrate("20261016_0082")
        constraints = inspect(migration_engine).get_check_constraints("facial_search_request")
        declaration_constraint = next(
            item for item in constraints if item["name"] == "ck_facial_search_subject_declaration"
        )
        assert "adult" in declaration_constraint["sqltext"]
        assert "minor" in declaration_constraint["sqltext"]
        assert "conditional" in declaration_constraint["sqltext"]
        with migration_engine.connect() as connection:
            declarations = connection.execute(
                text("SELECT subject_declaration, consent_version FROM facial_search_request ORDER BY subject_declaration")
            ).all()
        assert declarations == [
            ("adult", "historical-adult-v1"),
            ("minor", "historical-minor-v1"),
        ]
    finally:
        if migration_engine is not None:
            migration_engine.dispose()
        with control_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
        control_engine.dispose()
