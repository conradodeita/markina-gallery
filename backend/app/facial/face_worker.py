"""Entrypoint do worker facial opcional e isolado."""

from __future__ import annotations

import os
import signal
import threading
from pathlib import Path

from fastapi import HTTPException
from redis import Redis

from app.auth import FacialJob, SessionLocal
from app.facial.config import FacialConfigurationError, facial_settings_from_environment
from app.facial.crypto import FacialCipher
from app.facial.indexing import reconcile_automatic_gallery_policies
from app.facial.jobs import (
    FACIAL_JOB_KINDS_BY_CLASS,
    ClaimedFacialJob,
    FacialJobError,
    FacialJobRepository,
)
from app.facial.model_assets import verify_models
from app.facial.notifications import process_next_search_notification
from app.facial.provider import OpenCvSFaceProvider
from app.facial.retention import process_claimed_cleanup_job
from app.facial.runtime import BlockingFacialWorker
from app.facial.search_worker import process_claimed_search_job
from app.facial.worker import process_claimed_index_job, process_claimed_purge_job
from app.tenancy import TenantContextError, domain_session

_STOP_REQUESTED = threading.Event()


def _request_stop(_signum, _frame) -> None:
    # O handler não acessa banco/Redis nem interrompe a tarefa em andamento.
    _STOP_REQUESTED.set()


def run_worker_until_stopped(*, worker, active_class, settings, cipher, session_factory,
                             stop_requested: threading.Event) -> None:
    """Termina o ciclo em curso e não inicia outro após o pedido de parada."""
    while (
        not stop_requested.is_set()
        and (active_class == "maintenance" or worker.processed_jobs < settings.max_jobs_per_process)
    ):
        try:
            worker.run_cycle()
            if active_class == "search" and not stop_requested.is_set():
                with session_factory() as db:
                    process_next_search_notification(db, cipher=cipher, settings=settings)
        except TenantContextError:
            stop_requested.wait(settings.queue_block_seconds)


def record_provider_failure(repository: FacialJobRepository, claim: ClaimedFacialJob,
                            error: Exception) -> None:
    try:
        with domain_session(SessionLocal) as db:
            repository.fail(db, claim, error, max_attempts=3, retry_delay_seconds=5)
    except (TenantContextError, HTTPException):
        # Exceção estreita: só devolver o lease demonstrado, mesmo com owner suspenso.
        with SessionLocal() as db:
            repository.release_denied(db, claim)


def main(worker_class: str | None = None) -> None:
    _STOP_REQUESTED.clear()
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    active_class = (worker_class or os.getenv("FACIAL_WORKER_CLASS", "")).strip().lower()
    if active_class not in FACIAL_JOB_KINDS_BY_CLASS:
        raise FacialConfigurationError(
            "FACIAL_WORKER_CLASS deve ser search, index ou maintenance."
        )
    settings = facial_settings_from_environment(
        verify_runtime_assets=active_class != "maintenance"
    )
    if not settings.enabled:
        raise FacialConfigurationError("O worker facial não pode iniciar com a flag desligada.")
    model_paths = (
        verify_models(settings.manifest_path, settings.model_root)
        if active_class in {"search", "index"}
        else {}
    )
    cipher = FacialCipher(
        active_key_id=settings.active_key_id,
        keys=settings.aead_keys,
    )
    repository = FacialJobRepository()
    derivatives_root = Path(
        os.getenv("MEDIA_DERIVATIVES_ROOT", "/var/lib/markina/derivatives")
    ).resolve()
    if active_class == "index":
        with domain_session(SessionLocal) as db:
            reconcile_automatic_gallery_policies(
                db,
                derivatives_root=derivatives_root,
                settings=settings,
            )
            db.commit()

    def provider_loader():
        return OpenCvSFaceProvider(model_paths["yunet"], model_paths["sface"])

    def processor(db, claim: ClaimedFacialJob, provider: object | None) -> bool | None:
        try:
            repository._leased(db, claim)
            if claim.kind == "index":
                if not isinstance(provider, OpenCvSFaceProvider):
                    raise FacialJobError("Provider facial não está disponível.")
                process_claimed_index_job(
                    db,
                    claim,
                    repository=repository,
                    provider=provider,
                    cipher=cipher,
                    settings=settings,
                    derivatives_root=derivatives_root,
                )
            elif claim.kind == "search":
                if not isinstance(provider, OpenCvSFaceProvider):
                    raise FacialJobError("Provider facial não está disponível.")
                process_claimed_search_job(
                    db,
                    claim,
                    repository=repository,
                    provider=provider,
                    cipher=cipher,
                    settings=settings,
                )
            elif claim.kind == "cleanup":
                process_claimed_cleanup_job(
                    db,
                    claim,
                    repository=repository,
                    settings=settings,
                )
            elif claim.kind == "purge":
                process_claimed_purge_job(
                    db,
                    claim,
                    repository=repository,
                    reference_root=settings.reference_root,
                )
            else:
                raise FacialJobError("Tipo de job facial indisponível.")
            completed = db.get(FacialJob, claim.id, populate_existing=True)
            return completed is not None and completed.status not in {"queued", "failed"}
        except (TenantContextError, HTTPException):
            repository.release_denied(db, claim)
            return
        except Exception as error:  # noqa: BLE001 - fronteira do processo sanitiza a falha
            db.rollback()
            repository.fail(
                db,
                claim,
                error,
                max_attempts=3,
                retry_delay_seconds=5,
            )
            return False

    def provider_failure(claim: ClaimedFacialJob, error: Exception) -> None:
        record_provider_failure(repository, claim, error)

    wake_source = Redis.from_url(
        os.getenv("FACIAL_REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=max(settings.queue_block_seconds + 5, 15),
    )
    worker = BlockingFacialWorker(
        settings=settings,
        job_class=active_class,
        session_factory=SessionLocal,
        wake_source=wake_source,
        provider_loader=provider_loader,
        provider_required=lambda claim: claim.kind in {
            "index", "search"
        },
        provider_failure=provider_failure,
        processor=processor,
        repository=repository,
    )
    # SIGTERM termina o ciclo em curso. Maintenance segue atendendo lotes
    # grandes enquanto ativo, mas também respeita o pedido cooperativo de saída.
    run_worker_until_stopped(
        worker=worker,
        active_class=active_class,
        settings=settings,
        cipher=cipher,
        session_factory=SessionLocal,
        stop_requested=_STOP_REQUESTED,
    )


if __name__ == "__main__":
    main()
