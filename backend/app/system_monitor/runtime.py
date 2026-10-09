"""Coleta opt-in em background; nenhum thread é iniciado no import."""
import logging
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

from sqlalchemy import text

from app.system_monitor import telemetry
from app.system_monitor.config import Settings, enabled
from app.system_monitor.host import read_host
from app.system_monitor.incidents import evaluate, signals_for
from app.system_monitor.models import MonitorSample, MonitorWorker
from app.system_monitor.sources import collect_sections
from app.system_monitor.store import bounded, insert, operation_summary, prune, save_buckets

logger = logging.getLogger(__name__)
_instances = {}
_stopped = Event()
_thread = None
_quality = {"lost_observations": 0, "collection_failures": 0}


def flush(factory):
    buckets, workers, dropped = telemetry.drain()
    _quality["lost_observations"] += dropped
    try:
        telemetry._local.muted = True
        with factory() as db:
            bounded(db)
            save_buckets(db, buckets)
            for kind, (seen, progress) in workers.items():
                instance = _instances.setdefault(kind, uuid4())
                statement = insert(db, MonitorWorker).values(
                    instance=instance, kind=kind, last_seen=seen, last_progress=progress,
                )
                db.execute(statement.on_conflict_do_update(index_elements=["instance"],
                    set_={"last_seen": seen, "last_progress": progress}))
            db.commit()
        return True
    except Exception:  # noqa: BLE001 -- Telemetria não pode interromper a aplicação.
        _quality["lost_observations"] += sum(row[0] for row in buckets.values())
        logger.warning("system_monitor.persistence_unavailable")
        return False
    finally:
        telemetry._local.muted = False


def collect(factory, instant=None):
    from app.capacity_observability.collector import _collect_once

    instant = instant or datetime.now(UTC)
    minute = instant.replace(second=0, microsecond=0)
    settings = Settings.read()
    try:
        telemetry._local.muted = True
        with factory() as db:
            bounded(db)
            if db.bind.dialect.name == "postgresql" and not db.scalar(
                text("SELECT pg_try_advisory_xact_lock(73419072)")
            ):
                return
            if db.get(MonitorSample, minute):
                return
            payload = {"collected_at": instant.isoformat(), "capacity": None,
                       "host": read_host(instant), "quality": dict(_quality)}
            try:
                payload["capacity"] = _collect_once().model_dump(mode="json")
            except Exception:  # noqa: BLE001 -- Fonte opcional isolada.
                payload["capacity_reason"] = "source_unavailable"
            payload.update(collect_sections(factory, instant))
            operations = operation_summary(db, minute - timedelta(minutes=5), minute)
            evaluate(db, signals_for(payload, operations, settings), instant, settings)
            db.add(MonitorSample(minute=minute, payload=payload))
            prune(db, instant, settings)
            db.commit()
    except Exception:  # noqa: BLE001 -- O próximo ciclo recupera a coleta sem afetar negócio.
        _quality["collection_failures"] += 1
        logger.warning("system_monitor.collection_unavailable")
    finally:
        telemetry._local.muted = False


def start_monitor(*, collect_global=False):
    global _thread
    if not enabled() or (_thread and _thread.is_alive()):
        return
    from app.auth import SessionLocal

    _stopped.clear()

    def run():
        iteration = 0
        while not _stopped.wait(30):
            flush(SessionLocal)
            if collect_global and iteration % 2 == 0:
                collect(SessionLocal)
            iteration += 1
    _thread = Thread(target=run, name="system-monitor", daemon=True)
    _thread.start()


def stop_monitor():
    _stopped.set()
    if _thread:
        _thread.join(timeout=2)
