from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview_adjustment_migration_release as release  # noqa: E402
from test_preview_adjustment_migration_inventory import valid_inventory  # noqa: E402


class PreviewMigrationReleaseHostTests(unittest.TestCase):
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

    def test_compose_uses_original_base_to_preserve_relative_environment_files(self):
        host = release.ReleaseHost()
        host.run = lambda *_args: '2.35.1'
        with patch.object(release.Path, 'is_file', return_value=True), \
                patch.object(release.Path, 'is_symlink', return_value=False):
            command = host.compose_command(valid_inventory(), Path('/candidate'), Path('/candidate/overlay.json'))
        self.assertIn(str(release.ROOT / 'docker/docker-compose.yml'), command)
        self.assertNotIn('/candidate/docker/docker-compose.yml', command)

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
        self.assertEqual(host.stop_writers(data), ['api'])

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
