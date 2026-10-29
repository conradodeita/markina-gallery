"""Reconciliação restrita do Nginx; stdout contém somente recibos sanitizados."""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import hmac
import http.client
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
PROJECT = 'markina-gallery'
URL = 'https://markina.pickyourpic.com.br'
CONFIG_FILES = ('/etc/nginx/nginx.conf', '/etc/nginx/mime.types', '/etc/nginx/conf.d/default.conf')
HEX = re.compile(r'[0-9a-f]{64}\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')
MASKED = ['/proc/asound', '/proc/acpi', '/proc/interrupts', '/proc/kcore', '/proc/keys',
          '/proc/latency_stats', '/proc/timer_list', '/proc/timer_stats', '/proc/sched_debug',
          '/proc/scsi', '/sys/firmware', '/sys/devices/virtual/powercap']
READONLY = ['/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger']

# docker inspect adds these engine defaults to a created container even when
# the image config omits them. Accept only these exact values; any override is
# still a runtime customization and remains unsupported.
CONTAINER_CONFIG_DEFAULTS = {
    'Domainname': '', 'User': '', 'AttachStdin': False, 'Tty': False,
    'OpenStdin': False, 'StdinOnce': False,
}


class Refusal(RuntimeError):
    """A mensagem é sempre um código constante, nunca erro de Docker/host."""


def safe_failure_code(error):
    """Retorna apenas códigos fixos ASCII; nunca persiste detalhe de subprocesso."""
    code = str(error) if isinstance(error, Refusal) else ''
    return code if re.fullmatch(r'[a-z][a-z0-9_]{0,63}', code) else 'falha_interna'


