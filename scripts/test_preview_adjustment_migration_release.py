from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview_adjustment_migration_release as release  # noqa: E402
from test_preview_adjustment_migration_inventory import valid_inventory  # noqa: E402


class PreviewMigrationReleaseHostTests(unittest.TestCase):
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
