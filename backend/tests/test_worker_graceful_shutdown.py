import threading
import unittest

from app.worker import run_worker_until_stopped


class WorkerGracefulShutdownTests(unittest.TestCase):
    def test_finishes_the_current_cycle_and_does_not_start_another(self):
        stop_requested = threading.Event()
        calls = []

        def cycle():
            calls.append("cycle")
            stop_requested.set()
            return True

        run_worker_until_stopped(
            stop_requested=stop_requested,
            cycle=cycle,
            sleep=lambda _seconds: self.fail("não deve aguardar após pedido de parada"),
        )

        self.assertEqual(calls, ["cycle"])

    def test_wait_is_skipped_when_shutdown_arrives_during_an_idle_cycle(self):
        stop_requested = threading.Event()
        calls = []

        def cycle():
            calls.append("cycle")
            stop_requested.set()
            return False

        run_worker_until_stopped(
            stop_requested=stop_requested,
            cycle=cycle,
            sleep=lambda _seconds: self.fail("não deve iniciar espera durante shutdown"),
        )

        self.assertEqual(calls, ["cycle"])


if __name__ == "__main__":
    unittest.main()
