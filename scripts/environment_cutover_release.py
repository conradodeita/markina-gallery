"""Release restrito de configuração e envelopes; recibos públicos sem dados sensíveis."""
from __future__ import annotations

import argparse
import base64
import copy
import fcntl
import hashlib
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
WORK = STATE / 'environment-cutover'
CODE = Path(__file__).resolve().parents[1]
PROJECT = 'markina-gallery'
REPOSITORY = 'conradodeita/markina-gallery'
ORIGIN = 'https://markina.pickyourpic.com.br'
SCHEMA = '20261026_0090'
CONSUMERS = ('api', 'worker', 'face-index-worker', 'face-search-worker', 'face-maintenance-worker')
ACTIVE_CONSUMERS = ('api', 'worker')
FACIAL_CONSUMERS = CONSUMERS[2:]
EXPECTED = set(CONSUMERS) | {'web', 'nginx', 'db', 'redis', 'evolution-api', 'evolution-db',
                             'evolution-redis', 'preview-adjustment-worker'}
SHA = re.compile(r'[0-9a-f]{40}\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
SOURCE_ENVIRONMENTS = {'staging', 'development', 'test', 'homolog', 'homologation'}
PHASE = 'preconditions'


def phase(value):
    global PHASE
    PHASE = value


class ReleaseBlocked(RuntimeError):
    pass


def require(condition, category):
    if not condition:
        raise ReleaseBlocked(category)


def run(*args, data=None, timeout=60):
    try:
        result = subprocess.run(list(args), input=data, capture_output=True, text=True,
            cwd=str(ROOT), timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ReleaseBlocked('command_unavailable') from None
    require(result.returncode == 0, 'command_failed')
    return result.stdout.strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def github(path):
    request = Request('https://api.github.com/repos/' + REPOSITORY + path,
                      headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'markina-environment-release'})
    try:
        with urlopen(request, timeout=20) as response:
            require(response.url.startswith('https://api.github.com/'), 'github_origin_invalid')
            value = response.read(8_000_001)
        require(len(value) <= 8_000_000, 'github_response_excessive')
        return json.loads(value)
    except (OSError, ValueError, KeyError):
        raise ReleaseBlocked('github_unavailable') from None


def verify_candidate(sha):
    require(bool(SHA.fullmatch(sha)), 'candidate_invalid')
    require(github('/git/ref/heads/main')['object']['sha'] == sha, 'candidate_not_main')
    runs = github('/actions/runs?head_sha=' + sha + '&per_page=100')['workflow_runs']
    relevant = [r for r in runs if r.get('path') == '.github/workflows/ci.yml'
        and r.get('event') == 'push' and r.get('head_branch') == 'main' and r.get('head_sha') == sha]
    require(bool(relevant), 'main_ci_missing')
    latest = max(relevant, key=lambda r: (r['run_number'], r.get('run_attempt', 1)))
    require(latest.get('status') == 'completed' and latest.get('conclusion') == 'success', 'main_ci_not_green')
    tree = github('/git/trees/' + sha + '?recursive=1')
    require(tree.get('truncated') is False, 'candidate_tree_incomplete')
    expected = {x['path']: x['sha'] for x in tree['tree'] if x.get('type') == 'blob'}
    files = list((CODE / 'backend/app').rglob('*.py'))
    files += [Path(__file__).resolve(), CODE / 'scripts/app_env_transition_inventory.py']
    for path in files:
        require(not path.is_symlink(), 'candidate_source_symlink')
        relative = path.relative_to(CODE).as_posix()
        content = path.read_bytes()
        git_blob = hashlib.sha1(('blob ' + str(len(content)) + '\0').encode() + content).hexdigest()
        require(expected.get(relative) == git_blob, 'candidate_source_mismatch')


def environment(container):
    values = container['Config'].get('Env') or []
    result = {}
    for item in values:
        key, value = item.split('=', 1)
        require(key not in result, 'duplicate_environment')
        result[key] = value
    return result


def target_environment(source, *, live=False):
    require(source.get('APP_ENV') in SOURCE_ENVIRONMENTS | {'production'}, 'source_environment_invalid')
    old = source['APP_ENV']
    result = dict(source)
    for key, value in source.items():
        if value and (key in {'APP_ENV', 'INTEGRATION_SECRET_ENV', 'EMAIL_CREDENTIAL_ENV',
                   'WHATSAPP_CREDENTIAL_ENV', 'FACIAL_CREDENTIAL_ENV'} or (
            key.startswith('WHATSAPP_BINDING_') and key.endswith('_CREDENTIAL_ENV'))):
            require(value in {old, 'production'}, 'credential_binding_unknown')
            result[key] = 'production'
    result['FACIAL_PROCESSING_ENABLED'] = 'false'
    if 'MERCADOPAGO_ALLOW_LIVE_PAYMENTS' in result:
        result['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'] = 'true' if live else 'false'
    return result


def containers():
    ids = run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT).split()
    require(bool(ids), 'project_missing')
    inspected = json.loads(run('docker', 'inspect', *ids))
    result = {}
    for item in inspected:
        name = item['Config']['Labels'].get('com.docker.compose.service')
        if item['State']['Status'] != 'running':
            # Preserve retired and historical stopped containers; never remove them.
            continue
        require(name in EXPECTED and name not in result, 'service_unknown_or_duplicate')
        result[name] = item
    return result


