"""Opt-in full helper rehearsal on disposable Engine resources, never production."""
import json
import os
import shlex
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

try:
    import fcntl
except ImportError:
    fcntl = None

import production_app_compose_bridge as bridge


@unittest.skipUnless(os.environ.get('APP_HANDOFF_ENGINE_IMAGE') and os.name == 'posix', 'explicit Linux Engine lab required')
class FullHandoffEngineContracts(unittest.TestCase):
    def docker(self, *args):
        return bridge._docker(list(args))

    def inspect(self, identity):
        return json.loads(self.docker('inspect', identity))[0]

    def setUp(self):
        self.project = 'pyp-full-handoff-' + uuid.uuid4().hex[:12]
        self.projects = {self.project}
        self.container_ids = set()
        self.resources = []
        self.image = os.environ['APP_HANDOFF_ENGINE_IMAGE']
        self.temp = tempfile.TemporaryDirectory(prefix=self.project)
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        checkout, state_root = root / 'checkout', root / 'state'
        working, state, private = checkout / 'docker', state_root / 'deploy-state', state_root / 'bridge'
        for path in (checkout, working, state_root, state, private):
            path.mkdir(mode=0o700)
        for key, value in (('PROJECT', self.project), ('PROJECT_ROOT', checkout), ('WORKING_DIR', working),
                           ('MARKINA_STATE_ROOT', state_root), ('STATE_DIR', state), ('BRIDGE_STATE', private),
                           ('ENV_FILE', working / '.env.homolog')):
            self.enterContext(patch.object(bridge, key, value))
        self.enterContext(patch.dict(bridge._run.__kwdefaults__, {'cwd': checkout}))
        bridge.ENV_FILE.write_text('SYNTHETIC_ONLY=yes\n')
        bridge.ENV_FILE.chmod(0o600)
        lock = state / 'production-release.lock'
        lock.touch(mode=0o600)
        self.lock = lock.open('rb')
        self.addCleanup(self.lock.close)
        fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.addCleanup(self.cleanup_engine)
        info = json.loads(self.docker('image', 'inspect', self.image))[0]
        self.assertFalse(info['Config'].get('Volumes'))
        self.image_info = info
        self.network = self.project + '-network'
        self.volume = self.project + '-data'
        self.docker('network', 'create', '--label', 'pyp.lab=' + self.project, self.network)
        self.resources.append(('network', self.network))
        self.docker('volume', 'create', '--label', 'pyp.lab=' + self.project, self.volume)
        self.resources.append(('volume', self.volume))
        historical_source = state / 'legacy-source.json'
        historical_source.write_text('{"historical":"not-the-active-configuration"}')
        historical_source.chmod(0o600)
        self.originals = {}
        self.history_records = []
        self.expected_projects = {service: self.project for service in bridge.SERVICES}
        self.current_models = None
        setup = "from pathlib import Path; import time, signal, sys; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); p=Path('/data'); (p/'alembic').mkdir(exist_ok=True); (p/'alembic/__init__.py').touch(); (p/'alembic/__main__.py').write_text(\"print('20261113_0126')\"); q=p/'sentinel'; q.write_text('preserved') if not q.exists() else None; time.sleep(600)"
        health_code = "import os; exit(int(os.environ['APP_VERSION'] != '" + '1' * 40 + "'))"
        health_command = ('python -c ' + shlex.quote(health_code)
                          if self._testMethodName == 'test_unhealthy_candidate_keeps_recovery_available'
                          else 'python -c "exit(0)"')
        for service in bridge.SERVICES:
            args = ['run', '-d', '--name', self.project + '-' + service + '-1',
                    '--label', 'com.docker.compose.project=' + self.project,
                    '--label', 'com.docker.compose.service=' + service,
                    '--label', 'io.pickyourpic.release=' + '1' * 40,
                    '--label', 'com.docker.compose.project.working_dir=' + str(working),
                    '--label', 'com.docker.compose.project.config_files=' + str(historical_source),
                    '--network', self.network, '--network-alias', service,
                    '--env', 'APP_VERSION=' + '1' * 40, '--env', 'APP_ENV=production',
                    '--env', 'FACIAL_PROCESSING_ENABLED=true', '--env', 'ADMIN_TOTP_KEYS=synthetic-$literal',
                    '--health-cmd', health_command, '--health-interval', '1s', '--health-timeout', '1s']
            if service == 'api':
                args += ['--mount', 'type=volume,source=' + self.volume + ',target=/data', '--env', 'PYTHONPATH=/data']
            args += [self.image, 'python', '-c', setup if service == 'api' else 'import time, signal, sys; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); time.sleep(600)']
            identity = self.docker(*args).strip()
            self.container_ids.add(identity)
            deadline = time.monotonic() + 30
            while self.inspect(identity)['State'].get('Health', {}).get('Status') != 'healthy':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.5)
            self.originals[service] = self.inspect(identity)
        self.witness = self.docker('create', '--name', self.project + '-historical-api',
                                   '--label', 'com.docker.compose.project=' + self.project,
                                   '--label', 'com.docker.compose.service=api', '--network', 'none',
                                   self.image, 'python', '-c', 'pass').strip()
        self.container_ids.add(self.witness)
        self.witness_record = bridge.handoff_witness_record(self.inspect(self.witness))
        self.neighbor = self.docker('run', '-d', '--network', 'none', '--label', 'pyp.lab=' + self.project,
                                    self.image, 'python', '-c', 'import time, signal, sys; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); time.sleep(600)').strip()
        self.container_ids.add(self.neighbor)
        self.neighbor_before = self.inspect(self.neighbor)

    def cleanup_engine(self):
        for project in self.projects:
            ids = self.docker('ps', '-aq', '--no-trunc', '--filter', 'label=com.docker.compose.project=' + project).split()
            for identity in ids:
                self.assertEqual(self.inspect(identity)['Config']['Labels']['com.docker.compose.project'], project)
                self.container_ids.add(identity)
        for identity in self.container_ids:
            self.docker('rm', '-f', identity)
        for kind, name in reversed(self.resources):
            info = json.loads(self.docker(kind, 'inspect', name))[0]
            self.assertEqual(info['Labels']['pyp.lab'], self.project)
            self.docker(kind, 'rm', name)
        for project in self.projects:
            self.assertFalse(self.docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project).strip())

    def prepare(self, target='2' * 40):
        items = [self.inspect(self.project + '-' + service + '-1') for service in bridge.SERVICES]
        models = (json.loads(json.dumps(self.current_models)) if self.current_models else
                  {service: bridge.adoption_document(service, item, self.image_info)
                   for service, item in zip(bridge.SERVICES, items)})
        candidates = {service: bridge.replacement_document(service, models[service], item, item['Image'], target)
                      for service, item in zip(bridge.SERVICES, items)}
        records = [bridge.handoff_record(service, item, self.expected_projects[service])
                   for service, item in zip(bridge.SERVICES, items)]
        witness = self.inspect(self.witness)
        items.append(witness)
        records.append(self.witness_record)
        records += self.history_records
        items += [self.inspect(record["id"]) for record in self.history_records]
        source = bridge.STATE_DIR / ('source-' + target + '.json')
        source.write_text(json.dumps(models))
        source.chmod(0o600)
        plan = bridge.handoff_plan(target, '3' * 40, 'd' * 64, items, records, candidates, models,
                                   {str(source): bridge.snapshot_sha256(source)}, bridge.snapshot_sha256(bridge.ENV_FILE), '1' * 40)
        self.projects.add(plan['project'])
        identity, revision = bridge.handoff_journal_create(plan)
        return plan, identity, revision

    def test_real_first_handoff_and_recovery_preserve_data_and_neighbor(self):
        plan, identity, revision = self.prepare()
        revision = bridge.handoff_execute_service(identity, revision, 'api')
        bridge.handoff_execute_service(identity, revision, 'web')
        receipt = bridge.handoff_publish_runtime(identity)
        self.assertEqual(receipt['checkout_sha'], '2' * 40)
        self.assertEqual(receipt['web_version'], '2' * 40)
        # User labels remain unchanged; the candidate image/plan proves code origin.
        self.assertEqual(self.inspect(self.project + '-web-1')['Config']['Labels']['io.pickyourpic.release'], '1' * 40)
        self.assertEqual(set(bridge._inspect_api_web()), set(bridge.SERVICES))
        candidates = [self.inspect(self.project + '-' + service + '-1') for service in bridge.SERVICES]
        self.container_ids.update(item['Id'] for item in candidates)
        for service, item in zip(bridge.SERVICES, candidates):
            self.assertNotEqual(item['Id'], self.originals[service]['Id'])
            self.assertEqual(item['Config']['Labels']['com.docker.compose.project'], plan['project'])
            self.assertFalse(self.inspect(self.originals[service]['Id'])['State']['Running'])
        api = candidates[0]
        self.assertEqual(self.docker('exec', api['Id'], 'cat', '/data/sentinel').strip(), 'preserved')
        dns = self.docker('exec', api['Id'], 'python', '-c', "import socket; print(socket.gethostbyname('web'))").strip()
        self.assertEqual(dns, candidates[1]['NetworkSettings']['Networks'][self.network]['IPAddress'])
        inventory = bridge.handoff_recovery_inventory(identity, [self.inspect(i['Id']) for i in self.originals.values()] + candidates + [self.inspect(self.witness)],
                                                       {self.image_info['Id']: self.image_info}, '20261113_0126')
        recovery, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        revision = bridge.handoff_recover_service(recovery, revision, 'api')
        bridge.handoff_recover_service(recovery, revision, 'web')
        receipt = bridge.handoff_publish_runtime(recovery, restoring=True)
        self.assertEqual(receipt['checkout_sha'], '1' * 40)
        self.assertEqual(receipt['web_version'], '1' * 40)
        self.assertEqual(bridge._inspect_api_web()['api']['Id'], self.originals['api']['Id'])
        for service in bridge.SERVICES:
            restored = self.inspect(self.project + '-' + service + '-1')
            self.assertEqual(restored['Id'], self.originals[service]['Id'])
            self.assertTrue(restored['State']['Running'])
            self.assertEqual(restored['Config'], self.originals[service]['Config'])
        self.assertEqual(self.docker('exec', self.originals['api']['Id'], 'cat', '/data/sentinel').strip(), 'preserved')
        neighbor = self.inspect(self.neighbor)
        self.assertEqual(neighbor['State']['StartedAt'], self.neighbor_before['State']['StartedAt'])
        self.assertEqual(neighbor['Config'], self.neighbor_before['Config'])
        self.assertEqual(neighbor['Image'], self.neighbor_before['Image'])
        self.assertEqual(bridge.handoff_journal_read(recovery)[1]['phases'], {'api': 'healthy', 'web': 'healthy'})

    def relevant_items(self):
        identities = set()
        for project in self.projects:
            identities.update(self.docker('ps', '-aq', '--no-trunc', '--filter', 'label=com.docker.compose.project=' + project).split())
        return [self.inspect(identity) for identity in sorted(identities)]

    def recovery_inventory(self, identity):
        items = self.relevant_items()
        schema = None
        for item in items:
            if item['Name'] == '/' + self.project + '-api-1' and item['State']['Running'] and item['State'].get('Health', {}).get('Status') == 'healthy':
                schema = self.docker('exec', item['Id'], 'python', '-B', '-m', 'alembic', 'current').strip()
        return bridge.handoff_recovery_inventory(identity, items, {self.image_info['Id']: self.image_info}, schema)

    def recover_and_assert(self, identity):
        inventory = self.recovery_inventory(identity)
        recovery, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        revision = bridge.handoff_recover_service(recovery, revision, 'api')
        bridge.handoff_recover_service(recovery, revision, 'web')
        for service in bridge.SERVICES:
            restored = self.inspect(self.project + '-' + service + '-1')
            self.assertEqual(restored['Id'], self.originals[service]['Id'])
            self.assertTrue(restored['State']['Running'])
            self.assertEqual(restored['Config'], self.originals[service]['Config'])
        self.assertEqual(self.docker('exec', self.originals['api']['Id'], 'cat', '/data/sentinel').strip(), 'preserved')
        self.assertEqual(self.inspect(self.neighbor)['State']['StartedAt'], self.neighbor_before['State']['StartedAt'])
        self.assertFalse(self.inspect(self.witness)['State']['Running'])
        dns = self.docker('exec', self.originals['api']['Id'], 'python', '-c', "import socket; print(socket.gethostbyname('web'))").strip()
        self.assertEqual(dns, self.inspect(self.originals['web']['Id'])['NetworkSettings']['Networks'][self.network]['IPAddress'])

    def interruption(self, service, operation, after=True):
        _, identity, revision = self.prepare()
        if service == 'web':
            revision = bridge.handoff_execute_service(identity, revision, 'api')
        real_docker, real_run = bridge._docker, bridge._run
        fired = False
        def docker(args, **kwargs):
            nonlocal fired
            match = args[0] == operation and args[-1 if operation == 'stop' else 1] == self.originals[service]['Id']
            if match and not fired:
                fired = True
                if after:
                    real_docker(args, **kwargs)
                raise bridge.BridgeError('synthetic_effect_interruption')
            return real_docker(args, **kwargs)
        def run(args, **kwargs):
            nonlocal fired
            result = real_run(args, **kwargs)
            if operation == 'create' and len(args) > 2 and args[1] == 'compose' and 'up' in args and args[-1] == service and not fired:
                fired = True
                raise bridge.BridgeError('synthetic_effect_interruption')
            return result
        with (patch.object(bridge, '_docker', side_effect=docker),
              patch.object(bridge, '_run', side_effect=run),
              self.assertRaisesRegex(bridge.BridgeError, 'synthetic_effect_interruption')):
            bridge.handoff_execute_service(identity, revision, service)
        self.assertTrue(fired)
        self.recover_and_assert(identity)

    def test_interruption_before_api_stop(self):
        self.interruption('api', 'stop', after=False)

    def test_interruption_after_api_stop(self):
        self.interruption('api', 'stop')

    def test_interruption_after_api_rename(self):
        self.interruption('api', 'rename')

    def test_interruption_after_api_creation(self):
        self.interruption('api', 'create')

    def test_interruption_after_web_stop(self):
        self.interruption('web', 'stop')

    def test_interruption_after_web_creation(self):
        self.interruption('web', 'create')

    def test_interruption_after_web_rename(self):
        self.interruption('web', 'rename')

    def test_interruption_before_web_stop(self):
        self.interruption('web', 'stop', after=False)

    def test_unhealthy_candidate_keeps_recovery_available(self):
        _, identity, revision = self.prepare()
        original_run = bridge._run
        def shortened_wait(args, **kwargs):
            args = list(args)
            if len(args) > 2 and args[1] == 'compose' and '--wait-timeout' in args:
                args[args.index('--wait-timeout') + 1] = '5'
            return original_run(args, **kwargs)
        with patch.object(bridge, '_run', side_effect=shortened_wait), self.assertRaises(bridge.BridgeError):
            bridge.handoff_execute_service(identity, revision, 'api')
        self.assertEqual(bridge.handoff_journal_read(identity)[1]['phases']['api'], 'create_intent')
        self.recover_and_assert(identity)

    def test_later_generation_keeps_both_previous_generations(self):
        first, identity, revision = self.prepare()
        revision = bridge.handoff_execute_service(identity, revision, 'api')
        bridge.handoff_execute_service(identity, revision, 'web')
        first_candidates = {service: self.inspect(self.project + '-' + service + '-1') for service in bridge.SERVICES}
        for record in first['sources']:
            if not record['retained']:
                old = self.inspect(record['id'])
                expected = dict(record, retained=True, name=bridge.handoff_retained_name(record['service'], record['id']))
                self.assertEqual(bridge.handoff_record(record['service'], old, record['project'], retained=True), expected)
                self.history_records.append(expected)
        self.current_models = first['models']
        self.expected_projects = {service: first['project'] for service in bridge.SERVICES}
        second, identity, revision = self.prepare(target='4' * 40)
        self.assertNotEqual(first['project'], second['project'])
        revision = bridge.handoff_execute_service(identity, revision, 'api')
        bridge.handoff_execute_service(identity, revision, 'web')
        for previous in list(self.originals.values()) + list(first_candidates.values()):
            retained = self.inspect(previous['Id'])
            self.assertFalse(retained['State']['Running'])
            self.assertEqual(retained['Config'], previous['Config'])
        self.assertEqual(self.docker('exec', self.project + '-api-1', 'cat', '/data/sentinel').strip(), 'preserved')
        self.assertEqual(self.inspect(self.neighbor)['State']['StartedAt'], self.neighbor_before['State']['StartedAt'])


if __name__ == '__main__':
    unittest.main()
