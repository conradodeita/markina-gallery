"""Opt-in disposable Engine regression for the first Compose handoff.

Uses only a caller-provided local lab image and a unique project; never SSH.
"""
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


@unittest.skipUnless(os.environ.get('APP_HANDOFF_LAB_IMAGE'), 'explicit disposable Docker lab required')
class FirstHandoffEngineContracts(unittest.TestCase):
    service = 'api'
    def docker(self, *args, check=True):
        return subprocess.run(['docker', *args], text=True, capture_output=True, check=check)

    def setUp(self):
        self.project = 'pyp-handoff-' + uuid.uuid4().hex[:12]
        self.image = os.environ['APP_HANDOFF_LAB_IMAGE']
        self.active_project = self.project
        self.projects = {self.project}
        info = json.loads(self.docker('image', 'inspect', self.image).stdout)[0]
        self.assertFalse(info['Config'].get('Volumes'), 'lab image must not create anonymous volumes')
        self.temp = tempfile.TemporaryDirectory(prefix=self.project)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.cleanup_containers)
        self.path = Path(self.temp.name) / 'compose.json'
        self.path.write_text(json.dumps({'services': {self.service: {
            'image': info['Id'], 'network_mode': 'none',
            'command': ['python', '-c', 'import time; time.sleep(300)']}}}), encoding='utf-8')
        self.original_name = self.project + '-' + self.service + '-1'

    def cleanup_containers(self):
        for project in self.projects:
            ids = self.docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project).stdout.split()
            for identity in ids:
                labels = self.inspect(identity)['Config']['Labels']
                self.assertEqual(labels['com.docker.compose.project'], project)
                self.docker('rm', '-f', identity)
            self.assertFalse(self.docker('ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project).stdout.strip())

    def inspect(self, identity):
        return json.loads(self.docker('inspect', identity).stdout)[0]

    def compose(self, *args, check=True):
        binary = os.environ.get('APP_HANDOFF_COMPOSE_BINARY')
        if binary:
            return self.docker('run', '--rm', '--network', 'none',
                '--mount', f'type=bind,source={Path(binary).resolve()},target=/compose,readonly',
                '--mount', f'type=bind,source={self.path},target=/case.json,readonly',
                '--mount', 'type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock',
                '--entrypoint', '/compose', self.image, '-p', self.active_project, '-f', '/case.json', *args, check=check)
        return self.docker('compose', '-p', self.active_project, '-f', str(self.path), *args, check=check)

    def up(self, check=True):
        return self.compose('up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                            '--force-recreate', '--wait', '--wait-timeout', '10', self.service, check=check)

    def legacy(self):
        return self.docker('run', '-d', '--name', self.original_name,
            '--label', 'com.docker.compose.project=' + self.project,
            '--label', 'com.docker.compose.service=' + self.service, '--network', 'none',
            self.image, 'python', '-c', 'import time; time.sleep(300)').stdout.strip()

    def test_unmanaged_name_conflict_preserves_original(self):
        old = self.legacy()
        result = self.up(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already in use', result.stderr)
        self.assertTrue(self.inspect(old)['State']['Running'])
        self.assertEqual(self.inspect(old)['Name'], '/' + self.original_name)

    def test_first_stop_rename_creates_candidate_and_preserves_original(self):
        old = self.legacy()
        before = self.inspect(old)
        self.docker('stop', '-t', '1', old)
        self.docker('rename', old, self.project + '-retained-' + old)
        self.up()
        new = self.inspect(self.original_name)
        self.assertNotEqual(new['Id'], old)
        self.assertTrue(new['State']['Running'])
        self.assertTrue(new['Config']['Labels'].get('com.docker.compose.config-hash'))
        retained = self.inspect(old)
        self.assertFalse(retained['State']['Running'])
        self.assertEqual(retained['Config'], before['Config'])
        self.assertEqual(retained['Image'], before['Image'])

    def test_compose_must_not_consume_retained_managed_candidate(self):
        self.up()
        retained = self.inspect(self.original_name)['Id']
        self.docker('stop', '-t', '1', retained)
        self.docker('rename', retained, self.project + '-retained-' + retained)
        # A new native Compose project keeps an earlier generation out of its
        # resource selection. The original operational name is explicit.
        self.active_project = self.project + '-generation-two'
        self.projects.add(self.active_project)
        document = json.loads(self.path.read_text())
        document['services'][self.service]['container_name'] = self.original_name
        self.path.write_text(json.dumps(document), encoding='utf-8')
        self.up()
        probe = self.docker('inspect', retained, check=False)
        self.assertEqual(probe.returncode, 0, 'Compose consumed the retained managed container')
        self.assertFalse(json.loads(probe.stdout)[0]['State']['Running'])
        new = self.inspect(self.original_name)
        self.assertNotEqual(new['Id'], retained)
        self.assertTrue(new['State']['Running'])
        self.assertEqual(new['Config']['Labels']['com.docker.compose.project'], self.active_project)


class WebFirstHandoffEngineContracts(FirstHandoffEngineContracts):
    service = 'web'


if __name__ == '__main__':
    unittest.main()
