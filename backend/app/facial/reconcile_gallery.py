"""Reconciliação explícita e paginada do índice de uma Galeria pública."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from app.auth import SessionLocal
from app.facial.config import facial_settings_from_environment
from app.facial.indexing import reconcile_gallery_index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery-id", type=UUID, required=True)
    parser.add_argument("--page-size", type=int, default=100, choices=range(1, 501))
    args = parser.parse_args()
    settings = facial_settings_from_environment(verify_runtime_assets=False)
    derivatives_root = Path(
        os.getenv("MEDIA_DERIVATIVES_ROOT", "/var/lib/markina/derivatives")
    ).resolve()
    with SessionLocal() as db:
        result = reconcile_gallery_index(
            db,
            parent_gallery_id=args.gallery_id,
            derivatives_root=derivatives_root,
            settings=settings,
            page_size=args.page_size,
        )
    print(
        json.dumps(
            {
                "pages": result.pages,
                "photos_scanned": result.photos_scanned,
                "eligible_index_jobs": result.eligible_index_jobs,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
