"""Upgrade e compatibilidade de recibos em banco exclusivamente descartável."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Client, FacialSearchRequest, GalleryFacialPolicy, ParentGallery, now


def test_authorization_migration_preserves_receipts_and_rejects_false_consent(tmp_path):
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    env = {**os.environ, "DATABASE_URL": url}

    def migrate(direction, revision, check=True):
        return subprocess.run([sys.executable, "-m", "alembic", direction, revision],
                              cwd=root, env=env, capture_output=True, check=check)

    migrate("upgrade", "head")
    engine = create_engine(url)
    with Session(engine) as db:
        gallery = ParentGallery(name="Teste sintético")
        client = Client(full_name="Teste", phone_e164="+5511999999900")
        db.add_all([gallery, client])
        db.flush()
        policy = GalleryFacialPolicy(parent_gallery_id=gallery.id, model_version="m", quality_version="q")
        db.add(policy)
        db.flush()
        requests = [FacialSearchRequest(parent_gallery_id=gallery.id, client_id=client.id,
                    policy_id=policy.id, consent_version="receipt-v1", subject_declaration="adult",
                    legal_notice_version="notice-v1", model_version="m", quality_version="q",
                    index_generation=1, expires_at=now(), reference_region_id=region)
                    for region in (None, uuid4(), None)]
        requests[-1].reference_deleted_at = now()
        db.add_all(requests)
        db.commit()
    engine.dispose()
    migrate("downgrade", "20260921_0059")
    migrate("upgrade", "head")
    engine = create_engine(url)
    assert {"reference_source", "authorization_method"} <= {c["name"] for c in inspect(engine).get_columns("facial_search_request")}
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT reference_source, authorization_method, consent_version FROM facial_search_request")).all()
        assert set(rows) == {("upload", "legacy", "receipt-v1"), ("indexed_region", "legacy", "receipt-v1"), ("legacy_unknown", "legacy", "receipt-v1")}
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("UPDATE facial_search_request SET authorization_method='direct_region'"))
    with engine.begin() as conn:
        conn.execute(text("UPDATE facial_search_request SET authorization_method='direct_region', consent_version=NULL, subject_declaration=NULL WHERE reference_region_id IS NOT NULL"))
    engine.dispose()
    assert migrate("downgrade", "20260921_0059", check=False).returncode != 0
