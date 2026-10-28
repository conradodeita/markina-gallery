"""Falhas de release financeiro: nenhuma operação real ou credencial nos testes."""
import copy
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import orders_pilot_release as release


class CliContractTests(unittest.TestCase):
    def test_release_targets_integrated_orders_runtime_and_schema_0089(self):
        self.assertEqual(release.APPROVED_RUNTIME, 'b69a95c526912d725863a57a13f8735a62f671ed')
        self.assertEqual(release.SCHEMA, '20261024_0088')
        self.assertEqual(release.BASELINE_SHA, '9bd66c48d7d43462886652b8fe85fdcbff877f64')
        self.assertEqual(release.TARGET_SCHEMA, '20261025_0089')

    def test_inventory_sha_must_match_current_main_before_host_reads(self):
        with (patch.object(release.Host, 'main_sha', return_value='a' * 40),
              patch.object(release.Host, 'inventory') as inventory,
              patch('sys.argv', ['orders_pilot_release.py', 'inventory', '--sha', 'b' * 40]),
              self.assertRaisesRegex(release.GateError, 'candidato_nao_e_main')):
            release.main()
        inventory.assert_not_called()

    def test_operational_command_failure_reports_only_fixed_stage(self):
        host = release.Host()
        with (patch.object(release.subprocess, 'run', side_effect=subprocess.CalledProcessError(
                1, ['docker', 'exec'], stderr='sensitive output')),
              self.assertRaisesRegex(release.GateError,
                                     'comando_operacional_falhou:read_tenant_configuration_matrix') as caught):
            host.run('docker', 'exec', 'private-container', 'psql',
                     diagnostic_stage='read_tenant_configuration_matrix')
        self.assertNotIn('sensitive output', str(caught.exception))
        self.assertNotIn('private-container', str(caught.exception))

    def test_inventory_reports_only_validated_git_shas_for_checkout_lineage_mismatch(self):
        checkout_sha = 'b' * 40
        main_sha = 'a' * 40

        def run(*args, **kwargs):
            if args == ('git', 'remote', 'get-url', 'origin'):
                return release.REPOSITORY
            if args == ('git', 'rev-parse', 'HEAD'):
                return checkout_sha
            if args == ('git', 'merge-base', '--is-ancestor', checkout_sha, main_sha):
                return 1
            raise AssertionError(args)

        with (patch.object(release.Host, 'run', side_effect=run),
              patch.object(release.Host, 'main_sha', return_value=main_sha),
              self.assertRaisesRegex(release.GateError,
                  f'checkout_fora_da_main_history:checkout_sha={checkout_sha};main_sha={main_sha}') as caught):
            release.Host().live_gate_inventory()
        self.assertNotIn('private-container', str(caught.exception))

    def test_inventory_0090_uses_sanitized_live_gate_matrix(self):
        sha = 'a' * 40
        checkout_sha = 'b' * 40
        active_sha = release.LIVE_MINIMUM_SHA
        pair = {'tenant_id': str(release.uuid4()), 'client_id': str(release.uuid4())}
        matrix = {'preference_tenants': 3, 'pix_enabled': 2, 'mercadopago_enabled': 2,
                  'mp_enabled_production_active': 1, 'mp_enabled_test_active': 1,
                  'mp_enabled_unavailable': 0, 'mp_disabled': 1}
        ids = {name: str(index).zfill(64) for index, name in enumerate(sorted(release.SERVICES), 1)}

        git_calls = []

        def run(*args, **kwargs):
            if args and args[0] == 'git':
                git_calls.append(args)
            if args == ('git', 'remote', 'get-url', 'origin'):
                return release.REPOSITORY
            if args == ('git', 'rev-parse', 'HEAD'):
                return checkout_sha
            if args == ('git', 'status', '--porcelain'):
                return ''
            if args[:2] == ('git', 'merge-base'):
                return 0 if kwargs.get('check') is False else ''
            if args[:3] == ('docker', 'ps', '-q'):
                return ' '.join(ids.values())
            if args[:3] == ('docker', 'exec', ids['api']):
                return 'valid'
            raise AssertionError(args)

        def inspect(ident, diagnostic_stage=None):
            name = next(name for name, value in ids.items() if value == ident)
            env = []
            if name == 'api':
                env = ['APP_ENV=production', 'MERCADOPAGO_ALLOW_LIVE_PAYMENTS=false',
                       f'MERCADOPAGO_TEST_CUSTOMERS={json.dumps([pair])}', f'APP_VERSION={active_sha}']
            elif name in {'worker', 'web'}:
                env = [f'APP_VERSION={active_sha}']
            ports = {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if name == 'nginx' else {}
            return {'Id': ident, 'Image': 'sha256:' + 'b' * 64,
                    'Config': {'Labels': {'com.docker.compose.service': name,
                        'com.docker.compose.project.config_files': '/opt/active.compose.json',
                        'com.docker.compose.config-hash': 'c' * 64}, 'Env': env},
                    'State': {'Status': 'running', 'Health': {'Status': 'healthy'}},
                    'NetworkSettings': {'Ports': ports}}

        with (patch.object(release.socket, 'gethostname', return_value='clearbudget-vnic'),
              patch.object(release.Path, 'resolve', return_value=release.ROOT),
              patch.object(release.Host, 'schema', return_value=[release.LIVE_SCHEMA]),
              patch.object(release.Host, 'main_sha', return_value=sha),
              patch.object(release.Host, 'run', side_effect=run),
              patch.object(release.Host, 'inspect', side_effect=inspect),
              patch.object(release.Host, 'current_test_pair', return_value=(pair, release.fingerprint(pair))),
              patch.object(release.Host, 'pg', return_value=matrix),
              patch.object(release.Host, 'health', return_value=[200, 200, 200])):
            data = release.Host().inventory()
            mismatched = {**pair, 'tenant_id': str(release.uuid4())}
            with (patch.object(release.Host, 'current_test_pair', return_value=(mismatched,
                    release.fingerprint(mismatched))),
                  self.assertRaisesRegex(release.GateError, 'par_de_teste_divergente')):
                release.Host().inventory()

        self.assertEqual(data['inventory_kind'], 'mercadopago-live-gate-read-only')
        self.assertEqual(data['tenant_configuration_matrix'], matrix)
        self.assertEqual(data['live_gate'], 'false')
        self.assertEqual(data['main_sha'], sha)
        self.assertEqual(data['checkout_sha'], checkout_sha)
        self.assertIn(('git', 'merge-base', '--is-ancestor', checkout_sha, sha), git_calls)
        self.assertEqual(data['active_sha'], active_sha)
        self.assertEqual(data['test_allowlist_pairs'], 1)
        self.assertEqual(data['test_allowlist_pair_fingerprint'], release.fingerprint(pair))
        self.assertNotIn(pair['tenant_id'], json.dumps(data))
        self.assertNotIn(pair['client_id'], json.dumps(data))


def inventory():
    return {'host': 'clearbudget-vnic', 'root': str(release.ROOT), 'project': release.PROJECT,
        'origin': release.ORIGIN, 'checkout_sha': release.BASELINE_SHA, 'clean': True, 'schema': release.SCHEMA,
        'orders_tables': 4, 'pending': [], 'key': {'valid': True, 'mode': 0o600, 'path': str(release.KEY_TARGET),
          'sha256': hashlib.sha256(b'synthetic-key').hexdigest()},
        'app_env': 'staging', 'free_bytes': 8 * 1024**3,
        'files': {str(p): 'b' * 64 for p in release.CONFIGS + (release.ROOT / 'docker/.env.homolog',)},
        'https': [200, 200, 200], 'services': {
            s: {'id': str(n).zfill(64), 'image': release.PILLOW_IMAGES.get(s,
                    release.BASELINE_IMAGES.get('api' if s == 'worker' else s, 'sha256:' + str(n).zfill(64))),
                'compose_files': str(release.PILLOW_OVERLAY) + ',' + str(release.BASELINE_ORDERS_OVERLAY),
                'command': ['python', '-m', 'synthetic.' + s], 'status': 'running', 'health': 'healthy',
                'restart_policy': {'Name': 'unless-stopped' if s in release.SPECIALIZED else 'no', 'MaximumRetryCount': 0},
                'version': release.BASELINE_SHA if s in ('api', 'worker') else None,
                'ports': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if s == 'nginx' else {}}
            for n, s in enumerate(sorted(release.SERVICES), 1)},
        'orders_identity': {'sha256': release.BASELINE_IDENTITY_SHA256,
                            'overlay_sha256': release.BASELINE_OVERLAY_SHA256,
                            'receipt_sha256': release.BASELINE_RECEIPT_SHA256},
        'pillow': {'source_sha': release.PILLOW_SOURCE, 'approval': release.PILLOW_APPROVAL,
                   'receipt_sha256': 'e' * 64}}


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

    def published_orders(self):
        return {}, PAIR, {}

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

    def public_ready(self):
        release.Host.public_ready(self)

    def restore_before_ddl(self, *args):
        self.event('restore-before-ddl')


class PolicyTests(unittest.TestCase):
    def test_missing_pillow_proof_old_image_or_overlay_blocks_inventory(self):
        for case in ('receipt', 'image', 'overlay', 'approval'):
            data = inventory()
            if case == 'receipt':
                data.pop('pillow')
            elif case == 'image':
                data['services']['face-index-worker']['image'] = 'sha256:' + 'a' * 64
            elif case == 'overlay':
                data['services']['face-index-worker']['compose_files'] = 'old-compose-only'
            else:
                data['pillow']['approval'] = 'unapproved'
            with self.assertRaisesRegex(release.GateError, 'pillow'):
                release.validate_inventory(data)

    def test_pillow_published_receipt_and_exact_overlay_are_required(self):
        expected = {'services': {name: {'image': image} for name, image in release.PILLOW_IMAGES.items()}}
        proof = {'security_fixed': True, 'financial_preserved': True, 'fingerprint': release.PILLOW_APPROVAL,
                 'source_sha': release.PILLOW_SOURCE, 'schema': ['20261022_0087'], 'services': expected}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'published.json'
            path.write_text(json.dumps(proof))
            with (patch.object(release, 'PILLOW_RECEIPT', path),
                  patch.object(release, 'load', side_effect=[proof, expected])):
                self.assertEqual(release.Host().pillow()['source_sha'], release.PILLOW_SOURCE)
            for field, value in (('security_fixed', False), ('source_sha', 'other'),
                                 ('schema', ['other']), ('fingerprint', 'other'), ('services', {})):
                changed = dict(proof, **{field: value})
                with (patch.object(release, 'load', return_value=changed),
                      self.assertRaisesRegex(release.GateError, 'recibo_pillow')):
                    release.Host().pillow()
            with (patch.object(release, 'load', side_effect=[proof, {'services': {}}]),
                  self.assertRaisesRegex(release.GateError, 'overlay_pillow')):
                release.Host().pillow()

    def test_nginx_reload_waits_for_public_health_but_refuses_persistent_failure(self):
        host = release.Host()
        with (patch.object(host, 'health', side_effect=[[200, 200, 503], [200, 200, 200]]),
              patch.object(release.time, 'sleep') as sleep):
            host.public_ready()
            sleep.assert_called_once_with(0.5)
        with (patch.object(host, 'health', return_value=[200, 200, 503]),
              patch.object(release.time, 'monotonic', side_effect=[0, 16]),
              self.assertRaisesRegex(release.GateError, 'smoke_publico')):
            host.public_ready()

    def test_runtime_snapshot_remains_frozen_and_overlay_is_in_all_compose_commands(self):
        self.assertEqual(release.APPROVED_RUNTIME, 'b69a95c526912d725863a57a13f8735a62f671ed')
        with patch.object(release.Host, 'run', return_value='') as run:
            release.Host().compose(Path('/synthetic'), 'config', '--quiet')
        self.assertIn(str(release.PILLOW_OVERLAY), run.call_args.args)

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

    def test_upgrade_preserves_all_existing_distributions(self):
        before = {'python': '3.13.17', 'packages': {'requests': '2.34.2', 'mercadopago': '3.6.0'}}
        after = copy.deepcopy(before)
        release.package_parity(before, after)
        for mutate in [lambda d: d.update(python='3.14.0'),
                       lambda d: d['packages'].update(requests='changed'),
                       lambda d: d['packages'].update(mercadopago='3.7.0'),
                       lambda d: d['packages'].update(unrelated='1')]:
            value = copy.deepcopy(after)
            mutate(value)
            with self.assertRaises(release.GateError):
                release.package_parity(before, value)
        missing_sdk = copy.deepcopy(before)
        missing_sdk['packages'].pop('mercadopago')
        with self.assertRaises(release.GateError):
            release.package_parity(missing_sdk, after)

    def test_financial_snapshot_includes_all_orders_and_reference_columns(self):
        host = release.Host()
        queries = []
        host.pg = lambda query, db: queries.append(query) or {'count': 9, 'digest': 'synthetic'}
        result = host.financial('isolated-fixture')
        self.assertTrue({'mercadopago_account', 'mercadopago_payment', 'mercadopago_webhook',
                         'payment_preferences'} <= set(result))
        self.assertTrue(all('to_jsonb(t)::text' in query for query in queries))
        self.assertFalse(any("-'mercadopago_payment_id'" in query for query in queries))

    def test_historical_first_release_cannot_be_used_as_upgrade_inventory(self):
        for field, value in (('schema', '20261022_0087'), ('orders_tables', 0),
                             ('checkout_sha', '1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8'),
                             ('orders_identity', {})):
            data = inventory()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(release.GateError):
                release.validate_inventory(data)

    @unittest.skipUnless(os.name == 'posix', 'Permissoes do recibo sao verificadas no host Linux/CI.')
    def test_published_orders_pins_identity_receipt_overlay_and_owner_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            work = state / 'published'
            work.mkdir()
            overlay = work / 'active.compose.json'
            overlay.write_text('{}')
            receipt_path = work / 'prepared-main.json'
            receipt = {'sha': release.BASELINE_SHA, 'images': release.BASELINE_IMAGES, 'pair': PAIR}
            release.save(receipt_path, receipt)
            identity_path = state / 'orders-current.identity.json'
            identity = {'sha': release.BASELINE_SHA, 'schema': release.SCHEMA,
                        'images': release.BASELINE_IMAGES, 'receipt': str(receipt_path), 'emission': 'owner_test'}
            release.save(identity_path, identity)
            original = {path: path.read_bytes() for path in (identity_path, receipt_path, overlay)}
            with (patch.object(release, 'STATE', state), patch.object(release, 'BASELINE_ORDERS_WORK', work),
                  patch.object(release, 'BASELINE_ORDERS_OVERLAY', overlay),
                  patch.object(release, 'BASELINE_IDENTITY_SHA256', hashlib.sha256(original[identity_path]).hexdigest()),
                  patch.object(release, 'BASELINE_RECEIPT_SHA256', hashlib.sha256(original[receipt_path]).hexdigest()),
                  patch.object(release, 'BASELINE_OVERLAY_SHA256', hashlib.sha256(original[overlay]).hexdigest())):
                self.assertEqual(release.Host().published_orders()[1], PAIR)
                for path, contents in original.items():
                    path.write_bytes(contents + b' ')
                    with self.subTest(path=path.name), self.assertRaises(release.GateError):
                        release.Host().published_orders()
                    path.write_bytes(contents)

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
        self.addCleanup(patch.stopall)
        patch.object(release, 'STATE', self.state).start()
        identity = json.dumps({'sha': release.BASELINE_SHA, 'schema': release.SCHEMA,
                               'images': release.BASELINE_IMAGES}).encode()
        self.original_identity = identity
        (self.state / 'orders-current.identity.json').write_bytes(identity)
        patch.object(release, 'BASELINE_IDENTITY_SHA256', hashlib.sha256(identity).hexdigest()).start()
        self.work = self.state / 'orders-prepare-fixture'
        self.work.mkdir()
        self.backup = self.work / 'database.custom'
        self.backup.write_bytes(b'synthetic')
        (self.work / 'integration-secrets.backup.env').write_bytes(b'synthetic-key')
        identity_backup = self.work / 'baseline-orders.identity.json'
        identity_backup.write_bytes(identity)
        identity_backup.chmod(0o600)
        baseline = inventory()
        self.receipt = {'format': 2, 'operation': 'orders-0088-to-0089',
                        'previous_identity': str(self.work / 'baseline-orders.identity.json'),
                        'sha': 'f' * 40, 'build_sha': release.APPROVED_RUNTIME, 'rehearsal': 'passed', 'work': str(self.work),
                        'guard': 'passed',
                        'restart_policy_rehearsal': 'passed',
                        'callbacks': {'retry503': True, 'retryRefused': True, 'nonRetryable400': True,
                                      'source_sha256': 'a' * 64, 'image': baseline['services']['evolution-api']['image']},
                        'backup': str(self.backup), 'backup_sha256': hashlib.sha256(b'synthetic').hexdigest(),
                        'key_backup': str(self.work / 'integration-secrets.backup.env'), 'inventory': baseline,
                        'baseline_fingerprint': release.validate_inventory(baseline),
                        'images': IMAGES, 'pair': PAIR}
        patch.object(release, 'release_lock', nullcontext).start()

    def apply(self, host, *, approval=None, legacy=True):
        release.apply(host, self.receipt, approval or release.fingerprint(self.receipt), legacy=legacy)

    def test_success_preserves_specialized_and_orders_actions(self):
        host = FakeHost()
        with patch.object(release, 'load', side_effect=lambda path: json.loads(path.read_text())):
            self.apply(host)
        self.assertNotIn('restore-before-ddl', host.events)
        self.assertEqual(host.events.count('resume-specialized'), 6)
        migration = host.events.index('compose:run')
        for name in release.WRITERS:
            self.assertLess(host.events.index('stop:' + name), migration)
        self.assertLess(host.events.index('rehearse'), migration)
        self.assertLess(host.events.index('new-healthy'), host.events.index('maintenance:False'))
        self.assertFalse((self.state / 'app-in-flight.sha').exists())
        self.assertEqual((self.work / 'baseline-orders.identity.json').read_bytes(), self.original_identity)
        identity = json.loads((self.state / 'orders-current.identity.json').read_text())
        self.assertEqual(identity['schema'], release.TARGET_SCHEMA)
        self.assertEqual(identity['images'], IMAGES)

    def test_old_receipt_or_missing_identity_backup_blocks_before_host_calls(self):
        for mutation in ('format', 'missing', 'tampered'):
            receipt = copy.deepcopy(self.receipt)
            if mutation == 'format':
                receipt['format'] = 1
            elif mutation == 'missing':
                receipt.pop('previous_identity')
            else:
                Path(receipt['previous_identity']).write_bytes(b'tampered')
            host = FakeHost()
            with self.subTest(mutation=mutation), self.assertRaises(release.GateError):
                release.apply(host, receipt, release.fingerprint(receipt), legacy=True)
            self.assertEqual(host.events, [])

    def test_unknown_current_identity_is_never_overwritten(self):
        path = self.state / 'orders-current.identity.json'
        path.write_text(json.dumps({'sha': 'unknown'}))
        before = path.read_bytes()
        with (patch.object(release, 'load', side_effect=lambda item: json.loads(item.read_text())),
              self.assertRaisesRegex(release.GateError, 'identidade_orders_mudou')):
            release.publish_identity(self.receipt, emission='owner_test')
        self.assertEqual(path.read_bytes(), before)

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

    def test_recovery_keeps_0089_and_closes_emission_without_touching_database(self):
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

    def test_0088_is_not_a_valid_post_ddl_recovery(self):
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

    def test_crash_recovery_never_restores_original_after_0089(self):
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
