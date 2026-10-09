"""Aquisição completa inclui abertura de conexão; não é espera pura de fila."""
from time import perf_counter

from sqlalchemy.exc import TimeoutError
from sqlalchemy.pool import QueuePool

from app.system_monitor.telemetry import record


class MonitoredQueuePool(QueuePool):
    def _do_get(self):
        started = perf_counter()
        try:
            result = super()._do_get()
        except TimeoutError:
            record("pool.acquire", (perf_counter() - started) * 1000, 504)
            raise
        except Exception:
            record("pool.acquire", (perf_counter() - started) * 1000, 500)
            raise
        record("pool.acquire", (perf_counter() - started) * 1000)
        return result
