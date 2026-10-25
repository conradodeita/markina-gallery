"""Scoped Pillow release: explicit receipt approval, main CI, quiescence, no DDL.

inventory/seal are read-only against services. apply/recover require the exact
sealed fingerprint. No build, pull, migration, secret rotation or SIGKILL.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

from prepare_emergency_api_image import maintenance_configuration
from specialized_pillow_candidate import (
    METADATA,
    SERVICES,
    image_id,
    isolated,
    require,
    save,
    sync_directory,
    validate,
)

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
CONFIGS = (ROOT / 'docker/docker-compose.yml', STATE / 'branding.compose.yml',
           ROOT / 'docker/docker-compose.raw-development.yml', ROOT / 'docker/docker-compose.preview-adjustment.yml',
           ROOT / 'docker/docker-compose.system-monitor.yml', STATE / 'system-monitor.compose.yml')
ENV_FILE = ROOT / 'docker/.env.homolog'
SCHEMA = ['20261022_0087']
EXPECTED = set(SERVICES) | {'api', 'worker', 'web', 'nginx', 'db', 'redis', 'evolution-api', 'evolution-db', 'evolution-redis'}
QUEUES = ('media_job', 'whatsapp_delivery', 'email_delivery', 'notification_delivery',
          'gallery_lifecycle_operation', 'asset_file_cleanup', 'facial_job', 'raw_development_job',
          'preview_adjustment', 'payment_notification_outbox', 'gallery_reopening_notification_outbox',
          'gallery_membership_notification_outbox', 'facial_search_notification_outbox')
FINANCIAL = ('sale_order', 'sale_order_item', 'payment_group', 'provider_payment', 'provider_payment_attempt',
             'provider_payment_receipt', 'provider_payment_correction', 'payment_confirmation_correction',
             'payment_communication', 'global_pix_settings', 'notification_delivery', 'whatsapp_delivery')
PENDING = ('app-in-flight.sha', 'app-rollback-in-flight.sha', 'web-in-flight.sha', 'web-pending.identity',
           'infinitepay-retirement-in-flight.sha', 'pillow-in-flight.json')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def configuration(item):
    config = {k: v for k, v in item['Config'].items() if k not in ('Image', 'Hostname', 'Labels')}
    config['Env'] = sorted(config.get('Env') or [])
    config['Labels'] = {k: v for k, v in (item['Config'].get('Labels') or {}).items()
                        if not k.startswith('com.docker.compose.') and k != 'com.pickyourpic.pillow-candidate'}
    host = {k: v for k, v in item['HostConfig'].items() if k != 'RestartPolicy'}
    return fingerprint({'config': config, 'host': host})


def idle(queues):
    require(set(queues) == set(QUEUES), 'incomplete queue evidence')
    require(all(not n for states in queues.values() for state, n in states.items()
                if state in ('queued', 'pending', 'processing')), 'eligible/active jobs remain')


def validate_inventory(data):
    require(data['host'] == 'clearbudget-vnic' and data['schema'] == SCHEMA, 'host/schema drift')
    require(data['clean'] and not data['pending'], 'dirty checkout or pending release')
    require(data['checkout'] == '1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8', 'application baseline drift')
    require(set(data['services']) == EXPECTED, 'service inventory drift')
    for service, item in data['services'].items():
        require(item['status'] == 'running' and item['health'] == 'healthy', 'unhealthy: ' + service)
        image_id(item['image'])
        require(item['restart'] == {'Name': 'unless-stopped' if service in SERVICES else
                ('no' if service in ('api', 'worker', 'web') else item['restart']['Name']),
                'MaximumRetryCount': 0}, 'restart policy drift')
    require(data['https'] == [200, 200, 200], 'HTTPS unavailable')
    return fingerprint(data)


class Host:
    deadline = None

    def run(self, *args, data=None, timeout=60, raw=False):
        if self.deadline:
            timeout = min(timeout, self.deadline - time.monotonic())
            require(timeout > 0, 'maintenance time budget exceeded')
        try:
            result = subprocess.run(args, input=data, text=True, capture_output=True, check=True,
                                    cwd=ROOT, timeout=timeout).stdout
            return result if raw else result.strip()
        except (subprocess.SubprocessError, OSError):
            raise ValueError('operational command failed; inspect private journal') from None

    def inspect(self, ident):
        return json.loads(self.run('docker', 'inspect', ident))[0]

    def pg(self, sql):
        return json.loads(self.run('docker', 'exec', '-i', 'markina-gallery-db-1', 'sh', '-c',
            'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            data="BEGIN READ ONLY; SET LOCAL statement_timeout='15s'; " + sql + '; ROLLBACK;'))

    def queues(self):
        return {table: self.pg("SELECT coalesce(json_object_agg(state,n),'{}'::json) FROM (SELECT "
            + ('external_status' if table == 'gallery_membership_notification_outbox' else 'status')
            + ' state,count(*) n FROM ' + table + ' GROUP BY 1) q') for table in QUEUES}

    def consumer(self, service):
        require(service in SERVICES, 'consumer outside scope')
        identifiers = self.run('docker', 'ps', '-a', '-q', '--filter',
            'label=com.docker.compose.project=markina-gallery', '--filter',
            'label=com.docker.compose.service=' + service).split()
        require(len(identifiers) <= 1, 'duplicate consumer')
        return self.inspect(identifiers[0]) if identifiers else None

    def financial(self):
        return {table: self.pg("SELECT json_build_object('count',count(*),'digest',"
            "md5(coalesce(string_agg(md5(to_jsonb(t)::text),'' ORDER BY to_jsonb(t)::text),''))) FROM "
            + table + ' t') for table in FINANCIAL}

    def health(self):
        return [int(self.run('curl', '--proto', '=https', '--tlsv1.2', '--silent', '--show-error',
                '--max-time', '10', '--output', '/dev/null', '--write-out', '%{http_code}',
                'https://markina.pickyourpic.com.br' + path)) for path in ('/healthz', '/api/health', '/')]

    def inventory(self):
        require(socket.gethostname() == 'clearbudget-vnic', 'wrong host')
        identifiers = self.run('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=markina-gallery').split()
        services = {}
        for ident in identifiers:
            d = self.inspect(ident)
            name = d['Config']['Labels']['com.docker.compose.service']
            require(name not in services, 'duplicate service')
            services[name] = {'id': d['Id'], 'image': d['Image'], 'started': d['State']['StartedAt'],
                'status': d['State']['Status'], 'health': d['State'].get('Health', {}).get('Status'),
                'restart': d['HostConfig']['RestartPolicy'], 'configuration': configuration(d)}
        result = {'host': socket.gethostname(), 'schema': self.pg('SELECT json_agg(version_num) FROM alembic_version'),
            'checkout': self.run('git', 'rev-parse', 'HEAD'), 'clean': not self.run('git', 'status', '--porcelain'),
            'pending': [name for name in PENDING if (STATE / name).exists()], 'services': services,
            'files': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in CONFIGS + (ENV_FILE,)},
            'https': self.health()}
        validate_inventory(result)
        return result

    def compose(self, overlay, *args):
        command = ['docker', 'compose', '--env-file', str(ENV_FILE), '-p', 'markina-gallery']
        for path in CONFIGS + (overlay,):
            command += ['-f', str(path)]
        return self.run(*command, '--profile', '*', *args, timeout=180)

    def projected_environment(self, overlay):
        projected = json.loads(self.compose(overlay, 'config', '--format', 'json'))['services']
        for service in SERVICES:
            d = self.inspect('markina-gallery-' + service + '-1')
            existing = dict(value.split('=', 1) for value in d['Config'].get('Env', []) if '=' in value)
            wanted = projected[service].get('environment', {})
            require(all(existing.get(key) == str(value) for key, value in wanted.items()),
                    'projected environment differs: ' + service)
            require(projected[service].get('restart') == d['HostConfig']['RestartPolicy']['Name'],
                    'projected restart policy differs')

    def guard(self, work, enabled):
        name = 'markina-gallery-nginx-1'
        backup = work / 'nginx-before.conf'
        if enabled:
            if not backup.exists():
                source = self.run('docker', 'exec', name, 'cat', '/etc/nginx/nginx.conf', raw=True)
                pending = backup.with_suffix('.pending-' + os.urandom(8).hex())
                fd = os.open(str(pending), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    stream.write(source)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(pending, backup)
                sync_directory(work)
            source = self.run('docker', 'exec', name, 'cat', '/etc/nginx/conf.d/default.conf')
            config = maintenance_configuration(source)
        else:
            require(backup.is_file() and not backup.is_symlink(), 'missing nginx recovery file')
            config = backup.read_text()
        self.run('docker', 'exec', '-i', name, 'sh', '-c', 'cat > /etc/nginx/nginx.conf', data=config)
        self.run('docker', 'exec', name, 'nginx', '-t')
        self.run('docker', 'exec', name, 'nginx', '-s', 'reload')
        if enabled:
            end = time.monotonic() + 10
            while self.run('curl', '--silent', '--max-time', '2', '--output', '/dev/null', '--write-out',
                           '%{http_code}', 'http://127.0.0.1:8080/admin') != '503':
                require(time.monotonic() < end, 'ingress barrier not active')
                time.sleep(0.2)

    def stop(self, ident, service):
        item = self.inspect(ident)
        if item['State']['Status'] == 'running':
            if service in SERVICES:
                idle(self.queues())
                channel = self.run('docker', 'exec', ident, 'python', '-B', '-c',
                                  "from pathlib import Path; print(Path('/proc/1/wchan').read_text().strip())")
                require(channel in ('do_sys_poll', 'hrtimer_nanosleep'), 'legacy consumer not idle')
            self.run('docker', 'update', '--restart=no', ident)
            self.run('docker', 'kill', '--signal=SIGINT' if service in SERVICES else '--signal=SIGTERM', ident)
        end = time.monotonic() + 90
        while True:
            item = self.inspect(ident)
            if item['State']['Status'] != 'running':
                expected = 130 if service in SERVICES else 0
                require(item['State']['Status'] == 'exited' and item['State']['ExitCode'] == expected,
                        'shutdown not confirmed')
                return
            require(time.monotonic() < end, 'shutdown timed out; SIGKILL forbidden')
            time.sleep(0.25)

    def healthy(self, ident):
        end = time.monotonic() + 120
        while True:
            d = self.inspect(ident)
            if d['State'].get('Health', {}).get('Status') == 'healthy':
                return d
            require(d['State']['Status'] == 'running' and time.monotonic() < end, 'health failed')
            time.sleep(1)

    def verify_ci(self, sha):
        require(re.fullmatch('[0-9a-f]{40}', sha), 'invalid approved source SHA')
        main = self.run('git', 'ls-remote', 'origin', 'refs/heads/main').split()
        require(main and main[0] == sha, 'reviewed source is not main')
        url = 'https://api.github.com/repos/conradodeita/markina-gallery/actions/runs?head_sha=' + sha + '&per_page=100'
        with urlopen(url, timeout=20) as response:
            runs = json.load(response)['workflow_runs']
        runs = [r for r in runs if r['path'] == '.github/workflows/ci.yml' and r['head_sha'] == sha
                and r['event'] == 'push' and r['head_branch'] == 'main']
        require(runs, 'main CI missing')
        run = max(runs, key=lambda r: (r['run_number'], r.get('run_attempt', 1)))
        require(run['status'] == 'completed' and run['conclusion'] == 'success', 'main CI not green')
        # Bind the executed coordinator/probe to reviewed source; do not trust a
        # manually copied or edited production helper just because the app SHA exists.
        for name in ('specialized_pillow_release.py', 'specialized_pillow_candidate.py',
                     'specialized_pillow_probe.py', 'prepare_emergency_api_image.py'):
            url = 'https://raw.githubusercontent.com/conradodeita/markina-gallery/' + sha + '/scripts/' + name
            with urlopen(url, timeout=20) as response:
                published = response.read(128 * 1024 + 1)
            require(len(published) <= 128 * 1024 and published == Path(__file__).with_name(name).read_bytes(),
                    'executed helper differs from reviewed main')
        return run['id']


@contextlib.contextmanager
def lock():
    import fcntl
    with (STATE / 'production-release.lock').open('a') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def overlay(receipt, previous=False):
    return {'services': {service: {'image': receipt['services'][service][
        'previous_image' if previous else 'candidate_image']} for service in SERVICES}}


def result_receipt(path, result):
    # A crash after evidence fsync but before marker removal must be recoverable.
    # Preserve an existing matching result; never overwrite divergent evidence.
    if path.exists():
        require(not path.is_symlink() and json.loads(path.read_text()) == result, 'result receipt drift')
    else:
        save(path, result)


def seal(host, prepared, sha, destination):
    host.verify_ci(sha)
    require(prepared['project'] == 'markina-gallery' and prepared['active_unchanged'] is True,
            'candidate receipt incomplete')
    require(set(prepared['services']) == set(SERVICES), 'wrong candidate scope')
    inventory = host.inventory()
    for service, proof in prepared['services'].items():
        require(inventory['services'][service]['image'] == proof['previous_image'], 'baseline image drift')
        base = json.loads(host.run('docker', 'image', 'inspect', image_id(proof['previous_image'])))[0]
        candidate = json.loads(host.run('docker', 'image', 'inspect', image_id(proof['candidate_image'])))[0]
        current = json.loads(isolated(proof['candidate_image'], METADATA))
        require(current == proof['after'], 'candidate runtime drift')
        validate(proof['before'], current, base, candidate, proof['baseline_probe'], proof['candidate_probe'])
    receipt = {'format': 1, 'source_sha': sha, 'prepared': fingerprint(prepared),
               'services': prepared['services'], 'inventory': inventory}
    projection = destination.with_name(destination.name + '.images.compose.json')
    save(projection, overlay(receipt))
    host.projected_environment(projection)
    save(destination, receipt)
    print('approval_fingerprint=' + fingerprint(receipt))


def verify_services(host, receipt, *, previous=False):
    for service in SERVICES:
        proof = receipt['services'][service]
        d = host.healthy('markina-gallery-' + service + '-1')
        require(d['Image'] == proof['previous_image' if previous else 'candidate_image'], 'active image drift')
        require(configuration(d) == receipt['inventory']['services'][service]['configuration'], 'active config drift')
        require(d['HostConfig']['RestartPolicy'] == receipt['inventory']['services'][service]['restart'], 'restart drift')
        meta = json.loads(host.run('docker', 'exec', d['Id'], 'python', '-B', '-c', METADATA))
        require(meta == proof['before' if previous else 'after'], 'loaded runtime drift')
    for service in EXPECTED - set(SERVICES):
        before = receipt['inventory']['services'][service]
        d = host.healthy(before['id'])
        require(d['Id'] == before['id'] and d['Image'] == before['image'], 'protected service replaced')
        require(configuration(d) == before['configuration'], 'protected configuration drift')
        require(d['HostConfig']['RestartPolicy'] == before['restart'], 'protected restart policy drift')
        if service not in ('api', 'worker'):
            require(d['State']['StartedAt'] == before['started'], 'protected service restarted')
    require(host.pg('SELECT json_agg(version_num) FROM alembic_version') == SCHEMA, 'schema changed')


def restart_original_writers(host, receipt):
    # Wait a pending stop to finish before start: never leave a late signal queued.
    for service in ('api', 'worker'):
        original = receipt['inventory']['services'][service]
        d = host.inspect(original['id'])
        require(d['Image'] == original['image'], 'original writer replaced')
        if d['State']['Status'] != 'running':
            host.run('docker', 'start', original['id'])
        host.run('docker', 'update', '--restart=' + original['restart']['Name'], original['id'])
        host.healthy(original['id'])


def apply(host, receipt, path, approval, *, recovery=False):
    require(approval == fingerprint(receipt), 'explicit receipt approval required')
    require(path.parent.parent == STATE and path.parent.name.startswith('pillow-prepare-')
            and not path.parent.is_symlink(), 'unsafe release workspace')
    work = path.parent
    journal = STATE / 'pillow-in-flight.json'
    if not recovery:
        host.verify_ci(receipt['source_sha'])
        require(host.inventory() == receipt['inventory'], 'inventory changed; reseal/review required')
        idle(host.queues())
        # Persist marker before touching ingress; recover requires this same receipt.
        save(journal, {'receipt': str(path), 'fingerprint': approval, 'stops': [], 'replaced': False})
    record = json.loads(journal.read_text())
    require(record['receipt'] == str(path) and record['fingerprint'] == approval, 'wrong recovery receipt')
    def checkpoint():
        temporary = journal.with_suffix('.tmp')
        with os.fdopen(os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
            json.dump(record, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, journal)
        sync_directory(STATE)
    host.deadline = time.monotonic() + 300
    try:
        host.guard(work, True)
        for service in ('api', 'worker'):
            ident = receipt['inventory']['services'][service]['id']
            if service not in record['stops']:
                record['stops'].append(service)
                checkpoint()
            host.stop(ident, service)
        idle(host.queues())
        if 'financial' not in record:
            require(not record['replaced'], 'financial recovery evidence missing after replacement')
            record['financial'] = host.financial()
            checkpoint()
        for service in SERVICES:
            current = host.consumer(service)
            if current is None:
                require(recovery and record['replaced'], 'consumer disappeared before replacement')
                continue
            ident = current['Id']
            proof = receipt['services'][service]
            require(current['Image'] in (proof['previous_image'], proof['candidate_image']), 'unknown consumer image')
            if service not in record['stops']:
                record['stops'].append(service)
                checkpoint()
            host.stop(ident, service)
        idle(host.queues())
        require(host.pg("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND state IN ('active','idle in transaction','idle in transaction (aborted)')")
                == 0, 'database writer remains active')
        target = work / ('rollback.compose.json' if recovery else 'active.compose.json')
        if not target.exists():
            save(target, overlay(receipt, previous=recovery))
        require(json.loads(target.read_text()) == overlay(receipt, previous=recovery), 'image overlay drift')
        record['replaced'] = True
        checkpoint()
        host.compose(target, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', *SERVICES)
        # Keep admission closed and original writers stopped until financial/config proof.
        for service in SERVICES:
            host.healthy('markina-gallery-' + service + '-1')
        require(host.financial() == record['financial'], 'financial history changed')
        restart_original_writers(host, receipt)
        verify_services(host, receipt, previous=recovery)
        host.guard(work, False)
        require(host.health() == [200, 200, 200], 'public health failed')
        result_receipt(work / ('recovered.json' if recovery else 'published.json'),
             {'fingerprint': approval, 'source_sha': receipt['source_sha'], 'services': overlay(receipt, recovery),
              'financial_preserved': True, 'financial': record['financial'],
              'schema': SCHEMA, 'security_fixed': not recovery})
        journal.unlink()
        sync_directory(STATE)
        print('recovered_previous_images=true security_fixed=false' if recovery else 'published_pillow13=6')
    except Exception:
        # Leave admission fenced and durable recovery information. No blind restart
        # or automatic force-recreate after a partial failure or unknown stop.
        host.deadline = None
        try:
            host.guard(work, True)
        except (ValueError, OSError):
            print('barrier_recovery_failed=true inspect_private_journal=true')
        raise
    finally:
        host.deadline = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inventory', 'seal', 'apply', 'recover'))
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--source-sha')
    parser.add_argument('--approval')
    args = parser.parse_args()
    host = Host()
    with lock():
        if args.mode == 'inventory':
            print(json.dumps(host.inventory(), sort_keys=True))
        elif args.mode == 'seal':
            require(args.prepared and args.receipt and args.source_sha, 'seal arguments missing')
            seal(host, json.loads(args.prepared.read_text()), args.source_sha, args.receipt)
        else:
            require(args.receipt and args.approval, 'receipt/approval missing')
            apply(host, json.loads(args.receipt.read_text()), args.receipt, args.approval,
                  recovery=args.mode == 'recover')


if __name__ == '__main__':
    main()
