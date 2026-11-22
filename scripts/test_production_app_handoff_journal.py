"""Real root-only filesystem contracts for the handoff phase journal."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_inventory as inventory_contracts


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'geteuid', lambda: -1)() == 0, 'root Linux filesystem required')
class HandoffJournalContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pyp-handoff-journal-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.enterContext(patch.object(bridge, 'MARKINA_STATE_ROOT', root))
        self.enterContext(patch.object(bridge, 'BRIDGE_STATE', root / 'bridge'))
        self.enterContext(patch.object(bridge, '_assert_common_lock_held'))
        fixture = inventory_contracts.HandoffInventoryContracts()
        fixture.setUp()
        self.plan = fixture.plan()
        self.observation = {'id': 'a' * 64, 'configuration': 'c' * 64}
        self.identity, self.revision = bridge.handoff_journal_create(self.plan)
        self.directory = bridge._handoff_journal_directory(self.identity)

    def advance(self, phase, revision=None, service='api'):
        return bridge.handoff_journal_advance(self.identity, revision or self.revision, service, phase, self.observation)

    def test_journal_is_private_bound_and_initially_prepared(self):
        plan, state, revision = bridge.handoff_journal_read(self.identity)
        self.assertEqual(plan, self.plan)
        self.assertEqual(state['phases'], {'api': 'prepared', 'web': 'prepared'})
        self.assertEqual(revision, self.revision)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        for path in self.directory.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_uid, 0)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_already_exists'):
            bridge.handoff_journal_create(self.plan)

    def test_order_and_revision_reject_skips_replay_and_web_before_api(self):
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_phase_order'):
            self.advance('retained')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_api_health_required'):
            self.advance('stop_intent', service='web')
        newer = self.advance('stop_intent')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_revision_changed'):
            self.advance('stopped')
        final = self.advance('stopped', revision=newer)
        _, state, actual = bridge.handoff_journal_read(self.identity)
        self.assertEqual(final, actual)
        self.assertEqual(state['phases']['api'], 'stopped')
        self.assertTrue((self.directory / 'state-000000.json').exists())

    def test_preparation_can_reconcile_only_before_any_effect_intent(self):
        self.assertEqual(bridge._handoff_prepare_journal(self.plan), (self.identity, self.revision))
        (self.directory / 'active.json').unlink()  # interruption before the first pointer is durable
        self.assertEqual(bridge._handoff_prepare_journal(self.plan), (self.identity, self.revision))
        self.advance('stop_intent')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_preparation_has_effect_intent'):
            bridge._handoff_prepare_journal(self.plan)

    def test_unactivated_preparation_rejects_unexplained_history(self):
        (self.directory / 'active.json').unlink()
        (self.directory / 'state-000001.json').write_text('unexplained')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_preparation_unproven'):
            bridge._handoff_prepare_journal(self.plan)
        self.assertFalse((self.directory / 'active.json').exists())

    def test_partial_input_archive_resumes_only_for_identical_private_bytes(self):
        path = self.directory / 'historical-0000.json'
        bridge._handoff_archive_file(path, b'private synthetic source')
        original = path.stat()
        bridge._handoff_archive_file(path, b'private synthetic source')
        self.assertEqual(path.stat().st_ino, original.st_ino)
        with self.assertRaises(bridge.BridgeError):
            bridge._handoff_archive_file(path, b'changed source')
        self.assertEqual(path.read_bytes(), b'private synthetic source')

    def test_failed_activation_keeps_previous_pointer_and_history(self):
        original = os.replace
        def fail_pointer(source, destination):
            if Path(destination).name == 'active.json':
                raise OSError('synthetic interruption before activation')
            return original(source, destination)
        with patch.object(os, 'replace', side_effect=fail_pointer), self.assertRaises(OSError):
            self.advance('stop_intent')
        _, state, revision = bridge.handoff_journal_read(self.identity)
        self.assertEqual(revision, self.revision)
        self.assertEqual(state['phases']['api'], 'prepared')
        # Uncommitted bytes are accepted only if the exact event matches.
        self.advance('stop_intent')
        self.assertEqual(bridge.handoff_journal_read(self.identity)[1]['phases']['api'], 'stop_intent')

    def test_tampering_older_history_or_plan_fails(self):
        self.advance('stop_intent')
        initial = self.directory / 'state-000000.json'
        content = initial.read_bytes()
        initial.write_bytes(b'{}')
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_journal_read(self.identity)
        initial.write_bytes(content)
        plan = self.directory / 'plan.json'
        plan.write_text('{}')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_plan_changed'):
            bridge.handoff_journal_read(self.identity)

    def test_metadata_symlink_and_arbitrary_pointer_fail(self):
        pointer = self.directory / 'active.json'
        content = pointer.read_bytes()
        pointer.chmod(0o644)
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_journal_read(self.identity)
        pointer.chmod(0o600)
        pointer.write_text(json.dumps({'state': '../../outside', 'sha256': 'a' * 64}))
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_pointer_invalid'):
            bridge.handoff_journal_read(self.identity)
        pointer.write_bytes(content)
        target = self.directory / 'saved-pointer'
        pointer.rename(target)
        pointer.symlink_to(target)
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_journal_read(self.identity)

    def test_witness_registration_requires_approval_and_blocks_new_extras(self):
        fixture = inventory_contracts.HandoffInventoryContracts()
        fixture.setUp()
        witness = copy.deepcopy(fixture.items[0])
        witness['Id'] = 'e' * 64
        witness['Name'] = '/historical-private-api'
        witness['State'].update(Running=False, Status='exited')
        source = bridge.BRIDGE_STATE / 'source.json'
        source.write_text('{}')
        source.chmod(0o600)
        proof = bridge.handoff_witness_inventory('a' * 40, fixture.items + [witness], fixture.records,
                                                {str(source): bridge.snapshot_sha256(source)}, 'f' * 64)
        with patch.object(bridge, '_handoff_validate_inputs'):
            with self.assertRaisesRegex(bridge.BridgeError, 'handoff_witness_approval_mismatch'):
                bridge.handoff_register_witnesses(proof, '0' * 64)
            bridge.handoff_register_witnesses(proof, bridge.digest(proof))
        registry = bridge.handoff_witness_registry()
        self.assertEqual(registry['witnesses'][0]['id'], witness['Id'])
        self.assertEqual((bridge.BRIDGE_STATE / 'handoff-witnesses.json').stat().st_mode & 0o777, 0o600)
        extra = copy.deepcopy(witness)
        extra['Id'] = 'f' * 64
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_unregistered_container'):
            bridge.handoff_witness_inventory('a' * 40, fixture.items + [witness, extra], fixture.records,
                                             {str(source): bridge.snapshot_sha256(source)}, 'f' * 64)
        witness['State']['Running'] = True
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_witness_inventory('a' * 40, fixture.items + [witness], fixture.records,
                                             {str(source): bridge.snapshot_sha256(source)}, 'f' * 64)

    def test_hardlink_and_unknown_observation_fail(self):
        pointer = self.directory / 'active.json'
        os.link(pointer, self.directory / 'second-link')
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_journal_read(self.identity)
        (self.directory / 'second-link').unlink()
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_journal_observation_invalid'):
            bridge.handoff_journal_advance(self.identity, self.revision, 'api', 'stop_intent', {'arbitrary': 'value'})


if __name__ == '__main__':
    unittest.main()
