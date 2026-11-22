from __future__ import annotations

import sys
import unittest
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from preview_worker_maintenance_flow import (
    Approval,
    MaintenanceError,
    execute,
)

FINGERPRINT = "a" * 64
PREVIOUS = "sha256:" + "1" * 64
CANDIDATE = "sha256:" + "2" * 64


def valid_report() -> dict:
    return {
        "fingerprint": FINGERPRINT,
        "callback_policy": "provider_retry_proven",
        "previous_image_id": PREVIOUS,
        "candidate_image_id": CANDIDATE,
        "window_open": True,
        "checkout_clean": True,
        "compose_provenance_valid": True,
        "services_healthy": True,
        "candidate_identity_valid": True,
        "previous_image_preserved": True,
        "no_concurrent_release": True,
        "optional_writers_stopped": True,
        "schema_unchanged": True,
    }


class FakeHost:
    def __init__(
        self,
        *,
        report=None,
        drain=True,
        fail_at=None,
        recovery_fails=False,
        legacy_exit=130,
    ):
        self.report = valid_report() if report is None else report
        self.drain = drain
        self.fail_at = fail_at
        self.recovery_fails = recovery_fails
        self.legacy_exit = legacy_exit
        self.lock_fails = False
        self.barrier = False
        self.events = []

    @contextmanager
    def lock(self):
        self.events.append("lock")
        if self.lock_fails:
            raise RuntimeError("synthetic lock conflict")
        yield

    def _event(self, name):
        self.events.append(name)
        if self.fail_at == name:
            raise RuntimeError("synthetic failure")

    def preflight(self):
        self._event("preflight")
        return self.report

    def journal(self, phase, **details):
        self.events.append("journal:" + phase)

    def enable_maintenance(self):
        self._event("maintenance_on")
        self.barrier = True

    def pause_producers(self):
        self._event("pause_producers")

    def drain_preview_queue(self, timeout_seconds):
        self.events.append(f"drain:{timeout_seconds}")
        return self.drain

    def stop_legacy_worker(self):
        self._event("stop_legacy")
        return self.legacy_exit

    def replace_preview_worker(self):
        self._event("replace_worker")

    def verify_candidate(self):
        self._event("verify_candidate")

    def resume_producers(self):
        self._event("resume_producers")

    def disable_maintenance(self):
        self._event("maintenance_off")
        self.barrier = False

    def verify_restored_runtime(self):
        self._event("verify_restored_runtime")

    def write_success_receipt(self):
        self._event("success_receipt")

    def write_recovery_receipt(self, failed_phase):
        self.events.append("recovery_receipt:" + failed_phase)

    def finish_journal(self):
        self.events.append("finish_journal")

    def recover(self, phase, previous_image_id):
        self.events.append(f"recover:{phase}:{previous_image_id}")
        self.barrier = True
        if self.recovery_fails:
            raise RuntimeError("synthetic recovery failure")


