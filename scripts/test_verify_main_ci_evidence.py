"""Fail-closed tests for reusable protected CI evidence."""

import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.verify_main_ci_evidence import (
    REQUIRED_JOBS, EvidenceError, paginate, request_json, select_run, verify_jobs, verify_remote,
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

    def test_pagination_complete_and_incomplete(self):
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[
                {'total_count': 2, 'jobs': [{'id': 1}]}, {'total_count': 2, 'jobs': [{'id': 2}]}]):
            self.assertEqual(len(paginate('x', 'jobs', 'synthetic')), 2)
        for response in ({'total_count': 2, 'jobs': []}, {'total_count': '2', 'jobs': []},
                         {'total_count': 0, 'jobs': [{'id': 1}]}):
            with patch('scripts.verify_main_ci_evidence.request_json', return_value=response):
                with self.assertRaises(EvidenceError):
                    paginate('x', 'jobs', 'synthetic')
        with patch('scripts.verify_main_ci_evidence.request_json', side_effect=[
                {'total_count': 2, 'jobs': [{'id': 1}]}, {'total_count': 3, 'jobs': [{'id': 2}]}]):
            with self.assertRaisesRegex(EvidenceError, 'paginacao_mudou'):
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
             patch('scripts.verify_main_ci_evidence.paginate', side_effect=[[run()], jobs()]):
            with self.assertRaisesRegex(EvidenceError, 'main_mudou'):
                verify_remote(SHA, 'synthetic')
        with patch('scripts.verify_main_ci_evidence.request_json', return_value={'sha': 'b' * 40}):
            with self.assertRaisesRegex(EvidenceError, 'nao_e_main'):
                verify_remote(SHA, 'synthetic')


if __name__ == '__main__':
    unittest.main()
