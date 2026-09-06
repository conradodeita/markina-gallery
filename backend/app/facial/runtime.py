"""Loop facial bloqueante com carregamento preguiçoso e descarga por ociosidade."""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.orm import Session

from app.facial.config import FacialSettings
from app.facial.jobs import ClaimedFacialJob, FacialJobRepository


class BlockingWakeSource(Protocol):
    def brpop(self, queue_name: str, timeout: int) -> object | None: ...


class BlockingFacialWorker:
    """Mantém no máximo um provider carregado e nunca varre galerias por conta própria."""

    def __init__(
        self,
        *,
        settings: FacialSettings,
        session_factory: Callable[[], Session],
        wake_source: BlockingWakeSource,
        provider_loader: Callable[[], object],
        processor: Callable[[Session, ClaimedFacialJob, object], None],
        provider_required: Callable[[ClaimedFacialJob], bool] | None = None,
        provider_failure: Callable[[ClaimedFacialJob, Exception], None] | None = None,
        repository: FacialJobRepository | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        provider_unloader: Callable[[object], None] | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._wake_source = wake_source
        self._provider_loader = provider_loader
        self._processor = processor
        self._provider_required = provider_required or (lambda _claim: True)
        self._provider_failure = provider_failure
        self._repository = repository or FacialJobRepository()
        self._clock = clock
        self._sleeper = sleeper
        self._provider_unloader = provider_unloader
        self._provider: object | None = None
        self._last_work_at: float | None = None
        self.processed_jobs = 0

    @property
    def model_loaded(self) -> bool:
        return self._provider is not None

    def run_cycle(self) -> bool:
        claim = self._claim()
        if claim is None:
            self._unload_if_idle()
            try:
                self._wake_source.brpop(
                    self._settings.queue_name,
                    timeout=self._settings.queue_block_seconds,
                )
            except (ConnectionError, TimeoutError, OSError):
                # Redis apenas reduz latência. Sem ele, o banco continua sendo a
                # fonte durável e a pausa impede polling agressivo/CPU ativa.
                self._sleeper(self._settings.queue_block_seconds)
            claim = self._claim()
        if claim is None:
            self._unload_if_idle()
            return False
        provider = self._provider
        if provider is None and self._provider_required(claim):
            try:
                provider = self._provider_loader()
            except Exception as error:
                if self._provider_failure is None:
                    raise
                self._provider_failure(claim, error)
                self.processed_jobs += 1
                self._last_work_at = self._clock()
                return True
            self._provider = provider
        with self._session_factory() as db:
            self._processor(db, claim, provider)
        self.processed_jobs += 1
        self._last_work_at = self._clock()
        if self.processed_jobs >= self._settings.max_jobs_per_process:
            self.unload()
        return True

    def run(self) -> None:
        while self.processed_jobs < self._settings.max_jobs_per_process:
            self.run_cycle()

    def unload(self) -> None:
        provider = self._provider
        if provider is None:
            return
        if self._provider_unloader is not None:
            self._provider_unloader(provider)
        self._provider = None
        gc.collect()

    def _claim(self) -> ClaimedFacialJob | None:
        with self._session_factory() as db:
            return self._repository.claim_next(
                db, lease_seconds=self._settings.job_lease_seconds
            )

    def _unload_if_idle(self) -> None:
        if (
            self._provider is not None
            and self._last_work_at is not None
            and self._clock() - self._last_work_at
            >= self._settings.model_idle_seconds
        ):
            self.unload()
