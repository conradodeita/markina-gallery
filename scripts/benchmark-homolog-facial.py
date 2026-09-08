#!/usr/bin/env python3
# ruff: noqa: N999
"""Observador agregado e somente leitura de lote facial privado em homologação.

O script deve ser enviado por stdin ao host ARM e executado a partir do checkout
fixo da Markina. Ele não lê imagens, nomes, telefones, vetores ou scores.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/opt/markina-gallery")
PROJECT_NAME = "markina-gallery"
COMPOSE_FILE = "docker/docker-compose.yml"
ENV_FILE = "docker/.env.homolog"
STATE_DIR = Path("/var/lib/markina-gallery/deploy-state")
CONFIRMATION = "BENCHMARK_AUTHORIZED_PRIVATE_FACIAL_HOMOLOG"
SERVICES = ("api", "worker", "face-worker", "db")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")

DB_SNAPSHOT = r'''
import json
import sys
from sqlalchemy import text
from app.auth import SessionLocal

started_at, scope_expires_at = sys.argv[1:3]
with SessionLocal() as db:
    row = db.execute(text("""
        WITH new_photos AS (
            SELECT id FROM photo_asset
            WHERE created_at >= CAST(:started_at AS timestamptz)
              AND created_at < COALESCE(
                  CAST(NULLIF(:scope_expires_at, '') AS timestamptz),
                  'infinity'::timestamptz
              )
        ), media AS (
            SELECT
                COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                MAX(updated_at) AS last_updated
            FROM media_job WHERE photo_asset_id IN (SELECT id FROM new_photos)
        ), facial AS (
            SELECT
                COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
                COUNT(DISTINCT photo_asset_id) FILTER (WHERE status = 'completed') AS indexed_photos,
                MIN(created_at) AS first_created,
                MAX(updated_at) AS last_updated
            FROM facial_job
            WHERE kind = 'index' AND photo_asset_id IN (SELECT id FROM new_photos)
        ), derivatives AS (
            SELECT
                COUNT(*) FILTER (WHERE status = 'ready') AS ready,
                COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed
            FROM media_derivative WHERE photo_asset_id IN (SELECT id FROM new_photos)
        ), embeddings AS (
            SELECT COUNT(*) AS faces, COUNT(DISTINCT photo_asset_id) AS photos_with_faces
            FROM photo_face_embedding WHERE photo_asset_id IN (SELECT id FROM new_photos)
        )
        SELECT
            (SELECT COUNT(*) FROM new_photos) AS photos,
            COALESCE(media.queued, 0) AS media_queued,
            COALESCE(media.processing, 0) AS media_processing,
            COALESCE(media.completed, 0) AS media_completed,
            COALESCE(media.failed, 0) AS media_failed,
            media.last_updated AS media_last_updated,
            COALESCE(facial.queued, 0) AS facial_queued,
            COALESCE(facial.processing, 0) AS facial_processing,
            COALESCE(facial.completed, 0) AS facial_completed,
            COALESCE(facial.failed, 0) AS facial_failed,
            COALESCE(facial.cancelled, 0) AS facial_cancelled,
            COALESCE(facial.indexed_photos, 0) AS indexed_photos,
            facial.first_created AS facial_first_created,
            facial.last_updated AS facial_last_updated,
            COALESCE(derivatives.ready, 0) AS derivatives_ready,
            COALESCE(derivatives.queued, 0) AS derivatives_queued,
            COALESCE(derivatives.failed, 0) AS derivatives_failed,
            COALESCE(embeddings.faces, 0) AS faces,
            COALESCE(embeddings.photos_with_faces, 0) AS photos_with_faces
        FROM media CROSS JOIN facial CROSS JOIN derivatives CROSS JOIN embeddings
    """), {"started_at": started_at, "scope_expires_at": scope_expires_at}).mappings().one()
print(json.dumps(dict(row), default=lambda value: value.isoformat()))
'''


@dataclass(frozen=True)
class Options:
    mode: str
    expected_sha: str
    duration: int
    interval: int
    settle_samples: int
    confirmation: str
    batch_id: str
    authorization_ref: str
    expected_count: int
    contains_minors: bool
    scope_from_manifest: bool


def parse_args(argv: list[str]) -> Options:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("snapshot", "monitor"), default="snapshot")
    parser.add_argument("--sha", required=True, help="SHA integral esperado no host")
    parser.add_argument("--duration", type=int, default=7200)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--settle-samples", type=int, default=6)
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--expected-count", required=True, type=int)
    parser.add_argument("--contains-minors", choices=("true", "false"), required=True)
    parser.add_argument(
        "--scope-from-manifest",
        action="store_true",
        help="usar recorded_at do manifesto original em uma retomada autorizada",
    )
    args = parser.parse_args(argv)
    if not SHA_RE.fullmatch(args.sha):
        parser.error("--sha deve conter 40 caracteres hexadecimais minúsculos")
    if not 30 <= args.duration <= 14400:
        parser.error("--duration deve ficar entre 30 e 14400 segundos")
    if not 2 <= args.interval <= 60:
        parser.error("--interval deve ficar entre 2 e 60 segundos")
    if not 2 <= args.settle_samples <= 60:
        parser.error("--settle-samples deve ficar entre 2 e 60")
    if not REFERENCE_RE.fullmatch(args.batch_id):
        parser.error("--batch-id deve ser uma referência opaca, sem PII")
    if not REFERENCE_RE.fullmatch(args.authorization_ref):
        parser.error("--authorization-ref deve ser uma referência opaca, sem PII")
    if not 500 <= args.expected_count <= 1000:
        parser.error("--expected-count deve ficar entre 500 e 1000")
    if args.mode == "monitor" and args.confirmation != CONFIRMATION:
        parser.error("monitor exige confirmação explícita do lote privado autorizado")
    return Options(
        mode=args.mode,
        expected_sha=args.sha,
        duration=args.duration,
        interval=args.interval,
        settle_samples=args.settle_samples,
        confirmation=args.confirmation,
        batch_id=args.batch_id,
        authorization_ref=args.authorization_ref,
        expected_count=args.expected_count,
        contains_minors=args.contains_minors == "true",
        scope_from_manifest=args.scope_from_manifest,
    )


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(
        [
            "docker",
            "compose",
            "--env-file",
            ENV_FILE,
            "-p",
            PROJECT_NAME,
            "-f",
            COMPOSE_FILE,
            "--profile",
            "facial",
            *args,
        ],
        check=check,
    )


def verify_target(options: Options) -> None:
    if Path.cwd().resolve() != PROJECT_ROOT:
        raise RuntimeError(f"execução permitida somente em {PROJECT_ROOT}")
    if not Path(COMPOSE_FILE).is_file() or not Path(ENV_FILE).is_file():
        raise RuntimeError("Compose ou ambiente de homologação ausente")
    if run(["git", "rev-parse", "--show-toplevel"]).stdout.strip() != str(PROJECT_ROOT):
        raise RuntimeError("checkout remoto inesperado")
    if run(["git", "rev-parse", "HEAD"]).stdout.strip() != options.expected_sha:
        raise RuntimeError("SHA publicado diverge do SHA autorizado para a medição")
    if run(["uname", "-m"]).stdout.strip() not in {"aarch64", "arm64"}:
        raise RuntimeError("benchmark operacional exige o host ARM64 alvo")
    compose("config", "--quiet")
    active = compose("ps", "-q", "face-worker").stdout.strip()
    if not active:
        raise RuntimeError("face-worker não está ativo")
    runtime = compose(
        "exec",
        "-T",
        "api",
        "python",
        "-c",
        "import json, os; from app.facial.config import facial_settings_from_environment; s=facial_settings_from_environment(verify_runtime_assets=False); print(json.dumps({'enabled':s.enabled,'private':s.private_homologation_active,'batch':s.homolog_batch_id,'authorization':s.homolog_authorization_ref,'count':s.homolog_expected_count,'minors':s.homolog_contains_minors,'client_minor_search':s.minor_search_enabled}))",
    ).stdout
    gate = json.loads(runtime)
    expected_gate = {
        "enabled": True,
        "private": True,
        "batch": options.batch_id,
        "authorization": options.authorization_ref,
        "count": options.expected_count,
        "minors": options.contains_minors,
        "client_minor_search": options.contains_minors,
    }
    if gate != expected_gate:
        raise RuntimeError("gate privado ativo diverge do lote autorizado para a medição")


def db_snapshot(started_at: str, scope_expires_at: str = "") -> dict[str, Any]:
    result = compose(
        "exec", "-T", "api", "python", "-c", DB_SNAPSHOT, started_at, scope_expires_at
    )
    return json.loads(result.stdout)


def manifest_scope(
    options: Options, measurement_started_at: datetime
) -> tuple[str, str]:
    if not options.scope_from_manifest:
        return measurement_started_at.isoformat(), ""
    path = STATE_DIR / f"facial-batch-{options.batch_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "batch_id": options.batch_id,
        "authorization_ref": options.authorization_ref,
        "expected_count": options.expected_count,
        "contains_minors": options.contains_minors,
        "status": "active",
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise RuntimeError("manifesto diverge do lote autorizado para o benchmark retomado")
    recorded_at = datetime.fromisoformat(payload["recorded_at"])
    expires_at = datetime.fromisoformat(payload["window_expires_at"])
    scope_expires_at = datetime.fromisoformat(
        payload.get("scope_expires_at", payload["window_expires_at"])
    )
    if (
        recorded_at >= scope_expires_at
        or scope_expires_at > expires_at
        or expires_at <= measurement_started_at
    ):
        raise RuntimeError("janela do manifesto não está vigente para o benchmark retomado")
    return recorded_at.isoformat(), scope_expires_at.isoformat()


def parse_bytes(value: str) -> int:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)", value.strip())
    if match is None:
        raise ValueError("unidade de memória inesperada no docker stats")
    number, unit = match.groups()
    scales = {
        "B": 1,
        "kB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
    }
    return int(float(number) * scales[unit])


def resource_snapshot() -> dict[str, dict[str, float | int]]:
    container_ids: list[str] = []
    names: dict[str, str] = {}
    for service in SERVICES:
        container_id = compose("ps", "-q", service).stdout.strip()
        if container_id:
            container_ids.append(container_id)
            names[container_id] = service
            names[container_id[:12]] = service
    if not container_ids:
        return {}
    output = run(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", *container_ids]
    ).stdout
    resources: dict[str, dict[str, float | int]] = {}
    for line in output.splitlines():
        item = json.loads(line)
        service = names.get(item["ID"], item.get("Name", "unknown"))
        used = item["MemUsage"].split(" / ", 1)[0]
        resources[service] = {
            "cpu_percent": float(item["CPUPerc"].rstrip("%")),
            "memory_bytes": parse_bytes(used),
            "memory_percent": float(item["MemPerc"].rstrip("%")),
            "pids": int(item["PIDs"]),
        }
    return resources


def root_disk() -> dict[str, int]:
    stats = os.statvfs(PROJECT_ROOT)
    return {
        "total_bytes": stats.f_blocks * stats.f_frsize,
        "used_bytes": (stats.f_blocks - stats.f_bfree) * stats.f_frsize,
        "available_bytes": stats.f_bavail * stats.f_frsize,
    }


def service_health() -> dict[str, str]:
    result: dict[str, str] = {}
    for service in SERVICES:
        container = compose("ps", "-q", service).stdout.strip()
        if not container:
            result[service] = "absent"
            continue
        state = run(
            [
                "docker",
                "inspect",
                "--format",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                container,
            ]
        ).stdout.strip()
        result[service] = state
    return result


def emit(event: str, **payload: Any) -> None:
    print(
        json.dumps(
            {"event": event, "at": datetime.now(timezone.utc).isoformat(), **payload},
            sort_keys=True,
        ),
        flush=True,
    )


def is_settled(
    db: dict[str, Any],
    previous_photos: int,
    stable_samples: int,
    required: int,
    expected_count: int,
) -> bool:
    photos = int(db["photos"])
    if photos != expected_count or photos != previous_photos or stable_samples < required:
        return False
    media_open = int(db["media_queued"]) + int(db["media_processing"])
    face_open = int(db["facial_queued"]) + int(db["facial_processing"])
    face_terminal = int(db["facial_completed"]) + int(db["facial_failed"]) + int(
        db["facial_cancelled"]
    )
    return media_open == 0 and face_open == 0 and face_terminal >= photos


def monitor(options: Options) -> int:
    measurement_started_at = datetime.now(timezone.utc)
    started_at, scope_expires_at = manifest_scope(options, measurement_started_at)
    started_monotonic = time.monotonic()
    initial_disk = root_disk()
    maxima: dict[str, dict[str, float | int]] = {}
    samples = 0
    stable_samples = 0
    previous_photos = -1
    final_db = db_snapshot(started_at, scope_expires_at)
    initial_completed = int(final_db["facial_completed"])
    emit(
        "benchmark_started",
        sha=options.expected_sha,
        batch_id=options.batch_id,
        expected_count=options.expected_count,
        contains_minors=options.contains_minors,
        architecture=run(["uname", "-m"]).stdout.strip(),
        cpus=os.cpu_count(),
        duration_seconds=options.duration,
        interval_seconds=options.interval,
        scope_started_at=started_at,
        scope_expires_at=scope_expires_at or None,
        scope_from_manifest=options.scope_from_manifest,
        initial_facial_completed=initial_completed,
        health=service_health(),
        disk=initial_disk,
    )
    while time.monotonic() - started_monotonic <= options.duration:
        db = db_snapshot(started_at, scope_expires_at)
        resources = resource_snapshot()
        samples += 1
        for service, values in resources.items():
            current = maxima.setdefault(
                service,
                {"cpu_percent": 0.0, "memory_bytes": 0, "memory_percent": 0.0, "pids": 0},
            )
            for key, value in values.items():
                current[key] = max(current[key], value)
        photos = int(db["photos"])
        if photos > options.expected_count:
            raise RuntimeError("quantidade observada excede o lote autorizado")
        stable_samples = stable_samples + 1 if photos == previous_photos else 0
        emit("sample", elapsed_seconds=round(time.monotonic() - started_monotonic, 3), db=db, resources=resources)
        final_db = db
        if is_settled(
            db,
            previous_photos,
            stable_samples,
            options.settle_samples,
            options.expected_count,
        ):
            break
        previous_photos = photos
        time.sleep(options.interval)
    elapsed = round(time.monotonic() - started_monotonic, 3)
    completed = int(final_db.get("facial_completed", 0))
    first = final_db.get("facial_first_created")
    last = final_db.get("facial_last_updated")
    active_seconds: float | None = None
    if first and last:
        active_seconds = (
            datetime.fromisoformat(last) - datetime.fromisoformat(first)
        ).total_seconds()
    throughput = round(completed / active_seconds, 3) if active_seconds and active_seconds > 0 else None
    completed_delta = completed - initial_completed
    continuation_throughput = round(completed_delta / elapsed, 3) if elapsed > 0 else None
    final_disk = root_disk()
    success = (
        int(final_db.get("photos", 0)) == options.expected_count
        and int(final_db.get("media_failed", 0)) == 0
        and int(final_db.get("facial_failed", 0)) == 0
        and int(final_db.get("facial_completed", 0)) >= int(final_db.get("photos", 0))
    )
    emit(
        "benchmark_finished",
        batch_id=options.batch_id,
        success=success,
        elapsed_seconds=elapsed,
        samples=samples,
        db=final_db,
        facial_active_seconds=active_seconds,
        facial_throughput_photos_per_second=throughput,
        continuation_completed=completed_delta,
        continuation_throughput_photos_per_second=continuation_throughput,
        resource_maxima=maxima,
        disk={
            "initial": initial_disk,
            "final": final_disk,
            "used_delta_bytes": final_disk["used_bytes"] - initial_disk["used_bytes"],
        },
        health=service_health(),
    )
    return 0 if success else 2


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv or sys.argv[1:])
    verify_target(options)
    if options.mode == "snapshot":
        emit(
            "snapshot",
            sha=options.expected_sha,
            batch_id=options.batch_id,
            health=service_health(),
            resources=resource_snapshot(),
            disk=root_disk(),
        )
        return 0
    return monitor(options)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
        print(f"benchmark-homolog-facial: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
