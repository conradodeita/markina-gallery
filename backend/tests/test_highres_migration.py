
"""Migration aditiva em banco descartável; nenhum banco de operação é acessado."""
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.auth import ParentGallery, PhotoAsset, PhotoFaceEmbedding, PhotoFolder
from tests.tenant_fixtures import LEGACY_SCHEMA_HEAD, insert_legacy_model


def test_highres_upgrade_downgrade_upgrade(tmp_path):
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    env = {**os.environ, "DATABASE_URL": url}
    region_id = None
    for revision in (LEGACY_SCHEMA_HEAD, "20260914_0056", LEGACY_SCHEMA_HEAD):
        command = "downgrade" if revision.endswith("0056") else "upgrade"
        subprocess.run(
            [sys.executable, "-m", "alembic", command, revision],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
        )
        engine = create_engine(url)
        tables = inspect(engine).get_table_names()
        assert ("photo_analysis" in tables) == (command == "upgrade")
        assert "photo_asset" in tables
        if command == "upgrade":
            with Session(engine) as db:
                if region_id is None:
                    parent_id = insert_legacy_model(db.connection(), ParentGallery, name="Legado sintético")
                    folder_id = insert_legacy_model(db.connection(), PhotoFolder,
                                                   parent_gallery_id=parent_id, name="Fotos")
                    photo_id = insert_legacy_model(db.connection(), PhotoAsset,
                                                  parent_gallery_id=parent_id, folder_id=folder_id,
                                                  filename="legacy.jpg", storage_key="synthetic/legacy.jpg")
                    region_id = insert_legacy_model(db.connection(), PhotoFaceEmbedding,
                        parent_gallery_id=parent_id,
                        photo_asset_id=photo_id,
                        face_ordinal=0,
                        model_version="legacy-model",
                        quality_version="legacy-quality",
                        preview_fingerprint="a" * 64,
                        payload_ciphertext=b"synthetic-ciphertext",
                        payload_nonce=b"synthetic-nonce",
                        key_id="synthetic-key",
                    )
                    db.commit()
                else:
                    region = db.execute(text("SELECT payload_ciphertext, model_version, bbox_x, pipeline_version FROM photo_face_embedding WHERE id=:id"), {"id": region_id.hex}).one()
                    assert region.payload_ciphertext == b"synthetic-ciphertext"
                    assert region.model_version == "legacy-model"
                    assert region.bbox_x is None and region.pipeline_version == "legacy-preview-v1"
        engine.dispose()
