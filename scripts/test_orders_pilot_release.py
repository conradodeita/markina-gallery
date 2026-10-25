"""Falhas de release financeiro: nenhuma operação real ou credencial nos testes."""
import copy
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import orders_pilot_release as release


def inventory():
    return {'host': 'clearbudget-vnic', 'root': str(release.ROOT), 'project': release.PROJECT,
        'origin': release.ORIGIN, 'checkout_sha': release.BASELINE_SHA, 'clean': True, 'schema': release.SCHEMA,
        'orders_tables': 0, 'pending': [], 'key': {'valid': True, 'mode': 0o600, 'path': str(release.KEY_TARGET),
          'sha256': hashlib.sha256(b'synthetic-key').hexdigest()},
        'app_env': 'staging', 'free_bytes': 8 * 1024**3,
        'files': {str(p): 'b' * 64 for p in release.CONFIGS + (release.ROOT / 'docker/.env.homolog',)},
        'https': [200, 200, 200], 'services': {
            s: {'id': str(n).zfill(64), 'image': 'sha256:' + str(n).zfill(64),
                'command': ['python', '-m', 'synthetic.' + s], 'status': 'running', 'health': 'healthy',
                'restart_policy': {'Name': 'unless-stopped' if s in release.SPECIALIZED else 'no', 'MaximumRetryCount': 0},
                'version': release.BASELINE_SHA if s == 'api' else None,
                'ports': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if s == 'nginx' else {}}
            for n, s in enumerate(sorted(release.SERVICES), 1)}}


PAIR = {'tenant_id': '00000000-0000-4000-8000-000000000001',
        'client_id': '00000000-0000-4000-8000-000000000002'}
IMAGES = {'api': 'sha256:' + 'c' * 64, 'web': 'sha256:' + 'd' * 64}


class FakeHost:
    def __init__(self, fail=None):
        self.data = inventory()
        self.states = {v['id']: 'running' for v in self.data['services'].values()}
        self.revision = release.SCHEMA
        self.events = []
        self.fail = fail
        self.financial_calls = 0

    def event(self, name):
        self.events.append(name)
        if name == self.fail:
            raise release.GateError('injected')

    def inventory(self):
        self.event('inventory')
        return copy.deepcopy(self.data)

    def main_sha(self):
        return 'f' * 40

    def verify_ci(self, sha):
        self.event('ci')

    def inspect_image(self, image):
        return image

    def pg(self, sql):
        return 0 if 'pg_stat_activity' in sql else 1

    def inspect(self, ident):
        item = next(v for v in self.data['services'].values() if v['id'] == ident)
        service = next(k for k, v in self.data['services'].items() if v['id'] == ident)
        return {'Image': item['image'], 'Config': {'Cmd': item['command']},
                'State': {'Status': self.states[ident], 'ExitCode': 130 if service in release.SPECIALIZED else 0}}

    def run(self, *args):
        if args == ('git', 'rev-parse', 'HEAD'):
            return 'f' * 40
        if args == ('git', 'status', '--porcelain'):
            return ''
        if args[:3] == ('docker', 'ps', '-aq'):
            return ''
        if args[:2] == ('docker', 'kill'):
            ident = args[-1]
            service = next(k for k, v in self.data['services'].items() if v['id'] == ident)
            self.event('stop:' + service)
            self.states[ident] = 'exited'
        elif args[:2] == ('docker', 'exec'):
            return 'do_sys_poll'

    def queues(self):
        return {name: {'unknown': 68} if name == 'notification_delivery' else {} for name in release.QUEUES}

    def disable_restart(self, item):
        self.event('restart-disabled')

    def maintenance(self, work, enabled, **kwargs):
        self.event('maintenance:' + str(enabled))

    def schema(self):
        return [self.revision]

    def financial(self):
        self.financial_calls += 1
        return {'legacy': 'unchanged' if self.fail != 'financial-drift' or self.financial_calls == 1 else 'changed'}

    def dump(self, path):
        self.event('dump')
        path.write_bytes(b'synthetic-backup')

    def rehearse(self, *args, **kwargs):
        self.event('rehearse')
        return 'passed'

    def activate_source(self, source, sha):
        self.event('activate')

    def compose(self, work, *args):
        self.event('compose:' + args[0])
        if args[0] == 'run':
            self.revision = release.TARGET_SCHEMA

    def wait_new(self, receipt, **kwargs):
        self.event('new-healthy')

    def start_existing(self, item):
        self.event('resume-specialized')

    def verify_restored(self, *args, **kwargs):
        self.event('specialized-healthy')

    def health(self):
        return [200, 200, 200]

    def restore_before_ddl(self, *args):
        self.event('restore-before-ddl')


