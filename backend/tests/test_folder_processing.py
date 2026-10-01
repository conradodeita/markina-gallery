"""Substituição integral por pasta, preservando herança e revisões."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import (
    Base,
    FolderProcessingSettings,
    GalleryPreviewSettings,
    ParentGallery,
    PhotoFolder,
)
from app.folder_processing import effective_preview, facial_processing_allowed
from app.preview_adjustment.service import effective_fingerprint
from tests.tenant_fixtures import FIXTURE_TENANT_ID


def test_effective_preview_never_accumulates_exposure(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'effective.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        gallery = ParentGallery(tenant_id=FIXTURE_TENANT_ID, name="Exposição")
        db.add(gallery)
        db.flush()
        inherited = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, name="Geral", purpose="content", position=0)
        custom = PhotoFolder(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, name="Lote", purpose="content", position=1)
        db.add_all([inherited, custom])
        db.flush()
        gallery_config = GalleryPreviewSettings(tenant_id=FIXTURE_TENANT_ID, parent_gallery_id=gallery.id, enabled=True,
                                                strength=40, exposure_tenths=3, generation=2)
        override = FolderProcessingSettings(tenant_id=FIXTURE_TENANT_ID, folder_id=custom.id, preview_mode="custom",
                                            preview_strength=60, preview_exposure_tenths=5,
                                            facial_mode="off", revision=2)
        db.add_all([gallery_config, override])
        db.flush()
        assert effective_preview(db, inherited).exposure_tenths == 3
        own = effective_preview(db, custom)
        assert (own.strength, own.exposure_tenths) == (60, 5)
        assert own.generation == effective_preview(db, inherited).generation
        assert effective_fingerprint("a" * 64, own) != effective_fingerprint(
            "a" * 64, effective_preview(db, inherited))
        assert not facial_processing_allowed(db, custom.id, tenant_id=FIXTURE_TENANT_ID)
        gallery_config.exposure_tenths = 7
        db.flush()
        assert effective_preview(db, inherited).exposure_tenths == 7
        assert effective_preview(db, custom).exposure_tenths == 5
        override.preview_exposure_tenths = 0
        db.flush()
        assert effective_preview(db, custom).exposure_tenths == 0
        gallery_config.enabled = False
        db.flush()
        assert not effective_preview(db, inherited).enabled
        assert effective_preview(db, custom).enabled
        override.preview_mode = "off"
        db.flush()
        assert not effective_preview(db, custom).enabled
        override.preview_mode = "inherit"
        db.flush()
        assert not effective_preview(db, custom).enabled
    engine.dispose()
