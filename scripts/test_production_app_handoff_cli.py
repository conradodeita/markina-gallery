"""Closed command vocabulary for generation and recovery operations."""
import copy
import json
import unittest
from unittest.mock import patch

import production_app_compose_bridge as bridge
from test_production_app_compose_bridge import SHA


class HandoffCliContracts(unittest.TestCase):
    def arguments(self, operation, mode=None):
        mode = mode or bridge.HANDOFF_OPERATIONS[operation]
        args = ['--mode', mode, '--sha', SHA]
        if mode in {'release', 'rollback'}:
            args += ['--approval-fingerprint', 'f' * 64]
        if operation in bridge.HANDOFF_CANDIDATE_OPERATIONS:
            args += ['--artifact-sha256', 'a' * 64,
                     '--api-base-image-id', 'sha256:' + 'b' * 64,
                     '--candidate-api-id', 'sha256:' + 'c' * 64,
                     '--candidate-web-id', 'sha256:' + 'd' * 64]
        return args + [operation]

    def test_each_fixed_operation_accepts_only_its_mode(self):
        for operation, mode in bridge.HANDOFF_OPERATIONS.items():
            with self.subTest(operation=operation):
                self.assertEqual(bridge._parse_args(self.arguments(operation)).mode, mode)
                for wrong in {'inventory', 'release', 'rollback', 'rollback-inventory', 'adopt'} - {mode}:
                    with self.assertRaises(bridge.BridgeError):
                        bridge._parse_args(self.arguments(operation, mode=wrong))

    def test_approval_artifact_and_remainder_cannot_escape_the_table(self):
        for operation in bridge.HANDOFF_OPERATIONS:
            with self.subTest(operation=operation), self.assertRaises(bridge.BridgeError):
                bridge._parse_args(self.arguments(operation) + ['--', 'sh', '-c', 'id'])
        args = self.arguments('handoff-inventory')
        args[args.index('--candidate-web-id') + 1] = 'sha256:' + 'c' * 64
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_artifact_identity_invalid'):
            bridge._parse_args(args)
        with self.assertRaises(bridge.BridgeError):
            bridge._parse_args(['--mode', 'release', '--sha', SHA, 'handoff-prepare'])
        with self.assertRaisesRegex(bridge.BridgeError, 'handoff_artifact_arguments_not_allowed'):
            bridge._parse_args(['--mode', 'inventory', '--sha', SHA, '--artifact-sha256', 'a' * 64, 'hashes'])

    def test_nonroot_is_rejected_before_reading_any_generation_state(self):
        with patch.object(bridge, 'require_root', side_effect=bridge.BridgeError('root_identity_required')), \
                patch.object(bridge, '_handoff_cli') as handler:
            self.assertEqual(bridge.main(self.arguments('handoff-inventory')), 1)
        handler.assert_not_called()

    def test_mutation_requires_lock_before_support_or_runtime_reads(self):
        args = bridge._parse_args(self.arguments('handoff-apply'))
        with patch.object(bridge, '_assert_common_lock_held', side_effect=bridge.BridgeError('outer_release_lock_required')), \
                patch.object(bridge, '_git') as git, \
                self.assertRaisesRegex(bridge.BridgeError, 'outer_release_lock_required'):
            bridge._handoff_cli(args)
        git.assert_not_called()

    def test_readonly_dispatch_cannot_use_stale_main(self):
        args = bridge._parse_args(self.arguments('handoff-inventory'))
        with patch.object(bridge, '_git', return_value='e' * 40), patch.object(bridge, '_handoff_candidate_plan') as plan, \
                self.assertRaisesRegex(bridge.BridgeError, 'handoff_support_checkout_invalid'):
            bridge._handoff_cli(args)
        plan.assert_not_called()

    def test_apply_rejects_changed_bundle_base_or_candidate_before_mutation(self):
        plan = {'support_sha': SHA, 'target_sha': SHA, 'bundle_sha256': 'a' * 64,
                'original_models': {'api': {'services': {'api': {'image': 'sha256:' + 'b' * 64}}}},
                'services': {'api': {'candidate_image': 'sha256:' + 'c' * 64},
                             'web': {'candidate_image': 'sha256:' + 'd' * 64}}}
        for key in ('artifact_sha256', 'api_base_image_id', 'candidate_api_id', 'candidate_web_id'):
            args = bridge._parse_args(self.arguments('handoff-apply'))
            setattr(args, key, 'e' * 64 if key == 'artifact_sha256' else 'sha256:' + 'e' * 64)
            with self.subTest(key=key), patch.object(bridge, '_assert_common_lock_held'), \
                    patch.object(bridge, '_git', side_effect=[SHA, '']), \
                    patch.object(bridge, '_handoff_active_id', return_value='f' * 64), \
                    patch.object(bridge, 'handoff_journal_read', return_value=(plan, {}, 'revision')), \
                    patch.object(bridge, '_ensure_mutation_context') as mutation, \
                    self.assertRaisesRegex(bridge.BridgeError, 'handoff_candidate_binding_changed'):
                bridge._handoff_cli(args)
            mutation.assert_not_called()

    def test_proxy_reload_is_confined_to_same_running_nginx_and_exact_bind(self):
        item = {'Id': '1' * 64, 'Config': {'Labels': {'com.docker.compose.project': bridge.PROJECT,
                 'com.docker.compose.service': 'nginx'}}, 'HostConfig': {}, 'Mounts': [],
                'State': {'Running': True, 'StartedAt': 'synthetic-start'},
                'NetworkSettings': {'Ports': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]}, 'Networks': {}}}
        for mutation in (None, 'bind', 'project', 'restart'):
            current = copy.deepcopy(item)
            if mutation == 'bind':
                current['NetworkSettings']['Ports']['80/tcp'][0]['HostPort'] = '9999'
            elif mutation == 'project':
                current['Config']['Labels']['com.docker.compose.project'] = 'neighbor'
            elif mutation == 'restart':
                current['State']['StartedAt'] = 'changed-start'
            responses = [json.dumps([item]), '', json.dumps([current]), '']
            with self.subTest(mutation=mutation), patch.object(bridge, '_assert_common_lock_held'), \
                    patch.object(bridge, '_list_service_ids', return_value=[item['Id']]), \
                    patch.object(bridge, '_docker', side_effect=responses) as docker:
                if mutation:
                    with self.assertRaises(bridge.BridgeError):
                        bridge._handoff_nginx()
                    self.assertFalse(any(call.args[0][-2:] == ['-s', 'reload'] for call in docker.call_args_list))
                else:
                    bridge._handoff_nginx()
                    self.assertEqual(docker.call_args_list[-1].args[0], ['exec', item['Id'], 'nginx', '-s', 'reload'])

    def test_proxy_selection_requests_full_engine_ids_before_exact_identity_check(self):
        identity = '1' * 64
        item = {'Id': identity, 'Config': {'Labels': {'com.docker.compose.project': bridge.PROJECT,
                'com.docker.compose.service': 'nginx'}}, 'HostConfig': {}, 'Mounts': [],
                'State': {'Running': True, 'StartedAt': 'synthetic-start'},
                'NetworkSettings': {'Ports': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]}, 'Networks': {}}}
        effects = []
        def docker(arguments, **kwargs):
            if arguments[0] == 'ps':
                return (identity if '--no-trunc' in arguments else identity[:12]) + '\n'
            if arguments[0] == 'inspect':
                return json.dumps([item])
            effects.append(arguments)
            return ''
        with patch.object(bridge, '_assert_common_lock_held'), patch.object(bridge, '_docker', side_effect=docker):
            bridge._handoff_nginx()
        self.assertEqual(effects, [['exec', identity, 'nginx', '-t'], ['exec', identity, 'nginx', '-s', 'reload']])


if __name__ == '__main__':
    unittest.main()
