from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_adjustment_migration_inventory import canonical_fingerprint  # noqa: E402
from preview_adjustment_migration_release_flow import ReleaseError, execute  # noqa: E402
from test_preview_adjustment_migration_inventory import valid_inventory  # noqa: E402


class FakeHost:
    def __init__(self, fail=None):
        self.value = valid_inventory()
        self.events = []
        self.fail = fail

    def event(self, name):
        self.events.append(name)
        if name == self.fail:
            raise RuntimeError('synthetic failure')

    def inventory(self, _support_sha):
        self.event('inventory')
        return copy.deepcopy(self.value)

    def preserve_images(self, _inventory):
        self.event('preserve')
        return {'api': 'old-api', 'web': 'old-web'}

    def start_journal(self, _fingerprint):
        self.event('journal-start')

    def finish_journal(self):
        self.event('journal-finish')

    def stage_candidate(self, _inventory):
        self.event('stage')
        return {'api': 'candidate-api', 'web': 'candidate-web'}

    def assert_support_sha(self, _support_sha):
        self.event('support-current')

    def assert_historical_preserved(self, _inventory):
        self.event('historical-preserved')

    def maintenance(self, enabled):
        self.event('maintenance-on' if enabled else 'maintenance-off')

    def stop_writers(self, _inventory):
        self.event('stop')
        return ['api', 'worker']

    def assert_writers_idle(self, _inventory, _stopped):
        self.event('idle')

    def backup_and_verify(self, _inventory):
        self.event('backup')
        return {'sha256': 'f' * 64}

    def assert_backup(self, _backup, _inventory):
        self.event('backup-verified')

    def apply_migration(self, _image, revision):
        if revision != '20261026_0090':
            raise RuntimeError('wrong revision')
        self.event('migration')

    def database_revision(self):
        self.event('schema')
        return '20261026_0090'

    def publish_api_web(self, _candidate):
        self.event('publish')

    def start_writers(self, _inventory, _stopped):
        self.event('start-writers')

    def assert_runtime(self, _candidate, _inventory, _previous, _stopped):
        self.event('runtime')

    def assert_https_healthy(self):
        self.event('https')

    def write_success_receipt(self, *_args):
        self.event('success-receipt')

    def write_interrupted_receipt(self, *_args):
        self.event('interrupted-receipt')

    def restore_before_migration(self, _inventory, _stopped, _previous, _barrier):
        self.event('recover-before-ddl')


class PreviewMigrationReleaseFlowTests(unittest.TestCase):
    def test_historical_change_stops_before_maintenance_or_ddl(self):
        host = FakeHost(fail='historical-preserved')
        with self.assertRaises(ReleaseError):
            execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertNotIn('migration', host.events)
        self.assertNotIn('maintenance-on', host.events)

    def test_historical_change_after_ddl_keeps_fence(self):
        host = FakeHost()
        def verify(_inventory):
            if 'publish' in host.events:
                raise RuntimeError('historical changed')
        host.assert_historical_preserved = verify
        with self.assertRaises(ReleaseError):
            execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertIn('interrupted-receipt', host.events)
        self.assertNotIn('maintenance-off', host.events)

    def test_approved_release_orders_backup_ddl_runtime_and_ingress(self):
        host = FakeHost()
        execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertLess(host.events.index('backup-verified'), host.events.index('migration'))
        self.assertLess(host.events.index('migration'), host.events.index('publish'))
        self.assertLess(host.events.index('runtime'), host.events.index('maintenance-off'))
        self.assertEqual(host.events[-3:], ['https', 'success-receipt', 'journal-finish'])

    def test_bad_approval_stops_before_any_mutation(self):
        host = FakeHost()
        with self.assertRaisesRegex(ReleaseError, 'fingerprint_aprovado_divergente'):
            execute(host, 'a' * 40, 'b' * 64)
        self.assertEqual(host.events, ['inventory'])

    def test_failure_before_ddl_restores_previous_runtime(self):
        host = FakeHost(fail='backup')
        with self.assertRaisesRegex(ReleaseError, 'release_falhou'):
            execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertEqual(host.events[-2:], ['recover-before-ddl', 'journal-finish'])
        self.assertNotIn('migration', host.events)

    def test_candidate_build_failure_before_ingress_is_cleaned_up(self):
        host = FakeHost(fail='stage')
        with self.assertRaisesRegex(ReleaseError, 'release_falhou'):
            execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertEqual(host.events[-2:], ['recover-before-ddl', 'journal-finish'])
        self.assertNotIn('maintenance-on', host.events)
        self.assertNotIn('migration', host.events)

    def test_failure_after_ddl_keeps_fence_and_never_runs_automatic_rollback(self):
        host = FakeHost(fail='publish')
        with self.assertRaisesRegex(ReleaseError, 'release_falhou'):
            execute(host, 'a' * 40, canonical_fingerprint(host.value))
        self.assertIn('interrupted-receipt', host.events)
        self.assertNotIn('recover-before-ddl', host.events)
        self.assertNotIn('maintenance-off', host.events)


if __name__ == '__main__':
    unittest.main()
