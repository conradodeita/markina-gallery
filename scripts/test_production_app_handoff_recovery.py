"""Recovery contracts for stopped originals and interrupted candidate creation."""
import copy
import os
import unittest
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_execution as execution_contracts


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'geteuid', lambda: -1)() == 0, 'root Linux filesystem required')
class HandoffRecoveryContracts(unittest.TestCase):
    def setUp(self):
        self.execution = execution_contracts.HandoffExecutionContracts()
        self.execution.setUp()
        self.addCleanup(self.execution.doCleanups)
        self.identity = self.execution.identity
        self.revision = self.execution.revision

    def inventory(self, schema=None):
        e = self.execution
        return bridge.handoff_recovery_inventory(self.identity, e.items, {e.image['Id']: e.image}, schema)

    def stopped_original(self):
        self.execution.fail_after_stop = True
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_execute_service(self.identity, self.revision, 'api')
        self.execution.fail_after_stop = False

    def test_inventory_distinguishes_unavailable_schema_without_mutation(self):
        self.stopped_original()
        before = copy.deepcopy(self.execution.items)
        count = len(self.execution.calls)
        inventory = self.inventory()
        self.assertEqual(inventory['schema_status'], 'unavailable')
        self.assertIsNone(inventory['schema'])
        self.assertFalse(inventory['services']['api']['original_running'])
        self.assertIsNone(inventory['services']['api']['candidate'])
        self.assertEqual(self.execution.items, before)
        self.assertEqual(count, len(self.execution.calls))
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_recovery_schema_mismatch'):
            self.inventory('unexpected')

    def test_separate_approval_starts_only_the_proven_stopped_original(self):
        self.stopped_original()
        inventory = self.inventory()
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_recovery_approval_mismatch'):
            bridge.handoff_recovery_prepare(inventory, '0' * 64)
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        count = len(self.execution.calls)
        bridge.handoff_recover_service(identity, revision, 'api')
        self.assertTrue(self.execution.items[0]['State']['Running'])
        mutations = [c for c in self.execution.calls[count:] if c[0] in {'stop', 'rename', 'start', 'rm'}]
        self.assertEqual(mutations, [['start', 'a' * 64]])
        self.assertEqual(bridge.handoff_journal_read(identity)[1]['phases']['api'], 'healthy')

    def test_candidate_is_parked_and_original_restored_without_removal(self):
        bridge.handoff_execute_service(self.identity, self.revision, 'api')
        inventory = self.inventory('20261113_0126')
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        bridge.handoff_recover_service(identity, revision, 'api')
        original, candidate = self.execution.items[0], self.execution.items[-1]
        self.assertEqual(original['Name'], '/markina-gallery-api-1')
        self.assertTrue(original['State']['Running'])
        self.assertFalse(candidate['State']['Running'])
        self.assertEqual(candidate['Name'], '/markina-gallery-retained-api-' + candidate['Id'])
        self.assertFalse(any(c[0] in {'rm', 'remove', 'prune'} for c in self.execution.calls))

    def test_wrong_schema_after_restoring_prevents_healthy_receipt(self):
        self.stopped_original()
        inventory = self.inventory()
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        original = self.execution.docker
        def wrong_schema(args, **kwargs):
            if args[0] == 'exec':
                return 'unexpected_schema\n'
            return original(args, **kwargs)
        with patch.object(bridge, '_docker', side_effect=wrong_schema), self.assertRaisesRegex(bridge.BridgeError, 'handoff_restored_schema_mismatch'):
            bridge.handoff_recover_service(identity, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(identity)[1]['phases']['api'], 'original_started')
        self.assertTrue(self.execution.items[0]['State']['Running'])

    def test_interrupted_recovery_is_reinventoried_with_new_approval(self):
        bridge.handoff_execute_service(self.identity, self.revision, 'api')
        inventory = self.inventory('20261113_0126')
        recovery, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        candidate_id = self.execution.items[-1]['Id']
        original = self.execution.docker
        def crash_after_rename(args, **kwargs):
            result = original(args, **kwargs)
            if args[0] == 'rename' and args[1] == candidate_id:
                raise bridge.BridgeError('synthetic_recovery_crash')
            return result
        with patch.object(bridge, '_docker', side_effect=crash_after_rename), self.assertRaisesRegex(bridge.BridgeError, 'synthetic_recovery_crash'):
            bridge.handoff_recover_service(recovery, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(recovery)[1]['phases']['api'], 'candidate_rename_intent')
        e = self.execution
        resumed_inventory = bridge.handoff_recovery_inventory(recovery, e.items, {e.image['Id']: e.image}, None, support_sha='e' * 40)
        self.assertEqual(resumed_inventory['schema_status'], 'unavailable')
        self.assertEqual(resumed_inventory['support_sha'], 'e' * 40)
        self.assertNotEqual(bridge.digest(inventory), bridge.digest(resumed_inventory))
        resumed, revision = bridge.handoff_recovery_prepare(resumed_inventory, bridge.digest(resumed_inventory))
        bridge.handoff_recover_service(resumed, revision, 'api')
        self.assertTrue(e.items[0]['State']['Running'])
        self.assertFalse(e.items[-1]['State']['Running'])
        self.assertEqual(bridge.handoff_journal_read(resumed)[1]['phases']['api'], 'healthy')

    def test_changed_name_image_phase_or_missing_original_blocks_inventory(self):
        for mutation in (
            lambda i: i.update(Name='/unexpected'),
            lambda i: i.update(Image='sha256:' + 'f' * 64),
            lambda i: i['State'].update(Running=False),
        ):
            before = copy.deepcopy(self.execution.items)
            mutation(self.execution.items[0])
            with self.assertRaises(bridge.BridgeError):
                self.inventory()
            self.execution.items[:] = before
        self.execution.items.pop(0)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_recovery_original_missing'):
            self.inventory()


if __name__ == '__main__':
    unittest.main()
