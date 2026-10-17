"""Contratos de escopo da manutenção, com histórico Git sintético isolado."""

import copy
import base64
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_prod_facial_release_gates as gates


class MaintenanceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git("init", "-q")
        for name in gates.RUNTIME_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic baseline\n", encoding="utf-8")
        self.commit()
        baseline = self.run_git("rev-parse", "HEAD")
        (self.root / gates.RUNTIME_FILES[0]).write_text("approved reference update\n", encoding="utf-8")
        self.commit()
        self.payload = {
            "release_ready": False,
            "gates": {"base_legal": {"status": "pendente", "evidence": None}},
            "maintenance_release": {
                "authorized": True, "scope": "existing_facial_runtime",
                "evidence": "synthetic authorization", "baseline_sha": baseline,
                "runtime_blobs": {
                    name: [base64.b64encode(bytes.fromhex(self.run_git("rev-parse", "HEAD:" + name))).decode()[i:i + 7]
                           for i in range(0, 28, 7)]
                    for name in gates.RUNTIME_FILES
                },
            },
        }

    def run_git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
        return subprocess.run(["git", *args], cwd=self.root, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "synthetic fixture")

    def test_maintenance_does_not_approve_activation(self):
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (True, "manutencao_autorizada_sem_ativacao"))
        self.assertEqual(gates.activation_status(self.payload), (False, ["base_legal"]))

    def test_authorization_is_required(self):
        self.payload["maintenance_release"]["authorized"] = False
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (False, "autorizacao_de_manutencao_ausente"))

    def test_unreviewed_runtime_is_rejected(self):
        (self.root / gates.RUNTIME_FILES[0]).write_text("unreviewed change\n", encoding="utf-8")
        self.commit()
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (False, "runtime_diverge_do_blob_revisado"))

    def test_uncommitted_runtime_is_rejected(self):
        (self.root / gates.RUNTIME_FILES[0]).write_text("uncommitted change\n", encoding="utf-8")
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (False, "historico_ou_runtime_nao_comprovado"))

    def test_outside_scope_is_rejected(self):
        outside = self.root / "backend/app/facial/unapproved_runtime.py"
        outside.write_text("outside approved capture scope\n", encoding="utf-8")
        self.commit()
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (False, "arquivo_fora_do_escopo"))

    def test_missing_baseline_or_manifest_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["maintenance_release"]["baseline_sha"] = "0" * 40
        self.assertFalse(gates.evaluate_maintenance(payload, self.root)[0])
        self.payload["maintenance_release"]["runtime_blobs"].pop(gates.RUNTIME_FILES[0])
        self.assertEqual(gates.evaluate_maintenance(self.payload, self.root),
                         (False, "manifesto_de_runtime_incompleto"))


if __name__ == "__main__":
    unittest.main()
