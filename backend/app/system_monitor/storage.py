"""Inventário limitado dos arquivos registrados; nunca varre diretórios."""
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy import literal, select, union_all

from app.auth import MediaDerivative, PhotoAsset, PreviewAdjustment
from app.media import derivatives_root, media_namespace, source_root

_cached = None
_expires = 0.0


def file_inventory(db):
    global _cached, _expires
    if _cached is not None and monotonic() < _expires:
        return dict(_cached)
    # At most 1000 stats/hour/process; no recursive traversal or file contents.
    query = union_all(
        select(literal("source").label("kind"), PhotoAsset.tenant_id, PhotoAsset.storage_key.label("path")),
        select(literal("derived"), MediaDerivative.tenant_id, MediaDerivative.relative_path).where(MediaDerivative.relative_path.is_not(None)),
        select(literal("derived"), PreviewAdjustment.tenant_id, PreviewAdjustment.relative_path).where(PreviewAdjustment.relative_path.is_not(None)),
    ).limit(1001)
    rows = db.execute(query).all()
    total, checked, missing, seen = 0, 0, 0, set()
    deadline = monotonic() + 1
    for kind, tenant_id, relative in rows[:1000]:
        if monotonic() >= deadline:
            break
        checked += 1
        try:
            root = source_root() if kind == "source" else derivatives_root()
            media_namespace(relative, tenant_id)
            candidate = (root / relative).resolve()
            candidate.relative_to(root)
            media_namespace(candidate.relative_to(root).as_posix(), tenant_id)
            if candidate in seen:
                continue
            seen.add(candidate)
            if not candidate.is_file():
                raise FileNotFoundError
            total += Path(candidate).stat().st_size
        except (OSError, ValueError):
            missing += 1
    complete = checked == len(rows) and not missing and len(rows) <= 1000
    _cached = {"registered_file_bytes": total if complete else None,
               "verified_file_bytes_lower_bound": total, "files_checked": checked,
               "files_unavailable": missing, "inventory_complete": complete,
               "inventory_at": datetime.now(UTC).isoformat()}
    _expires = monotonic() + 3600
    return dict(_cached)
