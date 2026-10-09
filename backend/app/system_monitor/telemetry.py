"""Instrumentação sem IO no caminho da resposta; vocabulário e memória limitados."""
from bisect import bisect_left
from datetime import UTC, datetime
from functools import wraps
from threading import Lock, local
from time import perf_counter

from app.system_monitor.config import enabled

BOUNDS_MS = (25, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000, 60000)
OPERATIONS = frozenset({
    "http.auth", "http.upload", "http.preview", "http.gallery", "http.checkout",
    "http.other", "pool.acquire", "work.media", "work.preview_adjustment",
    "work.search", "work.index", "work.maintenance", "work.general",
})
WORKERS = frozenset({"general", "media", "preview_adjustment", "search", "index", "maintenance"})
_lock = Lock()
_buckets: dict[tuple, list] = {}
_workers: dict[str, tuple] = {}
_dropped = 0
_local = local()


def record(operation: str, milliseconds: float, status: int = 200) -> None:
    global _dropped
    if not enabled() or getattr(_local, "muted", False) or operation not in OPERATIONS:
        return
    minute = datetime.now(UTC).replace(second=0, microsecond=0)
    value = max(0.0, min(milliseconds, 86400000.0))
    key = (minute, operation, bisect_left(BOUNDS_MS, value))
    with _lock:
        if key not in _buckets and len(_buckets) >= 4096:
            _dropped += 1
            return
        row = _buckets.setdefault(key, [0, 0, 0, 0.0, 0])
        row[0] += 1
        row[1] += int(status >= 500)
        row[2] += int(400 <= status < 500)
        row[3] += value
        row[4] += int(operation == "pool.acquire" and status == 504)


def drain():
    global _buckets, _dropped
    with _lock:
        result = (_buckets, dict(_workers), _dropped)
        _buckets = {}
        _dropped = 0
    return result


def heartbeat(kind: str, progressed: bool) -> None:
    if not enabled() or kind not in WORKERS:
        return
    instant = datetime.now(UTC)
    with _lock:
        previous = _workers.get(kind)
        _workers[kind] = (instant, instant if progressed else (previous[1] if previous else None))


def observe_work(kind: str):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            started = perf_counter()
            try:
                result = function(*args, **kwargs)
            except Exception:
                record(f"work.{kind}", (perf_counter() - started) * 1000, 500)
                heartbeat(kind, False)
                raise
            heartbeat(kind, bool(result))
            if result:
                record(f"work.{kind}", (perf_counter() - started) * 1000)
            return result
        return call
    return decorate


def percentiles(histogram: dict[int, int]) -> dict:
    total = sum(histogram.values())
    result = {"samples": total, "method": "histogram_upper_bound_ms"}
    for label, fraction, minimum in (("p50", .5, 1), ("p95", .95, 20), ("p99", .99, 100)):
        result[label] = None
        if total < minimum:
            continue
        cumulative = 0
        for bucket, count in sorted(histogram.items()):
            cumulative += count
            if cumulative >= total * fraction:
                result[label] = BOUNDS_MS[bucket] if bucket < len(BOUNDS_MS) else None
                break
    return result


def operation_for(template: str) -> str:
    # Only registered route templates enter here, never request URLs/query strings.
    if template.startswith("/auth/"):
        return "http.auth"
    if "upload" in template or "import" in template:
        return "http.upload"
    if "preview" in template or "thumbnail" in template or "cover" in template:
        return "http.preview"
    if "checkout" in template or "cart" in template:
        return "http.checkout"
    if "galler" in template or "library" in template or "collection" in template:
        return "http.gallery"
    return "http.other"


class MonitorMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = perf_counter(), 500
        finished = False

        def finish():
            nonlocal finished
            if finished:
                return
            finished = True
            template = getattr(scope.get("route"), "path", "")
            if template.startswith(("/admin/system-monitor", "/auth/activity")):
                return
            record(operation_for(template), (perf_counter() - started) * 1000, status)

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                if scope.get("path", "").startswith(("/admin/system-monitor", "/auth/activity")):
                    message = dict(message)
                    message["headers"] = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"] + [(b"cache-control", b"private, no-store")]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                finish()

        try:
            await self.app(scope, receive, observed_send)
        except Exception:
            status = 500
            raise
        finally:
            finish()
