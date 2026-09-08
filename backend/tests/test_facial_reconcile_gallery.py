from __future__ import annotations

import json
from uuid import UUID

import pytest

from app.facial import reconcile_gallery
from app.facial.indexing import GalleryReconciliation

GALLERY_ID = UUID("11111111-1111-4111-8111-111111111111")


class _Database:
    def __init__(self) -> None:
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1


def test_reconcile_gallery_pages_existing_collection(monkeypatch, capsys) -> None:
    db = _Database()
    monkeypatch.setattr(reconcile_gallery, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        reconcile_gallery, "facial_settings_from_environment", lambda **_kwargs: object()
    )
    monkeypatch.setattr(
        reconcile_gallery,
        "reconcile_gallery_index",
        lambda *_args, **_kwargs: GalleryReconciliation(2, 137, 137),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["reconcile_gallery", "--gallery-id", str(GALLERY_ID), "--page-size", "100"],
    )

    assert reconcile_gallery.main() == 0
    assert db.commits == 0
    assert json.loads(capsys.readouterr().out) == {
        "eligible_index_jobs": 137,
        "pages": 2,
        "photos_scanned": 137,
    }


def test_reconcile_gallery_propagates_fail_closed_result(monkeypatch) -> None:
    db = _Database()
    monkeypatch.setattr(reconcile_gallery, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        reconcile_gallery, "facial_settings_from_environment", lambda **_kwargs: object()
    )

    def fail_closed(*_args, **_kwargs):
        raise SystemExit("Rollout facial ativo não encontrado para a galeria.")

    monkeypatch.setattr(reconcile_gallery, "reconcile_gallery_index", fail_closed)
    monkeypatch.setattr("sys.argv", ["reconcile_gallery", "--gallery-id", str(GALLERY_ID)])

    with pytest.raises(SystemExit, match="Rollout facial ativo"):
        reconcile_gallery.main()
    assert db.commits == 0
