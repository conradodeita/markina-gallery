from __future__ import annotations

import sys
import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview_adjustment_migration_release as release  # noqa: E402
from test_preview_adjustment_migration_inventory import valid_inventory  # noqa: E402


class PreviewMigrationReleaseHostTests(unittest.TestCase):
    def test_candidate_fetch_failure_categories_are_fixed_and_never_expose_stderr(self):
        cases = (
            (b"fatal: couldn't find remote ref secret-ref", 'ref_indisponivel'),
            (b'Could not resolve host: private.example', 'rede_indisponivel'),
            (b'Permission denied (publickey). https://user:token@private.example/path', 'acesso_negado'),
            (b'early EOF; index-pack failed for /private/path', 'transferencia_incompleta'),
            (b'opaque private server response', 'outro'),
        )
        for stderr, expected in cases:
            with self.subTest(category=expected):
                host = release.ReleaseHost()
                self.assertEqual(host.classify_candidate_fetch_failure(stderr), expected)
                with patch.object(release.subprocess, 'run', return_value=release.subprocess.CompletedProcess(
                        ['git', 'fetch'], 128, stderr=stderr)), \
                        patch('sys.stdout', new_callable=io.StringIO) as output, \
                        self.assertRaisesRegex(release.InventoryError,
                                               rf'candidate_fetch_falhou;categoria={expected};codigo_saida=128'):
                    host.fetch_candidate()
                text = output.getvalue()
                self.assertIn(f'candidate_fetch_result=failed;categoria={expected};codigo_saida=128', text)
                self.assertNotIn(stderr.decode(), text)
                for private in ('private.example', 'secret-ref', 'token', '/private/path'):
                    self.assertNotIn(private, text)

    def test_candidate_fetch_timeout_is_reported_as_network_failure(self):
        host = release.ReleaseHost()
        with patch.object(release.subprocess, 'run', side_effect=release.subprocess.TimeoutExpired(
                ['git', 'fetch'], 300, stderr=b'private endpoint')), \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError,
                                       'candidate_fetch_falhou;categoria=rede_indisponivel'):
            host.fetch_candidate()
        self.assertEqual(output.getvalue(), 'candidate_fetch_result=failed;categoria=rede_indisponivel\n')

    def test_fetch_usage_exit_129_triggers_bounded_compatibility_retry(self):
        self.assertTrue(release.ReleaseHost.fetch_usage_error_requires_compatibility_retry(129))
        self.assertFalse(release.ReleaseHost.fetch_usage_error_requires_compatibility_retry(128))
        self.assertFalse(release.ReleaseHost.fetch_usage_error_requires_compatibility_retry(1))

    def test_candidate_fetch_retries_once_without_optional_flag_on_exit_129(self):
        host = release.ReleaseHost()
        rejected = release.subprocess.CompletedProcess(
            ['git', 'fetch'], 129, stderr=b'localized private git diagnostic')
        accepted = release.subprocess.CompletedProcess(['git', 'fetch'], 0, stderr=b'')
        with patch('scripts.preview_adjustment_migration_release.subprocess.run',
                   side_effect=[rejected, accepted]) as run, \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            host.fetch_candidate()
        self.assertEqual(run.call_count, 2)
        self.assertIn('--no-write-fetch-head', run.call_args_list[0].args[0])
        self.assertNotIn('--no-write-fetch-head', run.call_args_list[1].args[0])
        self.assertEqual(run.call_args_list[1].args[0][-2:], ['origin', release.TARGET_SHA])
        self.assertEqual(output.getvalue(),
                         'candidate_fetch_compatibility=retry_com_fetch_head_padrao\n'
                         'candidate_fetch_result=success\n')
        self.assertNotIn('opção desconhecida', output.getvalue())

    def test_fetch_fallback_failure_keeps_fixed_diagnostics(self):
        host = release.ReleaseHost()
        rejected = release.subprocess.CompletedProcess(
            ['git', 'fetch'], 129, stderr=b'private git usage response')
        denied = release.subprocess.CompletedProcess(
            ['git', 'fetch'], 128, stderr=b'Permission denied private-host')
        with patch('scripts.preview_adjustment_migration_release.subprocess.run',
                   side_effect=[rejected, denied]) as run, \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError,
                                       'candidate_fetch_falhou;categoria=acesso_negado;codigo_saida=128'):
            host.fetch_candidate()
        self.assertEqual(run.call_count, 2)
        self.assertNotIn('private-host', output.getvalue())
        self.assertNotIn('Permission denied', output.getvalue())

    def test_failure_report_keeps_controlled_criteria_but_never_private_exception_messages(self):
        from preview_adjustment_migration_release_flow import ReleaseError
        self.assertEqual(release.sanitized_failure(ReleaseError('schema_origem_divergente_antes_backup')),
                         'schema_origem_divergente_antes_backup')
        for error in (TypeError('PRIVATE credentials /secret/path'),
                      ReleaseError('PRIVATE arbitrary response'), KeyError('PRIVATE customer payload')):
            result = release.sanitized_failure(error)
            self.assertNotIn('PRIVATE', result)
            self.assertNotIn('/secret', result)
            self.assertIn('classe=', result)
            self.assertIn('linha=', result)

    def test_health_starting_is_waited_for_but_timeout_or_exit_fails(self):
        host = release.ReleaseHost()
        starting = {'State': {'Status': 'running', 'Health': {'Status': 'starting'}}}
        healthy = {'State': {'Status': 'running', 'Health': {'Status': 'healthy'}}}
        with patch.object(host, 'inspect', side_effect=[starting, healthy]), patch.object(release.time, 'sleep'):
            self.assertEqual(host.wait_healthy('id'), healthy)
        with patch.object(host, 'inspect', return_value=starting), \
                patch.object(release.time, 'monotonic', side_effect=[0, 121]):
            with self.assertRaisesRegex(release.InventoryError, 'nao_retornou_saudavel'):
                host.wait_healthy('id')
        with patch.object(host, 'inspect', return_value={'State': {'Status': 'exited'}}):
            with self.assertRaisesRegex(release.InventoryError, 'runtime_parou'):
                host.wait_healthy('id')

    def test_compose_uses_exact_active_standalone_manifest_and_order(self):
        host = release.ReleaseHost()
        host.run = lambda *_args: '2.35.1'
        data = valid_inventory()
        active = '/var/lib/markina-gallery/deploy-state/retire-approved/active.compose.json'
        for name in ('api', 'web'):
            data['services'][name]['compose_files'] = [active]
        with patch.object(release.Path, 'is_file', return_value=True), \
                patch.object(release.Path, 'is_symlink', return_value=False):
            command = host.compose_command(data, Path('/candidate'), Path('/candidate/overlay.json'))
        self.assertIn(active, command)
        self.assertNotIn(str(release.ROOT / 'docker/docker-compose.yml'), command)
        self.assertNotIn('/candidate/docker/docker-compose.yml', command)

    @unittest.skipIf(os.name == 'nt', 'Permissões POSIX são verificadas no runner Linux, inclusive Python 3.8')
    def test_online_backup_creates_private_verifiable_manifest_without_release_journal(self):
        host = release.ReleaseHost()
        host.pg_scalar = lambda *_args: 1
        data = valid_inventory()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            def command(args, **kwargs):
                if 'pg_dump' in args[-1]:
                    kwargs['stdout'].write(b'synthetic-pg-dump')
            with patch.object(release, 'BACKUPS', directory), \
                    patch.object(release.subprocess, 'run', side_effect=command), \
                    patch.object(host, 'record') as record:
                result = host.backup_and_verify(data, record=False)
            record.assert_not_called()
            archive = Path(result['path'])
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertTrue(archive.with_name(archive.name + '.manifest').is_file())
            self.assertEqual(result['schema'], '20261025_0089')

    def test_publish_pins_version_and_refuses_dirty_checkout_before_switch(self):
        host = release.ReleaseHost()
        host.inventory_data = valid_inventory()
        calls = []
        host.command = lambda args, **kwargs: calls.append(args)
        host.record = lambda *_args, **_kwargs: None
        host.compose_command = lambda *_args: ['docker', 'compose']
        host.run = lambda *args: '' if 'status' in args else host.inventory_data['checkout_sha']
        with tempfile.TemporaryDirectory() as temporary:
            host.work = Path(temporary)
            host.publish_api_web({'api': 'sha256:' + 'a' * 64, 'web': 'sha256:' + 'b' * 64})
            data = json.loads((host.work / 'preview-migration-release.compose.json').read_text())
        self.assertEqual(data['services']['api']['environment']['APP_VERSION'], release.TARGET_SHA)
        self.assertEqual(calls[0], ['git', 'switch', '--detach', release.TARGET_SHA])
        self.assertIn('--no-deps', calls[1])
        host.run = lambda *_args: 'dirty'
        calls.clear()
        with self.assertRaisesRegex(release.InventoryError, 'checkout_mudou'):
            host.publish_api_web({})
        self.assertEqual(calls, [])

    def test_published_staging_is_not_deleted(self):
        host = release.ReleaseHost()
        host.journal = {'phase': 'published'}
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            journal = state / 'journal.json'
            journal.write_text('{}')
            host.work = state / 'retained'
            host.work.mkdir()
            (host.work / 'overlay.json').write_text('{}')
            host.worktree_added = True
            with patch.object(release, 'STATE', state), patch.object(release, 'JOURNAL', journal), \
                    patch.object(release.os, 'open', return_value=5), patch.object(release.os, 'fsync'), \
                    patch.object(release.os, 'close'), patch.object(host, 'command') as command:
                host.finish_journal()
            command.assert_not_called()
            self.assertTrue((host.work / 'overlay.json').is_file())
            self.assertFalse(journal.exists())

    def test_maintenance_barrier_allows_only_health_paths(self):
        source = 'server {\n    listen 80;\n    location / { proxy_pass http://web; }\n}'
        generated = release.ReleaseHost.maintenance_configuration(source)
        self.assertIn('^/(healthz|api/health)$', generated)
        self.assertIn('return 503', generated)
        self.assertIn('proxy_pass http://web', generated)

    def test_only_explicit_target_revision_can_reach_alembic(self):
        host = release.ReleaseHost()
        host.inventory_data = valid_inventory()
        with tempfile.TemporaryDirectory() as temporary:
            host.work = Path(temporary)
            calls = []
            host.command = lambda args, **kwargs: calls.append((args, kwargs))
            host.compose_command = lambda *_args: ['docker', 'compose']
            host.record = lambda *_args, **_kwargs: None
            host.apply_migration('sha256:' + 'a' * 64, '20261026_0090')
        args, kwargs = calls[0]
        self.assertEqual(args[-4:], ['-m', 'alembic', 'upgrade', '20261026_0090'])
        self.assertNotIn('head', args)
        self.assertTrue(kwargs['app_version'])
        with self.assertRaisesRegex(release.InventoryError, 'revision_migration_nao_permitida'):
            host.apply_migration('sha256:' + 'a' * 64, 'head')

    def test_unknown_writer_is_refused_before_any_signal(self):
        host = release.ReleaseHost()
        data = valid_inventory()
        data['services']['unclassified-worker'] = dict(data['services']['worker'])
        calls = []
        host.command = lambda *args, **kwargs: calls.append(args)
        with self.assertRaisesRegex(release.InventoryError, 'writer_markina_sem_classificacao'):
            host.stop_writers(data)
        self.assertEqual(calls, [])

    def test_sigterm_exit_status_is_accepted_as_graceful_stop(self):
        host = release.ReleaseHost()
        item = {'container_id': 'container-api', 'image': 'sha256:' + 'a' * 64,
                'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}}
        data = {'services': {'api': item}}
        host.journal = {}
        host.inspect = lambda _ident: {
            'Image': item['image'], 'State': {'Status': 'exited', 'ExitCode': 143}}
        host.command = lambda *_args, **_kwargs: None
        host.record = lambda *_args, **_kwargs: None
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(host.stop_writers(data), ['api'])
        self.assertEqual(output.getvalue(),
                         'writer_stop_requested=api\nwriter_stop_completed=api\n')

    def test_legacy_face_search_uses_sigint_only_after_durable_queue_is_idle(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-search-worker': {'container_id': 'facial-container', 'image': image,
                                   'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        host.inspect = lambda ident: {'Image': image,
                                      'State': {'Status': 'exited',
                                                'ExitCode': 130 if ident == 'facial-container' else 143}}
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = lambda _sql: 0
        host.record = lambda *_args, **_kwargs: None

        self.assertEqual(host.stop_writers(data), ['api', 'face-search-worker'])
        stop_commands = [args for args in commands if args[1:3] == ['kill', '--signal=SIGINT']]
        self.assertEqual(stop_commands, [['docker', 'kill', '--signal=SIGINT', 'facial-container']])

    def test_legacy_face_search_is_not_interrupted_with_pending_durable_work(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-search-worker': {'container_id': 'facial-container', 'image': image,
                                   'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        host.inspect = lambda _ident: {'Image': image,
                                       'State': {'Status': 'exited', 'ExitCode': 143}}
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = lambda _sql: 1
        host.record = lambda *_args, **_kwargs: None

        with patch.object(release.time, 'monotonic', side_effect=[0, 0, 121]), \
                patch.object(release.time, 'sleep'), \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError, 'fila_face_search_nao_ociosa'):
            host.stop_writers(data)

        self.assertNotIn(['docker', 'kill', '--signal=SIGINT', 'facial-container'], commands)
        self.assertIn('writer_idle_timeout=face-search-worker\n', output.getvalue())

    def test_legacy_face_index_waits_until_all_producers_stop_and_queue_drains(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'face-index-worker': {'container_id': 'index-container', 'image': image,
                                  'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-search-worker': {'container_id': 'search-container', 'image': image,
                                   'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-maintenance-worker': {'container_id': 'maintenance-container', 'image': image,
                                         'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'preview-adjustment-worker': {'container_id': 'preview-container', 'image': image,
                                          'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'worker': {'container_id': 'worker-container', 'image': image,
                       'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        idle_checks = []

        def inspect(ident):
            code = 130 if ident in {'index-container', 'search-container', 'maintenance-container',
                                    'preview-container'} else 143
            return {'Image': image, 'State': {'Status': 'exited', 'ExitCode': code}}

        def check_idle(sql):
            idle_checks.append(sql)
            return 0

        host.inspect = inspect
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = check_idle
        host.record = lambda *_args, **_kwargs: None

        stopped = host.stop_writers(data)
        signals = [(args[-1], args[2]) for args in commands if args[1] == 'kill']
        self.assertEqual(stopped, ['api', 'worker', 'face-index-worker', 'face-maintenance-worker',
                                   'face-search-worker', 'preview-adjustment-worker'])
        self.assertEqual(signals, [
            ('api-container', '--signal=SIGTERM'),
            ('worker-container', '--signal=SIGTERM'),
            ('index-container', '--signal=SIGINT'),
            ('maintenance-container', '--signal=SIGINT'),
            ('search-container', '--signal=SIGINT'),
            ('preview-container', '--signal=SIGINT'),
        ])
        self.assertEqual(sum("kind='index'" in sql for sql in idle_checks), 1)
        self.assertEqual(sum("'purge', 'cleanup'" in sql for sql in idle_checks), 1)
        self.assertEqual(sum("FROM preview_adjustment WHERE status IN ('queued', 'processing')" in sql
                             for sql in idle_checks), 1)

    def test_preview_adjustment_worker_waits_until_producers_stop_and_queue_is_idle(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'worker': {'container_id': 'worker-container', 'image': image,
                       'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-search-worker': {'container_id': 'search-container', 'image': image,
                                   'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'preview-adjustment-worker': {'container_id': 'preview-container', 'image': image,
                                          'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        queries = []

        def inspect(ident):
            exit_code = 130 if ident in {'search-container', 'preview-container'} else 143
            return {'Image': image, 'State': {'Status': 'exited', 'ExitCode': exit_code}}

        host.inspect = inspect
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = lambda sql: queries.append(sql) or 0
        host.record = lambda *_args, **_kwargs: None

        self.assertEqual(host.stop_writers(data), [
            'api', 'worker', 'face-search-worker', 'preview-adjustment-worker'])
        self.assertIn("FROM preview_adjustment WHERE status IN ('queued', 'processing')", queries[-1])
        self.assertEqual(commands[-2:], [
            ['docker', 'update', '--restart=no', 'preview-container'],
            ['docker', 'kill', '--signal=SIGINT', 'preview-container'],
        ])

    def test_preview_adjustment_worker_pending_queue_fails_before_signal(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'worker': {'container_id': 'worker-container', 'image': image,
                       'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'preview-adjustment-worker': {'container_id': 'preview-container', 'image': image,
                                          'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        host.inspect = lambda _ident: {'Image': image,
                                       'State': {'Status': 'exited', 'ExitCode': 143}}
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = lambda _sql: 1
        host.record = lambda *_args, **_kwargs: None

        with patch.object(release.time, 'monotonic', side_effect=[0, 0, 0, 121]), \
                patch.object(release.time, 'sleep'), \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError, 'fila_preview_adjustment_nao_ociosa'):
            host.stop_writers(data)

        self.assertNotIn(['docker', 'kill', '--signal=SIGINT', 'preview-container'], commands)
        self.assertIn('writer_idle_timeout=preview-adjustment-worker\n', output.getvalue())

    def test_preview_adjustment_worker_accepts_only_sigint_exit_130(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'preview-adjustment-worker': {'container_id': 'preview-container', 'image': image,
                                          'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        host.inspect = lambda ident: {'Image': image,
                                      'State': {'Status': 'exited', 'ExitCode': 143}}
        host.command = lambda args, **_kwargs: commands.append(args)
        host.pg_scalar = lambda _sql: 0
        host.record = lambda *_args, **_kwargs: None

        with self.assertRaisesRegex(release.InventoryError, 'writer_nao_encerrou_graciosamente'):
            host.stop_writers(data)

        self.assertIn(['docker', 'kill', '--signal=SIGINT', 'preview-container'], commands)

    def test_legacy_face_index_pending_work_fails_before_signaling_index_worker(self):
        host = release.ReleaseHost()
        image = 'sha256:' + 'a' * 64
        data = {'services': {
            'api': {'container_id': 'api-container', 'image': image,
                    'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
            'face-index-worker': {'container_id': 'index-container', 'image': image,
                                  'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}},
        }}
        host.journal = {}
        commands = []
        host.inspect = lambda _ident: {'Image': image,
                                       'State': {'Status': 'exited', 'ExitCode': 143}}
        host.command = lambda args, **_kwargs: commands.append(args)
        host.wait_for_face_index_idle = lambda: (_ for _ in ()).throw(
            release.InventoryError('fila_face_index_nao_ociosa'))
        host.record = lambda *_args, **_kwargs: None

        with self.assertRaisesRegex(release.InventoryError, 'fila_face_index_nao_ociosa'):
            host.stop_writers(data)

        signals = [args for args in commands if args[1:3] == ['kill', '--signal=SIGINT']]
        self.assertEqual(signals, [])
        self.assertFalse(any(args[-1] == 'index-container' and args[1] == 'update'
                             for args in commands))

    def test_legacy_face_maintenance_pending_work_times_out_without_private_data(self):
        host = release.ReleaseHost()
        queries = []
        host.pg_scalar = lambda sql: queries.append(sql) or 1

        with patch.object(release.time, 'monotonic', side_effect=[0, 121]), \
                patch.object(release.time, 'sleep'), \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError, 'fila_face_maintenance_nao_ociosa'):
            host.wait_for_face_maintenance_idle()

        self.assertEqual(len(queries), 1)
        self.assertIn("kind IN ('purge', 'cleanup')", queries[0])
        self.assertEqual(output.getvalue(),
                         'writer_idle_wait=face-maintenance-worker\n'
                         'writer_idle_timeout=face-maintenance-worker\n')

    def test_writer_stop_timeout_names_only_the_fixed_service(self):
        host = release.ReleaseHost()
        item = {'container_id': 'private-container-id', 'image': 'sha256:' + 'a' * 64,
                'restart_policy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0}}
        data = {'services': {'api': item}}
        host.journal = {}
        host.inspect = lambda _ident: {
            'Image': item['image'], 'State': {'Status': 'running'}}
        host.command = lambda *_args, **_kwargs: None
        host.record = lambda *_args, **_kwargs: None
        with patch.object(release.time, 'monotonic', side_effect=[0, 121]), \
                patch.object(release.time, 'sleep'), \
                patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(release.InventoryError, 'timeout_parada_graciosa_sem_sigkill'):
            host.stop_writers(data)
        self.assertEqual(output.getvalue(),
                         'writer_stop_requested=api\nwriter_stop_timeout=api\n')
        self.assertNotIn('private-container-id', output.getvalue())

    def test_interrupted_post_ddl_release_reinstalls_maintenance_fence(self):
        host = release.ReleaseHost()
        host.barrier = False
        calls = []
        host.maintenance = lambda enabled: calls.append(enabled)
        host.record = lambda phase, **_kwargs: calls.append(phase)
        host.write_interrupted_receipt('b' * 64, {'api': 'sha256:' + 'a' * 64}, None)
        self.assertEqual(calls, [True, 'recovery-required-after-migration-start'])


if __name__ == '__main__':
    unittest.main()
