"""Fail-closed tests for reusable protected CI evidence."""

import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.verify_main_ci_evidence import (
    REQUIRED_JOBS,
    EvidenceError,
    paginate,
    request_json,
    select_run,
    verify_app_handoff_failure,
    verify_jobs,
    verify_remote,
)

SHA = 'a' * 40


def run(**changes):
    return {'path': '.github/workflows/ci.yml', 'head_sha': SHA, 'event': 'push',
            'head_branch': 'main', 'id': 1, 'run_number': 1, 'run_attempt': 1,
            'status': 'completed', 'conclusion': 'success', **changes}


def jobs():
    return [{'name': name, 'status': 'completed', 'conclusion': 'success'}
            for name in sorted(REQUIRED_JOBS)]


class EvidenceTests(unittest.TestCase):
    def test_recovery_reuses_only_exact_operational_failure_with_all_code_gates_green(self):
        pipeline = ['production-app-preflight', 'production-app-image-artifact',
                    'production-app-handoff-preflight', 'production-app-release']
        for failed in (0, 2, 3):
            operational = [{'name': 'release-scope', 'status': 'completed', 'conclusion': 'success'}] + [
                {'name': name, 'status': 'completed',
                 'conclusion': 'success' if index < failed else 'failure' if index == failed else 'skipped'}
                for index, name in enumerate(pipeline)]
            with self.subTest(failed=failed), \
                    patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
                    patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run(conclusion='failure')], jobs() + operational]):
                self.assertEqual(verify_remote(SHA, 'synthetic', app_handoff_recovery=True)['sha'], SHA)
            for mutation in (
                lambda values: values.pop(),
                lambda values, failed=failed: values.append(dict(values[failed + 1])),
                lambda values, failed=failed: values[failed + 1].update(status='in_progress'),
                lambda values: values.append({'name': 'unrelated', 'status': 'completed', 'conclusion': 'failure'}),
                lambda values, failed=failed: values[-1].update(conclusion='success' if failed != 3 else 'cancelled'),
            ):
                values = [dict(value) for value in operational]
                mutation(values)
                with self.assertRaises(EvidenceError):
                    verify_app_handoff_failure(jobs() + values)
            broken_code = [dict(job) for job in jobs()]
            broken_code[0]['conclusion'] = 'failure'
            with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
                    patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run(conclusion='failure')], broken_code + operational]), \
                    self.assertRaisesRegex(EvidenceError, 'job_obrigatorio_nao_verde'):
                verify_remote(SHA, 'synthetic', app_handoff_recovery=True)

    def test_exact_success_and_newest_attempt(self):
        self.assertEqual(select_run([run(), run(run_attempt=2, id=2)], SHA)['id'], 2)
        verify_jobs(jobs())

    def test_rejects_newer_pending_or_failed_even_if_older_is_green(self):
        for change in ({'status': 'in_progress', 'conclusion': None}, {'conclusion': 'failure'}):
            with self.subTest(change=change), self.assertRaisesRegex(EvidenceError, 'nao_verde'):
                select_run([run(), run(run_attempt=2, **change)], SHA)

    def test_wrong_sha_branch_event_workflow_and_missing(self):
        for changes in ({'head_sha': 'b' * 40}, {'head_branch': 'develop'},
                        {'event': 'pull_request'}, {'path': '.github/workflows/other.yml'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(EvidenceError, 'ausente'):
                select_run([run(**changes)], SHA)
        with self.assertRaisesRegex(EvidenceError, 'sha_invalido'):
            select_run([run()], 'x')

    def test_missing_duplicate_skipped_or_failed_jobs_fail(self):
        for bad in (jobs()[:-1], jobs() + [jobs()[0]],
                    [dict(jobs()[0], conclusion='skipped')] + jobs()[1:],
                    [dict(jobs()[0], conclusion='failure')] + jobs()[1:]):
            with self.assertRaisesRegex(EvidenceError, 'job_obrigatorio_nao_verde'):
                verify_jobs(bad)

    def test_installer_can_reuse_code_checks_with_isolated_app_preflight_failure(self):
        release_jobs = jobs() + [
            {'name': 'release-scope', 'status': 'completed', 'conclusion': 'success'},
            {'name': 'production-app-preflight', 'status': 'completed', 'conclusion': 'failure'},
            {'name': 'production-app-release', 'status': 'completed', 'conclusion': 'skipped'},
        ]
        latest = run(run_attempt=2, conclusion='failure')
        with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
             patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run(), latest], release_jobs]) as api:
            evidence = verify_remote(SHA, 'synthetic', app_bridge_install=True)
        self.assertEqual(evidence, {'sha': SHA, 'run_id': 1, 'run_attempt': 2, 'conclusion': 'failure'})
        self.assertEqual(api.call_args_list[-1].args[0], 'actions/runs/1/attempts/2/jobs')
        with self.assertRaisesRegex(EvidenceError, 'nao_verde'):
            select_run([run(), latest], SHA)

    def test_installer_rejects_any_other_failure_incomplete_gate_or_release_attempt(self):
        scope = {'name': 'release-scope', 'status': 'completed', 'conclusion': 'success'}
        preflight = {'name': 'production-app-preflight', 'status': 'completed', 'conclusion': 'failure'}
        release = {'name': 'production-app-release', 'status': 'completed', 'conclusion': 'skipped'}
        for variant in (
            [preflight, release],
            [scope, preflight],
            [scope, dict(preflight, conclusion='cancelled'), release],
            [scope, preflight, dict(release, conclusion='success')],
            [scope, preflight, release, dict(preflight, name='production-other')],
            [scope, preflight, release, dict(preflight, conclusion='skipped')],
        ):
            with self.subTest(variant=variant), \
                 patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
                 patch('scripts.verify_main_ci_evidence.paginate',
                       side_effect=[[run(conclusion='failure')], jobs() + variant]), \
                 self.assertRaises(EvidenceError):
                verify_remote(SHA, 'synthetic', app_bridge_install=True)
        with self.assertRaisesRegex(EvidenceError, 'nao_verde'):
            select_run([run(status='in_progress', conclusion=None)], SHA, app_bridge_install=True)

    def test_runtime_adoption_accepts_only_the_existing_readonly_preflight_failure(self):
        release_jobs = jobs() + [
            {'name': 'release-scope', 'status': 'completed', 'conclusion': 'success'},
            {'name': 'production-app-preflight', 'status': 'completed', 'conclusion': 'failure'},
            {'name': 'production-app-release', 'status': 'completed', 'conclusion': 'skipped'},
        ]
        with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
             patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run(conclusion='failure')], release_jobs]):
            self.assertEqual(verify_remote(SHA, 'synthetic', app_runtime_adoption=True)['sha'], SHA)
        for variant in (release_jobs[:-1], release_jobs + [{'name': 'production-app-release', 'status': 'completed', 'conclusion': 'success'}]):
            with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': SHA}), \
                 patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run(conclusion='failure')], variant]), \
                 self.assertRaises(EvidenceError):
                verify_remote(SHA, 'synthetic', app_runtime_adoption=True)

    def test_pagination_complete_and_incomplete(self):
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[
                {'total_count': 2, 'jobs': [{'id': 1}]}, {'total_count': 2, 'jobs': [{'id': 2}]}]):
            self.assertEqual(len(paginate('x', 'jobs', 'synthetic')), 2)
        for response in ({'total_count': 2, 'jobs': []}, {'total_count': '2', 'jobs': []},
                         {'total_count': 0, 'jobs': [{'id': 1}]}):
            with patch('scripts.verify_main_ci_evidence.request_json', return_value=response), \
                 self.assertRaises(EvidenceError):
                paginate('x', 'jobs', 'synthetic')
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[
                {'total_count': 2, 'jobs': [{'id': 1}]}, {'total_count': 3, 'jobs': [{'id': 2}]}]), \
             self.assertRaisesRegex(EvidenceError, 'paginacao_mudou'):
            paginate('x', 'jobs', 'synthetic')

    def test_api_failure_is_sanitized_and_url_is_bounded(self):
        with patch('scripts.verify_main_ci_evidence.build_opener') as opener:
            opener.return_value.open.side_effect = URLError('secret-marker')
            with self.assertRaises(EvidenceError) as error:
                request_json('https://api.github.com/repos/conradodeita/markina-gallery/x', 'synthetic')
        self.assertEqual(str(error.exception), 'consulta_api_falhou')
        with self.assertRaisesRegex(EvidenceError, 'url_api_invalida'):
            request_json('https://example.invalid/', 'synthetic')

    def test_remote_checks_main_again_and_never_reuses_different_sha(self):
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[{'sha': SHA}, {'sha': SHA}]), \
             patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run()], jobs()]):
            self.assertEqual(verify_remote(SHA, 'synthetic')['run_id'], 1)
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[{'sha': SHA}, {'sha': 'b' * 40}]), \
             patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run()], jobs()]), \
             self.assertRaisesRegex(EvidenceError, 'main_mudou'):
            verify_remote(SHA, 'synthetic')
        with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': 'b' * 40}), \
             self.assertRaisesRegex(EvidenceError, 'nao_e_main'):
            verify_remote(SHA, 'synthetic')


if __name__ == '__main__':
    unittest.main()
