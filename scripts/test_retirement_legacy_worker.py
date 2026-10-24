"""Validate the explicitly authorized legacy stop without accessing Docker or queues."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

SOURCE = Path(__file__).with_name("deploy-prod-infinitepay-retirement.sh")
HARNESS = r'''
source "$LEGACY_SOURCE"
ALLOW_LEGACY_WORKER_INTERRUPTION=true
API_STOPPED=true
[[ "$LEGACY_CASE" != unauthorized ]] || ALLOW_LEGACY_WORKER_INTERRUPTION=false
compose_with_stdin() {
  cat >/dev/null
  if [[ "$LEGACY_CASE" == busy ]]; then echo 1; else echo 0; fi
}
docker() {
  case "$1" in
    inspect)
      if [[ "$3" == '{{.Image}}' ]]; then
        echo sha256:25067618cf99f3b662f9096fc2f7aa88bcf272da5b2ea62dd91d9de9bd8d3b21
      elif [[ "$LEGACY_CASE" == unexpected_exit ]]; then echo exited:137
      else echo exited:130; fi ;;
    exec)
      if [[ "$*" == *hashlib* ]]; then echo 2731fb50695ea6cac2df54b85994bf2f4162dbf5e811a3adc97f7b4668dbfc8a
      elif [[ "$LEGACY_CASE" == not_idle ]]; then echo do_poll
      else echo hrtimer_nanosleep; fi ;;
    kill) echo signal_sent >&2 ;;
    *) return 99 ;;
  esac
}
interrupt_approved_legacy_worker fixture-worker
[[ "$WORKER_STOPPED" == true ]]
'''


class LegacyWorkerStopTests(unittest.TestCase):
    def run_case(self, scenario):
        bash = shutil.which("bash")
        if sys.platform == "win32":
            candidate = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
            if candidate.exists():
                bash = str(candidate)
        self.assertIsNotNone(bash)
        return subprocess.run([bash, "-c", HARNESS], capture_output=True, text=True, encoding="utf-8", timeout=10,
                              env=dict(os.environ, LEGACY_SOURCE=SOURCE.as_posix(), LEGACY_CASE=scenario))

    def test_explicit_legacy_stop_accepts_only_known_idle_worker_exit_130(self):
        result = self.run_case("success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("exit_code=130 filas_ativas=0", result.stdout)
        self.assertIn("signal_sent", result.stderr)

    def test_no_signal_without_authorization_idle_and_empty_queues(self):
        for scenario in ("unauthorized", "busy", "not_idle"):
            with self.subTest(scenario=scenario):
                result = self.run_case(scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("signal_sent", result.stderr)

    def test_exit_137_is_never_accepted_as_legacy_shutdown(self):
        result = self.run_case("unexpected_exit")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("saída inesperada", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
