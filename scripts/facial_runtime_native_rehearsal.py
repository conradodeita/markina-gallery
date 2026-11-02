"""Ensaio sintético de 100 admissões/leases no candidato isolado; não calibra pessoas."""
import json
import math
import platform
import resource
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from app.auth import FacialJob, FacialSearchRequest, Tenant
from app.facial.model_assets import verify_models
from app.facial.provider import OpenCvSFaceProvider
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests import test_facial_search_worker as scenario
from tests.tenant_fixtures import FIXTURE_TENANT_ID


def main():
    assert platform.machine() in {"aarch64", "arm64"}
    cv2.setNumThreads(1)
    models = verify_models(Path("/app/facial-assets/model-manifest.json"),
                           Path("/opt/markina-face-models"))
    provider = OpenCvSFaceProvider(models["yunet"], models["sface"])
    original_create = scenario.Base.metadata.create_all

    def create_with_synthetic_tenant(bind, **kwargs):
        original_create(bind, **kwargs)
        with Session(bind) as db:
            if db.get(Tenant, FIXTURE_TENANT_ID) is None:
                db.add(Tenant(id=FIXTURE_TENANT_ID, status="active"))
                db.commit()

    scenario.Base.metadata.create_all = create_with_synthetic_tenant
    scenario.Provider = lambda _observations: provider
    monkeypatch = pytest.MonkeyPatch()
    started, cpu = time.perf_counter(), time.process_time()
    with tempfile.TemporaryDirectory(prefix="facial-native-") as temporary:
        root = Path(temporary)
        try:
            scenario.test_one_hundred_concurrent_searches_survive_backpressure_and_worker_restart(
                root, monkeypatch)
        finally:
            monkeypatch.undo()
            scenario.Base.metadata.create_all = original_create
        engine = scenario.create_engine(f"sqlite:///{root / 'concurrent-load.db'}")
        with Session(engine) as db:
            requests = list(db.scalars(select(FacialSearchRequest)))
            jobs = list(db.scalars(select(FacialJob).where(FacialJob.kind == "search")))
            durations = sorted((r.completed_at - r.created_at).total_seconds() for r in requests)
            oldest = max((j.updated_at - j.created_at).total_seconds() for j in jobs)
            assert len(requests) == 100 and all(r.status == "no_face" for r in requests)
            assert all(j.status == "completed" for j in jobs)
            p95 = durations[math.ceil(len(durations) * .95) - 1]
        references_left = len(list((root / "concurrent-references").glob("*.reference")))
        assert references_left == 0
    elapsed, cpu_seconds = time.perf_counter() - started, time.process_time() - cpu
    matrix = np.random.default_rng(0).normal(size=(14267, 128)).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    timings = []
    for index in range(100):
        instant = time.perf_counter()
        scores = matrix @ matrix[index]
        assert scores.shape == (14267,)
        timings.append(time.perf_counter() - instant)
    report = {
        "architecture": platform.machine(), "synthetic_only": True,
        "admissions": 100, "queue_peak": 100, "queue_remaining": 0,
        "lease_recovery": "passed", "backpressure": "passed",
        "terminal_state": "no_face", "real_yunet_provider": True,
        "duration_p95_seconds": p95, "max_job_age_seconds": oldest,
        "elapsed_seconds": elapsed, "cpu_seconds": cpu_seconds,
        "average_cpu_percent": cpu_seconds / elapsed * 100,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "references_remaining": references_left,
        "synthetic_vector_comparison_p95_seconds": float(np.quantile(timings, .95)),
        "scope": "Fila, leases, backpressure, detector real em JPEG sintético sem rosto e microbenchmark vetorial. Não mede precisão nem latência de retrieval positivo com PostgreSQL/acervo real.",
    }
    assert p95 <= 120 and oldest <= 300 and report["peak_rss_bytes"] < 460 * 1024 * 1024
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
