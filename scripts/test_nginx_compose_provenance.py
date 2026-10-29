"""Fixtures sintéticas: nenhuma credencial, foto ou container de produção."""
import contextlib
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import nginx_compose_provenance as mod


def fixture(source):
    config = {'Env': ['NGINX_VERSION=synthetic'], 'Entrypoint': ['/entrypoint'],
              'Cmd': ['nginx', '-g', 'daemon off;'], 'StopSignal': 'SIGQUIT',
              'User': '', 'WorkingDir': '', 'Hostname': 'generated', 'Image': 'nginx:test',
              'Domainname': '', 'AttachStdin': False, 'Tty': False,
              'OpenStdin': False, 'StdinOnce': False,
              'Labels': {'com.docker.compose.project': 'markina-gallery',
                         'com.docker.compose.service': 'nginx'},
              'Healthcheck': {'Test': ['CMD', 'true'], 'Interval': 1000000000,
                              'Timeout': 1000000000, 'Retries': 2}}
    host = {'Binds': [str(source) + ':/etc/nginx/conf.d/default.conf:ro'],
            'NetworkMode': 'markina-gallery_internal',
            'PortBindings': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]},
            'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
            'LogConfig': {'Type': 'json-file', 'Config': {}}, 'CgroupnsMode': 'host',
            'IpcMode': 'private', 'ShmSize': 67108864, 'Runtime': 'runc',
            'MaskedPaths': mod.MASKED, 'ReadonlyPaths': mod.READONLY}
    container = {'Id': 'a' * 64, 'Name': '/markina-gallery-nginx-1', 'Image': 'sha256:' + 'b' * 64,
                 'Config': config, 'HostConfig': host, 'RestartCount': 0,
                 'State': {'Running': True, 'Status': 'running', 'Health': {'Status': 'healthy'}},
                 'Mounts': [{'Type': 'bind', 'RW': False, 'Source': str(source),
                             'Destination': mod.CONFIG_FILES[2]}],
                 'NetworkSettings': {'Networks': {'markina-gallery_internal': {'Aliases': ['nginx']}}}}
    image = {'Id': container['Image'], 'Config': {k: v for k, v in config.items()
                                                if k not in ('Healthcheck', 'Labels', 'Hostname',
                                                             'Domainname', 'AttachStdin', 'Tty',
                                                             'OpenStdin', 'StdinOnce', 'User')}}
    return container, image


