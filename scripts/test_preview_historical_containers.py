"""Fail-closed classification and preservation of stopped release resources."""
import copy
import io
import subprocess
import unittest
from unittest.mock import patch

from scripts import preview_adjustment_migration_inventory as inventory
from scripts.test_preview_adjustment_migration_inventory import valid_inventory


def container(service='web', ident='a', status='exited', labelled=False):
    labels = {'com.docker.compose.project': inventory.PROJECT, 'com.docker.compose.service': service}
    if labelled:
        labels.update({'com.docker.compose.config-hash': 'c' * 64,
                       'com.docker.compose.oneoff': 'False', 'com.docker.compose.container-number': '1'})
    return {'Id': ident * 64, 'Image': 'sha256:' + 'b' * 64,
            'Name': f'/{inventory.PROJECT}-{service}-1' if status == 'running' else '/synthetic-historical',
            'Config': {'Labels': labels, 'Env': ['PRIVATE=synthetic-do-not-print']},
            'HostConfig': {'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}},
            'Mounts': [{'Source': '/synthetic/private', 'Destination': '/data', 'RW': True}],
            'State': {'Status': status, 'Running': status == 'running', 'Paused': False,
                      'Restarting': False, 'StartedAt': 'old', 'FinishedAt': 'old', 'ExitCode': 0},
            'NetworkSettings': {'Networks': {}}}


class HistoricalContainerTests(unittest.TestCase):
    def test_active_and_all_three_historical_categories_are_preserved_without_disclosure(self):
        items = [container('web', '1', 'running', True), container(),
                 container('migrate', '2', labelled=True), container('private-legacy', '3', labelled=True)]
        active, history = inventory.partition_containers(items)
        self.assertEqual(active, items[:1])
        self.assertEqual(len(history), 3)
        self.assertNotIn('private', str(history))
        self.assertNotIn('PRIVATE', str(history))

    def test_target_hash_presence_even_empty_is_not_safe(self):
        for value in ('', 'bad', 'c' * 64):
            item = container()
            item['Config']['Labels']['com.docker.compose.config-hash'] = value
            with self.assertRaisesRegex(inventory.InventoryError, 'selecionavel'):
                inventory.partition_containers([item])

    def test_unknown_active_duplicate_active_and_ambiguous_states_fail(self):
        cases = [[container('unknown', status='running', labelled=True)],
                 [container('web', '1', 'running', True), container('web', '2', 'running', True)],
                 [container(status='created')], [container(status='restarting')]]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(inventory.InventoryError):
                inventory.partition_containers(case)

    def test_wrong_project_and_automatic_restart_fail(self):
        item = container()
        item['Config']['Labels']['com.docker.compose.project'] = 'firefly_telegram'
        with self.assertRaises(inventory.InventoryError):
            inventory.partition_containers([item])
        item = container()
        item['HostConfig']['RestartPolicy']['Name'] = 'always'
        with self.assertRaises(inventory.InventoryError):
            inventory.partition_containers([item])

    def test_fingerprint_covers_each_preserved_field(self):
        original = container()
        baseline = inventory.historical_identity(original)
        self.assertEqual(set(baseline['fields_sha256']), set(inventory.HISTORICAL_OPERATIONAL_FIELDS))
        for field in ('Config', 'HostConfig', 'Mounts', 'State', 'NetworkSettings'):
            changed = copy.deepcopy(original)
            if field == 'Mounts':
                changed[field][0]['RW'] = False
            else:
                changed[field]['changed'] = True
            self.assertNotEqual(inventory.historical_identity(changed), baseline)

    def test_mount_component_diagnostics_hash_values_without_disclosing_paths(self):
        item = container()
        item['Mounts'][0].update({'Type': 'bind', 'Name': 'private-volume', 'Driver': 'local',
                                  'Mode': 'rw', 'Propagation': 'rprivate'})
        diagnostic = inventory.historical_mount_diagnostics(item['Mounts'])
        rendered = str(diagnostic)
        for private_value in ('/synthetic/private', '/data', 'private-volume', 'rprivate'):
            self.assertNotIn(private_value, rendered)
        self.assertEqual(diagnostic[0]['type'], 'bind')
        self.assertEqual(diagnostic[0]['rw'], 'sim')
        self.assertRegex(diagnostic[0]['Source_sha256'], r'^[0-9a-f]{64}$')
        changed = copy.deepcopy(item)
        changed['Mounts'][0]['Source'] = '/synthetic/other-private'
        changed_diagnostic = inventory.historical_mount_diagnostics(changed['Mounts'])
        self.assertNotEqual(diagnostic[0]['Source_sha256'], changed_diagnostic[0]['Source_sha256'])

    def test_exited_health_diagnostics_are_separate_from_operational_preservation(self):
        original = container()
        original['State']['Health'] = {'Status': 'unhealthy', 'FailingStreak': 1,
                                       'Log': [{'Output': 'PRIVATE diagnostic', 'Start': 'old'}]}
        changed = copy.deepcopy(original)
        changed['State']['Health']['FailingStreak'] = 2
        changed['State']['Health']['Log'][0]['Start'] = 'new'
        self.assertEqual(inventory.historical_identity(original), inventory.historical_identity(changed))
        hashes = inventory.historical_field_hashes([original, changed])
        self.assertNotEqual(hashes[0]['campos_sha256']['State'], hashes[1]['campos_sha256']['State'])
        self.assertEqual(hashes[0]['campos_sha256']['State_without_Health'],
                         hashes[1]['campos_sha256']['State_without_Health'])
        self.assertNotIn('PRIVATE', str(hashes))
        changed['State']['StartedAt'] = 'restarted'
        self.assertNotEqual(inventory.historical_identity(original), inventory.historical_identity(changed))

    def test_inventory_binds_history_and_refuses_other_compose_versions(self):
        data = valid_inventory()
        data['historical_containers'] = [inventory.historical_identity(container())]
        self.assertTrue(inventory.validate_inventory(data)[0])
        before = inventory.canonical_fingerprint(data)
        data['historical_containers'][0]['metadata_sha256'] = 'f' * 64
        self.assertNotEqual(before, inventory.canonical_fingerprint(data))
        data['compose_version'] = '5.6.1'
        self.assertFalse(inventory.validate_inventory(data)[0])

    def test_inventory_rejects_incomplete_per_field_historical_hashes(self):
        data = valid_inventory()
        data['historical_containers'] = [inventory.historical_identity(container())]
        self.assertTrue(inventory.validate_inventory(data)[0])
        del data['historical_containers'][0]['fields_sha256']['Mounts']
        self.assertEqual(inventory.validate_inventory(data)[1], 'historicos_invalidos')

    def test_candidate_build_failure_reports_fixed_subphase_without_path(self):
        import tempfile
        from pathlib import Path
        from scripts.preview_adjustment_migration_release import ReleaseHost
        from scripts.preview_adjustment_migration_release import InventoryError
        with tempfile.TemporaryDirectory() as temporary:
            host = ReleaseHost()
            with patch('scripts.preview_adjustment_migration_release.STATE', Path(temporary)), \
                    patch('scripts.preview_adjustment_migration_release.subprocess.run',
                          return_value=subprocess.CompletedProcess(
                              ['git', 'fetch'], 128, stderr=b'private remote response')) as run, \
                    patch('sys.stdout', new_callable=io.StringIO) as output, \
                    self.assertRaisesRegex(InventoryError,
                                           'candidate_fetch_falhou;categoria=outro;codigo_saida=128'):
                host.stage_candidate({'checkout_sha': 'a' * 40, 'services': {}})
            self.assertEqual(run.call_args.args[0][:3], ['git', 'fetch', '--quiet'])
            self.assertIn('candidate_build_phase=fetch', output.getvalue())
            self.assertIn('candidate_fetch_result=failed;categoria=outro;codigo_saida=128', output.getvalue())
            self.assertNotIn('private remote response', output.getvalue())
            self.assertNotIn(temporary, output.getvalue())

    def test_release_refuses_missing_restarted_or_changed_history(self):
        from scripts.preview_adjustment_migration_release import ReleaseHost
        host = ReleaseHost()
        original = container()
        data = {'historical_containers': [inventory.historical_identity(original)]}
        host.inspect = lambda _id: original
        host.assert_historical_preserved(data)
        for field, value in [('State', {'Status': 'running'})]:
            changed = copy.deepcopy(original)
            changed[field] = value
            host.inspect = lambda _id: changed
            with self.assertRaises(RuntimeError):
                host.assert_historical_preserved(data)
        changed = copy.deepcopy(original)
        changed['Mounts'][0]['Source'] = '/synthetic/changed-private'
        host.inspect = lambda _id: changed
        with patch('sys.stdout', new_callable=io.StringIO) as output, \
                self.assertRaisesRegex(RuntimeError, 'campos=Mounts'):
            host.assert_historical_preserved(data)
        self.assertIn('"campos":["Mounts"]', output.getvalue())
        self.assertNotIn('/synthetic/changed-private', output.getvalue())
        host.inspect = lambda _id: (_ for _ in ()).throw(RuntimeError('missing'))
        with self.assertRaises(RuntimeError):
            host.assert_historical_preserved(data)

    def test_release_overrides_orphan_removal_even_if_inherited(self):
        from scripts.preview_adjustment_migration_release import ReleaseHost
        with patch.dict('os.environ', {'COMPOSE_REMOVE_ORPHANS': 'true'}), \
                patch('scripts.preview_adjustment_migration_release.subprocess.run') as run:
            ReleaseHost().command(['docker', 'compose', 'version'])
        env = run.call_args.kwargs['env']
        self.assertEqual(env['COMPOSE_REMOVE_ORPHANS'], 'false')
        self.assertEqual(env['COMPOSE_IGNORE_ORPHANS'], 'true')


if __name__ == '__main__':
    unittest.main()
