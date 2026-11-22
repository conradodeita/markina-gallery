"""Planejador global; remoção explícita somente de cópia local redundante de ensaio."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from . import filesystem as fs
from .archive import (
    ArchiveReceipt,
    BackupContext,
    _key,
    _local_runtime,
    open_archive,
    verify_ciphertext,
)
from .catalog import BackupCatalog
from .payload import open_payload
from .storage import LocalBackupStore


@dataclass(frozen=True)
class GlobalBackupPolicy:
    daily: int = 7
    weekly: int = 4
    monthly: int = 3
    rpo_hours: int = 24
    rto_hours: int = 8

    def __post_init__(self) -> None:
        if any(type(value) is not int or not 1 <= value <= 3650
               for value in (self.daily, self.weekly, self.monthly, self.rpo_hours, self.rto_hours)):
            raise fs.BackupStorageError("unsafe")


@dataclass(frozen=True)
class RetentionPlan:
    retained: frozenset[UUID]
    expired: frozenset[UUID]
    fingerprint: str
    as_of: datetime
    policy: GlobalBackupPolicy
    points: tuple[BackupContext, ...] = field(repr=False)
    restored_ids: frozenset[UUID] = field(repr=False)


def plan_retention(points: tuple[BackupContext, ...], *, restored_ids: frozenset[UUID],
                   as_of: datetime, policy: GlobalBackupPolicy | None = None) -> RetentionPlan:
    _local_runtime()
    policy = policy or GlobalBackupPolicy()
    if (not isinstance(policy, GlobalBackupPolicy) or not isinstance(as_of, datetime)
            or as_of.utcoffset() != timedelta(0) or len(points) > 100000
            or any(not isinstance(point, BackupContext) or point.created_at > as_of for point in points)):
        raise fs.BackupStorageError("unsafe")
    ordered = tuple(sorted(points, key=lambda point: (point.created_at, str(point.backup_id)), reverse=True))
    identifiers = {point.backup_id for point in ordered}
    if (len(identifiers) != len(ordered) or not restored_ids <= identifiers
            or len({(point.instance_id, point.environment) for point in ordered}) > 1):
        raise fs.BackupStorageError("unsafe")
    keep = set()
    for limit, bucket in (
        (policy.daily, lambda point: point.created_at.date()),
        (policy.weekly, lambda point: point.created_at.isocalendar()[:2]),
        (policy.monthly, lambda point: (point.created_at.year, point.created_at.month)),
    ):
        seen = set()
        for point in ordered:
            group = bucket(point)
            if group not in seen:
                if len(seen) >= limit:
                    break
                seen.add(group)
                keep.add(point.backup_id)
    latest_recoverable = next((point for point in ordered if point.backup_id in restored_ids), None)
    if latest_recoverable is not None:
        keep.add(latest_recoverable.backup_id)
    encoded = json.dumps({
        "points": [json.loads(point.header()) for point in ordered],
        "restored_ids": sorted(str(value) for value in restored_ids),
        "as_of": as_of.isoformat(),
        "policy": {"daily": policy.daily, "weekly": policy.weekly, "monthly": policy.monthly,
                   "rpo_hours": policy.rpo_hours, "rto_hours": policy.rto_hours},
        "retained": sorted(str(value) for value in keep),
    }, sort_keys=True, separators=(",", ":")).encode()
    return RetentionPlan(frozenset(keep), frozenset(identifiers - keep),
                         hashlib.sha256(encoded).hexdigest(), as_of, policy, ordered,
                         frozenset(restored_ids))


def monthly_restore_due(last_restore: datetime | None, *, now: datetime) -> bool:
    if (not isinstance(now, datetime) or now.utcoffset() != timedelta(0)
            or (last_restore is not None and (not isinstance(last_restore, datetime)
                or last_restore.utcoffset() != timedelta(0) or last_restore > now))):
        raise fs.BackupStorageError("unsafe")
    return last_restore is None or (last_restore.year, last_restore.month) != (now.year, now.month)


def _restore_proven(events: list[dict], context: BackupContext, receipt: ArchiveReceipt,
                    destination_id: UUID, as_of: datetime) -> bool:
    verified = False
    restored = False
    for event in events:
        payload = event["payload"]
        data = payload["data"]
        if data.get("destination_id") != str(destination_id) or data.get("artifact_sha256") != receipt.sha256:
            continue
        if payload["event"] == "verified":
            verified = True
        if payload["event"] == "restore_verified" and data.get("schema_revision") == context.schema_revision:
            try:
                target = UUID(data["restore_target_id"])
                at = datetime.fromisoformat(payload["at"])
                restored = target != context.instance_id and at.utcoffset() == timedelta(0) and at <= as_of
            except (ValueError, TypeError, KeyError):
                raise fs.BackupStorageError("catalog") from None
    return verified and restored


def remove_redundant_local_copy(*, context: BackupContext, artifact: ArchiveReceipt,
                                plan: RetentionPlan, candidate: LocalBackupStore,
                                survivor: LocalBackupStore, catalog: BackupCatalog,
                                key: bytes, confirmation: str) -> None:
    _local_runtime()
    _key(key)
    if (not isinstance(plan, RetentionPlan) or not isinstance(context, BackupContext)
            or not isinstance(artifact, ArchiveReceipt) or artifact.backup_id != context.backup_id
            or context.backup_id not in plan.expired or context not in plan.points
            or confirmation != f"DELETE_LOCAL_BACKUP_COPY:{context.backup_id}:{candidate.destination_id}"
            or candidate.destination_id == survivor.destination_id
            or candidate.failure_domain == survivor.failure_domain
            or plan_retention(plan.points, restored_ids=plan.restored_ids, as_of=plan.as_of,
                              policy=plan.policy) != plan):
        raise fs.BackupStorageError("unsafe")
    events = catalog.events(context.backup_id)
    if not _restore_proven(events, context, artifact, survivor.destination_id, plan.as_of):
        raise fs.BackupStorageError("unsafe")
    name = str(context.backup_id) + ".pypb"
    stores = sorted((candidate, survivor), key=lambda store: str(store.destination_id))
    with ExitStack() as stack:
        directories = {store.destination_id: stack.enter_context(fs.directory(store.root)) for store in stores}
        identities = [(os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in directories.values()]
        if len(set(identities)) != 2:
            raise fs.BackupStorageError("unsafe")
        for store in stores:
            stack.enter_context(fs.lock(directories[store.destination_id], str(context.backup_id) + ".lock"))
        snapshots = {}
        for store in stores:
            fd = fs.open_file(directories[store.destination_id], name, os.O_RDONLY)
            stream = stack.enter_context(os.fdopen(fd, "rb"))
            verify_ciphertext(stream, artifact)
            with open_archive(stream, key=key, expected=context) as clear, open_payload(clear.stream, expected=context):
                pass
            info = os.fstat(fd)
            snapshots[store.destination_id] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        for store in stores:
            current = os.stat(name, dir_fd=directories[store.destination_id], follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != snapshots[store.destination_id]:
                raise fs.BackupStorageError("conflict")
        fields = {"destination_id": candidate.destination_id, "survivor_destination_id": survivor.destination_id,
                  "artifact_sha256": artifact.sha256, "size_bytes": artifact.size_bytes}
        catalog.append(context.backup_id, "deletion_planned", at=plan.as_of, **fields)
        os.unlink(name, dir_fd=directories[candidate.destination_id])
        os.fsync(directories[candidate.destination_id])
        catalog.append(context.backup_id, "deleted", at=plan.as_of, **fields)
