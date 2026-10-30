"""Contratos focados do corte; nenhuma credencial ou infraestrutura operacional."""

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if os.name == 'posix':
    from scripts import environment_cutover_release as release
else:
    release = None


@unittest.skipUnless(os.name == 'posix', 'Runner operacional exige POSIX')
class EnvironmentReleaseTests(unittest.TestCase):
    def test_maintenance_command_preserves_workdir_and_prefers_candidate_package(self):
        config = {'fingerprint': 'a'*64, 'plan': 'b'*64, 'services': {'api': {
            'Config': {'Env': ['APP_ENV=staging']}, 'Image': 'synthetic-image',
            'NetworkSettings': {'Networks': {'synthetic': {}}}}}}
        with (patch.object(release, 'maintenance_api', return_value='synthetic-api'),
              patch.object(release, 'run', return_value='{"status":"success"}') as command):
            release.runtime(config, 'preflight', 'synthetic')
        args = command.call_args.args
        self.assertEqual(args[args.index('synthetic-image')+1:args.index('preflight')],
                         ('-P', '-B', '-m', 'app.environment_transition_runtime'))
        self.assertNotIn('--workdir', args)
        self.assertIn('PYTHONPATH=/candidate/backend', args)

    def test_candidate_module_is_imported_over_published_package_without_changing_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            published = root / 'published'
            candidate = root / 'candidate'
            for path, marker in ((published, 'published'), (candidate, 'candidate')):
                (path / 'app').mkdir(parents=True)
                (path / 'app/__init__.py').write_text('SOURCE = ' + repr(marker))
            (candidate / 'app/environment_transition_runtime.py').write_text(
                'import app, json, os; print(json.dumps({"source":app.SOURCE,"cwd":os.getcwd()}))')
            result = subprocess.run([sys.executable, '-P', '-B', '-m', 'app.environment_transition_runtime'],
                cwd=published, env={**os.environ, 'PYTHONPATH': str(candidate)},
                capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), {'source': 'candidate', 'cwd': str(published)})

    def test_docker_mount_reordering_preserves_inventory_but_real_drift_blocks(self):
        mounts = [{'Destination': '/z', 'Source': '/synthetic/z', 'RW': False},
                  {'Destination': '/a', 'Source': '/synthetic/a', 'RW': True}]
        item = {'Id': 'synthetic-api', 'Image': 'synthetic-image',
                'State': {'Status': 'running', 'Health': {'Status': 'healthy'}},
                'Config': {'Env': ['APP_ENV=staging'], 'Cmd': ['python'], 'Entrypoint': None,
                           'Labels': {'com.docker.compose.service': 'api'}},
                'Mounts': mounts, 'NetworkSettings': {'Networks': {'synthetic': {}}},
                'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'}}}
        reordered = copy.deepcopy(item)
        reordered['Mounts'].reverse()
        with (patch.object(release, 'EXPECTED', {'api'}),
              patch.object(release, 'run', side_effect=[
                  'synthetic-api', json.dumps([item]),
                  'synthetic-api', json.dumps([reordered])])):
            config = {'services': release.containers()}
            release.verify_running(config, target=False)
        for field, value in [('Source', '/synthetic/changed'), ('RW', True)]:
            changed = copy.deepcopy(item)
            changed['Mounts'][0][field] = value
            with (patch.object(release, 'EXPECTED', {'api'}),
                  patch.object(release, 'run', side_effect=['synthetic-api', json.dumps([changed])]),
                  self.assertRaisesRegex(release.ReleaseBlocked, 'runtime_mounts_changed')):
                release.verify_running(config, target=False)
        self.assertEqual(item['Mounts'], mounts)

    def test_mount_destination_must_be_absolute_and_unique(self):
        for mounts in ([{'Source': '/synthetic'}], [{'Destination': 'relative'}],
                       [{'Destination': '/same'}, {'Destination': '/same'}]):
            with self.assertRaisesRegex(release.ReleaseBlocked, 'mount_destination_invalid'):
                release.canonical_mounts(mounts)

    def test_maintenance_selects_exact_inventory_name_with_historical_labels_preserved(self):
        source = {'Name': '/markina-gallery-api-1', 'Image': 'sha256:synthetic-original'}
        current = {**source, 'Id': 'synthetic-current', 'Config': {'Labels': {
            'com.docker.compose.project': 'markina-gallery', 'com.docker.compose.service': 'api'}}}
        with patch.object(release, 'run', return_value=json.dumps([current])) as command:
            self.assertEqual(release.maintenance_api(source), 'synthetic-current')
            self.assertEqual(command.call_args.args,
                             ('docker', 'inspect', '--type', 'container', source['Name']))
        with patch.object(release, 'run', return_value=json.dumps([{**current, 'Image': 'changed'}])), self.assertRaises(release.ReleaseBlocked):
            release.maintenance_api(source)

    def test_apply_keeps_financial_gate_closed_and_only_restarts_api_worker(self):
        config = {'fingerprint': 'a'*64, 'plan': 'b'*64, 'sha': 'd'*40,
                  'facts': {'biometric_counts': {'photo_embeddings': 2},
                            'credential_counts': {'mercadopago_access_token': 1}}}
        phases, commands = [], []

        def runtime(_config, mode, *args, **kwargs):
            phases.append(mode)
            return {'embedding_count': 2, 'account_count': 1, 'destination_verified': True,
                    'live_gate': False}

        with (patch.object(release, 'open_config', return_value=config),
              patch.object(release, 'load_receipt', return_value={
                  'fingerprint': 'a'*64, 'plan': 'b'*64, 'channels_verified': True}),
              patch.object(release, 'snapshot', return_value={'fingerprint': 'a'*64}),
              patch.object(release, 'model_path', return_value=Path('/synthetic/model')),
              patch.object(release, 'maintenance') as barrier,
              patch.object(release, 'stop_consumers'), patch.object(release, 'runtime', side_effect=runtime),
              patch.object(release, 'configure_files'),
              patch.object(release, 'compose', side_effect=lambda *a: commands.append(a)),
              patch.object(release, 'wait_running'), patch.object(release, 'target_config', return_value=config),
              patch.object(release, 'target_fingerprint', return_value='c'*64),
              patch.object(release, 'save_receipt')):
            result = release.apply('synthetic', 'a'*64)
        self.assertEqual(phases, ['prepare', 'apply', 'verify', 'channels', 'eligibility'])
        self.assertFalse(result['live_gate'])
        self.assertFalse(result['facial_enabled'])
        self.assertEqual(commands[0][-2:], ('api', 'worker'))
        self.assertEqual([call.args[1] for call in barrier.call_args_list], [True, False])

    def test_target_configuration_preserves_tokens_and_test_allowlist(self):
        source = {'APP_ENV': 'staging', 'APP_VERSION': 'a'*40,
            'INTEGRATION_SECRET_ENV': 'staging', 'FACIAL_PROCESSING_ENABLED': 'true',
            'MERCADOPAGO_ALLOW_LIVE_PAYMENTS': 'false', 'MERCADOPAGO_TEST_CUSTOMERS': '["synthetic"]',
            'WHATSAPP_BINDING_OWNER_CREDENTIAL_ENV': 'staging', 'SMTP_PASSWORD': 'synthetic$secret'}
        before = copy.deepcopy(source)
        target = release.target_environment(source)
        self.assertEqual(source, before)
        self.assertEqual(target['APP_ENV'], 'production')
        self.assertEqual(target['FACIAL_PROCESSING_ENABLED'], 'false')
        self.assertEqual(target['SMTP_PASSWORD'], source['SMTP_PASSWORD'])
        self.assertEqual(target['MERCADOPAGO_TEST_CUSTOMERS'], source['MERCADOPAGO_TEST_CUSTOMERS'])
        self.assertEqual(target['APP_VERSION'], source['APP_VERSION'])
        live = release.target_environment(source, live=True)
        self.assertEqual(live['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'], 'true')
        self.assertEqual(live['MERCADOPAGO_TEST_CUSTOMERS'], target['MERCADOPAGO_TEST_CUSTOMERS'])
        with self.assertRaises(release.ReleaseBlocked):
            release.target_environment({**source, 'WHATSAPP_BINDING_OWNER_CREDENTIAL_ENV': 'another-account'})

    def test_environment_file_changes_are_allowlisted_and_preserve_secret_bytes(self):
        source = b'# preserved\r\nAPP_ENV="staging"\r\nSMTP_PASSWORD=synthetic$secret\r\n'
        result = release.rewrite_environment(source, {'APP_ENV': 'production', 'FACIAL_PROCESSING_ENABLED': 'false'})
        self.assertIn(b'APP_ENV=production\r\n', result)
        self.assertIn(b'SMTP_PASSWORD=synthetic$secret\r\n', result)
        self.assertIn(b'FACIAL_PROCESSING_ENABLED=false\n', result)
        with self.assertRaises(release.ReleaseBlocked):
            release.rewrite_environment(b'APP_ENV=staging\nAPP_ENV=staging\n', {'APP_ENV': 'production'})

    def test_config_authentication_binds_operation(self):
        key = b'x'*32
        payload = release.seal_config({'private': 'synthetic-secret'}, key, 'synthetic')
        encoded = json.dumps(payload)
        self.assertNotIn('synthetic-secret', encoded)
        import base64

        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with self.assertRaises(InvalidTag):
            AESGCM(key).decrypt(base64.b64decode(payload['nonce']), base64.b64decode(payload['ciphertext']),
                                b'environment-host-v1:wrong-operation')

    def test_stop_has_no_forced_timeout_and_scopes_only_consumers(self):
        config = {'services': {name: {'Id': 'synthetic-' + name} for name in release.CONSUMERS}}
        with patch.object(release, 'run') as command:
            release.stop_consumers(config)
        self.assertEqual(len(command.call_args_list), 5)
        for call in command.call_args_list:
            self.assertEqual(call.args[:4], ('docker', 'stop', '--timeout', '-1'))
            self.assertNotIn('nginx', call.args)
            self.assertNotIn('--force', call.args)

    def test_main_ci_must_be_latest_successful_push_on_exact_revision(self):
        sha = 'a'*40
        responses = [
            {'object': {'sha': sha}},
            {'workflow_runs': [{'path': '.github/workflows/ci.yml', 'head_sha': sha,
                'head_branch': 'main', 'event': 'push', 'run_number': 1, 'run_attempt': 1,
                'status': 'completed', 'conclusion': 'failure'}]},
        ]
        with patch.object(release, 'github', side_effect=responses), self.assertRaises(release.ReleaseBlocked):
            release.verify_candidate(sha)

    def test_host_source_is_python38_compatible(self):
        ast.parse(Path(release.__file__).read_text(), feature_version=(3, 8))

    def test_model_escapes_resolved_dollars_without_loading_other_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'compose.json'
            path.write_text('{}')
            services = {name: {'Image': 'synthetic-image', 'Config': {
                'Env': ['APP_ENV=staging', 'PYP_TOKEN=synthetic$literal'],
                'Cmd': ['python', '-c', 'print("$literal")'], 'Entrypoint': None,
                'Labels': {'com.docker.compose.project.config_files': str(path)}}}
                for name in release.CONSUMERS}
            model = {'services': {name: {} for name in release.CONSUMERS}}
            with patch.object(release, 'ROOT', root), patch.object(release, 'run', return_value=json.dumps(model)):
                result = release.compose_model(services)
            self.assertEqual(result['services']['api']['environment']['PYP_TOKEN'], 'synthetic$$literal')
            self.assertEqual(result['services']['api']['command'][2], 'print("$$literal")')


if __name__ == '__main__':
    unittest.main()
