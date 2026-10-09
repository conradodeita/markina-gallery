"""Fronteira somente leitura para amostra de host coletada fora do container."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.system_monitor.config import Settings, utc


class HostSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    schema_version: Literal[1]
    source: Literal["linux_procfs", "oci_monitoring"]
    scope: Literal["host", "container"]
    collected_at: datetime
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_total_bytes: int | None = Field(default=None, ge=0)
    memory_available_bytes: int | None = Field(default=None, ge=0)
    disk_total_bytes: int | None = Field(default=None, ge=0)
    disk_free_bytes: int | None = Field(default=None, ge=0)
    network_in_bytes_per_second: float | None = Field(default=None, ge=0)
    network_out_bytes_per_second: float | None = Field(default=None, ge=0)
    io_read_bytes_per_second: float | None = Field(default=None, ge=0)
    io_write_bytes_per_second: float | None = Field(default=None, ge=0)
    io_busy_percent: float | None = Field(default=None, ge=0, le=100)


def read_host(instant, path: str | None = None):
    path = path if path is not None else os.getenv("SYSTEM_MONITOR_HOST_SNAPSHOT", "")
    if not path:
        return {"status": "not_collected", "reason": "host_source_not_configured", "data": None}
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(16385)
        if len(raw) > 16384:
            raise ValueError("size")
        sample = HostSnapshot.model_validate_json(raw)
        if sample.collected_at.tzinfo is None:
            raise ValueError("timezone")
        age = (instant - utc(sample.collected_at)).total_seconds()
        if age < -5:
            raise ValueError("future")
        for used, total in ((sample.memory_available_bytes, sample.memory_total_bytes),
                            (sample.disk_free_bytes, sample.disk_total_bytes)):
            if used is not None and total is not None and used > total:
                raise ValueError("bounds")
        return {"status": "stale" if age > Settings.read().stale_seconds else "observed", "reason": None,
                "age_seconds": max(0, age), "data": sample.model_dump(mode="json")}
    except PermissionError:
        reason = "permission_denied"
    except (OSError, ValueError, ValidationError, json.JSONDecodeError):
        reason = "host_source_unavailable"
    return {"status": "unavailable", "reason": reason, "data": None}
