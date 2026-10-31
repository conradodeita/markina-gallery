"""Coordenacao fail-closed da manutencao isolada do worker de previas.

Este modulo define o contrato de transicao. Ele nao implementa acesso SSH,
Docker, Compose, banco, Redis ou proxy; nenhuma chamada opera um ambiente real.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class MaintenanceError(RuntimeError):
    """A manutencao foi recusada ou nao pode ser recuperada com seguranca."""


@dataclass(frozen=True)
class Approval:
    fingerprint: str
    callback_policy: str
    window_approved: bool


class MaintenanceHost(Protocol):
    def lock(self): ...
    def preflight(self) -> dict[str, Any]: ...
    def journal(self, phase: str, **details: Any) -> None: ...
    def enable_maintenance(self) -> None: ...
    def pause_producers(self) -> None: ...
    def pause_producers_for_recovery(self) -> None: ...
    def drain_preview_queue(self, timeout_seconds: int) -> bool: ...
    def stop_legacy_worker(self) -> int: ...
    def replace_preview_worker(self) -> None: ...
    def verify_candidate(self) -> None: ...
    def resume_producers(self) -> None: ...
    def disable_maintenance(self) -> None: ...
    def verify_restored_runtime(self) -> None: ...
    def write_success_receipt(self) -> None: ...
    def write_recovery_receipt(self, failed_phase: str) -> None: ...
    def finish_journal(self) -> None: ...
    def recover(self, phase: str, previous_image_id: str) -> None:
        """Re-arm the ingress barrier first, then restore only the prior worker ID.

        Must leave the barrier and durable journal in place if identity or health
        cannot be proven. It must never mutate database/schema or unrelated apps.
        """
        ...


REQUIRED_PREFLIGHT = (
    "checkout_clean",
    "compose_provenance_valid",
    "services_healthy",
    "candidate_identity_valid",
    "previous_image_preserved",
    "no_concurrent_release",
    "optional_writers_stopped",
    "schema_unchanged",
)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise MaintenanceError(reason)


def validate_preflight(report: dict[str, Any], approval: Approval) -> None:
    """Validate gates before the host is allowed to perform any mutation."""
    _require(isinstance(report, dict), "inventario_invalido")
    for gate in REQUIRED_PREFLIGHT:
        _require(report.get(gate) is True, f"gate_{gate}_bloqueado")
    fingerprint = report.get("fingerprint")
    _require(
        isinstance(fingerprint, str) and len(fingerprint) == 64, "fingerprint_invalido"
    )
    _require(approval.fingerprint == fingerprint, "fingerprint_aprovado_divergente")
    _require(
        approval.callback_policy
        in {"provider_retry_proven", "callback_outage_accepted"},
        "politica_callback_nao_aceita",
    )
    _require(
        report.get("callback_policy") == approval.callback_policy,
        "politica_callback_divergente",
    )
    _require(
        approval.window_approved is True and report.get("window_open") is True,
        "janela_operacional_nao_aprovada",
    )
    previous = report.get("previous_image_id")
    candidate = report.get("candidate_image_id")
    _require(
        isinstance(previous, str)
        and previous.startswith("sha256:")
        and len(previous) == 71,
        "imagem_anterior_nao_preservada",
    )
    _require(
        isinstance(candidate, str)
        and candidate.startswith("sha256:")
        and len(candidate) == 71,
        "identidade_candidata_invalida",
    )
    _require(previous != candidate, "imagem_candidata_igual_a_anterior")


def execute(
    host: MaintenanceHost, approval: Approval, *, drain_timeout_seconds: int = 120
) -> None:
    """Run the reviewed transition against a host implementing the explicit contract.

    All authorization/inventory gates are checked while the common release
    lock is held. Production calls are not made by this module or its tests.
    """
    _require(
        type(drain_timeout_seconds) is int and 1 <= drain_timeout_seconds <= 120,
        "timeout_drenagem_invalido",
    )
    with host.lock():
        before = host.preflight()
        validate_preflight(before, approval)
        host.journal(
            "approved",
            fingerprint=before["fingerprint"],
            previous_image_id=before["previous_image_id"],
            candidate_image_id=before["candidate_image_id"],
        )
        phase = "approved"
        try:
            phase = "maintenance_starting"
            host.journal(phase)
            host.enable_maintenance()
            phase = "maintenance_active"
            host.journal(phase)
            phase = "producers_pausing"
            host.journal(phase)
            host.pause_producers()
            phase = "producers_paused"
            host.journal(phase)
            # The host contract must implement a bounded poll and report
            # success only after queued and processing counts both reach zero.
            phase = "draining_queue"
            host.journal(phase)
            if host.drain_preview_queue(drain_timeout_seconds) is not True:
                raise MaintenanceError("fila_preview_nao_drenada")
            phase = "queue_drained"
            host.journal(phase)
            phase = "legacy_stopping"
            host.journal(phase)
            exit_code = host.stop_legacy_worker()
            if exit_code != 130:
                raise MaintenanceError("worker_legado_saida_nao_confirmada")
            phase = "legacy_stopped"
            host.journal(phase)
            phase = "candidate_starting"
            host.journal(phase)
            host.replace_preview_worker()
            phase = "candidate_started"
            host.journal(phase)
            phase = "candidate_verifying"
            host.journal(phase)
            host.verify_candidate()
            phase = "candidate_verified"
            host.journal(phase)
            phase = "producers_resuming"
            host.journal(phase)
            host.resume_producers()
            phase = "producers_resumed"
            host.journal(phase)
            phase = "maintenance_disabling"
            host.journal(phase)
            host.disable_maintenance()
            phase = "traffic_restored"
            host.journal(phase)
            phase = "final_runtime_verifying"
            host.journal(phase)
            host.verify_restored_runtime()
            phase = "final_runtime_verified"
            host.journal(phase)
            phase = "success_receipt_writing"
            host.journal(phase)
            host.write_success_receipt()
            host.journal("complete")
            host.finish_journal()
        except Exception as exc:
            try:
                host.journal("recovery-started", failed_phase=phase)
                host.recover(phase, before["previous_image_id"])
                host.journal("recovered", failed_phase=phase)
                host.write_recovery_receipt(phase)
                host.journal("complete", result="recovered", failed_phase=phase)
                host.finish_journal()
            except Exception as recovery_error:
                # Keep the operational barrier and journal for explicit recovery.
                raise MaintenanceError(
                    "recovery_incompleta; isolamento_e_journal_preservados"
                ) from recovery_error
            if isinstance(exc, MaintenanceError):
                raise
            raise MaintenanceError(f"falha_na_fase_{phase}") from exc
