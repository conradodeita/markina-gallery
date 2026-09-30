"""Contratos fechados do diagnóstico administrativo de capacidade."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Evidence(StrEnum):
    OBSERVED = "observed"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class Scope(StrEnum):
    RESPONDING_API_PROCESS = "responding_api_process"
    APPLICATION_DATABASE = "application_database"
    POSTGRESQL_SERVER = "postgresql_server"


class Unit(StrEnum):
    CONNECTIONS = "connections"
    JOBS = "jobs"
    SECONDS = "seconds"


class Source(StrEnum):
    SQLALCHEMY_POOL = "sqlalchemy_pool"
    PG_STAT_ACTIVITY = "pg_stat_activity"
    PG_SETTINGS = "pg_settings"
    MEDIA_JOB = "media_job"
    PREVIEW_ADJUSTMENT = "preview_adjustment"
    FACIAL_JOB = "facial_job"
    NONE = "none"


class UnavailableReason(StrEnum):
    EMPTY_QUEUE = "empty_queue"
    UNSUPPORTED_BACKEND = "unsupported_backend"
    UNSUPPORTED_POOL = "unsupported_pool"
    PERMISSION_DENIED = "permission_denied"
    SOURCE_UNAVAILABLE = "source_unavailable"
    QUERY_TIMEOUT = "query_timeout"
    COLLECTION_BUSY = "collection_busy"
    INCONSISTENT_TIMESTAMP = "inconsistent_timestamp"
    PROCESS_INVENTORY_MISSING = "process_inventory_missing"
    EXTERNAL_CONSUMERS_UNKNOWN = "external_consumers_unknown"
    OPERATIONAL_RESERVE_UNAPPROVED = "operational_reserve_unapproved"
    FIELD_UNAVAILABLE = "field_unavailable"


class MetricValue(ClosedModel):
    value: int | float | None
    unit: Unit
    evidence: Evidence
    scope: Scope
    source: Source
    collected_at: datetime
    reason: UnavailableReason | None = None

    @model_validator(mode="after")
    def validate_value(self) -> MetricValue:
        if self.collected_at.tzinfo is None or self.collected_at.utcoffset() is None:
            raise ValueError("collected_at precisa incluir fuso horário.")
        if self.value is None:
            if self.evidence is not Evidence.UNAVAILABLE or self.reason is None:
                raise ValueError("Valor nulo exige evidência indisponível e motivo.")
            return self
        if self.evidence is Evidence.UNAVAILABLE or self.reason is not None:
            raise ValueError("Valor disponível não pode ter motivo de indisponibilidade.")
        if isinstance(self.value, bool) or self.value < 0:
            raise ValueError("Métricas precisam ser não negativas e numéricas.")
        if self.unit is Unit.SECONDS and not isinstance(self.value, (int, float)):
            raise ValueError("Duração precisa ser numérica.")
        if self.unit in {Unit.CONNECTIONS, Unit.JOBS} and not isinstance(self.value, int):
            raise ValueError("Contagens precisam ser inteiras.")
        return self


class ConnectionStates(ClosedModel):
    active: MetricValue
    idle: MetricValue
    idle_in_transaction: MetricValue
    other: MetricValue
    unknown: MetricValue


class DatabaseSnapshot(ClosedModel):
    database_client_connections: ConnectionStates
    server_client_connections: ConnectionStates
    max_connections: MetricValue
    superuser_reserved_connections: MetricValue
    reserved_connections: MetricValue


class PoolSnapshot(ClosedModel):
    pool_class: Literal["queue_pool", "null_pool", "other"]
    finite_limit: bool
    unbounded_overflow: bool
    base_size: MetricValue
    max_overflow: MetricValue
    potential_max: MetricValue
    acquisition_timeout_seconds: MetricValue
    checked_in: MetricValue
    checked_out: MetricValue
    open_connections_estimate: MetricValue
    wait_seconds: MetricValue
    timeout_count: MetricValue


QueueClass = Literal["media", "preview_adjustment", "search", "index", "maintenance"]


class QueueSnapshot(ClosedModel):
    queue_class: QueueClass
    queued_total: MetricValue
    scheduled_total: MetricValue
    claim_candidates_total: MetricValue
    processing_total: MetricValue
    blocked_dependency_total: MetricValue
    reclaimable_total: MetricValue
    oldest_record_age_seconds: MetricValue
    oldest_due_age_seconds: MetricValue
    oldest_updated_age_seconds: MetricValue
    wait_semantics: Literal["created_age_estimate", "updated_age_estimate", "available_at_age_estimate", "exact_wait_unavailable"]


class ConnectionBudgetSnapshot(ClosedModel):
    status: Literal["unavailable"]
    potential_connections: MetricValue
    budget_headroom: MetricValue
    limitations: list[UnavailableReason]


class CapacitySnapshot(ClosedModel):
    schema_version: Literal[1] = 1
    collection_started_at: datetime
    collection_finished_at: datetime
    cached: bool
    database: DatabaseSnapshot
    pool: PoolSnapshot
    queues: list[QueueSnapshot]
    connection_budget: ConnectionBudgetSnapshot
    coverage: list[QueueClass]
    limitations: list[UnavailableReason]

    @model_validator(mode="after")
    def validate_window(self) -> CapacitySnapshot:
        if self.collection_started_at.tzinfo is None or self.collection_started_at.utcoffset() is None:
            raise ValueError("collection_started_at precisa incluir fuso horário.")
        if self.collection_finished_at.tzinfo is None or self.collection_finished_at.utcoffset() is None:
            raise ValueError("collection_finished_at precisa incluir fuso horário.")
        if self.collection_finished_at < self.collection_started_at:
            raise ValueError("Janela de coleta inconsistente.")
        if len(self.queues) != len({item.queue_class for item in self.queues}):
            raise ValueError("Classes de fila duplicadas.")
        return self


def unavailable(
    *,
    unit: Unit,
    scope: Scope,
    collected_at: datetime,
    reason: UnavailableReason,
) -> MetricValue:
    return MetricValue(
        value=None,
        unit=unit,
        evidence=Evidence.UNAVAILABLE,
        scope=scope,
        source=Source.NONE,
        collected_at=collected_at.astimezone(UTC),
        reason=reason,
    )