class FakeRunner:
    def __init__(self, container, image):
        self.container, self.image = container, image
        self.change = False
        self.calls = []

    def run(self, *args, **kwargs):
        self.calls.append(args)
        if args[:2] == ('docker', 'ps'):
            return (self.container['Id'] + '\n').encode()
        if args[:3] == ('docker', 'compose', 'version'):
            return b'2.35.1\n'
        if args[:2] == ('docker', 'compose') and 'config' in args:
            return kwargs['data']
        if args[-2:] == ('nginx', '-T'):
            return ''.join('# configuration file ' + p + ':\n' for p in mod.CONFIG_FILES).encode()
        if args[-2] == 'cat':
            return b'fixture-config\n'
        raise AssertionError(args)

    def json(self, *args):
        self.calls.append(args)
        if args[:3] == ('docker', 'image', 'inspect'):
            return [copy.deepcopy(self.image)]
        c = copy.deepcopy(self.container)
        if self.change and sum(a[:2] == ('docker', 'inspect') for a in self.calls) > 1:
            c['RestartCount'] += 1
        return [c]


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'private-sentinel.conf'
        self.source.write_bytes(b'fixture-config\n')
        self.container, self.image = fixture(self.source)
        self.runner = FakeRunner(self.container, self.image)
        self.operation = mod.Operation(self.runner, self.root, self.root / 'state')

    def test_inventory_is_stable_and_report_does_not_leak(self):
        payload = self.operation.snapshot()
        self.assertEqual(payload, self.operation.snapshot())
        output = json.dumps(self.operation.report(payload))
        for sensitive in ('fixture-config', str(self.source), 'NGINX_VERSION', 'generated'):
            self.assertNotIn(sensitive, output)
        self.assertFalse((self.root / 'state').exists())
        self.assertTrue(all(a[1] in ('ps', 'inspect', 'image', 'exec', 'compose')
                            for a in self.runner.calls))

    def test_race_blocks_inventory(self):
        self.runner.change = True
        with self.assertRaisesRegex(mod.Refusal, '^runtime_mudou$'):
            self.operation.snapshot()

    def test_mount_enumeration_order_does_not_change_identity(self):
        c = copy.deepcopy(self.container)
        c['Mounts'].append({'Type': 'bind', 'Source': '/fixture', 'Destination': '/fixture', 'RW': False})
        before = mod.stable_container(c)
        c['Mounts'].reverse()
        self.assertEqual(before, mod.stable_container(c))

    def test_operator_pin_matches_exact_module_blob(self):
        folder = Path(__file__).resolve().parent
        raw = (folder / 'nginx_compose_provenance.py').read_bytes().replace(b'\r\n', b'\n')
        blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
        wrapper = (folder / 'deploy-prod-nginx-provenance.sh').read_text()
        self.assertIn("MODULE_BLOB_SHA='" + blob + "'", wrapper)
        self.assertNotIn('PIN_PENDING', wrapper)

    def test_unknown_host_policy_blocks(self):
        self.container['HostConfig']['Privileged'] = True
        with self.assertRaisesRegex(mod.Refusal, '^politica_host_nao_suportada$'):
            self.operation.snapshot()

    def test_non_default_container_config_override_blocks(self):
        self.container['Config']['Tty'] = True
        with self.assertRaisesRegex(mod.Refusal, '^configuracao_imagem_nao_suportada$'):
            self.operation.snapshot()

    def test_other_project_and_network_block(self):
        self.container['Config']['Labels']['com.docker.compose.project'] = 'another-project'
        with self.assertRaises(mod.Refusal):
            self.operation.snapshot()
        self.container['Config']['Labels']['com.docker.compose.project'] = 'markina-gallery'
        self.container['NetworkSettings']['Networks']['unapproved'] = {}
        with self.assertRaisesRegex(mod.Refusal, '^rede_fora_do_escopo$'):
            self.operation.snapshot()

    def test_candidate_preserves_external_alias_and_does_not_include_retired_services(self):
        self.container['NetworkSettings']['Networks']['npm-network'] = {'Aliases': ['existing-alias']}
        payload = self.operation.snapshot()
        candidate = payload['candidate']
        self.assertEqual(set(candidate['services']), {'nginx'})
        self.assertEqual(candidate['services']['nginx']['networks']['npm-network']['aliases'], ['existing-alias'])
        self.assertTrue(candidate['networks']['npm-network']['external'])
        self.assertEqual(len(candidate['services']['nginx']['volumes']), 3)

    def test_missing_and_stale_approval_prevent_any_write(self):
        with self.assertRaisesRegex(mod.Refusal, '^aprovacao_ausente$'):
            self.operation.prepare(None)
        with mock.patch.object(mod, 'exclusive_lock', return_value=contextlib.nullcontext()), self.assertRaisesRegex(mod.Refusal, '^aprovacao_divergente$'):
            self.operation.prepare('0' * 64)
        self.assertFalse((self.root / 'state').exists())

    def test_tampered_candidate_or_configuration_is_rejected(self):
        payload = self.operation.snapshot()
        mod.validate_payload(payload, self.operation.state, self.operation.project)
        payload['candidate']['services']['nginx']['privileged'] = True
        with self.assertRaisesRegex(mod.Refusal, '^candidato_divergente$'):
            mod.validate_payload(payload, self.operation.state, self.operation.project)
        payload = self.operation.snapshot()
        payload['files'][mod.CONFIG_FILES[0]] = 'c2Vuc2l0aXZl'
        with self.assertRaisesRegex(mod.Refusal, '^backup_configuracao_divergente$'):
            mod.validate_payload(payload, self.operation.state, self.operation.project)

    @unittest.skipIf(os.name == 'nt', 'armazenamento e trava POSIX são validados no CI Linux')
    def test_persisted_backup_authenticated_and_corruption_refused(self):
        self.operation.state.mkdir(mode=0o700)
        (self.operation.state / 'production-release.lock').touch(mode=0o600)
        payload = self.operation.snapshot()
        result = self.operation.prepare(payload['approval_fingerprint'])
        self.assertEqual(result['status'], 'backup_verificado')
        self.operation.load(payload['bundle_id'], payload['approval_fingerprint'])
        directory = self.operation.state / 'nginx-provenance' / payload['bundle_id']
        (directory / 'config-0').write_bytes(b'corruption')
        with self.assertRaisesRegex(mod.Refusal, '^backup_corrompido$'):
            self.operation.load(payload['bundle_id'], payload['approval_fingerprint'])

    @unittest.skipIf(os.name == 'nt', 'permissões POSIX')
    def test_symlink_and_missing_backup_never_create_paths(self):
        missing = self.root / 'missing'
        with self.assertRaises(OSError):
            mod.private_directory(missing)
        self.assertFalse(missing.exists())
        target = self.root / 'secret'
        target.write_bytes(b'sentinel')
        target.chmod(0o600)
        link = self.root / 'symlink'
        link.symlink_to(target)
        with self.assertRaises(OSError):
            mod.private_read(link)

    @unittest.skipIf(os.name == 'nt', 'trava POSIX')
    def test_exclusive_lock_refuses_second_operator(self):
        self.operation.state.mkdir(mode=0o700)
        (self.operation.state / 'production-release.lock').touch(mode=0o600)
        with mod.exclusive_lock(self.operation.state), self.assertRaisesRegex(mod.Refusal, '^outro_release_em_andamento$'), mod.exclusive_lock(self.operation.state):
            self.fail('segundo operador entrou')

    @unittest.skipIf(os.name == 'nt', 'permissões POSIX')
    def test_signature_tampering_and_world_readable_file_are_refused(self):
        self.operation.state.mkdir(mode=0o700)
        (self.operation.state / 'production-release.lock').touch(mode=0o600)
        payload = self.operation.snapshot()
        self.operation.prepare(payload['approval_fingerprint'])
        directory = self.operation.state / 'nginx-provenance' / payload['bundle_id']
        seal_path = directory / 'seal.json'
        seal = json.loads(seal_path.read_bytes())
        seal['signature'] = '0' * 64
        seal_path.write_bytes(mod.encoded(seal))
        with self.assertRaisesRegex(mod.Refusal, '^backup_nao_autenticado$'):
            self.operation.load(payload['bundle_id'], payload['approval_fingerprint'])
        seal_path.chmod(0o644)
        with self.assertRaisesRegex(mod.Refusal, '^arquivo_inseguro$'):
            self.operation.load(payload['bundle_id'], payload['approval_fingerprint'])


if __name__ == '__main__':
    unittest.main()
