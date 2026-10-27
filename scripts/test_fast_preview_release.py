"""Protect the narrow authorized 0090 workflow against accidental broadening."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAST = (ROOT / '.github/workflows/preview-migration-0090-authorized.yml').read_text(encoding='utf-8')
ORIGINAL = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')


def section(text, name, next_name):
    return text.split(f'  {name}:\n', 1)[1].split(f'  {next_name}:\n', 1)[0]


class FastPreviewReleaseTests(unittest.TestCase):
    def test_backup_is_separate_protected_authorized_main_only_operation(self):
        backup = section(FAST, 'preview-adjustment-migration-backup', 'preview-adjustment-migration-scope')
        for required in ("github.ref == 'refs/heads/main'", 'inputs.authorization_confirmed == true',
                         'environment: production', 'ci-evidence', 'preview-adjustment-migration-scope',
                         '--mode prepare-backup', "--support-sha '$GITHUB_SHA'"):
            self.assertIn(required, backup)
        self.assertNotIn('--mode release', backup)
        self.assertNotIn('alembic', backup)

    def test_manual_main_only_and_no_automatic_trigger(self):
        header = FAST.split('\njobs:\n', 1)[0]
        self.assertIn('  workflow_dispatch:', header)
        self.assertNotIn('  push:', header)
        self.assertNotIn('  pull_request:', header)
        self.assertIn("github.ref == 'refs/heads/main'", FAST)
        self.assertIn('permissions: {}', header)
        self.assertIn('actions: read', FAST)
        self.assertNotIn('actions: write', FAST)
        self.assertIn('scripts/verify_main_ci_evidence.py --sha "$GITHUB_SHA"', FAST)
        evidence = FAST.split('      - name: Conferir CI de push da main para o SHA de suporte\n', 1)[1].split('\n  preview-adjustment-migration-scope:', 1)[0]
        self.assertIn('shell: bash', evidence)

    def test_pull_request_falls_back_to_its_full_checks_when_main_ci_is_not_green(self):
        step = ORIGINAL.split('      - name: Reutilizar CI verde da main ou validar integralmente esta PR\n', 1)[1]
        step = step.split('      - name: Reconciliação e preservação dos containers históricos 0090\n', 1)[0]
        self.assertIn('if python scripts/verify_main_ci_evidence.py --sha "$CI_BASE_SHA"; then', step)
        self.assertIn('os jobs completos desta PR continuam sendo exigidos', step)
        self.assertIn('ci_reuse_evidence=unavailable_full_pr_validation=required', step)
        self.assertIn('preview-adjustment-migration-wrapper-install', FAST)
        self.assertIn('scripts/verify_main_ci_evidence.py --sha "$GITHUB_SHA"', FAST)

    def test_sensitive_jobs_require_scope_environment_and_authorization(self):
        wrapper = section(FAST, 'preview-adjustment-migration-wrapper-install',
                          'preview-adjustment-migration-preflight')
        preflight = section(FAST, 'preview-adjustment-migration-preflight',
                            'preview-adjustment-migration-release')
        release = FAST.split('  preview-adjustment-migration-release:\n', 1)[1]
        for job in (wrapper, release):
            self.assertIn('inputs.authorization_confirmed == true', job)
            self.assertIn('environment: production\n', job)
            self.assertIn('preview-adjustment-migration-scope', job)
            self.assertIn('ci-evidence', job)
        self.assertIn('environment: production-preflight', preflight)
        self.assertIn('secrets.PRODUCTION_PREFLIGHT_SSH_PRIVATE_KEY', preflight)
        self.assertNotIn('secrets.PRODUCTION_SSH_PRIVATE_KEY', preflight)
        self.assertIn('preview-adjustment-migration-preflight', release)
        self.assertIn('needs.preview-adjustment-migration-preflight.outputs.approval_fingerprint', release)
        self.assertIn("--approval-fingerprint '$APPROVAL_FINGERPRINT'", release)
        self.assertIn("--support-sha '$GITHUB_SHA'", release)

    def test_operational_steps_are_identical_to_reviewed_original(self):
        boundaries = {
            'preview-adjustment-migration-scope': ('preview-adjustment-migration-preflight',
                                                   'preview-adjustment-migration-wrapper-install'),
            'preview-adjustment-migration-wrapper-install': ('preview-adjustment-migration-scope',
                                                             'preview-adjustment-migration-preflight'),
            'preview-adjustment-migration-preflight': ('preview-adjustment-migration-release-approval',
                                                      'preview-adjustment-migration-release'),
        }
        for name, (old_end, new_end) in boundaries.items():
            with self.subTest(job=name):
                old = section(ORIGINAL, name, old_end).split('    steps:\n', 1)[1]
                new = section(FAST, name, new_end).split('    steps:\n', 1)[1]
                self.assertEqual(old, new)
        old_release = section(ORIGINAL, 'preview-adjustment-migration-release', 'production-preflight')
        new_release = FAST.split('  preview-adjustment-migration-release:\n', 1)[1]
        self.assertEqual(old_release.split('    steps:\n', 1)[1].rstrip(),
                         new_release.split('    steps:\n', 1)[1].rstrip())


if __name__ == '__main__':
    unittest.main()
