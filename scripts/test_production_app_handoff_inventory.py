"""Private handoff inventory contracts derived from the approved transition spec."""
import copy
import unittest

import production_app_compose_bridge as bridge
from test_production_app_compose_bridge import SHA, semantic_fixture

BUNDLE = 'd' * 64


class HandoffInventoryContracts(unittest.TestCase):
    def setUp(self):
        self.items, self.models = [], {}
        for service, char in (('api', 'a'), ('web', 'b')):
            _, _, item, image = semantic_fixture()
            item['Id'] = char * 64
            item['Name'] = '/markina-gallery-' + service + '-1'
            item['Config']['Labels']['com.docker.compose.service'] = service
            item['State']['Running'] = True
            item['State']['Health'] = {'Status': 'healthy'}
            item['NetworkSettings']['Networks']['markina-gallery_internal']['Aliases'] = [service]
            self.items.append(item)
            self.models[service] = bridge.adoption_document(service, item, image)
        self.records = [bridge.handoff_record(s, i, bridge.PROJECT) for s, i in zip(bridge.SERVICES, self.items)]

    def plan(self, **overrides):
        args = {'target_sha': SHA, 'support_sha': 'f' * 40, 'bundle_sha256': BUNDLE,
                'items': self.items, 'active_records': self.records, 'models': self.models,
                'original_models': self.models, 'source_digests': {'/synthetic/source.json': 'e' * 64},
                'environment_digest': 'f' * 64, 'checkout_sha': SHA}
        return bridge.handoff_plan(**(args | overrides))

    def test_plan_binds_approved_identities_and_preserves_private_models(self):
        original = copy.deepcopy(self.models)
        plan = self.plan()
        self.assertEqual(plan['domain'], 'app-first-handoff-v1')
        self.assertEqual(plan['services']['api']['original_id'], 'a' * 64)
        self.assertEqual(plan['services']['web']['retained_name'], 'markina-gallery-retained-web-' + 'b' * 64)
        self.assertEqual(plan['models']['api']['services']['api']['container_name'], 'markina-gallery-api-1')
        self.assertEqual(self.models, original)
        self.assertNotEqual(bridge.digest(plan), bridge.digest(self.plan(bundle_sha256='e' * 64)))
        self.assertNotEqual(plan['project'], self.plan(support_sha='e' * 40)['project'])
        self.assertEqual(plan['models']['api']['services']['api']['environment'], original['api']['services']['api']['environment'])

    def test_selection_includes_only_exact_active_and_stopped_retained_ids(self):
        retained = copy.deepcopy(self.items[0])
        retained['Id'] = 'c' * 64
        retained['Name'] = '/markina-gallery-retained-api-' + retained['Id']
        retained['State']['Running'] = False
        retained_record = bridge.handoff_record('api', retained, bridge.PROJECT, retained=True)
        selected = bridge.handoff_select(self.items + [retained], self.records + [retained_record])
        self.assertEqual(selected['api']['Id'], 'a' * 64)
        retained['State']['Running'] = True
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_retained_running'):
            bridge.handoff_select(self.items + [retained], self.records + [retained_record])

    def test_unknown_generation_is_not_authorized_by_prefix(self):
        extra = copy.deepcopy(self.items[0])
        extra['Id'] = 'c' * 64
        extra['State']['Running'] = False
        extra['Config']['Labels']['com.docker.compose.project'] = 'markina-gallery-app-unregistered'
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_unregistered_container'):
            bridge.handoff_select(self.items + [extra], self.records)

    def test_concurrent_configuration_image_name_or_label_change_blocks_selection(self):
        mutations = (
            lambda i: i['Config']['Env'].append('CHANGED=sentinel'),
            lambda i: i.update(Image='sha256:' + 'f' * 64),
            lambda i: i.update(Name='/unexpected'),
            lambda i: i['Config']['Labels'].update({'com.docker.compose.project': 'another-project'}),
        )
        for mutate in mutations:
            items = copy.deepcopy(self.items)
            mutate(items[0])
            with self.subTest(mutation=mutate), self.assertRaises(bridge.BridgeError):
                self.plan(items=items)

    def test_collision_checks_all_names_including_unrelated_projects(self):
        occupied = {'Id': 'e' * 64, 'Name': '/markina-gallery-retained-api-' + 'a' * 64}
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_retained_name_occupied'):
            self.plan(items=self.items + [occupied])

    def test_non_external_resource_or_fabricated_labels_blocks_planning(self):
        models = copy.deepcopy(self.models)
        models['api']['networks']['unsafe'] = {'name': 'not-approved', 'external': False}
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_resource_not_external'):
            self.plan(models=models)
        models = copy.deepcopy(self.models)
        models['api']['services']['api']['labels']['com.docker.compose.config-hash'] = 'fabricated'
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_fabricated_compose_labels'):
            self.plan(models=models)

    def test_generation_changes_with_preserved_set_and_not_registry_order(self):
        before = self.plan()
        self.assertEqual(before, self.plan(active_records=list(reversed(self.records))))
        retained = copy.deepcopy(self.items[0])
        retained['Id'] = 'c' * 64
        retained['Name'] = '/markina-gallery-retained-api-' + retained['Id']
        retained['State']['Running'] = False
        record = bridge.handoff_record('api', retained, bridge.PROJECT, retained=True)
        after = self.plan(items=self.items + [retained], active_records=self.records + [record])
        self.assertNotEqual(before['project'], after['project'])

    def test_approved_stopped_witness_is_bound_but_never_selected(self):
        witness = copy.deepcopy(self.items[0])
        witness['Id'] = 'e' * 64
        witness['Name'] = '/historical-private-api'
        witness['State'].update(Running=False, Status='exited')
        record = bridge.handoff_witness_record(witness)
        plan = self.plan(items=self.items + [witness], active_records=self.records + [record])
        self.assertEqual(plan['services']['api']['original_id'], 'a' * 64)
        self.assertNotEqual(plan['project'], self.plan()['project'])
        witness['State']['Running'] = True
        with self.assertRaises(bridge.BridgeError):
            self.plan(items=self.items + [witness], active_records=self.records + [record])
        witness['State'].update(Running=False, Status='exited')
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_unregistered_container'):
            self.plan(items=self.items + [witness])
        witness['State']['StartedAt'] = 'synthetic-external-restart'
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_registry_runtime_mismatch'):
            self.plan(items=self.items + [witness], active_records=self.records + [record])

    def test_witness_cannot_hide_an_interrupted_original_or_retained(self):
        witness = copy.deepcopy(self.items[0])
        witness['State'].update(Running=False, Status='exited')
        for name in ('/markina-gallery-api-1', '/markina-gallery-retained-api-' + 'a' * 64):
            witness['Name'] = name
            with self.subTest(name=name), self.assertRaisesRegex(bridge.BridgeError, 'handoff_witness_invalid'):
                bridge.handoff_witness_record(witness)

    def test_invalid_identities_and_missing_records_fail_closed(self):
        for sha in ('main', '../escape', '0' * 39):
            with self.subTest(sha=sha), self.assertRaises(bridge.BridgeError):
                self.plan(target_sha=sha)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_registry_incomplete'):
            self.plan(items=self.items[:1])
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_registry_invalid'):
            self.plan(active_records=self.records + self.records[:1])


if __name__ == '__main__':
    unittest.main()
