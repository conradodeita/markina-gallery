"""Ensaio Docker opt-in em runner Linux descartável, nunca no projeto publicado."""
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

import nginx_compose_provenance as mod


@unittest.skipUnless(os.environ.get('NGINX_PROVENANCE_DOCKER_TEST') == '1' and os.name == 'posix',
                     'ensaio Docker exclusivo do runner Linux descartável')
class DockerProof(unittest.TestCase):
    def setUp(self):
        self.project = 'markina-nginx-proof-' + uuid.uuid4().hex[:12]
        self.temp = tempfile.TemporaryDirectory(prefix=self.project)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        (self.state / 'production-release.lock').touch(mode=0o600)
        self.network = self.project + '_internal'
        self.runner = mod.Runner()
        self.addCleanup(self.cleanup_resources)
        self.runner.run('docker', 'network', 'create', '--label',
                        'com.docker.compose.project=' + self.project, self.network)
        source = self.root / 'server.conf'
        source.write_text('server { listen 80; location / { return 200 "fixture"; } }\n')
        self.compose_file = self.root / 'initial.compose.json'
        with socket.socket() as allocation:
            allocation.bind(('127.0.0.1', 0))
            test_port = allocation.getsockname()[1]
        model = {'name': self.project, 'services': {'nginx': {
            'image': 'nginx:1.27-alpine', 'ports': [{'target': 80, 'published': str(test_port), 'host_ip': '127.0.0.1'}],
            'volumes': [{'type': 'bind', 'source': str(source), 'target': mod.CONFIG_FILES[2],
                         'read_only': True}],
            'networks': {self.network: {'aliases': ['proof-alias']}}, 'cgroup': 'host',
            'logging': {'driver': 'json-file'},
            'healthcheck': {'test': ['CMD-SHELL', 'wget -qO- http://127.0.0.1/healthz >/dev/null'],
                            'interval': '1s', 'timeout': '1s', 'retries': 5},
        }}, 'networks': {self.network: {'external': True, 'name': self.network}}}
        self.compose_file.write_text(json.dumps(model))
        self.runner.run('docker', 'compose', '-p', self.project, '-f', str(self.compose_file),
                        'up', '-d', '--no-deps', 'nginx', timeout=120)
        deadline = time.monotonic() + 30
        while True:
            cid = self.runner.run('docker', 'ps', '-q', '--filter',
                                  'label=com.docker.compose.project=' + self.project).decode().strip()
            c = self.runner.json('docker', 'inspect', cid)[0]
            if c['State'].get('Health', {}).get('Status') == 'healthy':
                break
            self.assertLess(time.monotonic(), deadline)
            time.sleep(1)
        # Estes caminhos são defaults do daemon/host e variam entre runners;
        # a prova valida que a recriação preserva os do próprio runtime isolado.
        self.assertIsInstance(c['HostConfig'].get('MaskedPaths'), list)
        self.assertIsInstance(c['HostConfig'].get('ReadonlyPaths'), list)
        original_masked, original_readonly = mod.MASKED, mod.READONLY
        mod.MASKED = list(c['HostConfig']['MaskedPaths'])
        mod.READONLY = list(c['HostConfig']['ReadonlyPaths'])
        self.addCleanup(setattr, mod, 'MASKED', original_masked)
        self.addCleanup(setattr, mod, 'READONLY', original_readonly)
        # Testemunha parada: identidade deve sobreviver à publicação e à recuperação.
        self.runner.run('docker', 'create', '--label', 'com.docker.compose.project=' + self.project,
                        '--label', 'com.docker.compose.service=witness', 'nginx:1.27-alpine', 'true')
        port = c['HostConfig']['PortBindings']['80/tcp'][0]['HostPort']
        self.operation = mod.Operation(root=self.root, state=self.state, project=self.project,
                                       url='http://127.0.0.1:' + port)

    def cleanup_resources(self):
        # Somente fixtures deste UUID. Não faz down/prune e não remove imagens.
        if not self.project.startswith('markina-nginx-proof-'):
            raise AssertionError('projeto inválido')
        ids = subprocess.check_output(['docker', 'ps', '-aq', '--filter',
                                      'label=com.docker.compose.project=' + self.project], text=True).split()
        for cid in ids:
            subprocess.run(['docker', 'stop', '--timeout', '-1', cid], capture_output=True, timeout=30, check=False)
            subprocess.run(['docker', 'rm', cid], capture_output=True, check=True)
        subprocess.run(['docker', 'network', 'rm', self.network], capture_output=True, check=False)
        self.temp.cleanup()

    def prepared(self):
        payload = self.operation.snapshot()
        self.operation.validate_model(payload)
        self.operation.prepare(payload['approval_fingerprint'])
        return payload

    def test_success_preserves_bytes_image_and_witness(self):
        payload = self.prepared()
        result = self.operation.release(payload['bundle_id'], payload['approval_fingerprint'])
        self.assertEqual(result['status'], 'publicado')
        current = self.operation.verify_running(payload)
        self.assertNotEqual(current['Id'], payload['nginx']['Id'])
        self.assertEqual(current['Config']['Labels']['com.docker.compose.project.config_files'],
                         str(self.state / 'nginx-provenance' / payload['bundle_id'] / 'candidate.compose.json'))

    def test_post_creation_failure_recovers_real_container(self):
        payload = self.prepared()
        original_verify = self.operation.verify_running
        failures = [True]

        def fail_once(value):
            if failures:
                failures.pop()
                raise mod.Refusal('synthetic_post_creation_failure')
            return original_verify(value)

        self.operation.verify_running = fail_once
        with self.assertRaisesRegex(mod.Refusal, '^publicacao_falhou_recuperada$'):
            self.operation.release(payload['bundle_id'], payload['approval_fingerprint'])
        original_verify(payload)

    def test_corrupt_backup_and_peer_drift_do_not_stop_nginx(self):
        payload = self.prepared()
        directory = self.state / 'nginx-provenance' / payload['bundle_id']
        (directory / 'config-0').write_bytes(b'corrupt')
        with self.assertRaisesRegex(mod.Refusal, '^backup_corrompido$'):
            self.operation.release(payload['bundle_id'], payload['approval_fingerprint'])
        self.assertEqual(self.operation.target()['Id'], payload['nginx']['Id'])
        (directory / 'config-0').write_bytes(__import__('base64').b64decode(payload['files'][mod.CONFIG_FILES[0]]))
        self.runner.run('docker', 'create', '--label', 'com.docker.compose.project=' + self.project,
                        '--label', 'com.docker.compose.service=extra', 'nginx:1.27-alpine', 'true')
        with self.assertRaisesRegex(mod.Refusal, '^runtime_mudou_antes_da_publicacao$'):
            self.operation.release(payload['bundle_id'], payload['approval_fingerprint'])
        self.assertEqual(self.operation.target()['Id'], payload['nginx']['Id'])


if __name__ == '__main__':
    unittest.main()
