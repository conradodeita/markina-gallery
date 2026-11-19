"""Recover an untouched legacy attempt without touching Docker or clearing blindly."""
import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_inventory as inventory_contracts


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'geteuid', lambda: -1)() == 0, 'root Linux filesystem required')
class LegacyRecoveryContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='pyp-legacy-recovery-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.enterContext(patch.object(bridge, 'PROJECT_ROOT', root))
        self.enterContext(patch.object(bridge, 'MARKINA_STATE_ROOT', root))
        self.enterContext(patch.object(bridge, 'BRIDGE_STATE', root / 'bridge'))
        self.enterContext(patch.object(bridge, 'STATE_DIR', root / 'deploy-state'))
        bridge.STATE_DIR.mkdir(mode=0o700)
        bridge._ensure_root_bridge_directory()
        self.support, self.target, self.baseline = 'e' * 40, 'd' * 40, 'c' * 40
        self.head = self.target
        fixture = inventory_contracts.HandoffInventoryContracts()
        fixture.setUp()
        for item in fixture.items:
            item['Config']['Env'] = ['APP_VERSION=' + self.baseline]
            item['Config']['Labels']['io.pickyourpic.release'] = self.baseline
        self.context = {'containers': dict(zip(bridge.SERVICES, fixture.items)),
                        'checkout_sha': self.target, 'digests': {}, 'environment_digest': 'f' * 64}
        self.records = fixture.records
        directory = bridge._operation_directory('release', self.target, 'a' * 64)
        directory.mkdir(mode=0o700)
        self.directory = directory
        self.write(directory / 'manifest.json', {'version': 1, 'target_sha': self.target,
                   'fingerprint': 'a' * 64, 'models': fixture.models,
                   'containers': copy.deepcopy(self.context['containers'])})
        candidates = {}
        for service in bridge.SERVICES:
            path = directory / ('apply-' + service + '.compose.json')
            self.write(path, fixture.models[service])
            candidates[service] = bridge.snapshot_sha256(path)
        transition = {'version': 1, 'mode': 'release', 'target_sha': self.target,
                      'approval': 'a' * 64, 'manifest_sha256': bridge.snapshot_sha256(directory / 'manifest.json'),
                      'candidates': candidates}
        self.write(directory / 'transition.json', transition)
        self.write(bridge.BRIDGE_STATE / 'active-transition.json', {
            'mode': 'release', 'target_sha': self.target, 'approval': 'a' * 64,
            'sha256': bridge.snapshot_sha256(directory / 'transition.json')})
        self.marker = bridge.STATE_DIR / 'app-in-flight.sha'
        self.marker.write_text(self.target + '\n')
        self.marker.chmod(0o600)
        self.enterContext(patch.object(bridge, '_handoff_proven_context', self.proven_context))
        self.enterContext(patch.object(bridge, '_handoff_context_records', return_value=self.records))
        self.enterContext(patch.object(bridge, '_handoff_read_items', return_value=fixture.items))
        self.enterContext(patch.object(bridge, 'handoff_witness_inventory', return_value={'witnesses': []}))
        self.enterContext(patch.object(bridge, 'handoff_witness_registry', return_value={'witnesses': []}))
        self.enterContext(patch.object(bridge, '_assert_common_lock_held'))
        self.enterContext(patch.object(bridge, '_git', self.git))
        self.docker = self.enterContext(patch.object(bridge, '_docker', side_effect=AssertionError('Docker mutation forbidden')))

    def write(self, path, value):
        bridge._write_private_file(path, json.dumps(value, sort_keys=True).encode())

    @contextmanager
    def proven_context(self, support):
        self.assertEqual(support, self.support)
        self.context['checkout_sha'] = self.head
        yield self.context

    def git(self, *args):
        if args == ('rev-parse', 'HEAD'):
            return self.head
        if args[:2] == ('merge-base', '--is-ancestor'):
            return ''
        raise AssertionError(args)

    def arguments(self, operation, approval=None):
        return SimpleNamespace(operation=operation, sha=self.support,
                               approval_fingerprint=approval or bridge.digest(bridge._handoff_legacy_proof(self.support)))

    def invoke(self, operation, approval):
        with redirect_stdout(io.StringIO()) as output:
            result = bridge._handoff_legacy_cli(self.arguments(operation, approval))
        self.assertEqual(result, 0)
        self.docker.assert_not_called()
        return output.getvalue()

    def prepare(self):
        approval = bridge.digest(bridge._handoff_legacy_proof(self.support))
        self.invoke('handoff-legacy-recovery-prepare', approval)
        return approval

    def test_proof_binds_intact_originals_marker_and_private_sources(self):
        proof = bridge._handoff_legacy_proof(self.support)
        self.assertEqual(proof['restore_checkout'], self.baseline)
        self.assertTrue(proof['marker_present'])
        self.assertIn(str(self.directory / 'transition.json'), proof['source_digests'])
        self.context['containers']['api']['Image'] = 'sha256:' + '1' * 64
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_originals_not_intact'):
            bridge._handoff_legacy_proof(self.support)
        self.assertTrue(self.marker.exists())

    def test_wrong_approval_or_missing_witness_registration_cannot_prepare(self):
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_approval_mismatch'):
            self.invoke('handoff-legacy-recovery-prepare', '0' * 64)
        with patch.object(bridge, 'handoff_witness_registry', return_value=None), \
                self.assertRaisesRegex(bridge.BridgeError, 'handoff_witness_registration_required'):
            self.prepare()
        self.assertTrue(self.marker.exists())

    def test_only_restored_checkout_allows_finalization(self):
        approval = self.prepare()
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_checkout_not_restored'):
            self.invoke('handoff-legacy-recovery-finalize', approval)
        self.assertTrue(self.marker.exists())
        self.head = self.baseline
        output = self.invoke('handoff-legacy-recovery-finalize', approval)
        self.assertIn('legacy_recovery_status=healthy', output)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.invoke('handoff-legacy-recovery-finalize', approval), output)

    def test_proxy_is_available_only_after_proven_checkout_restoration(self):
        approval = self.prepare()
        with patch.object(bridge, '_handoff_nginx') as nginx:
            with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_checkout_not_restored'):
                self.invoke('handoff-legacy-recovery-proxy', approval)
            nginx.assert_not_called()
            self.head = self.baseline
            self.invoke('handoff-legacy-recovery-proxy', approval)
            nginx.assert_called_once_with()
        self.assertTrue(self.marker.exists())

    def test_marker_absence_without_durable_intent_is_not_success(self):
        approval = self.prepare()
        self.head = self.baseline
        self.marker.unlink()
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_marker_required'):
            self.invoke('handoff-legacy-recovery-finalize', approval)

    def test_interruption_after_unlink_can_finish_from_durable_intent(self):
        approval = self.prepare()
        self.head = self.baseline
        original = bridge._write_private_file
        def interrupt(path, content):
            if path.name == 'committed.json':
                raise OSError('synthetic receipt interruption')
            return original(path, content)
        with patch.object(bridge, '_write_private_file', interrupt), self.assertRaises(OSError):
            self.invoke('handoff-legacy-recovery-finalize', approval)
        self.assertFalse(self.marker.exists())
        self.invoke('handoff-legacy-recovery-finalize', approval)

    def test_changed_marker_source_or_original_blocks_finalization(self):
        approval = self.prepare()
        self.head = self.baseline
        self.marker.write_text('1' * 40)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_legacy_marker_changed'):
            self.invoke('handoff-legacy-recovery-finalize', approval)
        self.marker.write_text(self.target)
        path = self.directory / 'apply-api.compose.json'
        path.write_text('{}')
        with self.assertRaises(bridge.BridgeError):
            self.invoke('handoff-legacy-recovery-finalize', approval)
        self.assertTrue(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
