"""Contagens high-res administrativas, sem geometria ou biometria."""

from __future__ import annotations

import math
from datetime import UTC

from sqlalchemy import select

from app.auth import FacialJob, PhotoAnalysis, PhotoAsset, now

COUNTERS = frozenset(
    {
        "elapsed_ms",
        "raw_detections",
        "deduplicated",
        "faces_accepted",
        "faces_rejected",
        "embedding_successes",
        "embedding_failures",
        "detection_failures",
        "tiles",
    }
)


def safe_attempt_metrics(payload):
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if key in COUNTERS
        and type(value) in (int, float)
        and 0 <= value <= 1e15
        and math.isfinite(value)
    }


def gallery_analysis_metrics(db, *, parent_gallery_id, derived_gallery_id=None):
    scope = (
        PhotoAsset.parent_gallery_id == parent_gallery_id,
        PhotoAsset.derived_gallery_id == derived_gallery_id,
    )
    rows = list(
        db.scalars(
            select(PhotoAnalysis)
            .join(PhotoAsset, PhotoAsset.id == PhotoAnalysis.photo_asset_id)
            .where(*scope)
        )
    )
    result = {key: 0 for key in COUNTERS}
    processed = with_faces = 0
    for row in rows:
        metrics = safe_attempt_metrics(row.metrics)
        for key, value in metrics.items():
            result[key] += value
        processed += int(row.state == "ready")
        with_faces += int(row.state == "ready" and metrics.get("faces_accepted", 0) > 0)
    pending = list(
        db.scalars(
            select(FacialJob.created_at)
            .join(PhotoAsset, PhotoAsset.id == FacialJob.photo_asset_id)
            .where(
                *scope, FacialJob.kind == "index", FacialJob.status.in_(("queued", "processing"))
            )
        )
    )
    instant = now()
    ages = [
        (instant - (date.replace(tzinfo=UTC) if date.tzinfo is None else date)).total_seconds()
        for date in pending
    ]
    return {
        **result,
        "photos_total": len(rows),
        "photos_processed": processed,
        "photos_with_faces": with_faces,
        "faces_per_processed_photo": result["faces_accepted"] / processed if processed else 0,
        "queue_depth": len(pending),
        "oldest_job_age_seconds": max([0, *ages]),
    }