def require(condition, code):
    if not condition:
        raise Refusal(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class Runner:
    def run(self, *args, data=None, timeout=45):
        try:
            result = subprocess.run(args, input=data, capture_output=True, timeout=timeout,
                                    check=False, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
        except (OSError, subprocess.TimeoutExpired):
            raise Refusal('comando_indisponivel') from None
        require(result.returncode == 0, 'comando_recusado')
        return result.stdout

    def json(self, *args):
        try:
            return json.loads(self.run(*args))
        except (ValueError, TypeError):
            raise Refusal('resposta_invalida') from None


def stable_container(c):
    """Não inclui clocks, logs de healthcheck, contadores de aplicação ou estado SQL."""
    return {
        'id': c['Id'], 'image': c['Image'], 'config': digest(c['Config']),
        'host': digest(c['HostConfig']),
        'mounts': digest(sorted(c['Mounts'], key=lambda m: (m['Destination'], m['Source']))),
        'networks': digest(c['NetworkSettings']['Networks']),
        'status': c['State']['Status'], 'restart_count': c['RestartCount'],
    }


def validate_runtime(c, image, project):
    labels = c['Config'].get('Labels') or {}
    require(labels.get('com.docker.compose.project') == project
            and labels.get('com.docker.compose.service') == 'nginx', 'alvo_fora_do_escopo')
    require(c['State']['Running'] and c['State'].get('Health', {}).get('Status') == 'healthy',
            'nginx_nao_saudavel')
    require(c['Image'] == image['Id'], 'imagem_divergente')
    names = [v.split('=', 1)[0] for v in c['Config'].get('Env', [])]
    require(len(names) == len(set(names)), 'ambiente_ambiguo')
    # Qualquer customização da imagem requer ampliar explicitamente o contrato.
    ignored = {'Hostname', 'Labels', 'Image', 'Healthcheck', 'AttachStdout', 'AttachStderr'}
    image_config = image['Config']
    def matches_image_config(key, value):
        image_value = image_config.get(key)
        if value == image_value:
            return True
        return (image_value is None and key in CONTAINER_CONFIG_DEFAULTS
                and value == CONTAINER_CONFIG_DEFAULTS[key])
    require(all(matches_image_config(k, v) for k, v in c['Config'].items() if k not in ignored),
            'configuracao_imagem_nao_suportada')
    require(c['Config'].get('StopSignal') == 'SIGQUIT', 'sinal_gracioso_nao_comprovado')
    h = c['HostConfig']
    defaults = {'Binds': h.get('Binds'), 'NetworkMode': project + '_internal',
                'PortBindings': h.get('PortBindings'), 'LogConfig': {'Type': 'json-file', 'Config': {}},
                'RestartPolicy': h.get('RestartPolicy'), 'ConsoleSize': [0, 0],
                'CgroupnsMode': 'host', 'IpcMode': 'private', 'ShmSize': 67108864,
                'Runtime': 'runc', 'MaskedPaths': MASKED, 'ReadonlyPaths': READONLY}
    require(all(v == defaults.get(k) or (k not in defaults and v in (None, False, 0, '', [], {}))
                for k, v in h.items()), 'politica_host_nao_suportada')
    require(h.get('RestartPolicy') in ({'Name': 'no', 'MaximumRetryCount': 0},
                                     {'Name': 'unless-stopped', 'MaximumRetryCount': 0}),
            'restart_nao_suportado')
    ports = h.get('PortBindings') or {}
    require(set(ports) == {'80/tcp'} and len(ports['80/tcp']) == 1
            and ports['80/tcp'][0]['HostIp'] == '127.0.0.1', 'porta_fora_do_escopo')
    networks = c['NetworkSettings']['Networks']
    require(project + '_internal' in networks
            and set(networks) <= {project + '_internal', 'npm-network'}
            and all(not n.get('IPAMConfig') and not n.get('Links') for n in networks.values()),
            'rede_fora_do_escopo')
    mounts = c['Mounts']
    require(len(mounts) == 1 and mounts[0]['Type'] == 'bind' and not mounts[0]['RW']
            and mounts[0]['Destination'] == CONFIG_FILES[2], 'montagem_nao_suportada')


def healthcheck_model(value):
    result = {'test': value['Test'], 'retries': value['Retries']}
    for key, target in [('Interval', 'interval'), ('Timeout', 'timeout'),
                        ('StartPeriod', 'start_period'), ('StartInterval', 'start_interval')]:
        if value.get(key):
            result[target] = str(value[key]) + 'ns'
    return result


def candidate_model(c, directory, project):
    config, host = c['Config'], c['HostConfig']
    mounts = [{'type': 'bind', 'source': c['Mounts'][0]['Source'], 'target': CONFIG_FILES[2],
               'read_only': True, 'bind': {'create_host_path': False}}]
    for index, target in enumerate(CONFIG_FILES[:2]):
        mounts.append({'type': 'bind', 'source': str(directory / ('config-' + str(index))),
                       'target': target, 'read_only': True, 'bind': {'create_host_path': False}})
    network = project + '_internal'
    service = {
        'image': c['Image'], 'container_name': c['Name'].lstrip('/'),
        'hostname': config['Hostname'], 'entrypoint': config['Entrypoint'], 'command': config['Cmd'],
        'environment': [v.replace('$', '$$') for v in config.get('Env', [])],
        'stop_signal': 'SIGQUIT', 'restart': host['RestartPolicy']['Name'],
        'healthcheck': healthcheck_model(config['Healthcheck']), 'cgroup': 'host', 'ipc': 'private',
        'runtime': 'runc', 'shm_size': 67108864, 'logging': {'driver': 'json-file'},
        'ports': [{'target': 80, 'published': host['PortBindings']['80/tcp'][0]['HostPort'],
                   'host_ip': '127.0.0.1', 'protocol': 'tcp'}], 'volumes': mounts,
        'networks': {name: {'aliases': data.get('Aliases') or [],
                            'priority': 100 if name == network else 0}
                     for name, data in c['NetworkSettings']['Networks'].items()},
        'labels': {k: v for k, v in (config.get('Labels') or {}).items()
                   if not k.startswith('com.docker.compose.')},
    }
    for source, target in [('WorkingDir', 'working_dir'), ('User', 'user')]:
        if config.get(source):
            service[target] = config[source]
    return {'name': project, 'services': {'nginx': service},
            'networks': {name: {'external': True, 'name': name}
                         for name in c['NetworkSettings']['Networks']}}


def recovery_host_config(original, directory):
    """Constrói HostConfig de create usando somente os binds autenticados."""
    host = dict(original['HostConfig'])
    host.pop('Mounts', None)  # campo de inspect não deve competir com Binds de recuperação
    host['Binds'] = [str(directory / ('config-' + str(index))) + ':' + path + ':ro'
                     for index, path in enumerate(CONFIG_FILES)]
    return host


def plan_fingerprint(payload):
    return digest({'version': payload['version'], 'project': payload['project'],
                   'identity': payload['identity'], 'candidate': payload['candidate']})


def validate_payload(payload, state, project):
    require(payload.get('version') == 1 and payload.get('project') == project, 'backup_fora_do_escopo')
    require(HEX.fullmatch(payload.get('bundle_id', '')) is not None, 'backup_invalido')
    require(digest(payload['identity']) == payload['bundle_id'], 'identidade_backup_divergente')
    require(stable_container(payload['nginx']) == payload['identity']['nginx'], 'backup_runtime_divergente')
    require(set(payload['files']) == set(CONFIG_FILES), 'backup_configuracao_incompleto')
    require(set(payload['identity']['files']) == set(CONFIG_FILES), 'backup_hashes_incompletos')
    require(all(sha_bytes(base64.b64decode(payload['files'][p], validate=True)) == expected
                for p, expected in payload['identity']['files'].items()), 'backup_configuracao_divergente')
    directory = state / 'nginx-provenance' / payload['bundle_id']
    require(payload['candidate'] == candidate_model(payload['nginx'], directory, project), 'candidato_divergente')
    require(hmac.compare_digest(payload['approval_fingerprint'], plan_fingerprint(payload)), 'plano_divergente')


def private_directory(path, create=False):
    """Cria somente armazenamento da operação; nunca segue symlinks."""
    if create and not path.exists():
        path.mkdir(mode=0o700)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not path.is_symlink()
            and path.resolve() == path.absolute() and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700, 'diretorio_inseguro')


def private_read(path):
    with os.fdopen(os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600
                and info.st_size <= 8 * 1048576, 'arquivo_inseguro')
        return stream.read(8 * 1048576 + 1)


def private_write(path, data):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


@contextlib.contextmanager
def exclusive_lock(state):
    import fcntl  # POSIX do host operacional; testes Windows não executam mutação.
    path = state / 'production-release.lock'
    require(path.is_file() and not path.is_symlink(), 'trava_ausente')
    with os.fdopen(os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600, 'trava_insegura')
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal('outro_release_em_andamento') from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class UnixDocker(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def configuration_projection(c):
    config = {k: v for k, v in c['Config'].items()
              if k not in ('Hostname', 'Image', 'Labels', 'AttachStdout', 'AttachStderr')}
    config['Env'] = sorted(config.get('Env') or [])
    host = {k: v for k, v in c['HostConfig'].items()
            if k not in ('Binds', 'ConsoleSize', 'Mounts')}
    for key in ('CapAdd', 'CapDrop', 'Devices', 'DeviceRequests', 'DeviceCgroupRules', 'Dns',
                'DnsOptions', 'DnsSearch', 'ExtraHosts', 'GroupAdd', 'Links', 'SecurityOpt',
                'StorageOpt', 'Sysctls', 'VolumesFrom', 'Mounts', 'Ulimits', 'Tmpfs', 'Annotations'):
        if key in host and not host[key]:
            host[key] = None
    return {'image': c['Image'], 'config': config, 'host': host,
            'labels': {k: v for k, v in c['Config'].get('Labels', {}).items()
                       if not k.startswith('com.docker.compose.')},
            'networks': {name: sorted(set(n.get('Aliases') or []))
                         for name, n in c['NetworkSettings']['Networks'].items()}}


class Operation:
    def __init__(self, runner=None, root=ROOT, state=STATE, project=PROJECT, url=URL):
        self.runner = runner or Runner()
        self.root, self.state, self.project, self.url = Path(root), Path(state), project, url

    def containers(self):
        ids = self.runner.run('docker', 'ps', '-aq', '--filter',
                              'label=com.docker.compose.project=' + self.project).decode().split()
        require(bool(ids), 'projeto_ausente')
        items = self.runner.json('docker', 'inspect', *ids)
        require(all(x['Config']['Labels'].get('com.docker.compose.project') == self.project
                    for x in items), 'container_fora_do_escopo')
        return items

    def snapshot(self):
        items = self.containers()
        targets = [c for c in items if c['Config']['Labels'].get('com.docker.compose.service') == 'nginx']
        require(len(targets) == 1, 'nginx_ambiguo')
        c = targets[0]
        image = self.runner.json('docker', 'image', 'inspect', c['Image'])[0]
        validate_runtime(c, image, self.project)
        dump = self.runner.run('docker', 'exec', c['Id'], 'nginx', '-T')
        paths = [p.decode() for p in re.findall(rb'^# configuration file ([^\n]+):$', dump, re.MULTILINE)]
        require(len(paths) == len(CONFIG_FILES) and set(paths) == set(CONFIG_FILES),
                'arquivos_carregados_nao_suportados')
        files = {}
        for path in CONFIG_FILES:
            raw = self.runner.run('docker', 'exec', c['Id'], 'cat', path)
            require(0 < len(raw) <= 1048576, 'arquivo_configuracao_invalido')
            files[path] = base64.b64encode(raw).decode()
        source = Path(c['Mounts'][0]['Source'])
        require(source.is_file() and not source.is_symlink()
                and source.resolve() == source.absolute()
                and any(within(source, p) for p in (self.root, self.state)), 'fonte_insegura')
        require(base64.b64encode(source.read_bytes()).decode() == files[CONFIG_FILES[2]],
                'montagem_diverge_do_container')
        peers = {x['Id']: stable_container(x) for x in items if x['Id'] != c['Id']}
        require(all(not x['State']['Running'] or x['State'].get('Health', {}).get('Status')
                    in (None, 'healthy') for x in items), 'servico_nao_saudavel')
        identity = {'nginx': stable_container(c), 'peers': peers,
                    'files': {p: sha_bytes(base64.b64decode(b)) for p, b in files.items()},
                    'compose_version': self.runner.run('docker', 'compose', 'version', '--short').decode().strip()}
        bundle_id = digest(identity)
        directory = self.state / 'nginx-provenance' / bundle_id
        model = candidate_model(c, directory, self.project)
        payload = {'version': 1, 'project': self.project, 'identity': identity,
                   'bundle_id': bundle_id, 'nginx': c, 'files': files, 'candidate': model}
        final = {x['Id']: stable_container(x) for x in self.containers()}
        require(final == {x['Id']: stable_container(x) for x in items}, 'runtime_mudou')
        require(all(base64.b64encode(self.runner.run('docker', 'exec', c['Id'], 'cat', p)).decode() == b
                    for p, b in files.items()), 'configuracao_mudou')
        payload['approval_fingerprint'] = plan_fingerprint(payload)
        return payload

    @staticmethod
    def report(payload):
        return {'status': 'inventariado', 'bundle_id': payload['bundle_id'],
                'approval_fingerprint': payload['approval_fingerprint'],
                'peer_count': len(payload['identity']['peers']),
                'image': payload['nginx']['Image'],
                'nginx_config_hashes': dict(zip(('main', 'mime', 'server'),
                                                (payload['identity']['files'][p] for p in CONFIG_FILES))),
                'candidate_digest': digest(payload['candidate']),
                'compose_version': payload['identity']['compose_version'],
                'port': '127.0.0.1:' + payload['nginx']['HostConfig']['PortBindings']['80/tcp'][0]['HostPort'],
                'added_readonly_config_mounts': 2}

    def compose(self, directory, *args):
        return self.runner.run('docker', 'compose', '-p', self.project, '--project-directory', str(self.root),
                               '-f', str(directory / 'candidate.compose.json'), *args, timeout=120)

    def validate_model(self, payload):
        raw = self.runner.run('docker', 'compose', '-p', self.project, '--project-directory', str(self.root),
                              '-f', '-', 'config', '--format', 'json', data=encoded(payload['candidate']))
        model = json.loads(raw)
        require(set(model['services']) == {'nginx'} and not model.get('volumes')
                and set(model['networks']) == set(payload['candidate']['networks']), 'modelo_fora_do_escopo')
        service = model['services']['nginx']
        require(service['image'] == payload['nginx']['Image'] and not service.get('build')
                and not service.get('depends_on') and not service.get('profiles'), 'modelo_invalido')
        return digest(model)

    def prepare(self, approval):
        require(HEX.fullmatch(approval or '') is not None, 'aprovacao_ausente')
        with exclusive_lock(self.state):
            payload = self.snapshot()
            validate_payload(payload, self.state, self.project)
            require(approval == payload['approval_fingerprint'], 'aprovacao_divergente')
            model_digest = self.validate_model(payload)
            parent = self.state / 'nginx-provenance'
            auth = self.state / 'nginx-provenance-auth'
            private_directory(parent, create=True)
            private_directory(auth, create=True)
            directory = parent / payload['bundle_id']
            require(not directory.exists(), 'backup_ja_existe')
            private_directory(directory, create=True)
            private_write(directory / 'bundle.json', encoded(payload))
            private_write(directory / 'candidate.compose.json', encoded(payload['candidate']))
            for i, path in enumerate(CONFIG_FILES):
                private_write(directory / ('config-' + str(i)), base64.b64decode(payload['files'][path]))
            names = ['bundle.json', 'candidate.compose.json', 'config-0', 'config-1', 'config-2']
            manifest = {'files': {n: sha_bytes(private_read(directory / n)) for n in names},
                        'approval': approval, 'resolved_model_digest': model_digest}
            key = secrets.token_bytes(32)
            private_write(auth / (payload['bundle_id'] + '.key'), key)
            seal = {'manifest': manifest, 'signature': hmac.new(key, encoded(manifest), hashlib.sha256).hexdigest()}
            private_write(directory / 'seal.json', encoded(seal))
            # Releitura e autenticação reais antes de considerar backup preparado.
            self.load(payload['bundle_id'], approval)
            require(self.snapshot()['identity'] == payload['identity'], 'runtime_mudou_durante_preparo')
            return {**self.report(payload), 'status': 'backup_verificado', 'resolved_model_digest': model_digest}

    def load(self, bundle_id, approval):
        require(HEX.fullmatch(bundle_id or '') is not None, 'bundle_invalido')
        directory = self.state / 'nginx-provenance' / bundle_id
        private_directory(directory.parent)
        private_directory(self.state / 'nginx-provenance-auth')
        private_directory(directory)
        seal = json.loads(private_read(directory / 'seal.json'))
        key = private_read(self.state / 'nginx-provenance-auth' / (bundle_id + '.key'))
        require(len(key) == 32 and hmac.compare_digest(seal['signature'],
                hmac.new(key, encoded(seal['manifest']), hashlib.sha256).hexdigest()), 'backup_nao_autenticado')
        expected_names = {'bundle.json', 'candidate.compose.json', 'config-0', 'config-1', 'config-2'}
        require(set(seal['manifest']['files']) == expected_names, 'manifesto_invalido')
        require(all(sha_bytes(private_read(directory / n)) == value
                    for n, value in seal['manifest']['files'].items()), 'backup_corrompido')
        payload = json.loads(private_read(directory / 'bundle.json'))
        validate_payload(payload, self.state, self.project)
        require(payload['bundle_id'] == bundle_id and approval == payload['approval_fingerprint']
                and seal['manifest']['approval'] == approval, 'aprovacao_divergente')
        require(private_read(directory / 'candidate.compose.json') == encoded(payload['candidate']),
                'candidato_armazenado_divergente')
        require(self.validate_model(payload) == seal['manifest']['resolved_model_digest'], 'compose_resolvido_mudou')
        return payload, directory

    def peers_unchanged(self, payload):
        peers = {x['Id']: stable_container(x) for x in self.containers()
                 if x['Config']['Labels'].get('com.docker.compose.service') != 'nginx'}
        require(peers == payload['identity']['peers'], 'outro_container_mudou')

    def target(self):
        targets = [c for c in self.containers()
                   if c['Config']['Labels'].get('com.docker.compose.service') == 'nginx']
        require(len(targets) <= 1, 'nginx_ambiguo')
        return targets[0] if targets else None

    def graceful_stop(self, container):
        # -1 impede fallback SIGKILL; timeout do cliente não autoriza outro passo.
        require(container['Config'].get('StopSignal') == 'SIGQUIT', 'sinal_gracioso_nao_comprovado')
        self.runner.run('docker', 'stop', '--timeout', '-1', container['Id'], timeout=120)
        after = self.runner.json('docker', 'inspect', container['Id'])[0]
        require(not after['State']['Running'], 'parada_nao_confirmada')

    def verify_running(self, payload, expected_mount_sources=None):
        deadline = time.monotonic() + 90
        while True:
            c = self.target()
            require(c is not None, 'nginx_ausente')
            if c['State'].get('Health', {}).get('Status') == 'healthy':
                break
            require(c['State']['Running'] and time.monotonic() < deadline, 'nginx_nao_saudavel')
            time.sleep(1)
        expected = configuration_projection(payload['nginx'])
        observed = configuration_projection(c)
        for key in sorted(set(expected['host']) | set(observed['host'])):
            if observed['host'].get(key) != expected['host'].get(key):
                # Docker HostConfig keys are API field names, never values.
                suffix = key.lower() if re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,31}', key) else 'outro_campo'
                raise Refusal('host_' + suffix + '_divergente')
        for section, code in (('image', 'imagem_candidata_divergente'),
                              ('config', 'configuracao_candidata_divergente'),
                              ('labels', 'labels_candidatas_divergentes'),
                              ('networks', 'redes_candidatas_divergentes')):
            require(observed[section] == expected[section], code)
        require(len(c['Mounts']) == 3 and all(m['Type'] == 'bind' and not m['RW'] for m in c['Mounts']),
                'montagens_divergentes')
        require({m['Destination'] for m in c['Mounts']} == set(CONFIG_FILES), 'destinos_divergentes')
        if expected_mount_sources is None:
            expected_mounts = {volume['target']: str(Path(volume['source']).resolve())
                               for volume in payload['candidate']['services']['nginx']['volumes']}
        else:
            require(set(expected_mount_sources) == set(CONFIG_FILES), 'montagens_esperadas_invalidas')
            expected_mounts = {target: str(Path(source).resolve())
                               for target, source in expected_mount_sources.items()}
        observed_mounts = {mount['Destination']: str(Path(mount['Source']).resolve())
                           for mount in c['Mounts']}
        names = {CONFIG_FILES[0]: 'nginx_config', CONFIG_FILES[1]: 'mime_types',
                 CONFIG_FILES[2]: 'server_config'}
        for destination in CONFIG_FILES:
            require(observed_mounts.get(destination) == expected_mounts.get(destination),
                    'fonte_' + names[destination] + '_divergente')
        for path, value in payload['files'].items():
            require(self.runner.run('docker', 'exec', c['Id'], 'cat', path) == base64.b64decode(value),
                    'bytes_configuracao_divergentes')
        self.runner.run('docker', 'exec', c['Id'], 'nginx', '-t')
        for path in ('/healthz', '/api/health', '/'):
            code = self.runner.run('curl', '--silent', '--show-error', '--max-time', '15',
                                   '--output', '/dev/null', '--write-out', '%{http_code}', self.url + path)
            require(code == b'200', 'https_falhou')
        self.peers_unchanged(payload)
        return c

    def recover(self, payload, directory):
        current = self.target()
        if current:
            require(current['Name'] == payload['nginx']['Name']
                    and current['Image'] == payload['nginx']['Image'], 'recuperacao_alvo_divergente')
            require(current['Id'] == payload['nginx']['Id'] or
                    current['Config']['Labels'].get('com.docker.compose.project.config_files') ==
                    str(directory / 'candidate.compose.json'), 'recuperacao_proveniencia_divergente')
            if current['State']['Running']:
                self.graceful_stop(current)
            self.runner.run('docker', 'rm', current['Id'])  # nunca --force
        original = payload['nginx']
        body = {**original['Config'], 'Image': original['Image'],
                'HostConfig': recovery_host_config(original, directory),
                'NetworkingConfig': {'EndpointsConfig': {
                    name: {'Aliases': data.get('Aliases') or []}
                    for name, data in original['NetworkSettings']['Networks'].items()}}}
        version = self.runner.run('docker', 'version', '--format', '{{.Server.APIVersion}}').decode().strip()
        require(re.fullmatch(r'1\.[0-9]+', version) is not None, 'api_docker_invalida')
        connection = UnixDocker('localhost', timeout=45)
        try:
            connection.request('POST', '/v' + version + '/containers/create?name=' +
                               quote(original['Name'].lstrip('/'), safe=''), body=encoded(body),
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            raw = response.read()
            require(response.status == 201, 'recuperacao_criacao_falhou')
            new_id = json.loads(raw)['Id']
        finally:
            connection.close()
        require(re.fullmatch(r'[0-9a-f]{64}', new_id) is not None, 'recuperacao_id_invalido')
        self.runner.run('docker', 'start', new_id)
        self.verify_running(payload, expected_mount_sources={
            target: str(directory / ('config-' + str(index)))
            for index, target in enumerate(CONFIG_FILES)})

    def recovery_inventory(self, bundle_id, approval):
        payload, directory = self.load(bundle_id, approval)
        require((directory / 'execution.json').is_file(), 'execucao_nao_iniciada')
        self.peers_unchanged(payload)
        target = self.target()
        fingerprint = digest({'bundle': bundle_id, 'approval': approval,
                              'target': stable_container(target) if target else None,
                              'peers': payload['identity']['peers']})
        return payload, directory, fingerprint

    def approved_recovery(self, bundle_id, approval, recovery_approval):
        with exclusive_lock(self.state):
            payload, directory, fingerprint = self.recovery_inventory(bundle_id, approval)
            require(recovery_approval == fingerprint, 'aprovacao_recuperacao_divergente')
            self.recover(payload, directory)
            private_write(directory / ('recovery-' + fingerprint + '.json'),
                          encoded({'state': 'recovered', 'fingerprint': fingerprint}))
            return {'status': 'recuperado', 'bundle_id': bundle_id}

    def release(self, bundle_id, approval):
        with exclusive_lock(self.state):
            payload, directory = self.load(bundle_id, approval)
            require(self.snapshot()['identity'] == payload['identity'], 'runtime_mudou_antes_da_publicacao')
            require(not (directory / 'execution.json').exists(), 'execucao_ja_iniciada')
            private_write(directory / 'execution.json', encoded({'state': 'started', 'approval': approval}))
            current = self.target()
            # Se SIGQUIT não confirmar encerramento, preservar estado sem recriar ou remover.
            self.graceful_stop(current)
            try:
                self.peers_unchanged(payload)
                self.compose(directory, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'nginx')
                published = self.verify_running(payload)
                expected_hash = self.compose(directory, 'config', '--hash', 'nginx').decode().split()
                require(len(expected_hash) == 2 and expected_hash[0] == 'nginx'
                        and published['Config']['Labels'].get('com.docker.compose.config-hash') == expected_hash[1]
                        and published['Config']['Labels'].get('com.docker.compose.project.config_files') ==
                        str(directory / 'candidate.compose.json'), 'proveniencia_publicada_divergente')
            except Exception as publish_error:  # noqa: BLE001 - falha posterior à parada exige recuperação
                failure_code = safe_failure_code(publish_error)
                try:
                    self.recover(payload, directory)
                    private_write(directory / 'result.json', encoded({'state': 'recovered', 'approval': approval,
                                                                      'failure': failure_code}))
                except Exception as recovery_error:  # noqa: BLE001 - não vazar erros de Docker/configuração
                    private_write(directory / 'result.json', encoded({
                        'state': 'recovery_required', 'approval': approval,
                        'failure': failure_code, 'recovery_failure': safe_failure_code(recovery_error)}))
                    raise Refusal('recuperacao_requer_operador') from None
                raise Refusal('publicacao_falhou_recuperada') from None
            private_write(directory / 'result.json', encoded({'state': 'published', 'approval': approval}))
            return {'status': 'publicado', 'bundle_id': bundle_id, 'approval_fingerprint': approval}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['inventory', 'prepare', 'release', 'recovery-inventory', 'recover'])
    parser.add_argument('--approval')
    parser.add_argument('--bundle')
    parser.add_argument('--recovery-approval')
    args = parser.parse_args()
    operation = Operation()
    if args.mode == 'inventory':
        payload = operation.snapshot()
        print(json.dumps({**operation.report(payload),
                          'resolved_model_digest': operation.validate_model(payload)}, sort_keys=True))
    elif args.mode == 'prepare':
        print(json.dumps(operation.prepare(args.approval), sort_keys=True))
    elif args.mode == 'release':
        print(json.dumps(operation.release(args.bundle, args.approval), sort_keys=True))
    elif args.mode == 'recovery-inventory':
        _, _, fingerprint = operation.recovery_inventory(args.bundle, args.approval)
        print(json.dumps({'status': 'recuperacao_inventariada', 'recovery_fingerprint': fingerprint}))
    else:
        print(json.dumps(operation.approved_recovery(args.bundle, args.approval, args.recovery_approval)))


if __name__ == '__main__':
    try:
        main()
    except Refusal as exc:
        print(json.dumps({'status': 'bloqueado', 'category': str(exc)}))
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001 - fronteira sanitizada do operador
        print('{"status":"bloqueado","category":"falha_interna"}')
        raise SystemExit(2) from None
