"""Worker exclusivo, sem portas e sem dependência do ciclo HTTP ou da fila facial."""

import logging
import time

from app.auth import SessionLocal
from app.maintenance_control import MaintenanceBusy, MaintenanceUnavailable, shared_operation
from app.preview_adjustment.service import process_one

logger = logging.getLogger(__name__)


def main():
    from app.system_monitor.runtime import start_monitor
    start_monitor()
    logging.basicConfig(level=logging.INFO)
    logger.info("preview_adjustment.worker_ready")
    while True:
        try:
            with shared_operation(SessionLocal.kw["bind"], service="preview-adjustment-worker"):
                worked = process_one(SessionLocal)
        except MaintenanceBusy:
            worked = False
        except MaintenanceUnavailable:
            logger.warning("preview_adjustment.maintenance_control_unavailable")
            worked = False
        except Exception:  # noqa: BLE001 -- Recuperação do loop após falha de infraestrutura.
            logger.warning("preview_adjustment.worker_unavailable")
            worked = False
        if not worked:
            time.sleep(5)


if __name__ == "__main__":
    main()
