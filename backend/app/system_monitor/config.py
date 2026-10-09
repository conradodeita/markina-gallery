"""Defaults propostos para ativação operacional explícita."""
import os
from dataclasses import dataclass
from datetime import UTC, datetime


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def setting(name: str, default: int, low: int, high: int) -> int:
    try:
        return min(high, max(low, int(os.getenv(f"SYSTEM_MONITOR_{name}", str(default)))))
    except ValueError:
        return default


def enabled() -> bool:
    return os.getenv("SYSTEM_MONITOR_ENABLED", "false").lower() == "true"


@dataclass(frozen=True)
class Settings:
    retention_days: int = 7
    active_seconds: int = 120
    recent_seconds: int = 1800
    stale_seconds: int = 180
    minimum_alert_seconds: int = 120
    error_percent: int = 5
    latency_ms: int = 2000
    queue_age_seconds: int = 300
    disk_free_percent: int = 10
    pool_percent: int = 90
    failure_count: int = 3
    cpu_percent: int = 90
    memory_free_percent: int = 10

    @classmethod
    def read(cls):
        return cls(
            retention_days=setting("RETENTION_DAYS", 7, 1, 30),
            active_seconds=setting("ACTIVE_SECONDS", 120, 60, 300),
            recent_seconds=setting("RECENT_SECONDS", 1800, 600, 3600),
            stale_seconds=setting("STALE_SECONDS", 180, 120, 600),
            minimum_alert_seconds=setting("ALERT_SECONDS", 120, 60, 900),
            error_percent=setting("ERROR_PERCENT", 5, 1, 100),
            latency_ms=setting("LATENCY_MS", 2000, 100, 60000),
            queue_age_seconds=setting("QUEUE_AGE_SECONDS", 300, 60, 3600),
            disk_free_percent=setting("DISK_FREE_PERCENT", 10, 1, 50),
            pool_percent=setting("POOL_PERCENT", 90, 50, 100),
            failure_count=setting("FAILURE_COUNT", 3, 1, 1000),
            cpu_percent=setting("CPU_PERCENT", 90, 50, 100),
            memory_free_percent=setting("MEMORY_FREE_PERCENT", 10, 1, 50),
        )