class PreviewWorkerMaintenanceFlowTests(unittest.TestCase):
    def setUp(self):
        self.approval = Approval(FINGERPRINT, "provider_retry_proven", True)

    def test_success_orders_barrier_drain_replacement_and_resume(self):
        host = FakeHost()
        execute(host, self.approval)
        self.assertLess(
            host.events.index("journal:maintenance_starting"),
            host.events.index("maintenance_on"),
        )
        self.assertLess(
            host.events.index("maintenance_on"), host.events.index("pause_producers")
        )
        self.assertLess(
            host.events.index("journal:producers_pausing"),
            host.events.index("pause_producers"),
        )
        self.assertLess(
            host.events.index("pause_producers"), host.events.index("drain:120")
        )
        self.assertLess(
            host.events.index("drain:120"), host.events.index("stop_legacy")
        )
        self.assertLess(
            host.events.index("stop_legacy"), host.events.index("replace_worker")
        )
        self.assertLess(
            host.events.index("verify_candidate"), host.events.index("resume_producers")
        )
        self.assertLess(
            host.events.index("resume_producers"), host.events.index("maintenance_off")
        )
        self.assertLess(
            host.events.index("maintenance_off"),
            host.events.index("verify_restored_runtime"),
        )
        self.assertIn("journal:complete", host.events)

    def test_missing_or_unaccepted_callback_policy_fails_before_mutation(self):
        report = valid_report()
        report["callback_policy"] = None
        host = FakeHost(report=report)
        approval = Approval(FINGERPRINT, "unreviewed", True)
        with self.assertRaisesRegex(MaintenanceError, "politica_callback_nao_aceita"):
            execute(host, approval)
        self.assertFalse(
            any(event in host.events for event in ("maintenance_on", "pause_producers"))
        )

    def test_fingerprint_drift_fails_before_mutation(self):
        host = FakeHost()
        approval = Approval("b" * 64, "provider_retry_proven", True)
        with self.assertRaisesRegex(
            MaintenanceError, "fingerprint_aprovado_divergente"
        ):
            execute(host, approval)
        self.assertNotIn("maintenance_on", host.events)

    def test_missing_required_gate_fails_before_mutation(self):
        report = valid_report()
        report["compose_provenance_valid"] = False
        host = FakeHost(report=report)
        with self.assertRaisesRegex(
            MaintenanceError, "gate_compose_provenance_valid_bloqueado"
        ):
            execute(host, self.approval)
        self.assertNotIn("maintenance_on", host.events)

    def test_busy_queue_recovers_without_stopping_legacy_worker(self):
        host = FakeHost(drain=False)
        with self.assertRaisesRegex(MaintenanceError, "fila_preview_nao_drenada"):
            execute(host, self.approval)
        self.assertIn(f"recover:draining_queue:{PREVIOUS}", host.events)
        self.assertNotIn("stop_legacy", host.events)

    def test_candidate_failure_invokes_recovery_with_exact_previous_id(self):
        host = FakeHost(fail_at="verify_candidate")
        with self.assertRaisesRegex(
            MaintenanceError, "falha_na_fase_candidate_verifying"
        ):
            execute(host, self.approval)
        self.assertIn(f"recover:candidate_verifying:{PREVIOUS}", host.events)

    def test_unexpected_legacy_exit_recovers_before_replacement(self):
        host = FakeHost(legacy_exit=0)
        with self.assertRaisesRegex(
            MaintenanceError, "worker_legado_saida_nao_confirmada"
        ):
            execute(host, self.approval)
        self.assertIn(f"recover:legacy_stopping:{PREVIOUS}", host.events)
        self.assertNotIn("replace_worker", host.events)

    def test_recovery_failure_fails_closed(self):
        host = FakeHost(fail_at="verify_candidate", recovery_fails=True)
        with self.assertRaisesRegex(MaintenanceError, "recovery_incompleta"):
            execute(host, self.approval)
        self.assertIn("journal:candidate_verifying", host.events)
        self.assertNotIn("maintenance_off", host.events)
        self.assertTrue(host.barrier)

    def test_receipt_failure_rearms_barrier_before_recovery(self):
        host = FakeHost(fail_at="success_receipt")
        with self.assertRaisesRegex(
            MaintenanceError, "falha_na_fase_success_receipt_writing"
        ):
            execute(host, self.approval)
        self.assertLess(
            host.events.index("maintenance_off"),
            host.events.index(f"recover:success_receipt_writing:{PREVIOUS}"),
        )
        self.assertTrue(host.barrier)

    def test_invalid_timeout_rejected_before_lock(self):
        host = FakeHost()
        with self.assertRaisesRegex(MaintenanceError, "timeout_drenagem_invalido"):
            execute(host, self.approval, drain_timeout_seconds=121)
        self.assertEqual(host.events, [])

    def test_lock_conflict_prevents_preflight_and_mutation(self):
        host = FakeHost()
        host.lock_fails = True
        with self.assertRaisesRegex(RuntimeError, "lock conflict"):
            execute(host, self.approval)
        self.assertEqual(host.events, ["lock"])


if __name__ == "__main__":
    unittest.main()
