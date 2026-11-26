"""Handoff sequencing against a real private journal and controlled Engine boundary."""
import copy
import json
import os
import unittest
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_inventory as inventory_contracts
import test_production_app_handoff_journal as journal_contracts
from test_production_app_compose_bridge import semantic_fixture


@unittest.skipUnless(os.name == 'posix' and getattr(os, 'geteuid', lambda: -1)() == 0, 'root Linux filesystem required')
class HandoffExecutionContracts(unittest.TestCase):
    def setUp(self):
        self.journal = journal_contracts.HandoffJournalContracts()
        self.journal.setUp()
        self.addCleanup(self.journal.doCleanups)
        self.identity, self.revision = self.journal.identity, self.journal.revision
        fixture = inventory_contracts.HandoffInventoryContracts()
        fixture.setUp()
        self.items = copy.deepcopy(fixture.items)
        self.image = semantic_fixture()[3]
        self.calls = []
        self.fail_after_stop = False
        self.enterContext(patch.object(bridge, '_validate_env_file', return_value=self.journal.plan['environment_digest']))
        self.enterContext(patch.object(bridge, '_validate_snapshot_source', side_effect=lambda path: self.journal.plan['source_digests'][str(path)]))
        self.enterContext(patch.object(bridge, '_docker', side_effect=self.docker))
        self.enterContext(patch.object(bridge, '_run', side_effect=self.run_command))

    def docker(self, args, **kwargs):
        self.calls.append(args)
        if args[0] == 'exec':
            return '20261113_0126\n'
        if args[0] == 'ps':
            return ''
        if args[0] == 'inspect':
            return json.dumps([next(i for i in self.items if i['Id'] == args[1] or i['Name'] == '/' + args[1])])
        if args[:2] == ['image', 'inspect']:
            return json.dumps([self.image])
        item = next(i for i in self.items if i['Id'] == args[-1 if args[0] == 'stop' else 1])
        if args[0] == 'stop':
            item['State']['Running'] = False
            if self.fail_after_stop:
                raise bridge.BridgeError('synthetic_effect_before_receipt')
        elif args[0] == 'start':
            item['State']['Running'] = True
            item['State']['Status'] = 'running'
            item['State']['Health'] = {'Status': 'healthy'}
        elif args[0] == 'rename':
            self.assertFalse(item['State']['Running'])
            item['Name'] = '/' + args[2]
        else:
            self.fail('unexpected mutation ' + args[0])
        return ''

    def run_command(self, args, **kwargs):
        self.calls.append(args)
        self.assertIn('--no-deps', args)
        self.assertIn('--no-build', args)
        self.assertEqual(args[args.index('--pull') + 1], 'never')
        self.assertEqual(args[args.index('-p') + 1], self.journal.plan['project'])
        service = args[-1]
        original = next(i for i in self.items if i['Config']['Labels']['com.docker.compose.service'] == service)
        self.assertFalse(original['State']['Running'])
        self.assertIn('-retained-', original['Name'])
        candidate = copy.deepcopy(original)
        candidate['Id'] = ('c' if service == 'api' else 'd') * 64
        candidate['Name'] = '/markina-gallery-' + service + '-1'
        candidate['Config']['Labels']['com.docker.compose.project'] = self.journal.plan['project']
        candidate['State']['Running'] = True
        self.items.append(candidate)
        return ''

    def test_api_then_web_keeps_originals_and_records_healthy_candidates(self):
        revision = bridge.handoff_execute_service(self.identity, self.revision, 'api')
        bridge.handoff_execute_service(self.identity, revision, 'web')
        _, state, _ = bridge.handoff_journal_read(self.identity)
        self.assertEqual(state['phases'], {'api': 'healthy', 'web': 'healthy'})
        self.assertEqual([i['Id'] for i in self.items if not i['State']['Running']], ['a' * 64, 'b' * 64])
        self.assertFalse(any(c[0] in {'rm', 'remove', 'prune'} for c in self.calls))

    def test_changed_source_or_environment_cannot_stop_original(self):
        for boundary in ('_validate_env_file', '_validate_snapshot_source'):
            with patch.object(bridge, boundary, return_value='0' * 64), self.assertRaises(bridge.BridgeError):
                bridge.handoff_execute_service(self.identity, self.revision, 'api')
            self.assertFalse(self.calls)
            self.assertTrue(self.items[0]['State']['Running'])

    def test_web_cannot_stop_before_api_is_proven_healthy(self):
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_api_health_required'):
            bridge.handoff_execute_service(self.identity, self.revision, 'web')
        self.assertFalse(self.calls)

    def test_crash_after_stop_keeps_intent_and_cannot_resume_blindly(self):
        self.fail_after_stop = True
        with self.assertRaisesRegex(bridge.BridgeError, 'synthetic_effect_before_receipt'):
            bridge.handoff_execute_service(self.identity, self.revision, 'api')
        _, state, revision = bridge.handoff_journal_read(self.identity)
        self.assertEqual(state['phases']['api'], 'stop_intent')
        self.assertFalse(self.items[0]['State']['Running'])
        count = len(self.calls)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_execution_requires_prepared'):
            bridge.handoff_execute_service(self.identity, revision, 'api')
        self.assertEqual(count, len(self.calls))


if __name__ == '__main__':
    unittest.main()
