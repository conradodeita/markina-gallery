"""Recovery contracts for stopped originals and interrupted candidate creation."""
import copy
import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_execution as execution_contracts


class PickerFreeRecoveryRecipeTests(unittest.TestCase):
    def document(self, volumes=None, **model_fields):
        model = {"image": "sha256:" + "a" * 64, **model_fields}
        if volumes is not None:
            model["volumes"] = copy.deepcopy(volumes)
        return {"services": {"api": model}, "networks": {}, "volumes": {}}

    def test_removes_only_exact_picker_bind_and_preserves_oauth_and_other_mounts(self):
        media = {"type": "volume", "source": "media", "target": "/media"}
        oauth = {"type": "bind", "source": "/etc/pyp-google-drive/oauth-client.json",
                 "target": "/run/secrets/google-drive-oauth-client.json", "read_only": True}
        picker = {"type": "bind", "source": bridge.PICKER_CONFIG_SOURCE,
                  "target": bridge.PICKER_CONFIG_TARGET, "read_only": True,
                  "bind": {"propagation": "rprivate", "create_host_path": False}}
        original = self.document([media, oauth, picker], environment={"APP_ENV": "production"})

        sanitized, removed = bridge._picker_free_recovery_model("api", original)

        self.assertTrue(removed)
        self.assertEqual(sanitized["services"]["api"]["image"], "sha256:" + "a" * 64)
        self.assertEqual(sanitized["services"]["api"]["volumes"], [media, oauth])
        self.assertEqual(original["services"]["api"]["volumes"], [media, oauth, picker])

    def test_model_without_picker_is_preserved(self):
        oauth = {"type": "bind", "source": "/etc/pyp-google-drive/oauth-client.json",
                 "target": "/run/secrets/google-drive-oauth-client.json", "read_only": True}
        original = self.document([oauth], environment={"APP_ENV": "production"})

        sanitized, removed = bridge._picker_free_recovery_model("api", original)

        self.assertFalse(removed)
        self.assertEqual(sanitized, original)

    def test_ambiguous_parent_noncanonical_duplicate_and_wrong_type_mounts_fail_closed(self):
        exact = {"type": "bind", "source": bridge.PICKER_CONFIG_SOURCE,
                 "target": bridge.PICKER_CONFIG_TARGET, "read_only": True}
        variants = (
            [{"type": "bind", "source": "/etc/pyp-google-drive", "target": "/run/secrets"}],
            [{"type": "bind", "source": bridge.PICKER_CONFIG_SOURCE, "target": "/run/secrets/other.json"}],
            [{"type": "bind", "source": "/etc/other/picker-config.json", "target": bridge.PICKER_CONFIG_TARGET}],
            [{"type": "bind", "source": "/etc/pyp-google-drive/../pyp-google-drive/picker-config.json",
              "target": bridge.PICKER_CONFIG_TARGET}],
            [{"type": "volume", "source": "picker-config", "target": bridge.PICKER_CONFIG_TARGET}],
            [exact, copy.deepcopy(exact)],
        )
        for mounts in variants:
            with self.subTest(mounts=mounts), self.assertRaises(bridge.BridgeError):
                bridge._picker_free_recovery_model("api", self.document(mounts))
        with self.assertRaisesRegex(bridge.BridgeError, "handoff_recovery_recipe_picker_mount_ambiguous"):
            bridge._picker_free_recovery_model("api", self.document([], tmpfs=["/run/secrets:rw"]))

    def test_recipe_binds_image_model_and_hashes_to_original_identity(self):
        api = self.document([{"type": "bind", "source": bridge.PICKER_CONFIG_SOURCE,
                             "target": bridge.PICKER_CONFIG_TARGET, "read_only": True}],
                            environment={"APP_ENV": "production"})
        web = {"services": {"web": {"image": "sha256:" + "b" * 64, "volumes": []}},
               "networks": {}, "volumes": {}}
        plan = {"original_models": {"api": api, "web": web},
                "sources": [{"service": "api", "retained": False, "image": "sha256:" + "a" * 64},
                            {"service": "web", "retained": False, "image": "sha256:" + "b" * 64}]}

        recipe = bridge._handoff_picker_free_recovery_recipe(plan)
        unsigned = {key: value for key, value in recipe.items() if key != "sha256"}
        self.assertEqual(recipe["sha256"], bridge.digest(unsigned))
        self.assertTrue(recipe["services"]["api"]["picker_bind_removed"])
        self.assertEqual(recipe["services"]["api"]["image_id"], "sha256:" + "a" * 64)
        self.assertEqual(recipe["services"]["api"]["model_sha256"],
                         bridge.digest(recipe["services"]["api"]["model"]))
        self.assertFalse(recipe["services"]["web"]["picker_bind_removed"])
        plan["domain"] = "app-first-handoff-recovery-plan-v1"
        plan["picker_free_recovery_recipe"] = recipe
        plan["recovery_project"] = "markina-gallery-app-" + "c" * 32
        plan["recovery_models"] = {}
        for service in bridge.SERVICES:
            model = copy.deepcopy(recipe["services"][service]["model"])
            model["services"][service]["container_name"] = "markina-gallery-" + service + "-1"
            plan["recovery_models"][service] = model
        plan["recovery_model_sha256"] = {service: bridge.digest(model)
                                         for service, model in plan["recovery_models"].items()}
        self.assertEqual(bridge._handoff_validate_picker_free_recovery_plan(plan), plan["recovery_models"])
        plan["recovery_model_sha256"]["api"] = "0" * 64
        with self.assertRaisesRegex(bridge.BridgeError, "handoff_recovery_model_changed"):
            bridge._handoff_validate_picker_free_recovery_plan(plan)
        plan["sources"][0]["image"] = "sha256:" + "c" * 64
        with self.assertRaisesRegex(bridge.BridgeError, "handoff_recovery_recipe_image_mismatch"):
            bridge._handoff_picker_free_recovery_recipe(plan)


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

    def compose_create(self, identity):
        e = self.execution
        plan, _, _ = bridge.handoff_journal_read(identity)

        def create(args, **kwargs):
            e.calls.append(args)
            self.assertIn('create', args)
            self.assertIn('--no-build', args)
            self.assertIn('--no-recreate', args)
            self.assertEqual(args[args.index('--pull') + 1], 'never')
            self.assertEqual(args[args.index('-p') + 1], plan['recovery_project'])
            service = args[-1]
            source_record = next(record for record in plan['sources']
                                 if record['service'] == service and not record['retained'])
            source = next(item for item in e.items if item['Id'] == source_record['id'])
            self.assertFalse(source['State']['Running'])
            self.assertIn('-retained-', source['Name'])
            recipe = plan['picker_free_recovery_recipe']['services'][service]
            candidate = bridge._handoff_picker_free_expected_runtime(service, source, recipe['picker_bind_removed'])
            candidate_id = ('e' if service == 'api' else 'f') * 64
            candidate['Id'] = candidate_id
            candidate['Image'] = recipe['image_id']
            candidate['Name'] = '/markina-gallery-' + service + '-1'
            candidate['Config']['Hostname'] = plan['recovery_models'][service]['services'][service].get(
                'hostname', candidate_id[:12])
            candidate['Config']['Labels']['com.docker.compose.project'] = plan['recovery_project']
            candidate['Config']['Labels']['com.docker.compose.service'] = service
            candidate['State'].update(Running=False, Status='created', Health={'Status': 'starting'})
            for network in candidate.get('NetworkSettings', {}).get('Networks', {}).values():
                network['Aliases'] = sorted({service, candidate_id[:12], candidate['Name'].lstrip('/')})
            e.items.append(candidate)
            return ''

        return patch.object(bridge, '_run', side_effect=create)

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

    def test_separate_approval_creates_picker_free_candidate_without_starting_original(self):
        self.stopped_original()
        inventory = self.inventory()
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_recovery_approval_mismatch'):
            bridge.handoff_recovery_prepare(inventory, '0' * 64)
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        saved_plan, _, _ = bridge.handoff_journal_read(identity)
        recipe = saved_plan["picker_free_recovery_recipe"]
        self.assertEqual(recipe["domain"], "app-picker-free-recovery-recipe-v1")
        self.assertEqual(recipe["sha256"], bridge.digest({key: value for key, value in recipe.items() if key != "sha256"}))
        self.assertFalse(recipe["services"]["api"]["picker_bind_removed"])
        count = len(self.execution.calls)
        with self.compose_create(identity):
            bridge.handoff_recover_service(identity, revision, 'api')
        original, recovered = self.execution.items[0], self.execution.items[-1]
        self.assertFalse(original['State']['Running'])
        self.assertIn('-retained-', original['Name'])
        self.assertTrue(recovered['State']['Running'])
        self.assertEqual(recovered['Config']['Labels']['com.docker.compose.project'], saved_plan['recovery_project'])
        mutations = [c for c in self.execution.calls[count:] if c[0] in {'stop', 'rename', 'start', 'rm'}]
        self.assertIn(['start', recovered['Id']], mutations)
        self.assertNotIn(['start', original['Id']], mutations)
        self.assertEqual(bridge.handoff_journal_read(identity)[1]['phases']['api'], 'healthy')

    def test_candidate_and_original_are_parked_before_picker_free_recreation(self):
        bridge.handoff_execute_service(self.identity, self.revision, 'api')
        inventory = self.inventory('20261113_0126')
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        with self.compose_create(identity):
            bridge.handoff_recover_service(identity, revision, 'api')
        original, previous_candidate, recovered = self.execution.items[0], self.execution.items[-2], self.execution.items[-1]
        self.assertFalse(original['State']['Running'])
        self.assertIn('-retained-', original['Name'])
        self.assertFalse(previous_candidate['State']['Running'])
        self.assertIn('-retained-', previous_candidate['Name'])
        self.assertTrue(recovered['State']['Running'])
        self.assertEqual(recovered['Name'], '/markina-gallery-api-1')
        self.assertFalse(any(c[0] in {'rm', 'remove', 'prune'} for c in self.execution.calls))

    def test_recovery_orders_api_before_web_and_never_starts_source_containers(self):
        self.stopped_original()
        inventory = self.inventory()
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        before = len(self.execution.calls)
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_api_health_required'):
            bridge.handoff_recover_service(identity, revision, 'web')
        self.assertEqual(len(self.execution.calls), before)

        with self.compose_create(identity):
            revision = bridge.handoff_recover_service(identity, revision, 'api')
            revision = bridge.handoff_recover_service(identity, revision, 'web')
        _, state, _ = bridge.handoff_journal_read(identity)
        self.assertEqual(state['phases'], {'api': 'healthy', 'web': 'healthy'})
        self.assertEqual([item['Id'] for item in self.execution.items[:2] if item['State']['Running']], [])
        started_ids = [call[1] for call in self.execution.calls if call[0] == 'start']
        self.assertEqual(started_ids, ['e' * 64, 'f' * 64])
        self.assertNotIn('a' * 64, started_ids)
        self.assertNotIn('b' * 64, started_ids)

    def test_publish_uses_healthy_picker_free_generation_and_retains_previous_runtime(self):
        self.stopped_original()
        inventory = self.inventory()
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        with self.compose_create(identity):
            revision = bridge.handoff_recover_service(identity, revision, 'api')
            bridge.handoff_recover_service(identity, revision, 'web')

        plan, _, _ = bridge.handoff_journal_read(identity)
        published = {}
        base_context = {'paths': [], 'digests': {}, 'sources': {}, 'config_hashes': {}}
        read_journal = bridge.handoff_journal_read

        def read_with_original_version(journal_identity):
            current_plan, state, current_revision = read_journal(journal_identity)
            current_plan['original_web_version'] = 'a' * 40
            return current_plan, state, current_revision

        def prepare_context(context, *args):
            context['models'] = copy.deepcopy(plan['recovery_models'])
            context['semantic_hashes'] = {'web': 'a' * 64}
            return context

        def publish_runtime(context, models, proof, approval, handoff_records=None):
            published.update(context=context, models=copy.deepcopy(models), proof=proof,
                             approval=approval, records=copy.deepcopy(handoff_records))

        with (patch.object(bridge, '_handoff_read_items', return_value=self.execution.items),
              patch.object(bridge, 'handoff_journal_read', side_effect=read_with_original_version),
              patch.object(bridge, '_discover_context', return_value=base_context),
              patch.object(bridge, '_prepare_compose_context', side_effect=prepare_context),
              patch.object(bridge, '_prove_context'),
              patch.object(bridge, '_publish_runtime_base', side_effect=publish_runtime)):
            receipt = bridge.handoff_publish_runtime(identity, restoring=True)

        active = [record for record in published['records'] if not record['retained']]
        retained_ids = {record['id'] for record in published['records'] if record['retained']}
        self.assertEqual(receipt['checkout_sha'], plan['checkout_sha'])
        self.assertEqual(published['approval'], plan['approval'])
        self.assertEqual({record['service'] for record in active}, {'api', 'web'})
        self.assertEqual({record['project'] for record in active}, {plan['recovery_project']})
        self.assertEqual({record['id'] for record in active}, {'e' * 64, 'f' * 64})
        self.assertTrue({'a' * 64, 'b' * 64}.issubset(retained_ids))
        self.assertEqual(published['models'], plan['recovery_models'])
        for document in published['models'].values():
            for mount in document['services'][next(iter(document['services']))].get('volumes', []):
                self.assertNotEqual(mount.get('source'), bridge.PICKER_CONFIG_SOURCE)
                self.assertNotEqual(mount.get('target'), bridge.PICKER_CONFIG_TARGET)

    def test_picker_free_receipt_binds_healthy_runtime_recipe_and_active_base(self):
        self.stopped_original()
        inventory = self.inventory()
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        with self.compose_create(identity):
            revision = bridge.handoff_recover_service(identity, revision, 'api')
            bridge.handoff_recover_service(identity, revision, 'web')

        plan, _, _ = bridge.handoff_journal_read(identity)
        published = {}
        base_context = {'paths': [], 'digests': {}, 'sources': {}, 'config_hashes': {}}
        read_journal = bridge.handoff_journal_read

        def read_with_original_version(journal_identity):
            current_plan, state, current_revision = read_journal(journal_identity)
            current_plan['original_web_version'] = 'a' * 40
            return current_plan, state, current_revision

        def prepare_context(context, *args):
            context['models'] = copy.deepcopy(plan['recovery_models'])
            context['semantic_hashes'] = {'web': 'a' * 64}
            return context

        def publish_runtime(context, models, proof, approval, handoff_records=None):
            published.update(proof=proof, approval=approval, records=copy.deepcopy(handoff_records))

        with (patch.object(bridge, '_handoff_read_items', return_value=self.execution.items),
              patch.object(bridge, 'handoff_journal_read', side_effect=read_with_original_version),
              patch.object(bridge, '_discover_context', return_value=base_context),
              patch.object(bridge, '_prepare_compose_context', side_effect=prepare_context),
              patch.object(bridge, '_prove_context'),
              patch.object(bridge, '_publish_runtime_base', side_effect=publish_runtime)):
            bridge.handoff_publish_runtime(identity, restoring=True)

        pointer = {'base': 'b' * 64, 'manifest_sha256': 'c' * 64}
        manifest_models = {
            service: hashlib.sha256(json.dumps(bridge._escape_compose(plan['recovery_models'][service]),
                                               sort_keys=True).encode()).hexdigest()
            for service in bridge.SERVICES
        }
        manifest = {
            'approval': published['approval'], 'proof': published['proof'],
            'handoff_records': published['records'], 'runtime': published['proof']['runtime'],
            'models': manifest_models,
        }
        active_base_pointer = bridge.BRIDGE_STATE / 'active-base.json'
        bridge._write_private_file(active_base_pointer, b'synthetic active base pointer')
        proof = bridge.handoff_recovery_inventory(
            identity, self.execution.items, {self.execution.image['Id']: self.execution.image},
            '20261113_0126', support_sha=plan['support_sha'],
        )
        with (patch.object(bridge, '_handoff_active_id', return_value=identity),
              patch.object(bridge, '_read_base_pointer', return_value=pointer),
              patch.object(bridge, '_read_runtime_base', return_value=(Path('/tmp'), manifest)),
              patch.object(bridge, '_handoff_read_items', return_value=self.execution.items)):
            receipt = bridge._handoff_picker_free_runtime_receipt(plan['support_sha'], proof)

        self.assertEqual(receipt['recipe_sha256'], plan['picker_free_recovery_recipe']['sha256'])
        self.assertEqual(receipt['runtime_base'], pointer['base'])
        self.assertEqual(receipt['runtime_pointer_sha256'], bridge.snapshot_sha256(active_base_pointer))
        self.assertEqual(receipt['services']['api']['health'], 'healthy')
        self.assertEqual(receipt['services']['web']['running'], True)
        self.assertEqual(receipt['receipt_sha256'], bridge.digest({key: value for key, value in receipt.items()
                                                                  if key != 'receipt_sha256'}))

        invalid_manifest = manifest | {'approval': '0' * 64}
        with (patch.object(bridge, '_handoff_active_id', return_value=identity),
              patch.object(bridge, '_read_base_pointer', return_value=pointer),
              patch.object(bridge, '_read_runtime_base', return_value=(Path('/tmp'), invalid_manifest)),
              patch.object(bridge, '_handoff_read_items', return_value=self.execution.items),
              self.assertRaisesRegex(bridge.BridgeError, 'handoff_picker_free_runtime_receipt_mismatch')):
            bridge._handoff_picker_free_runtime_receipt(plan['support_sha'], proof)

    def test_wrong_schema_after_restoring_prevents_healthy_receipt(self):
        self.stopped_original()
        inventory = self.inventory()
        identity, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        original = self.execution.docker
        def wrong_schema(args, **kwargs):
            if args[0] == 'exec':
                return 'unexpected_schema\n'
            return original(args, **kwargs)
        with self.compose_create(identity), patch.object(bridge, '_docker', side_effect=wrong_schema), self.assertRaisesRegex(bridge.BridgeError, 'handoff_restored_schema_mismatch'):
            bridge.handoff_recover_service(identity, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(identity)[1]['phases']['api'], 'recovery_started')
        self.assertFalse(self.execution.items[0]['State']['Running'])

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
        with self.compose_create(recovery), patch.object(bridge, '_docker', side_effect=crash_after_rename), self.assertRaisesRegex(bridge.BridgeError, 'synthetic_recovery_crash'):
            bridge.handoff_recover_service(recovery, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(recovery)[1]['phases']['api'], 'candidate_rename_intent')
        e = self.execution
        resumed_inventory = bridge.handoff_recovery_inventory(recovery, e.items, {e.image['Id']: e.image}, None, support_sha='e' * 40)
        self.assertEqual(resumed_inventory['schema_status'], 'unavailable')
        self.assertEqual(resumed_inventory['support_sha'], 'e' * 40)
        self.assertNotEqual(bridge.digest(inventory), bridge.digest(resumed_inventory))
        resumed, revision = bridge.handoff_recovery_prepare(resumed_inventory, bridge.digest(resumed_inventory))
        with self.compose_create(resumed):
            bridge.handoff_recover_service(resumed, revision, 'api')
        self.assertFalse(e.items[0]['State']['Running'])
        self.assertTrue(e.items[-1]['State']['Running'])
        self.assertEqual(bridge.handoff_journal_read(resumed)[1]['phases']['api'], 'healthy')

    def test_recovery_create_interruption_is_reinventoried_without_duplicate_candidate(self):
        self.stopped_original()
        inventory = self.inventory()
        recovery, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        with self.compose_create(recovery) as create_mock:
            create = create_mock.side_effect

            def create_then_interrupt(args, **kwargs):
                create(args, **kwargs)
                raise bridge.BridgeError('synthetic_recovery_create_interruption')

            create_mock.side_effect = create_then_interrupt
            with self.assertRaisesRegex(bridge.BridgeError, 'synthetic_recovery_create_interruption'):
                bridge.handoff_recover_service(recovery, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(recovery)[1]['phases']['api'], 'recovery_create_intent')
        candidate_id = self.execution.items[-1]['Id']
        self.assertFalse(self.execution.items[-1]['State']['Running'])

        resumed_inventory = self.inventory_for(recovery)
        resumed, revision = bridge.handoff_recovery_prepare(resumed_inventory, bridge.digest(resumed_inventory))
        with self.compose_create(resumed):
            bridge.handoff_recover_service(resumed, revision, 'api')

        candidates = [item for item in self.execution.items if item['Id'] == candidate_id]
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0]['State']['Running'])
        self.assertEqual(bridge.handoff_journal_read(resumed)[1]['phases']['api'], 'healthy')

    def inventory_for(self, identity, schema=None):
        e = self.execution
        return bridge.handoff_recovery_inventory(identity, e.items, {e.image['Id']: e.image}, schema)

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
