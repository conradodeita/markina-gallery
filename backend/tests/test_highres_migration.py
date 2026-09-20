"""Migration aditiva em banco descartável; nenhum banco de operação é acessado."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.auth import ParentGallery, PhotoAsset, PhotoFaceEmbedding, PhotoFolder


def test_highres_upgrade_downgrade_upgrade(tmp_path):
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    env = {**os.environ, "DATABASE_URL": url}
    region_id = None
    for revision in ("head", "20260914_0056", "head"):
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
                    parent = ParentGallery(name="Legado sintético")
                    db.add(parent)
                    db.flush()
                    folder = PhotoFolder(parent_gallery_id=parent.id, name="Fotos")
                    db.add(folder)
                    db.flush()
                    photo = PhotoAsset(
                        parent_gallery_id=parent.id,
                        folder_id=folder.id,
                        filename="legacy.jpg",
                        storage_key="synthetic/legacy.jpg",
                    )
                    db.add(photo)
                    db.flush()
                    region = PhotoFaceEmbedding(
                        parent_gallery_id=parent.id,
                        photo_asset_id=photo.id,
                        face_ordinal=0,
                        model_version="legacy-model",
                        quality_version="legacy-quality",
                        preview_fingerprint="a" * 64,
                        payload_ciphertext=b"synthetic-ciphertext",
                        payload_nonce=b"synthetic-nonce",
                        key_id="synthetic-key",
                    )
                    db.add(region)
                    db.commit()
                    region_id = region.id
                else:
                    region = db.get(PhotoFaceEmbedding, region_id)
                    assert region.payload_ciphertext == b"synthetic-ciphertext"
                    assert region.model_version == "legacy-model"
                    assert region.bbox_x is None and region.pipeline_version == "legacy-preview-v1"
        engine.dispose()
