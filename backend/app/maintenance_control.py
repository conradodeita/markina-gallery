"""Barreira cooperativa de manutenção para ingressos HTTP e ciclos Python.

O modo é opt-in. Quando ativo, Redis registra operações admitidas antes de
efeitos e mantém recibos sem TTL até ACK explícito. Redis/SQLite local não
comprovam homologação operacional; o controle de produção requer PostgreSQL e
Redis, além de todos os processos participantes reconhecendo esta barreira.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import Engine

MAINTENANCE_KEY = "markina:maintenance:v1:mode"
ACTIVE_KEY = "markina:maintenance:v1:active"
MAINTENANCE_ENABLED_ENV = "CONTROLLED_MAINTENANCE_ENABLED"

_ENTER = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[2], ARGV[1], ARGV[2])
return 1
"""
_ENTER_CRITICAL = """
redis.call('HSET', KEYS[2], ARGV[1], ARGV[2])
return 1
"""
_LEAVE = "return redis.call('HDEL', KEYS[1], ARGV[1])"
_BEGIN_MAINTENANCE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('SET', KEYS[1], ARGV[1] .. ':active')
return 1
"""
_FINISH_MAINTENANCE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] .. ':active' then return 0 end
if redis.call('HLEN', KEYS[2]) ~= 0 then return -1 end
return redis.call('DEL', KEYS[1])
"""


class MaintenanceBusy(RuntimeError):
    """A manutenção está ativa, divergente ou ainda há operações sem ACK."""


class MaintenanceUnavailable(RuntimeError):
    """O estado da barreira não pôde ser verificado com segurança."""


def maintenance_control_enabled() -> bool:
    """A barreira é opt-in para preservar o comportamento normal por padrão."""
    value = os.getenv(MAINTENANCE_ENABLED_ENV, "false").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off", ""}:
        return False
    raise MaintenanceUnavailable("flag de manutenção inválida")


def redis_client() -> Redis:
    url = os.getenv("FACIAL_REDIS_URL") or os.getenv("REDIS_URL")
    if not url:
        raise MaintenanceUnavailable("URL Redis da barreira ausente")
    client = None
    try:
        client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
        client.ping()
    except (RedisError, ValueError, OSError) as error:
        if client is not None:
            client.close()
        raise MaintenanceUnavailable("Redis da barreira indisponível") from error
    return client


@dataclass
class ActiveOperation:
    client: Redis | None
    token: str | None

    def release(self) -> None:
        if self.client is None or self.token is None:
            return
        try:
            removed = self.client.eval(_LEAVE, 1, ACTIVE_KEY, self.token)
            if removed != 1:
                raise MaintenanceUnavailable("recibo ativo ausente; conclusão não confirmada")
        except (RedisError, ValueError, OSError) as error:
            raise MaintenanceUnavailable("não foi possível confirmar a conclusão") from error
        finally:
            self.client.close()
            self.client = None

    def abandon(self) -> None:
        """Fecha sem ACK; o recibo persistente exige recuperação explícita."""
        if self.client is not None:
            self.client.close()
            self.client = None


def _enter(engine: Engine, *, service: str, critical: bool = False) -> ActiveOperation | None:
    if not maintenance_control_enabled():
        return ActiveOperation(None, None)
    if engine.dialect.name == "sqlite":
        return ActiveOperation(None, None)
    if engine.dialect.name != "postgresql":
        raise MaintenanceUnavailable("dialeto sem suporte à barreira cooperativa")
    client = redis_client()
    token = f"{service}:{os.getpid()}:{uuid4().hex}"
    try:
        script = _ENTER_CRITICAL if critical else _ENTER
        entered = client.eval(script, 2, MAINTENANCE_KEY, ACTIVE_KEY, token, service)
        if entered != 1:
            client.close()
            return None
        return ActiveOperation(client, token)
    except (RedisError, ValueError, OSError) as error:
        client.close()
        raise MaintenanceUnavailable("não foi possível registrar operação ativa") from error


def try_enter(engine: Engine, *, service: str) -> ActiveOperation | None:
    """Registra antes do handler ou do início do ciclo de worker."""
    return _enter(engine, service=service)


def try_enter_critical(engine: Engine, *, service: str) -> ActiveOperation | None:
    """Registra um callback permitido durante manutenção, sem bypass do recibo."""
    return _enter(engine, service=service, critical=True)


@contextmanager
def shared_operation(engine: Engine, *, service: str = "python") -> Iterator[None]:
    active = try_enter(engine, service=service)
    if active is None:
        raise MaintenanceBusy("manutenção em andamento")
    try:
        yield
    except BaseException:
        active.abandon()
        raise
    else:
        active.release()


def begin_maintenance(operation_id: str, *, client: Redis | None = None) -> Redis:
    """Fecha novas entradas comuns e mantém callbacks críticos rastreados."""
    if not maintenance_control_enabled():
        raise MaintenanceUnavailable("controle de manutenção desativado neste processo")
    if not operation_id or len(operation_id) > 128 or ":active" in operation_id:
        raise ValueError("identidade de manutenção inválida")
    owned = client is None
    redis = client or redis_client()
    try:
        started = redis.eval(_BEGIN_MAINTENANCE, 1, MAINTENANCE_KEY, operation_id)
    except (RedisError, ValueError, OSError) as error:
        if owned:
            redis.close()
        raise MaintenanceUnavailable("não foi possível ativar manutenção") from error
    if started != 1:
        if owned:
            redis.close()
        raise MaintenanceBusy("já existe uma manutenção ativa")
    return redis


def wait_for_drain(client: Redis, *, timeout_seconds: float, poll_seconds: float = 0.1) -> bool:
    """Retorna somente após ACK de todas as operações; timeout não abre a barreira."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            if client.hlen(ACTIVE_KEY) == 0:
                return True
        except (RedisError, ValueError, OSError) as error:
            raise MaintenanceUnavailable("estado de drenagem indisponível") from error
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(poll_seconds, remaining))


def finish_maintenance(operation_id: str, *, client: Redis) -> None:
    """Reabre entradas somente com dono correto e nenhum recibo ativo."""
    if not maintenance_control_enabled():
        raise MaintenanceUnavailable("controle de manutenção desativado neste processo")
    try:
        result = client.eval(
            _FINISH_MAINTENANCE, 2, MAINTENANCE_KEY, ACTIVE_KEY, operation_id
        )
    except (RedisError, ValueError, OSError) as error:
        raise MaintenanceUnavailable("não foi possível encerrar manutenção") from error
    if result != 1:
        raise MaintenanceBusy("manutenção divergente ou existem operações ativas")
