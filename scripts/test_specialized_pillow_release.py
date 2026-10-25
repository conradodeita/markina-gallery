"""Orchestration contracts: synthetic host, no Docker/network/production access."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import specialized_pillow_release as release


def container(service, image=None):
    return {'Id': service + '-original', 'Image': image or 'sha256:' + 'a' * 64,
            'State': {'StartedAt': 'before', 'Status': 'running', 'Health': {'Status': 'healthy'}},
            'Config': {'Env': ['APP_ENV=staging'], 'Image': 'original-tag',
                       'Labels': {'com.docker.compose.service': service}, 'Cmd': ['python', '-m', service]},
            'HostConfig': {'Binds': ['/same:/same:rw'], 'RestartPolicy': {
                'Name': 'no' if service in ('api', 'worker', 'web') else 'unless-stopped', 'MaximumRetryCount': 0}}}


class FakeHost:
    def __init__(self):
        self.items = {name: container(name) for name in release.EXPECTED}
        services = {name: {'id': d['Id'], 'image': d['Image'], 'started': d['State']['StartedAt'],
            'status': 'running', 'health': 'healthy', 'restart': d['HostConfig']['RestartPolicy'],
            'configuration': release.configuration(d)} for name, d in self.items.items()}
        self.original = {'host': 'clearbudget-vnic', 'schema': release.SCHEMA,
            'checkout': '1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8', 'clean': True,
            'pending': [], 'services': services, 'files': {'compose': 'unchanged'}, 'https': [200, 200, 200]}
        self.events, self.guarded, self.fail = [], False, None

    def inspect(self, ident):
        return next(d for name, d in self.items.items() if ident in (d['Id'], 'markina-gallery-' + name + '-1'))

    def consumer(self, service):
        return self.items.get(service)

    def inventory(self):
        return copy.deepcopy(self.original)

    def verify_ci(self, sha):
        self.events.append('ci')
        if self.fail == 'ci':
            raise ValueError('CI failed')

    def queues(self):
        return {table: {'processing': 1 if self.fail == 'queue' else 0} for table in release.QUEUES}

    def financial(self):
        return {'financial': 'changed' if self.fail == 'financial' and 'compose' in self.events else 'preserved'}

    def guard(self, work, enabled):
        self.guarded = enabled
        self.events.append('guard' if enabled else 'unguard')

    def stop(self, ident, service):
        self.events.append('stop:' + service)
        if self.fail == service:
            raise ValueError('shutdown not confirmed')
        self.inspect(ident)['State']['Status'] = 'exited'

    def healthy(self, ident):
        d = self.inspect(ident)
        if self.fail == 'health' and 'compose' in self.events:
            raise ValueError('health failed')
        if d['State']['Status'] != 'running':
            raise ValueError('stopped service')
        return d

    def run(self, *args):
        if args[:2] == ('docker', 'start'):
            self.inspect(args[2])['State'].update(Status='running', StartedAt='restarted')
        elif args[:2] == ('docker', 'update'):
            pass
        elif args[:2] == ('docker', 'exec'):
            d = self.inspect(args[2])
            return json.dumps({'pillow': '13' if d['Image'].endswith('b' * 64) else '12'})
        else:
            raise AssertionError(args)
        return ''

    def pg(self, sql):
        return release.SCHEMA if 'alembic_version' in sql else 0

    def compose(self, path, *args):
        self.events.append('compose')
        self.assert_all_stopped = all(d['State']['Status'] == 'exited' for n, d in self.items.items()
                                      if n in set(release.SERVICES) | {'api', 'worker'})
        for service, change in json.loads(path.read_text())['services'].items():
            d = container(service, change['image'])
            d['Id'] = service + '-replacement'
            d['State']['StartedAt'] = 'replacement'
            self.items[service] = d

    def health(self):
        return [200, 200, 200]


def receipt(host):
    return {'format': 1, 'source_sha': 'c' * 40, 'inventory': host.inventory(),
            'services': {name: {'previous_image': 'sha256:' + 'a' * 64,
                'candidate_image': 'sha256:' + 'b' * 64, 'before': {'pillow': '12'},
                'after': {'pillow': '13'}} for name in release.SERVICES}}


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.work = self.state / 'pillow-prepare-synthetic'
        self.work.mkdir()
        self.path = self.work / 'sealed.json'
        self.host = FakeHost()
        self.receipt = receipt(self.host)
        self.approval = release.fingerprint(self.receipt)
        self.patcher = patch.object(release, 'STATE', self.state)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def apply(self, recovery=False):
        release.apply(self.host, self.receipt, self.path, self.approval, recovery=recovery)

    def test_happy_release_only_six_images_with_admission_fenced(self):
        self.apply()
        self.assertTrue(self.host.assert_all_stopped)
        self.assertEqual(self.host.events.count('compose'), 1)
        self.assertLess(self.host.events.index('guard'), self.host.events.index('stop:api'))
        self.assertEqual(self.host.events[-1], 'unguard')
        self.assertFalse(self.host.guarded)
        self.assertFalse((self.state / 'pillow-in-flight.json').exists())
        self.assertTrue(json.loads((self.work / 'published.json').read_text())['security_fixed'])

    def test_bad_approval_never_mutates(self):
        with self.assertRaisesRegex(ValueError, 'approval'):
            release.apply(self.host, self.receipt, self.path, 'wrong')
        self.assertEqual(self.host.events, [])

    def test_ci_or_inventory_or_queues_stop_before_maintenance(self):
        for failure in ('ci', 'inventory', 'queue'):
            self.host = FakeHost()
            self.host.fail = failure
            if failure == 'inventory':
                self.host.original['services']['api']['image'] = 'different'
            with self.assertRaises(ValueError):
                self.apply()
            self.assertFalse(self.host.guarded)
            self.assertNotIn('compose', self.host.events)

    def test_pending_stop_failure_keeps_barrier_and_durable_recovery(self):
        self.host.fail = 'face-search-worker'
        with self.assertRaises(ValueError):
            self.apply()
        self.assertTrue(self.host.guarded)
        self.assertNotIn('compose', self.host.events)
        record = json.loads((self.state / 'pillow-in-flight.json').read_text())
        self.assertIn('face-search-worker', record['stops'])
        self.host.fail = None
        self.apply(recovery=True)
        self.assertFalse(self.host.guarded)
        self.assertFalse(json.loads((self.work / 'recovered.json').read_text())['security_fixed'])

    def test_health_failure_recovers_previous_images_without_ci_access(self):
        self.host.fail = 'health'
        with self.assertRaises(ValueError):
            self.apply()
        self.assertTrue(self.host.guarded)
        self.host.fail = None
        self.apply(recovery=True)
        self.assertEqual(self.host.events.count('ci'), 1)
        for service in release.SERVICES:
            self.assertEqual(self.host.items[service]['Image'], 'sha256:' + 'a' * 64)

    def test_partial_compose_missing_consumer_recovers(self):
        self.host.fail = 'health'
        with self.assertRaises(ValueError):
            self.apply()
        del self.host.items['face-search-worker']
        self.host.fail = None
        self.apply(recovery=True)
        self.assertIn('face-search-worker', self.host.items)

    def test_recovery_before_financial_capture(self):
        self.host.fail = 'api'
        with self.assertRaises(ValueError):
            self.apply()
        self.host.fail = None
        self.apply(recovery=True)
        self.assertFalse(self.host.guarded)

    def test_financial_drift_never_reopens_admission(self):
        self.host.fail = 'financial'
        with self.assertRaisesRegex(ValueError, 'financial'):
            self.apply()
        self.assertTrue(self.host.guarded)

    def test_all_thirteen_queue_names_are_required(self):
        for states in ({}, {name: {} for name in release.QUEUES[:-1]},
                       {name: {'pending': 1} for name in release.QUEUES}):
            with self.assertRaises(ValueError):
                release.idle(states)

    def test_inventory_wrong_schema_host_pending_or_unhealthy(self):
        release.validate_inventory(self.host.inventory())
        for field, value in (('host', 'another-project'), ('schema', ['different']),
                             ('pending', ['other-release']), ('clean', False), ('https', [200, 503, 200])):
            data = self.host.inventory()
            data[field] = value
            with self.assertRaises(ValueError):
                release.validate_inventory(data)

    def test_images_overlay_has_exactly_six_services_and_no_secrets(self):
        data = release.overlay(self.receipt)
        self.assertEqual(set(data['services']), set(release.SERVICES))
        self.assertTrue(all(set(item) == {'image'} for item in data['services'].values()))

    def test_result_receipt_is_idempotent_after_crash_but_rejects_different_evidence(self):
        result = {'security_fixed': False, 'fingerprint': self.approval}
        path = self.work / 'recovered.json'
        release.result_receipt(path, result)
        release.result_receipt(path, result)
        with self.assertRaisesRegex(ValueError, 'receipt drift'):
            release.result_receipt(path, dict(result, security_fixed=True))

    def test_config_backup_reads_preserve_original_newlines(self):
        host = release.Host()
        with patch.object(release.subprocess, 'run') as command:
            command.return_value.stdout = '  original config\n\n'
            self.assertEqual(host.run('synthetic', raw=True), '  original config\n\n')
            self.assertEqual(host.run('synthetic'), 'original config')

    def test_configuration_ignores_only_volatile_identity_and_candidate_label(self):
        old = container('face-index-worker')
        new = copy.deepcopy(old)
        new['Config']['Image'] = 'candidate'
        new['Config']['Hostname'] = 'new-id'
        new['Config']['Labels']['com.pickyourpic.pillow-candidate'] = '13.0.0'
        self.assertEqual(release.configuration(old), release.configuration(new))
        for field, value in (('Env', ['APP_ENV=production']), ('Cmd', ['other-engine'])):
            altered = copy.deepcopy(new)
            altered['Config'][field] = value
            self.assertNotEqual(release.configuration(old), release.configuration(altered))
        new['HostConfig']['Binds'] = ['/other-volume:/same:rw']
        self.assertNotEqual(release.configuration(old), release.configuration(new))


if __name__ == '__main__':
    unittest.main()