def snapshot(owner_operation=None):
    ignored = set()
    if owner_operation:
        value = json.loads((STATE / 'environment-cutover-in-flight.json').read_text())
        require(value['operation'] == owner_operation
                and (STATE / 'app-in-flight.sha').read_text().strip() == value['sha'],
                'release_marker_owner_mismatch')
        ignored = {'app-in-flight.sha', 'environment-cutover-in-flight.json'}
    require(not any((STATE / name).exists() for name in (
        'app-in-flight.sha', 'web-in-flight.sha', 'app-rollback-in-flight.sha',
        'orders-in-flight.json', 'pillow-in-flight.json', 'environment-cutover-in-flight.json',
        'preview-adjustment-migration-in-flight.json',
    ) if name not in ignored), 'another_release_pending')
    services = containers()
    require(set(services) == EXPECTED, 'service_inventory_incomplete')
    for name, item in services.items():
        require(item['State'].get('Health', {}).get('Status') == 'healthy', 'service_unhealthy')
        ports = {k:v for k,v in (item['NetworkSettings'].get('Ports') or {}).items() if v}
        expected_ports = {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if name == 'nginx' else {}
        require(ports == expected_ports, 'published_ports_changed')
    origin = environment(services['api'])['APP_ENV']
    require(origin in SOURCE_ENVIRONMENTS | {'production'}, 'source_environment_invalid')
    for name in CONSUMERS:
        require(environment(services[name]).get('APP_ENV') == origin, 'consumer_environment_divergent')
    nginx_files = [m['Source'] for m in services['nginx']['Mounts']
                   if m['Destination'] == '/etc/nginx/conf.d/default.conf']
    require(len(nginx_files) == 1, 'nginx_config_unknown')
    files = [ROOT / 'docker/.env.homolog', STATE / 'integration-secrets.env', Path(nginx_files[0])]
    saved_files = []
    for path in files:
        resolved = path.resolve(strict=True)
        require(not path.is_symlink() and (ROOT in resolved.parents or STATE in resolved.parents), 'config_path_invalid')
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'config_file_invalid')
        saved_files.append({'path': str(path), 'content': base64.b64encode(path.read_bytes()).decode(),
                            'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid})
    sys.path.insert(0, str(CODE))
    from scripts.app_env_transition_inventory import database_probe
    probe = database_probe(services['api']['Id'])
    require(probe['schema_revision'] == SCHEMA, 'schema_divergent')
    require(probe.get('unknown_reference_entries') == 0, 'reference_store_unknown')
    counts = probe['biometric_counts']
    require(all(counts[k] == 0 for k in ('active_jobs', 'reference_files', 'search_reference_locators',
                                        'search_notifications')), 'unsupported_biometric_storage')
    facts = {'schema': SCHEMA, 'services': {name: {
        'id': item['Id'], 'image': item['Image'], 'version': environment(item).get('APP_VERSION'),
        'environment_digest': digest(environment(item)),
        'mounts_digest': digest(item['Mounts']),
        'networks_digest': digest(item['NetworkSettings']['Networks']),
    } for name, item in services.items()},
        'configuration_digests': [hashlib.sha256(base64.b64decode(x['content'])).hexdigest() for x in saved_files],
        'biometric_counts': counts, 'credential_counts': probe['credential_counts']}
    return {'services': services, 'files': saved_files, 'facts': facts, 'fingerprint': digest(facts)}


def roots():
    for path in (WORK, WORK / 'packages', WORK / 'keys', WORK / 'models'):
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
        info = path.stat()
        require(not path.is_symlink() and info.st_uid == os.geteuid()
                and stat.S_IMODE(info.st_mode) == 0o700, 'state_directory_insecure')


def stores():
    sys.path.insert(0, str(CODE))
    from backend.app.facial.environment_package_store import (
        persist_encrypted_package,
        reopen_package,
    )
    return persist_encrypted_package, reopen_package


def seal_config(value, key, operation):
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(nonce, json.dumps(value, sort_keys=True).encode(),
                                    ('environment-host-v1:' + operation).encode())
    return {'version': 1, 'nonce': base64.b64encode(nonce).decode(),
            'ciphertext': base64.b64encode(encrypted).decode()}


def open_config(operation):
    _, reopen = stores()
    saved = reopen(WORK / 'packages', WORK / 'keys', operation + '-host')
    payload = saved.payload
    value = AESGCM(saved.key).decrypt(base64.b64decode(payload['nonce'], validate=True),
        base64.b64decode(payload['ciphertext'], validate=True),
        ('environment-host-v1:' + operation).encode())
    return json.loads(value)


def compose_model(services):
    paths = []
    for item in services.values():
        for raw in item['Config']['Labels']['com.docker.compose.project.config_files'].split(','):
            path = Path(raw).resolve(strict=True)
            require(ROOT in path.parents or STATE in path.parents, 'compose_source_outside_project')
            if str(path) not in paths:
                paths.append(str(path))
    args = ['docker', 'compose', '-p', PROJECT, '--profile', 'facial', '--project-directory', str(ROOT),
            '--env-file', str(ROOT / 'docker/.env.homolog')]
    for path in paths:
        args += ['-f', path]
    model = json.loads(run(*args, 'config', '--format', 'json'))
    for name in CONSUMERS:
        item = services[name]
        require(name in model['services'], 'compose_consumer_missing')
        model['services'][name]['image'] = item['Image']
        # Captured values are already resolved. Escape dollars for one more Compose parse.
        model['services'][name]['environment'] = {k:v.replace('$', '$$') for k,v in environment(item).items()}
        for key, source in (('command', 'Cmd'), ('entrypoint', 'Entrypoint')):
            model['services'][name][key] = [x.replace('$', '$$') for x in item['Config'][source]] if item['Config'][source] else None
    return model


def write_private(path, value):
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def runtime(config, mode, operation, *, paused=False, network_checks=False):
    api = config['services']['api']
    selected_api = api['Id']
    # The original API may have been replaced; use the current project's API if present.
    candidates = run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                     '--filter', 'label=com.docker.compose.service=api').split()
    require(len(candidates) == 1, 'maintenance_api_ambiguous')
    selected_api = candidates[0]
    networks = list(api['NetworkSettings']['Networks'])
    require(len(networks) == 1, 'maintenance_network_ambiguous')
    values = environment(api)
    values['FACIAL_PROCESSING_ENABLED'] = 'false'
    if mode != 'eligibility':
        values['MERCADOPAGO_ALLOW_LIVE_PAYMENTS'] = 'false'
    descriptor = os.memfd_create('markina-environment-maintenance', flags=0)
    try:
        lines = []
        for key, value in values.items():
            require('\n' not in value and '\r' not in value, 'multiline_environment_unsupported')
            lines.append(key + '=' + value + '\n')
        content = ''.join(lines).encode()
        with os.fdopen(os.dup(descriptor), 'wb') as stream:
            stream.write(content)
            stream.flush()
        os.lseek(descriptor, 0, os.SEEK_SET)
        args = ['docker', 'run', '--rm', '--read-only', '--user', '0', '--cap-drop', 'ALL',
                '--cap-add', 'DAC_READ_SEARCH', '--security-opt', 'no-new-privileges',
                '--memory', '1536m', '--cpus', '1', '--network', networks[0],
                '--label', 'com.docker.compose.project=markina-gallery-env-maintenance',
                '--env-file', '/proc/' + str(os.getpid()) + '/fd/' + str(descriptor), '-e', 'PYTHONPATH=/candidate/backend',
                '--tmpfs', '/tmp:rw,nosuid,noexec,size=64m', '--volumes-from', selected_api + ':ro',
                '--mount', 'type=bind,src=' + str(CODE / 'backend') + ',dst=/candidate/backend,readonly',
                '--mount', 'type=bind,src=' + str(WORK / 'packages') + ',dst=' + str(WORK / 'packages'),
                '--mount', 'type=bind,src=' + str(WORK / 'keys') + ',dst=' + str(WORK / 'keys'),
                '--entrypoint', 'python', api['Image'], '-B', '-m', 'app.environment_transition_runtime',
                mode, '--operation', operation, '--inventory', config['fingerprint'], '--plan', config['plan']]
        if paused:
            args.append('--paused')
        if network_checks:
            args.append('--network-checks')
        result = json.loads(run(*args, timeout=240))
        require(result.get('status') == 'success', 'maintenance_runtime_blocked')
        return result
    finally:
        os.close(descriptor)


def prepare(sha, operation, fingerprint):
    phase('prepare_inventory')
    current = snapshot()
    require(current['fingerprint'] == fingerprint, 'inventory_drift')
    require(environment(current['services']['api'])['APP_ENV'] in SOURCE_ENVIRONMENTS, 'already_production')
    phase('prepare_compose')
    config = {**current, 'sha': sha, 'model': compose_model(current['services'])}
    config['plan'] = digest({'inventory': fingerprint, 'sha': sha, 'consumers': CONSUMERS,
                             'target': 'production', 'facial': False, 'live': False})
    key = secrets.token_bytes(32)
    persist, _ = stores()
    persist(WORK / 'packages', WORK / 'keys', operation + '-host',
                    encrypted_payload=seal_config(config, key, operation), backup_key=key)
    require(open_config(operation) == config, 'config_reopen_mismatch')
    phase('prepare_channels_profile')
    result = runtime(config, 'preflight', operation, network_checks=True)
    require(snapshot()['fingerprint'] == fingerprint, 'inventory_changed_during_prepare')
    save_receipt(operation, 'ready', {'fingerprint': fingerprint, 'plan': config['plan'],
                                    'channels_verified': result['channels_verified']})
    return {'status': 'prepared', 'fingerprint': fingerprint, 'plan': config['plan'],
            'embedding_count': result['embedding_count'],
            'account_count': current['facts']['credential_counts']['mercadopago_access_token']}


def model_path(config, operation, target, live=False, reuse=False):
    model = copy.deepcopy(config['model'])
    if target:
        for name in CONSUMERS:
            values = target_environment(environment(config['services'][name]), live=live)
            model['services'][name]['environment'] = {k:v.replace('$', '$$') for k,v in values.items()}
    suffix = 'live' if live else 'target' if target else 'source'
    path = WORK / 'models' / (operation + '-' + suffix + '.json')
    if path.exists():
        require(reuse and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600
                and json.loads(path.read_text()) == model, 'model_already_exists_or_changed')
        return path
    write_private(path, model)
    # Resolve/validate normally; never use --no-consistency to accept an invalid model.
    compose(path, 'config', '--quiet')
    return path


def compose(path, *args):
    return run('docker', 'compose', '-p', PROJECT, '--project-directory', str(ROOT),
               '--env-file', str(ROOT / 'docker/.env.homolog'), '-f', str(path), *args, timeout=300)


def replace_file(saved, content, *, same_inode=False):
    path = Path(saved['path'])
    require(not path.is_symlink(), 'config_symlink_changed')
    if same_inode:
        with path.open('r+b') as stream:
            stream.write(content)
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
        return
    descriptor, filename = tempfile.mkstemp(prefix='environment-cutover-', dir=str(path.parent))
    try:
        os.fchmod(descriptor, saved['mode'])
        os.fchown(descriptor, saved['uid'], saved['gid'])
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(filename, path)
        directory = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(filename).unlink(missing_ok=True)


def rewrite_environment(original, replacements):
    lines, seen = [], set()
    for line in original.decode().splitlines(keepends=True):
        match = re.match(r'^([A-Z][A-Z0-9_]*)=(.*?)(\r?\n)?$', line)
        if match and match.group(1) in replacements:
            name = match.group(1)
            require(name not in seen, 'duplicate_environment_file_key')
            seen.add(name)
            value = match.group(2).strip().strip('\"\'')
            require(value in SOURCE_ENVIRONMENTS | {'production', 'true', 'false', ''}, 'environment_file_binding_unknown')
            line = name + '=' + replacements[name] + (match.group(3) or '')
        lines.append(line)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    for name in sorted(replacements.keys() - seen):
        lines.append(name + '=' + replacements[name] + '\n')
    return ''.join(lines).encode()


def configure_files(config, *, target, live=False):
    old = environment(config['services']['api'])
    new = target_environment(old, live=live)
    changes = {k:v for k,v in new.items() if old.get(k) != v}
    # These flags must be explicit in the durable source file even if inherited before.
    changes.update(APP_ENV='production', FACIAL_PROCESSING_ENABLED='false',
                   MERCADOPAGO_ALLOW_LIVE_PAYMENTS='true' if live else 'false')
    for saved in config['files'][:2]:
        raw = base64.b64decode(saved['content'])
        replacements = changes if saved['path'].endswith('.env.homolog') else {'INTEGRATION_SECRET_ENV': 'production'}
        replace_file(saved, rewrite_environment(raw, replacements) if target else raw)


def maintenance(config, enabled):
    saved = config['files'][2]
    content = (b'server { listen 80; location = /healthz { return 200 "ok"; } '
               b'location / { add_header Retry-After 60 always; return 503; } }\n') if enabled else base64.b64decode(saved['content'])
    replace_file(saved, content, same_inode=True)
    nginx = config['services']['nginx']['Id']
    run('docker', 'exec', nginx, 'nginx', '-t')
    run('docker', 'exec', nginx, 'nginx', '-s', 'reload')
    time.sleep(1)
    expected = '503' if enabled else '200'
    require(run('curl', '--silent', '--show-error', '--max-time', '15', '--output', '/dev/null',
                '--write-out', '%{http_code}', ORIGIN + '/') == expected, 'maintenance_barrier_unverified')


def stop_consumers(config):
    for name in CONSUMERS:
        run('docker', 'stop', '--timeout', '-1', config['services'][name]['Id'], timeout=300)


def target_config(config, *, live=False):
    result = copy.deepcopy(config)
    for name in CONSUMERS:
        values = target_environment(environment(config['services'][name]), live=live)
        result['services'][name]['Config']['Env'] = [k + '=' + v for k,v in values.items()]
    return result


def target_fingerprint(config, *, live=False, allow_maintenance=False):
    verify_running(config, target=True, live=live)
    active = containers()
    expected_nginx = hashlib.sha256(base64.b64decode(config['files'][2]['content'])).hexdigest()
    if not allow_maintenance:
        require(hashlib.sha256(Path(config['files'][2]['path']).read_bytes()).hexdigest() == expected_nginx,
                'nginx_configuration_not_restored')
    facts = {name: {'id': value['Id'], 'image': value['Image'],
                   'environment': digest(environment(value)), 'mounts': digest(value['Mounts'])}
             for name, value in active.items()}
    return digest({'services': facts, 'nginx_configuration': expected_nginx,
        'configuration': [hashlib.sha256(Path(x['path']).read_bytes()).hexdigest() for x in config['files'][:2]],
        'paused_facial': {name: config['services'][name]['Id'] for name in FACIAL_CONSUMERS}})


def save_receipt(operation, phase, value):
    name = operation + '-' + phase
    key = secrets.token_bytes(32)
    persist, _ = stores()
    persist(WORK / 'packages', WORK / 'keys', name,
            encrypted_payload=seal_config(value, key, name), backup_key=key)


def load_receipt(operation, phase):
    name = operation + '-' + phase
    _, reopen = stores()
    saved = reopen(WORK / 'packages', WORK / 'keys', name)
    return json.loads(AESGCM(saved.key).decrypt(base64.b64decode(saved.payload['nonce']),
        base64.b64decode(saved.payload['ciphertext']), ('environment-host-v1:' + name).encode()))


def claim_release_marker(sha, operation, fingerprint):
    path = STATE / 'app-in-flight.sha'
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(sha + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    owner = STATE.stat()
    os.chown(str(path), owner.st_uid, owner.st_gid)
    try:
        write_private(STATE / 'environment-cutover-in-flight.json',
                      {'sha': sha, 'operation': operation, 'fingerprint': fingerprint})
    except Exception:
        require(path.read_text().strip() == sha, 'new_marker_changed')
        path.unlink()
        raise


def clear_release_marker(operation):
    sidecar = STATE / 'environment-cutover-in-flight.json'
    value = json.loads(sidecar.read_text())
    marker = STATE / 'app-in-flight.sha'
    require(value['operation'] == operation and marker.read_text().strip() == value['sha'],
            'release_marker_owner_mismatch')
    marker.unlink()
    sidecar.unlink()


def verify_running(config, *, target, live=False):
    active = containers()
    require(set(active) == (EXPECTED - set(FACIAL_CONSUMERS) if target else EXPECTED), 'runtime_services_changed')
    for name, old in config['services'].items():
        if target and name in FACIAL_CONSUMERS:
            paused = json.loads(run('docker', 'inspect', old['Id']))[0]
            require(paused['Image'] == old['Image'] and paused['State']['Status'] == 'exited'
                    and paused['State']['Running'] is False, 'facial_consumer_not_paused')
            continue
        current = active[name]
        require(current['State'].get('Health', {}).get('Status') == 'healthy', 'runtime_unhealthy')
        if name not in CONSUMERS:
            require(current['Id'] == old['Id'], 'peer_container_changed')
        else:
            expected = target_environment(environment(old), live=live) if target else environment(old)
            require(current['Image'] == old['Image'] and environment(current) == expected, 'runtime_identity_or_environment_changed')
            require(current['Config']['Cmd'] == old['Config']['Cmd']
                    and current['Config']['Entrypoint'] == old['Config']['Entrypoint'], 'runtime_command_changed')
            require(current['Mounts'] == old['Mounts'], 'runtime_mounts_changed')
            require(set(current['NetworkSettings']['Networks']) == set(old['NetworkSettings']['Networks']), 'runtime_network_changed')
            require(current['HostConfig']['RestartPolicy'] == old['HostConfig']['RestartPolicy'], 'runtime_restart_policy_changed')


def wait_running(config, *, target, live=False):
    end = time.monotonic() + 120
    while True:
        try:
            verify_running(config, target=target, live=live)
            return
        except ReleaseBlocked as error:
            if str(error) not in {'runtime_unhealthy', 'runtime_services_changed'}:
                raise
            require(time.monotonic() < end, 'runtime_verification_timeout')
            time.sleep(2)


def apply(operation, fingerprint):
    config = open_config(operation)
    ready = load_receipt(operation, 'ready')
    require(ready['fingerprint'] == fingerprint and ready['plan'] == config['plan']
            and ready['channels_verified'] is True, 'preparation_not_verified')
    # Our marker is claimed by main before this function; snapshot must ignore
    # exactly this marker while keeping every other release marker fail-closed.
    require(config['fingerprint'] == fingerprint and snapshot(operation)['fingerprint'] == fingerprint, 'inventory_drift')
    source_model = model_path(config, operation, False)
    target_model = model_path(config, operation, True)
    barrier = False
    database_attempted = False
    try:
        barrier = True
        phase('maintenance_barrier')
        maintenance(config, True)
        phase('pause_consumers')
        stop_consumers(config)
        phase('database_package_prepare')
        prepared = runtime(config, 'prepare', operation, paused=True, network_checks=True)
        require(prepared['embedding_count'] == config['facts']['biometric_counts']['photo_embeddings']
                and prepared['account_count'] == config['facts']['credential_counts']['mercadopago_access_token'],
                'database_counts_changed_during_pause')
        database_attempted = True
        phase('database_apply')
        runtime(config, 'apply', operation, paused=True)
        phase('database_destination_verify')
        proof = runtime(config, 'verify', operation, paused=True)
        require(proof.get('destination_verified') is True, 'database_destination_unverified')
        configure_files(config, target=True)
        phase('target_startup')
        compose(target_model, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', *ACTIVE_CONSUMERS)
        wait_running(config, target=True)
        runtime(target_config(config), 'channels', operation, network_checks=True)
        phase('target_eligibility')
        matrix = runtime(target_config(config), 'eligibility', operation)
        require(matrix['live_gate'] is False, 'live_gate_opened_during_transition')
        target_identity = target_fingerprint(config, allow_maintenance=True)
        phase('target_receipt')
        save_receipt(operation, 'published', {'source_fingerprint': fingerprint,
            'target_fingerprint': target_identity, 'sha': config['sha'], 'matrix': matrix})
        maintenance(config, False)
        require(target_fingerprint(config) == target_identity, 'published_runtime_drift')
        barrier = False
        return {'status': 'published', 'production_environment': True, 'facial_enabled': False,
                'live_gate': False, 'financial_preserved': True, 'channels_verified': True,
                'target_fingerprint': target_identity, 'tenant_matrix': matrix}
    except Exception:  # noqa: BLE001 - recuperação precede qualquer reabertura e erros permanecem sanitizados
        if barrier:
            try:
                phase('source_recovery')
                maintenance(config, True)
                current = containers()
                for name in CONSUMERS:
                    if name in current:
                        run('docker', 'stop', '--timeout', '-1', current[name]['Id'], timeout=300)
                if database_attempted:
                    proof = runtime(config, 'verify', operation, paused=True)
                    if not proof.get('source_verified'):
                        require(proof.get('destination_verified') is True, 'recovery_database_unknown')
                        runtime(config, 'recover', operation, paused=True)
                configure_files(config, target=False)
                compose(source_model, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', *ACTIVE_CONSUMERS)
                for name in FACIAL_CONSUMERS:
                    run('docker', 'start', config['services'][name]['Id'])
                wait_running(config, target=False)
                maintenance(config, False)
            except Exception:  # noqa: BLE001 - barreira deve permanecer fechada em qualquer falha de recovery
                raise ReleaseBlocked('recovery_requires_operator_barrier_preserved') from None
        raise ReleaseBlocked('release_failed_source_recovered') from None


def enable_live(operation, fingerprint):
    phase('live_inventory')
    config = open_config(operation)
    published = load_receipt(operation, 'published')
    require(published['source_fingerprint'] == config['fingerprint']
            and published['target_fingerprint'] == fingerprint
            and target_fingerprint(config) == fingerprint, 'published_runtime_drift')
    active_model = model_path(config, operation, True, live=True)
    rollback_model = model_path(config, operation, True, reuse=True)
    barrier = False
    try:
        barrier = True
        phase('live_barrier_and_pause')
        maintenance(config, True)
        active = containers()
        for name in ACTIVE_CONSUMERS:
            run('docker', 'stop', '--timeout', '-1', active[name]['Id'], timeout=300)
        configure_files(config, target=True, live=True)
        phase('live_startup')
        compose(active_model, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', *ACTIVE_CONSUMERS)
        wait_running(config, target=True, live=True)
        current = target_config(config, live=True)
        phase('live_channels_and_eligibility')
        runtime(current, 'channels', operation, network_checks=True)
        matrix = runtime(current, 'eligibility', operation)
        require(matrix['live_gate'] is True and matrix['vault_verified'] is True
                and matrix['sandbox_pairs'] == 1, 'live_eligibility_unverified')
        identity = target_fingerprint(config, live=True, allow_maintenance=True)
        save_receipt(operation, 'live', {'source_fingerprint': fingerprint,
            'target_fingerprint': identity, 'matrix': matrix, 'live_gate': True})
        maintenance(config, False)
        require(target_fingerprint(config, live=True) == identity, 'live_runtime_drift')
        barrier = False
        return {'status': 'live_enabled', 'production_environment': True, 'live_gate': True,
                'facial_enabled': False, 'target_fingerprint': identity, 'tenant_matrix': matrix}
    except Exception:  # noqa: BLE001 - fechar somente novas emissões; preservar dados já migrados
        if barrier:
            try:
                phase('live_gate_recovery')
                maintenance(config, True)
                active = containers()
                for name in ACTIVE_CONSUMERS:
                    if name in active:
                        run('docker', 'stop', '--timeout', '-1', active[name]['Id'], timeout=300)
                configure_files(config, target=True)
                compose(rollback_model, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', *ACTIVE_CONSUMERS)
                wait_running(config, target=True)
                maintenance(config, False)
            except Exception:  # noqa: BLE001 - conservar barreira se qualquer recuperação falhar
                raise ReleaseBlocked('live_recovery_requires_operator_barrier_preserved') from None
        raise ReleaseBlocked('live_activation_failed_gate_closed') from None


def recover_release(operation, fingerprint):
    config = open_config(operation)
    marker = json.loads((STATE / 'environment-cutover-in-flight.json').read_text())
    require(marker['operation'] == operation and marker['fingerprint'] == fingerprint,
            'recovery_marker_mismatch')
    source_model = model_path(config, operation, False, reuse=True)
    maintenance(config, True)
    active = containers()
    for name in CONSUMERS:
        if name in active:
            run('docker', 'stop', '--timeout', '-1', active[name]['Id'], timeout=300)
    proof = runtime(config, 'verify', operation, paused=True)
    if not proof.get('source_verified'):
        require(proof.get('destination_verified') is True, 'recovery_database_unknown')
        runtime(config, 'recover', operation, paused=True)
    configure_files(config, target=False)
    compose(source_model, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', *ACTIVE_CONSUMERS)
    for name in FACIAL_CONSUMERS:
        run('docker', 'start', config['services'][name]['Id'])
    wait_running(config, target=False)
    maintenance(config, False)
    return {'status': 'source_recovered', 'live_gate': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('inventory', 'prepare', 'apply', 'enable-live', 'recover'))
    parser.add_argument('--sha', required=True)
    parser.add_argument('--operation')
    parser.add_argument('--fingerprint')
    args = parser.parse_args()
    require(socket.gethostname() == 'clearbudget-vnic' and ROOT.resolve() == ROOT, 'host_scope_invalid')
    require(os.geteuid() == 0, 'root_operator_required')
    verify_candidate(args.sha)
    if args.mode == 'inventory':
        value = snapshot()
        print(json.dumps({'status': 'inventoried', 'fingerprint': value['fingerprint'],
                          'schema': SCHEMA, 'service_count': len(value['services']),
                          'nginx_bind': '127.0.0.1:8080', 'biometric_counts': value['facts']['biometric_counts']}))
        return
    require(args.operation and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,45}', args.operation), 'operation_invalid')
    require(args.fingerprint and HEX.fullmatch(args.fingerprint), 'fingerprint_invalid')
    roots()
    with (STATE / 'production-release.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.mode == 'prepare':
            result = prepare(args.sha, args.operation, args.fingerprint)
        else:
            if args.mode != 'recover':
                claim_release_marker(args.sha, args.operation, args.fingerprint)
            try:
                if args.mode == 'apply':
                    result = apply(args.operation, args.fingerprint)
                elif args.mode == 'enable-live':
                    result = enable_live(args.operation, args.fingerprint)
                else:
                    result = recover_release(args.operation, args.fingerprint)
            except ReleaseBlocked as error:
                if str(error) in {'release_failed_source_recovered', 'live_activation_failed_gate_closed',
                                  'inventory_drift', 'published_runtime_drift', 'model_already_exists_or_changed'}:
                    clear_release_marker(args.operation)
                raise
            clear_release_marker(args.operation)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except ReleaseBlocked as error:
        print(json.dumps({'status': 'blocked', 'category': str(error), 'phase': PHASE}))
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001 - não emitir traceback de configuração/SQL/ambiente
        print(json.dumps({'status': 'blocked', 'category': 'unexpected_operator_failure', 'phase': PHASE}))
        raise SystemExit(2) from None