class PolicyTests(unittest.TestCase):
    def test_complete_inventory_has_stable_fingerprint(self):
        data = inventory()
        self.assertRegex(release.validate_inventory(data), r'^[0-9a-f]{64}$')
        self.assertEqual(release.validate_inventory(data), release.validate_inventory(copy.deepcopy(data)))

    def test_divergent_inventory_is_closed(self):
        for key, value in [('host', 'other'), ('root', '/'), ('project', 'firefly'), ('origin', 'http://localhost'),
                           ('checkout_sha', 'short'), ('clean', False), ('schema', release.TARGET_SCHEMA),
                           ('orders_tables', 1), ('pending', ['app-in-flight.sha']), ('app_env', 'development'),
                           ('free_bytes', 1), ('https', [200, 503, 200]), ('files', {})]:
            with self.subTest(key=key):
                data = inventory()
                data[key] = value
                with self.assertRaises(release.GateError):
                    release.validate_inventory(data)

    def test_exposed_ports_or_unhealthy_or_duplicate_scope_rejected(self):
        for mutate in [lambda d: d['services']['db'].update(ports={'5432/tcp': [{'HostIp': '0.0.0.0'}]}),
                       lambda d: d['services']['api'].update(health='unhealthy'),
                       lambda d: d['services'].pop('worker'),
                       lambda d: d['services'].update(unrelated=d['services']['api']),
                       lambda d: d['key'].update(valid=False),
                       lambda d: d['key'].update(mode=0o644),
                       lambda d: d['services']['api'].update(version='e' * 40)]:
            data = inventory()
            mutate(data)
            with self.assertRaises(release.GateError):
                release.validate_inventory(data)

    def test_only_authorized_distribution_addition(self):
        before = {'python': '3.13.17', 'packages': {'requests': '2.34.2'}}
        after = {'python': before['python'], 'packages': {**before['packages'], 'mercadopago': '3.6.0'}}
        release.package_parity(before, after)
        for mutate in [lambda d: d.update(python='3.14.0'),
                       lambda d: d['packages'].update(requests='changed'),
                       lambda d: d['packages'].update(mercadopago='3.7.0'),
                       lambda d: d['packages'].update(unrelated='1')]:
            value = copy.deepcopy(after)
            mutate(value)
            with self.assertRaises(release.GateError):
                release.package_parity(before, value)

    def test_pair_strict_and_sql_safe(self):
        self.assertEqual(release.pilot_pair(PAIR), PAIR)
        for value in [[], {}, {**PAIR, 'other': True}, {**PAIR, 'client_id': "';DROP TABLE client;--"}]:
            with self.assertRaises(release.GateError):
                release.pilot_pair(value)

    def test_close_emission_keeps_worker_and_real_block(self):
        for enabled in (True, False):
            overlay = release.release_overlay(IMAGES, PAIR, enabled=enabled)
            services = overlay['services']
            self.assertEqual(set(services), {'api', 'web', 'worker'})
            self.assertEqual(services['api']['environment']['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'], 'false')
            self.assertEqual(services['worker']['environment']['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'], 'false')
            self.assertEqual(services['worker']['image'], IMAGES['api'])
            raw = services['api']['environment']['MERCADOPAGO_TEST_CUSTOMERS']
            self.assertEqual(json.loads(raw) if enabled else raw, [PAIR] if enabled else '')

    def test_unknown_is_not_requeued_but_eligible_blocks(self):
        queues = {name: {} for name in release.QUEUES}
        queues['notification_delivery']['unknown'] = 68
        release.idle_queues(queues)
        self.assertEqual(queues['notification_delivery']['unknown'], 68)
        for name in release.QUEUES:
            for state in ('queued', 'pending', 'processing'):
                data = copy.deepcopy(queues)
                data[name][state] = 1
                with self.assertRaises(release.GateError):
                    release.idle_queues(data)

    def test_exit_status_is_specific_no_sigkill(self):
        for service in release.WRITERS:
            release.stopped(service, 'exited', 130 if service in release.SPECIALIZED else 0)
            for state, code in [('running', 0), ('exited', 137), ('exited', 143), ('dead', 130)]:
                with self.assertRaises(release.GateError):
                    release.stopped(service, state, code)

    def test_source_archive_refuses_links_and_traversal(self):
        for name, kind in [('backend/app.py', tarfile.SYMTYPE), ('backend/../../escape', tarfile.REGTYPE),
                           ('/backend/app.py', tarfile.REGTYPE), ('unrelated/data', tarfile.REGTYPE)]:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w') as tar:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                tar.addfile(item)
            with tempfile.TemporaryDirectory() as root, self.assertRaises(release.GateError):
                release.extract(buffer.getvalue(), Path(root))

    def test_operational_error_does_not_disclose_stderr_or_secrets(self):
        import subprocess
        error = subprocess.CalledProcessError(1, ['fixture'], stderr='secret-that-must-not-escape')
        with patch.object(release.subprocess, 'run', side_effect=error), self.assertRaises(release.GateError) as caught:
            release.Host().run('fixture')
        self.assertNotIn('secret', str(caught.exception))

    def test_ci_requires_latest_completed_success_on_exact_main_sha(self):
        sha = 'f' * 40
        good = {'path': '.github/workflows/ci.yml', 'head_sha': sha, 'event': 'push', 'head_branch': 'main',
                'run_number': 10, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success', 'id': 1}
        cases = [([good], True), ([], False), ([{**good, 'event': 'pull_request'}], False),
                 ([{**good, 'head_sha': 'a' * 40}], False), ([{**good, 'status': 'in_progress'}], False),
                 ([good, {**good, 'run_attempt': 2, 'conclusion': 'failure'}], False)]
        for runs, accepted in cases:
            response = SimpleNamespace(url='https://api.github.com/fixture',
                                       read=lambda limit, runs=runs: json.dumps({'workflow_runs': runs}).encode())
            with self.subTest(runs=runs), patch.object(release, 'urlopen') as opened:
                opened.return_value.__enter__.return_value = response
                if accepted:
                    self.assertEqual(release.Host().verify_ci(sha), 1)
                else:
                    with self.assertRaises(release.GateError):
                        release.Host().verify_ci(sha)

    def test_queue_sql_uses_membership_external_status_and_readonly_transaction(self):
        host = release.Host()
        queries = []
        host.pg = lambda sql: queries.append(sql) or {}
        self.assertEqual(set(host.queues()), set(release.QUEUES))
        special = next(q for q in queries if 'gallery_membership_notification_outbox' in q)
        self.assertIn('SELECT external_status state', special)
        with patch.object(host, 'run', return_value='1') as call:
            self.assertEqual(release.Host.pg(host, 'SELECT 1'), 1)
            self.assertTrue(call.call_args.kwargs['data'].startswith('BEGIN READ ONLY;'))
            self.assertTrue(call.call_args.kwargs['data'].endswith('; ROLLBACK;'))

    def test_expired_maintenance_budget_never_starts_another_command(self):
        host = release.Host()
        host.deadline = 1
        with patch.object(release.time, 'monotonic', return_value=2), patch.object(release.subprocess, 'run') as run:
            with self.assertRaisesRegex(release.GateError, 'janela'):
                host.run('fixture')
            run.assert_not_called()

    def test_recovery_does_not_mistake_still_terminating_api_for_healthy_runtime(self):
        host = release.Host()
        item = inventory()['services']['api']
        running = {'Image': item['image'], 'State': {'Status': 'running'}}
        exited = {'Image': item['image'], 'State': {'Status': 'exited'}}
        with (patch.object(host, 'inspect', side_effect=[running, exited]),
              patch.object(host, 'run') as run, patch.object(host, 'wait_healthy'),
              patch.object(host, 'disable_restart'), patch.object(host, 'restore_restart'),
              patch.object(release, 'wait_exit') as wait):
            host.start_existing(item, ensure_stop=True, service='api')
            wait.assert_called_once_with(host, item['id'], 'api')
            self.assertEqual(run.call_args_list[0].args, ('docker', 'kill', '--signal=SIGTERM', item['id']))
            self.assertEqual(run.call_args_list[1].args, ('docker', 'start', item['id']))

    def test_recovery_never_interrupts_a_busy_legacy_worker(self):
        host = release.Host()
        item = inventory()['services']['face-index-worker']
        queues = {name: {} for name in release.QUEUES}
        queues['facial_job']['processing'] = 1
        with (patch.object(host, 'inspect', return_value={'Image': item['image'], 'State': {'Status': 'running'}}),
              patch.object(host, 'queues', return_value=queues), patch.object(host, 'run') as run,
              patch.object(host, 'disable_restart'),
              self.assertRaisesRegex(release.GateError, 'trabalho_ativo')):
            host.start_existing(item, ensure_stop=True, service='face-index-worker')
        run.assert_not_called()

    def test_restart_policy_is_suspended_and_restored_exactly(self):
        host = release.Host()
        item = inventory()['services']['face-index-worker']
        original = {'Image': item['image'], 'State': {'Status': 'running'},
                    'HostConfig': {'RestartPolicy': item['restart_policy']}}
        disabled = copy.deepcopy(original)
        disabled['HostConfig']['RestartPolicy'] = {'Name': 'no', 'MaximumRetryCount': 0}
        with patch.object(host, 'inspect', side_effect=[original, disabled]), patch.object(host, 'run') as run:
            host.disable_restart(item)
            run.assert_called_once_with('docker', 'update', '--restart=no', item['id'])
        with patch.object(host, 'inspect', side_effect=[disabled, original]), patch.object(host, 'run') as run:
            host.restore_restart(item)
            run.assert_called_once_with('docker', 'update', '--restart=unless-stopped', item['id'])

    def test_changed_restart_policy_is_not_overwritten(self):
        host = release.Host()
        item = inventory()['services']['face-index-worker']
        other = {'Image': item['image'], 'State': {'Status': 'running'},
                 'HostConfig': {'RestartPolicy': {'Name': 'always', 'MaximumRetryCount': 0}}}
        with (patch.object(host, 'inspect', return_value=other), patch.object(host, 'run') as run,
              self.assertRaisesRegex(release.GateError, 'reinicio_mudou')):
            host.disable_restart(item)
        run.assert_not_called()


class SequenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name)
        self.work = self.state / 'orders-prepare-fixture'
        self.work.mkdir()
        self.backup = self.work / 'database.custom'
        self.backup.write_bytes(b'synthetic')
        (self.work / 'integration-secrets.backup.env').write_bytes(b'synthetic-key')
        baseline = inventory()
        self.receipt = {'sha': 'f' * 40, 'build_sha': release.APPROVED_RUNTIME, 'rehearsal': 'passed', 'work': str(self.work),
                        'guard': 'passed',
                        'restart_policy_rehearsal': 'passed',
                        'callbacks': {'retry503': True, 'retryRefused': True, 'nonRetryable400': True,
                                      'source_sha256': 'a' * 64, 'image': baseline['services']['evolution-api']['image']},
                        'backup': str(self.backup), 'backup_sha256': hashlib.sha256(b'synthetic').hexdigest(),
                        'key_backup': str(self.work / 'integration-secrets.backup.env'), 'inventory': baseline,
                        'baseline_fingerprint': release.validate_inventory(baseline),
                        'images': IMAGES, 'pair': PAIR}
        self.addCleanup(patch.stopall)
        patch.object(release, 'STATE', self.state).start()
        patch.object(release, 'release_lock', nullcontext).start()

    def apply(self, host, *, approval=None, legacy=True):
        release.apply(host, self.receipt, approval or release.fingerprint(self.receipt), legacy=legacy)

    def test_success_preserves_specialized_and_orders_actions(self):
        host = FakeHost()
        self.apply(host)
        self.assertNotIn('restore-before-ddl', host.events)
        self.assertEqual(host.events.count('resume-specialized'), 6)
        migration = host.events.index('compose:run')
        for name in release.WRITERS:
            self.assertLess(host.events.index('stop:' + name), migration)
        self.assertLess(host.events.index('rehearse'), migration)
        self.assertLess(host.events.index('new-healthy'), host.events.index('maintenance:False'))
        self.assertFalse((self.state / 'app-in-flight.sha').exists())

    def test_wrong_approval_blocks_before_any_host_call(self):
        host = FakeHost()
        with self.assertRaises(release.GateError):
            self.apply(host, approval='0' * 64)
        self.assertEqual(host.events, [])

    def test_missing_callback_rehearsal_blocks_before_any_host_call(self):
        self.receipt.pop('callbacks')
        host = FakeHost()
        with self.assertRaisesRegex(release.GateError, 'callbacks'):
            self.apply(host)
        self.assertEqual(host.events, [])

    def test_artifact_outside_operation_directory_is_refused(self):
        self.receipt['key_backup'] = str(self.state / 'unrelated.env')
        host = FakeHost()
        with self.assertRaisesRegex(release.GateError, 'inseguro'):
            self.apply(host)
        self.assertEqual(host.events, [])

    def test_corrupted_key_backup_is_refused_before_any_host_call(self):
        (self.work / 'integration-secrets.backup.env').write_bytes(b'changed-key')
        host = FakeHost()
        with self.assertRaisesRegex(release.GateError, 'cofre_divergente'):
            self.apply(host)
        self.assertEqual(host.events, [])

    def test_merge_seal_keeps_same_images_and_requires_identical_runtime(self):
        host = FakeHost()
        calls = []
        original = host.run
        host.run = lambda *args, **kwargs: calls.append(args) or original(*args)
        result = release.seal(host, self.receipt, 'f' * 40)
        self.assertEqual(result['images'], IMAGES)
        self.assertEqual(result['build_sha'], release.APPROVED_RUNTIME)
        self.assertTrue(any('diff' in call and call[-3:] == ('backend', 'frontend', 'docker') for call in calls))
        self.assertFalse(any(call[0] == 'docker' for call in calls))
        (self.work / 'prepared-main.json').unlink()
        host.run = lambda *args, **kwargs: 'backend/app/main.py' if 'diff' in args else None
        with self.assertRaisesRegex(release.GateError, 'runtime_integrado'):
            release.seal(host, self.receipt, 'f' * 40)

    def test_missing_ci_or_changed_inventory_never_stops(self):
        for variant in ('ci', 'changed', 'legacy'):
            host = FakeHost(fail='ci' if variant == 'ci' else None)
            if variant == 'changed':
                host.data['services']['worker']['image'] = 'sha256:' + 'e' * 64
            with self.subTest(variant=variant), self.assertRaises(release.GateError):
                self.apply(host, legacy=variant != 'legacy')
            self.assertNotIn('maintenance:True', host.events)
            self.assertNotIn('stop:api', host.events)

    def test_every_pre_ddl_failure_restores_existing_containers(self):
        for fail in ('maintenance:True', 'stop:api', 'stop:worker', 'stop:face-search-worker',
                     'dump', 'rehearse', 'activate', 'compose:config'):
            host = FakeHost(fail=fail)
            with self.subTest(fail=fail), self.assertRaises(release.GateError):
                self.apply(host)
            self.assertIn('restore-before-ddl', host.events)
            self.assertNotIn('compose:run', host.events)
            self.assertFalse((self.state / 'app-in-flight.sha').exists())
            for p in ('stage.json', 'before-financial.json', 'pre-migration.custom', 'active.compose.json'):
                (self.work / p).unlink(missing_ok=True)

    def test_every_post_ddl_failure_holds_maintenance_and_never_rolls_back(self):
        for fail in ('compose:run', 'financial-drift', 'compose:up', 'new-healthy', 'resume-specialized',
                     'specialized-healthy', 'maintenance:False'):
            host = FakeHost(fail=fail)
            with self.subTest(fail=fail), self.assertRaises(release.GateError):
                self.apply(host)
            self.assertNotIn('restore-before-ddl', host.events)
            self.assertTrue((self.state / 'app-in-flight.sha').exists())
            self.assertTrue(json.loads((self.work / 'stage.json').read_text())['schema_started'])
            (self.state / 'app-in-flight.sha').unlink()
            for p in ('stage.json', 'before-financial.json', 'pre-migration.custom', 'active.compose.json'):
                (self.work / p).unlink(missing_ok=True)

    def test_specialized_stops_never_touch_evolution_database_or_proxy(self):
        host = FakeHost()
        release.quiesce(host, host.data, legacy=True)
        names = [item.removeprefix('stop:') for item in host.events if item.startswith('stop:')]
        self.assertEqual(set(names), set(release.WRITERS) | {'web'})

    def test_recovery_keeps_0088_and_closes_emission_without_touching_database(self):
        host = FakeHost(fail='new-healthy')
        with self.assertRaises(release.GateError):
            self.apply(host)
        host.fail = None
        host.events.clear()
        with patch.object(release, 'load', side_effect=lambda p: json.loads(p.read_text())):
            release.resume(host, self.receipt, release.fingerprint(self.receipt))
        self.assertNotIn('compose:run', host.events)
        self.assertNotIn('activate', host.events)
        overlay = json.loads((self.work / 'active.compose.json').read_text())
        self.assertEqual(overlay['services']['api']['environment']['MERCADOPAGO_TEST_CUSTOMERS'], '')
        self.assertEqual(overlay['services']['api']['environment']['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'], 'false')
        self.assertFalse((self.state / 'app-in-flight.sha').exists())

    def test_0087_is_not_a_valid_post_ddl_recovery(self):
        host = FakeHost(fail='compose:run')
        with self.assertRaises(release.GateError):
            self.apply(host)
        host.fail = None
        host.events.clear()
        with (patch.object(release, 'load', side_effect=lambda p: json.loads(p.read_text())),
              self.assertRaisesRegex(release.GateError, 'compativel')):
            release.resume(host, self.receipt, release.fingerprint(self.receipt))
        self.assertNotIn('compose:up', host.events)

    def test_crash_before_ddl_recovers_original_runtime_without_external_ci(self):
        stage = {'sha': self.receipt['sha'], 'schema_started': False, 'baseline': inventory()}
        release.save(self.work / 'stage.json', stage)
        (self.state / 'app-in-flight.sha').write_text(self.receipt['sha'])
        host = FakeHost()
        with patch.object(release, 'load', side_effect=lambda p: json.loads(p.read_text())):
            release.recover(host, self.receipt, release.fingerprint(self.receipt))
        self.assertEqual(host.events, ['restore-before-ddl'])
        self.assertFalse((self.state / 'app-in-flight.sha').exists())

    def test_crash_recovery_never_restores_original_after_0088(self):
        stage = {'sha': self.receipt['sha'], 'schema_started': False, 'baseline': inventory()}
        release.save(self.work / 'stage.json', stage)
        (self.state / 'app-in-flight.sha').write_text(self.receipt['sha'])
        host = FakeHost()
        host.revision = release.TARGET_SCHEMA
        with (patch.object(release, 'load', side_effect=lambda p: json.loads(p.read_text())),
              self.assertRaisesRegex(release.GateError, 'schema_original')):
            release.recover(host, self.receipt, release.fingerprint(self.receipt))
        self.assertEqual(host.events, [])

    def test_timeout_never_escalates_to_sigkill(self):
        host = FakeHost()
        ident = host.data['services']['worker']['id']
        with (patch.object(release.time, 'monotonic', side_effect=[0, 0, 2]),
              patch.object(release.time, 'sleep'), self.assertRaisesRegex(release.GateError, 'timeout')):
            release.wait_exit(host, ident, 'worker', seconds=1)
        self.assertEqual(host.events, [])


if __name__ == '__main__':
    unittest.main()
