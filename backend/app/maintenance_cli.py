"""CLI explícita para coordenar manutenção no Redis e no estado persistido."""

from __future__ import annotations

import argparse
import json
import sys

from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import (
    EmailDelivery,
    FacialJob,
    FacialSearchNotificationOutbox,
    GalleryLifecycleOperation,
    GalleryMembershipNotificationOutbox,
    GalleryReopeningNotificationOutbox,
    MediaJob,
    NotificationDelivery,
    PaymentNotificationOutbox,
    PhotoAnalysis,
    PreviewAdjustment,
    RawDevelopmentJob,
    SessionLocal,
    WhatsAppDelivery,
)
from app.maintenance_control import (
    ACTIVE_KEY,
    MAINTENANCE_KEY,
    MaintenanceBusy,
    MaintenanceUnavailable,
    begin_maintenance,
    finish_maintenance,
    redis_client,
    wait_for_drain,
)


def _persisted_active_queues() -> dict[str, int]:
    active_checks = (
        ("facial", FacialJob, FacialJob.status == "processing"),
        ("facial_notifications", FacialSearchNotificationOutbox,
         FacialSearchNotificationOutbox.status == "processing"),
        ("media", MediaJob, MediaJob.status == "processing"),
        ("preview", PreviewAdjustment, PreviewAdjustment.status == "processing"),
        ("raw", RawDevelopmentJob, RawDevelopmentJob.status.in_(("receiving", "processing"))),
        ("highres_upload", PhotoAnalysis, PhotoAnalysis.state == "receiving"),
        ("lifecycle", GalleryLifecycleOperation,
         GalleryLifecycleOperation.status.in_(("preparing_history", "removing_storage", "removing_records"))),
        ("email", EmailDelivery, EmailDelivery.status == "processing"),
        ("whatsapp", WhatsAppDelivery, WhatsAppDelivery.status == "processing"),
        ("notifications", NotificationDelivery, NotificationDelivery.status == "processing"),
        ("payment_outbox", PaymentNotificationOutbox, PaymentNotificationOutbox.status == "processing"),
        ("reopening_outbox", GalleryReopeningNotificationOutbox,
         GalleryReopeningNotificationOutbox.status == "processing"),
        ("membership_outbox", GalleryMembershipNotificationOutbox,
         GalleryMembershipNotificationOutbox.external_status == "processing"),
    )
    counts: dict[str, int] = {}
    with SessionLocal() as db:
        for name, model, condition in active_checks:
            count = db.scalar(select(func.count()).select_from(model).where(condition)) or 0
            if count:
                counts[name] = count
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("maintenance-begin", "wait", "maintenance-finish", "status", "verify-state"),
    )
    parser.add_argument("--operation")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    client = None
    try:
        if args.command == "maintenance-begin":
            if not args.operation:
                raise ValueError("operation required")
            client = begin_maintenance(args.operation)
            print(json.dumps({"state": "maintenance_active", "operation": args.operation}))
        elif args.command == "wait":
            if not args.operation:
                raise ValueError("operation required")
            client = redis_client()
            if client.get(MAINTENANCE_KEY) != f"{args.operation}:active":
                raise MaintenanceBusy("maintenance identity differs")
            drained = wait_for_drain(client, timeout_seconds=args.timeout)
            active = client.hgetall(ACTIVE_KEY)
            counts: dict[str, int] = {}
            for service in active.values():
                counts[service] = counts.get(service, 0) + 1
            print(json.dumps({"state": "drained" if drained else "timeout", "active_by_service": counts}, sort_keys=True))
            return 0 if drained else 2
        elif args.command == "maintenance-finish":
            if not args.operation:
                raise ValueError("operation required")
            client = redis_client()
            if (
                client.get(MAINTENANCE_KEY) != f"{args.operation}:active"
                or client.hlen(ACTIVE_KEY) != 0
            ):
                raise MaintenanceBusy("manutenção não drenada ou identidade divergente")
            try:
                persisted = _persisted_active_queues()
            except SQLAlchemyError as error:
                raise MaintenanceUnavailable("estado persistido não verificável") from error
            if persisted:
                print(json.dumps({"state": "persisted_work_active", "queues": persisted}, sort_keys=True))
                return 2
            finish_maintenance(args.operation, client=client)
            print(json.dumps({"state": "maintenance_closed", "operation": args.operation}))
        elif args.command == "status":
            client = redis_client()
            active = client.hgetall(ACTIVE_KEY)
            counts: dict[str, int] = {}
            for service in active.values():
                counts[service] = counts.get(service, 0) + 1
            print(json.dumps({"maintenance": client.get(MAINTENANCE_KEY), "active_by_service": counts}, sort_keys=True))
        else:
            if not args.operation:
                raise ValueError("operation required")
            state = redis_client()
            try:
                if (
                    state.get(MAINTENANCE_KEY) != f"{args.operation}:active"
                    or state.hlen(ACTIVE_KEY) != 0
                ):
                    raise MaintenanceBusy("barreira não está drenada ou a identidade diverge")
            finally:
                state.close()
            try:
                counts = _persisted_active_queues()
            except SQLAlchemyError:
                print("maintenance: estado persistido não verificável", file=sys.stderr)
                return 1
            print(json.dumps({"persisted_active_by_queue": counts}, sort_keys=True))
            return 2 if counts else 0
        return 0
    except (MaintenanceBusy, MaintenanceUnavailable, RedisError, ValueError) as error:
        print("maintenance: " + str(error), file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
