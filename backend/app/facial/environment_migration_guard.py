"""Guarda fail-closed de preflight para uma futura operação biométrica."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.facial.crypto import FacialCryptoContextPair

_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_REQUIRED_CONSUMERS = frozenset(
    {"api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker"}
)
_GUARD_FAILURES = frozenset(
    {
        "approval_missing",
        "app_env_changed",
        "backup_unverified",
        "consumers_not_paused",
        "fingerprint_mismatch",
        "inventory_unverified",
        "environment_context_invalid",
        "jobs_active",
        "plan_unverified",
        "production_gates_open",
        "record_count_mismatch",
        "invalid_preflight",
        "unsupported_storage_present",
    }
)


class FacialWriteGuardError(RuntimeError):
    """Falha constante sem conteúdo do inventário ou do plano operacional."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = (
            reason_code if reason_code in _GUARD_FAILURES else "invalid_preflight"
        )
        super().__init__("Preflight de transição biométrica bloqueado.")


@dataclass(frozen=True, slots=True, repr=False)
class BiometricWritePreflight:
    contexts: FacialCryptoContextPair = field(repr=False)
    current_inventory_fingerprint: str
    approved_inventory_fingerprint: str
    backup_inventory_fingerprint: str
    inventory_current: bool
    backup_authenticated_and_reopened: bool
    backup_record_count: int
    expected_record_count: int
    operation_plan_fingerprint: str
    approved_plan_fingerprint: str
    plan_reviewed: bool
    approval_confirmation: str
    paused_consumers: frozenset[str]
    active_job_count: int
    facial_processing_enabled: bool
    live_payments_allowed: bool
    app_environment_before: str
    app_environment_after: str
    reference_file_count: int | None = None
    reference_locator_count: int | None = None
    unknown_reference_entry_count: int | None = None
    nonempty_notification_count: int | None = None

    def __repr__(self) -> str:
        return "BiometricWritePreflight(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class BiometricWritePermit:
    inventory_fingerprint: str = field(repr=False)
    operation_plan_fingerprint: str = field(repr=False)
    source_environment: str = field(repr=False)
    target_environment: str = field(repr=False)

    def __repr__(self) -> str:
        return "BiometricWritePermit(<redacted>)"


def authorize_biometric_migration_write(
    preflight: BiometricWritePreflight,
) -> BiometricWritePermit:
    """Cria uma permissão em memória somente após validar todos os gates."""

    if not isinstance(preflight, BiometricWritePreflight) or not isinstance(
        preflight.contexts, FacialCryptoContextPair
    ):
        raise FacialWriteGuardError("invalid_preflight")
    if (
        preflight.contexts.destination.environment != "production"
        or preflight.contexts.source.environment
        not in {"development", "homolog", "homologation", "staging", "test"}
    ):
        raise FacialWriteGuardError("environment_context_invalid")
    fingerprints = (
        preflight.current_inventory_fingerprint,
        preflight.approved_inventory_fingerprint,
        preflight.backup_inventory_fingerprint,
        preflight.operation_plan_fingerprint,
        preflight.approved_plan_fingerprint,
    )
    if any(not isinstance(item, str) or not _FINGERPRINT.fullmatch(item) for item in fingerprints):
        raise FacialWriteGuardError("invalid_preflight")
    if preflight.inventory_current is not True:
        raise FacialWriteGuardError("inventory_unverified")
    if not (
        preflight.current_inventory_fingerprint
        == preflight.approved_inventory_fingerprint
        == preflight.backup_inventory_fingerprint
    ):
        raise FacialWriteGuardError("fingerprint_mismatch")
    if preflight.backup_authenticated_and_reopened is not True:
        raise FacialWriteGuardError("backup_unverified")
    if (
        type(preflight.backup_record_count) is not int
        or type(preflight.expected_record_count) is not int
        or preflight.backup_record_count < 0
        or preflight.expected_record_count < 0
        or preflight.backup_record_count != preflight.expected_record_count
    ):
        raise FacialWriteGuardError("record_count_mismatch")
    if (
        preflight.operation_plan_fingerprint != preflight.approved_plan_fingerprint
        or preflight.plan_reviewed is not True
    ):
        raise FacialWriteGuardError("plan_unverified")
    expected_confirmation = (
        "APPLY_BIOMETRIC_CONTEXT:"
        f"{preflight.current_inventory_fingerprint}:"
        f"{preflight.operation_plan_fingerprint}"
    )
    if (
        not isinstance(preflight.approval_confirmation, str)
        or preflight.approval_confirmation != expected_confirmation
    ):
        raise FacialWriteGuardError("approval_missing")
    if (
        not isinstance(preflight.paused_consumers, frozenset)
        or preflight.paused_consumers != _REQUIRED_CONSUMERS
    ):
        raise FacialWriteGuardError("consumers_not_paused")
    if type(preflight.active_job_count) is not int or preflight.active_job_count != 0:
        raise FacialWriteGuardError("jobs_active")
    if any(type(count) is not int or count != 0 for count in (
        preflight.reference_file_count, preflight.reference_locator_count,
        preflight.unknown_reference_entry_count, preflight.nonempty_notification_count,
    )):
        raise FacialWriteGuardError("unsupported_storage_present")
    if (
        type(preflight.facial_processing_enabled) is not bool
        or preflight.facial_processing_enabled
        or type(preflight.live_payments_allowed) is not bool
        or preflight.live_payments_allowed
    ):
        raise FacialWriteGuardError("production_gates_open")
    if (
        not isinstance(preflight.app_environment_before, str)
        or not preflight.app_environment_before
        or preflight.app_environment_before != preflight.app_environment_after
    ):
        raise FacialWriteGuardError("app_env_changed")

    return BiometricWritePermit(
        inventory_fingerprint=preflight.current_inventory_fingerprint,
        operation_plan_fingerprint=preflight.operation_plan_fingerprint,
        source_environment=preflight.contexts.source.environment,
        target_environment=preflight.contexts.destination.environment,
    )


def run_guarded_biometric_write(
    preflight: BiometricWritePreflight,
    *,
    write: Callable[[BiometricWritePermit], Any],
) -> Any:
    """Executa o callback somente depois de o preflight emitir uma permissão."""

    permit = authorize_biometric_migration_write(preflight)
    return write(permit)
