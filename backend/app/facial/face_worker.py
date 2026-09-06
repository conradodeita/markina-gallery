"""Entrypoint do worker facial opcional e isolado."""

from __future__ import annotations

import os
from pathlib import Path

from redis import Redis

from app.auth import SessionLocal
from app.facial.config import FacialConfigurationError, facial_settings_from_environment
from app.facial.crypto import FacialCipher
from app.facial.indexing import reconcile_automatic_gallery_policies
from app.facial.jobs import ClaimedFacialJob, FacialJobError, FacialJobRepository
from app.facial.model_assets import verify_models
from app.facial.notifications import process_next_search_notification
from app.facial.provider import OpenCvSFaceProvider
from app.facial.retention import process_claimed_cleanup_job
from app.facial.runtime import BlockingFacialWorker
from app.facial.search_worker import process_claimed_search_job
from app.facial.worker import process_claimed_index_job, process_claimed_purge_job
from app.messaging import WhatsAppConfigurationError, whatsapp_provider_from_environment


class _UnavailableMessenger:
    def connection_status(self):
        raise WhatsAppConfigurationError("Canal transacional indisponível.")

    def send_transactional(self, *_args, **_kwargs):
        raise WhatsAppConfigurationError("Canal transacional indisponível.")


def main() -> None:
    settings = facial_settings_from_environment()
    if not settings.enabled:
        raise FacialConfigurationError("O worker facial não pode iniciar com a flag desligada.")
    model_paths = verify_models(settings.manifest_path, settings.model_root)
    cipher = FacialCipher(
        active_key_id=settings.active_key_id,
        keys=settings.aead_keys,
    )
    repository = FacialJobRepository()
    derivatives_root = Path(
        os.getenv("MEDIA_DERIVATIVES_ROOT", "/var/lib/markina/derivatives")
    ).resolve()
    with SessionLocal() as db:
        reconcile_automatic_gallery_policies(
            db,
            derivatives_root=derivatives_root,
            settings=settings,
        )
        db.commit()

    def provider_loader() -> OpenCvSFaceProvider:
        return OpenCvSFaceProvider(model_paths["yunet"], model_paths["sface"])

    def processor(db, claim: ClaimedFacialJob, provider: object | None) -> None:
        try:
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
        except Exception as error:  # noqa: BLE001 - fronteira do processo sanitiza a falha
            db.rollback()
            repository.fail(
                db,
                claim,
                error,
                max_attempts=3,
                retry_delay_seconds=5,
            )

    def provider_failure(claim: ClaimedFacialJob, error: Exception) -> None:
        with SessionLocal() as db:
            repository.fail(
                db,
                claim,
                error,
                max_attempts=3,
                retry_delay_seconds=5,
            )

    wake_source = Redis.from_url(
        os.getenv("FACIAL_REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=max(settings.queue_block_seconds + 5, 15),
    )
    worker = BlockingFacialWorker(
        settings=settings,
        session_factory=SessionLocal,
        wake_source=wake_source,
        provider_loader=provider_loader,
        provider_required=lambda claim: claim.kind in {"index", "search"},
        provider_failure=provider_failure,
        processor=processor,
        repository=repository,
    )
    while worker.processed_jobs < settings.max_jobs_per_process:
        worker.run_cycle()
        try:
            messenger = whatsapp_provider_from_environment()
        except WhatsAppConfigurationError:
            messenger = _UnavailableMessenger()
        with SessionLocal() as db:
            process_next_search_notification(
                db,
                provider=messenger,
                cipher=cipher,
                settings=settings,
            )


if __name__ == "__main__":
    main()
