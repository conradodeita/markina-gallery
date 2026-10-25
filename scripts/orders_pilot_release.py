#!/usr/bin/env python3
"""Procedimento pontual Orders 0087 -> 0088; inventário é o modo padrão.

Uso no host inventariado. Nunca importar configuração operacional para logs.
Preparação não substitui containers ativos. Aplicação exige recibo e fingerprint.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import tarfile
import time
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID, uuid4

from prepare_emergency_api_image import METADATA, STARTUP, maintenance_configuration

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
PROJECT = 'markina-gallery'
ORIGIN = 'https://markina.pickyourpic.com.br'
REPOSITORY = 'https://github.com/conradodeita/markina-gallery.git'
SCHEMA = '20261022_0087'
TARGET_SCHEMA = '20261024_0088'
BASELINE_SHA = '1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8'
APPROVED_RUNTIME = '47af72bdf503295e93b1ee8e68bef97da2d9d947'
SHA = re.compile(r'[0-9a-f]{40}')
HASH = re.compile(r'[0-9a-f]{64}')
IMAGE = re.compile(r'sha256:[0-9a-f]{64}')
SPECIALIZED = ('face-index-worker', 'face-gemma-index-worker', 'face-search-worker',
               'face-maintenance-worker', 'preview-adjustment-worker', 'raw-development-worker')
WRITERS = ('api', 'worker') + SPECIALIZED
SERVICES = set(WRITERS) | {'web', 'nginx', 'db', 'redis', 'evolution-api', 'evolution-db', 'evolution-redis'}
EXTRAS = (STATE / 'branding.compose.yml', ROOT / 'docker/docker-compose.raw-development.yml',
          ROOT / 'docker/docker-compose.preview-adjustment.yml', ROOT / 'docker/docker-compose.system-monitor.yml',
          STATE / 'system-monitor.compose.yml')
CONFIGS = (ROOT / 'docker/docker-compose.yml',) + EXTRAS
KEY_BINDING = ROOT / 'docker/.env.integration-secrets'
KEY_TARGET = STATE / 'integration-secrets.env'
PENDING = ('app-in-flight.sha', 'app-rollback-in-flight.sha', 'web-in-flight.sha',
           'web-pending.identity', 'infinitepay-retirement-in-flight.sha')
FINANCIAL = ('sale_order', 'sale_order_item', 'payment_group', 'provider_payment',
             'provider_payment_attempt', 'provider_payment_receipt', 'provider_payment_correction',
             'payment_confirmation_correction', 'payment_communication', 'global_pix_settings',
             'notification_delivery', 'whatsapp_delivery')
QUEUES = ('media_job', 'whatsapp_delivery', 'email_delivery', 'notification_delivery',
          'gallery_lifecycle_operation', 'asset_file_cleanup', 'facial_job', 'raw_development_job',
          'preview_adjustment', 'payment_notification_outbox', 'gallery_reopening_notification_outbox',
          'gallery_membership_notification_outbox', 'facial_search_notification_outbox')

CALLBACK_REHEARSAL = r"""
const fs=require('fs'),http=require('http'),crypto=require('crypto'),axios=require('axios');
const s=fs.readFileSync('/evolution/dist/main.js','utf8');
const begin=s.indexOf('async retryWebhookRequest'),end=s.indexOf('generateJwtToken',begin);
if(begin<0||end<begin)throw Error('retry source missing');
const method=s.slice(begin,end),E={get:()=>({RETRY:{}})};
const receiver=eval('({'+method+'})');receiver.logger={log:()=>{},error:()=>{}};
const listen=(server,port=0)=>new Promise(r=>server.listen(port,'127.0.0.1',r));
const close=server=>new Promise(r=>server.close(r));
const body={event:'synthetic-release-test',id:'one-synthetic-receipt'};
async function test(kind){
 let attempts=0,accepted=new Set();
 const server=http.createServer((req,res)=>{let chunks='';req.on('data',d=>chunks+=d);
  req.on('end',()=>{attempts++;let status=kind==='400'?400:kind==='503'&&attempts===1?503:200;
   if(status===200)accepted.add(JSON.parse(chunks).id);res.writeHead(status);res.end('synthetic');});});
 await listen(server);const port=server.address().port;
 const client=axios.create({baseURL:'http://127.0.0.1:'+port,proxy:false,timeout:1000});
 if(kind==='refused'){await close(server);setTimeout(()=>listen(server,port),1000);}
 let rejected=false;
 try{await receiver.retryWebhookRequest(client,body,'synthetic','loopback-only','none');}
 catch(e){if(kind!=='400')throw e;rejected=true;}
 await close(server);
 if(kind==='400'){if(!rejected||attempts!==1||accepted.size!==0)throw Error('unexpected 400 retry');}
 else if(accepted.size!==1||attempts!==(kind==='503'?2:1))throw Error('lost or duplicated receipt');
}
(async()=>{await test('503');await test('refused');await test('400');
 console.log(JSON.stringify({retry503:true,retryRefused:true,nonRetryable400:true,
 source_sha256:crypto.createHash('sha256').update(method).digest('hex')}));})()
.catch(()=>{process.stderr.write('synthetic callback rehearsal failed\n');process.exitCode=1;});
"""


class GateError(RuntimeError):
    """Somente categorias de erro públicas; nunca stderr, SQL retornado ou env."""


def require(condition, category):
    if not condition:
        raise GateError(category)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def pilot_pair(value):
    require(isinstance(value, dict) and set(value) == {'tenant_id', 'client_id'}, 'par_de_teste_invalido')
    try:
        result = {key: str(UUID(item)) for key, item in value.items()}
    except (ValueError, TypeError, AttributeError):
        raise GateError('par_de_teste_invalido') from None
    return result


def package_parity(before, after):
    require(before['python'] == after['python'], 'python_divergente')
    require(after['packages'] == {**before['packages'], 'mercadopago': '3.6.0'}, 'distribuicoes_divergentes')


def validate_inventory(data):
    require(data.get('host') == 'clearbudget-vnic' and data.get('root') == str(ROOT), 'host_ou_raiz_divergente')
    require(data.get('project') == PROJECT and data.get('origin') == ORIGIN, 'projeto_ou_origem_divergente')
    require(data.get('checkout_sha') == BASELINE_SHA and data.get('clean') is True, 'checkout_divergente')
    require(data.get('schema') == SCHEMA and data.get('orders_tables') == 0, 'schema_divergente')
    require(data.get('pending') == [], 'operacao_pendente')
    require(data.get('key', {}).get('valid') is True and data['key'].get('mode') == 0o600, 'cofre_invalido')
    require(data['key'].get('path') == str(KEY_TARGET), 'binding_divergente')
    require(data.get('app_env') == 'staging', 'ambiente_divergente')
    require(data.get('free_bytes', 0) >= 8 * 1024**3, 'espaco_insuficiente')
    services = data.get('services', {})
    require(set(services) == SERVICES, 'servicos_divergentes')
    for service, item in services.items():
        require(item.get('status') == 'running' and item.get('health') == 'healthy', 'servico_nao_saudavel')
        require(IMAGE.fullmatch(item.get('image', '')) and HASH.fullmatch(item.get('id', '')), 'identidade_invalida')
        expected = {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if service == 'nginx' else None
        ports = {k: v for k, v in (item.get('ports') or {}).items() if v}
        require(ports == (expected or {}), 'porta_divergente')
        if service in WRITERS + ('web',):
            require(item.get('restart_policy') == {'Name': 'unless-stopped' if service in SPECIALIZED else 'no',
                    'MaximumRetryCount': 0}, 'politica_de_reinicio_divergente')
    require(services['api'].get('version') == data['checkout_sha'], 'versao_ativa_divergente')
    require(set(data.get('files', {})) == {str(p) for p in CONFIGS + (ROOT / 'docker/.env.homolog',)},
            'configuracao_incompleta')
    require(all(HASH.fullmatch(h) for h in data['files'].values()), 'hash_de_configuracao_invalido')
    require(data.get('https') == [200, 200, 200], 'https_indisponivel')
    return fingerprint(data)


def idle_queues(queues):
    require(set(queues) == set(QUEUES), 'filas_incompletas')
    for values in queues.values():
        require(isinstance(values, dict), 'fila_invalida')
        require(not any(count for state, count in values.items() if state in {'queued', 'pending', 'processing'}),
                'trabalho_ativo_ou_elegivel')


def stopped(service, status, code):
    expected = {130} if service in SPECIALIZED else {0, 143} if service == 'web' else {0}
    require(status == 'exited' and code in expected, 'parada_nao_confirmada')


def release_overlay(images, pair, *, enabled=True):
    require(set(images) == {'api', 'web'} and all(IMAGE.fullmatch(i) for i in images.values()), 'imagens_invalidas')
    pair = pilot_pair(pair)
    env = {'MERCADOPAGO_ALLOW_LIVE_PAYMENTS': 'false',
           'MERCADOPAGO_TEST_CUSTOMERS': json.dumps([pair], separators=(',', ':')) if enabled else ''}
    return {'services': {
        'api': {'image': images['api'], 'environment': env},
        'worker': {'image': images['api'], 'environment': {'MERCADOPAGO_ALLOW_LIVE_PAYMENTS': 'false'},
                   'env_file': [{'path': str(KEY_TARGET), 'required': True, 'format': 'raw'}]},
        'web': {'image': images['web']}}}


class Host:
    def run(self, *args, data=None, timeout=60, binary=False):
        if getattr(self, 'deadline', None) is not None:
            timeout = min(timeout, self.deadline - time.monotonic())
            require(timeout > 0, 'janela_de_manutencao_excedida')
        try:
            result = subprocess.run(list(args), input=data, capture_output=True, text=not binary,
                                    timeout=timeout, cwd=ROOT, check=True,
                                    env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
        except (subprocess.SubprocessError, OSError):
            raise GateError('comando_operacional_falhou') from None
        return result.stdout if binary else result.stdout.strip()

    def inspect(self, ident):
        return json.loads(self.run('docker', 'inspect', ident))[0]

    def pg(self, sql, db='markina-gallery-db-1'):
        command = 'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
        return json.loads(self.run('docker', 'exec', '-i', db, 'sh', '-c', command,
                                  data="BEGIN READ ONLY; SET LOCAL statement_timeout='15s'; " + sql + '; ROLLBACK;'))

    def schema(self, db='markina-gallery-db-1'):
        return self.pg("SELECT coalesce(json_agg(version_num),'[]'::json) FROM alembic_version", db)

    def financial(self, db='markina-gallery-db-1'):
        result = {}
        for table in FINANCIAL:
            # New additive FK does not change a legacy order's financial snapshot.
            result[table] = self.pg("SELECT json_build_object('count',count(*),'digest',"
                "md5(coalesce(string_agg(md5((to_jsonb(t)-'mercadopago_payment_id')::text),'' ORDER BY "
                "(to_jsonb(t)-'mercadopago_payment_id')::text),''))) FROM " + table + ' t', db)
        return result

    def queues(self):
        result = {}
        for table in QUEUES:
            column = 'external_status' if table == 'gallery_membership_notification_outbox' else 'status'
            result[table] = self.pg("SELECT coalesce(json_object_agg(state,n),'{}'::json) FROM "
                '(SELECT ' + column + ' state,count(*) n FROM ' + table + ' GROUP BY ' + column + ') q')
        return result

    def health(self):
        return [int(self.run('curl', '--proto', '=https', '--tlsv1.2', '--silent', '--show-error',
                             '--max-time', '10', '--output', '/dev/null', '--write-out', '%{http_code}', ORIGIN + p))
                for p in ('/healthz', '/api/health', '/')]

    def inventory(self):
        require(socket.gethostname() == 'clearbudget-vnic' and ROOT.resolve() == ROOT, 'host_ou_raiz_divergente')
        require(self.run('git', 'remote', 'get-url', 'origin') in {
            REPOSITORY, REPOSITORY[:-4], 'git@github.com:conradodeita/markina-gallery.git'}, 'repositorio_divergente')
        ids = self.run('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + PROJECT).split()
        services = {}
        app_env = None
        for ident in ids:
            d = self.inspect(ident)
            labels = d['Config'].get('Labels') or {}
            name = labels.get('com.docker.compose.service')
            require(name not in services, 'servico_duplicado')
            env = dict(x.split('=', 1) for x in d['Config'].get('Env', []) if '=' in x)
            services[name] = {'id': d['Id'], 'image': d['Image'], 'command': d['Config']['Cmd'],
                'health': d['State'].get('Health', {}).get('Status'), 'status': d['State']['Status'],
                'config_hash': labels.get('com.docker.compose.config-hash'),
                'started_at': d['State']['StartedAt'],
                'restart_policy': d['HostConfig']['RestartPolicy'],
                'compose_files': labels.get('com.docker.compose.project.config_files'),
                'ports': d['NetworkSettings'].get('Ports'), 'version': env.get('APP_VERSION')}
            if name == 'api':
                app_env = env.get('APP_ENV')
        require(KEY_BINDING.resolve(strict=True) == KEY_TARGET, 'binding_divergente')
        st = KEY_TARGET.lstat()
        require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_uid == os.getuid(), 'cofre_inseguro')
        probe = "from app.integration_secrets import IntegrationCipher; IntegrationCipher(); print('valid')"
        key_valid = self.run('docker', 'exec', services['api']['id'], 'python', '-B', '-c', probe) == 'valid'
        key_config = dict(line.split('=', 1) for line in KEY_TARGET.read_text().splitlines()
                          if '=' in line and not line.lstrip().startswith('#'))
        api_env = dict(x.split('=', 1) for x in self.inspect(services['api']['id'])['Config']['Env'] if '=' in x)
        require(all(api_env.get(k) == key_config.get(k) and key_config.get(k) for k in
                    ('INTEGRATION_SECRET_ENV', 'INTEGRATION_SECRET_ACTIVE_KEY_ID', 'INTEGRATION_SECRET_KEYS')),
                'cofre_do_host_diverge_da_api')
        schema = self.schema()
        data = {'host': socket.gethostname(), 'root': str(ROOT), 'project': PROJECT, 'origin': ORIGIN,
                'checkout_sha': self.run('git', 'rev-parse', 'HEAD'),
                'clean': not self.run('git', 'status', '--porcelain'), 'schema': schema[0] if len(schema) == 1 else None,
                'orders_tables': self.pg("SELECT count(*) FROM pg_tables WHERE schemaname='public' "
                    "AND tablename IN ('mercadopago_account','mercadopago_payment','mercadopago_webhook','payment_preferences')"),
                'services': services, 'app_env': app_env, 'key': {'path': str(KEY_TARGET),
                    'mode': stat.S_IMODE(st.st_mode), 'valid': key_valid, 'inode': st.st_ino,
                    'sha256': hashlib.sha256(KEY_TARGET.read_bytes()).hexdigest()},
                'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in CONFIGS + (ROOT / 'docker/.env.homolog',)},
                'free_bytes': shutil.disk_usage(ROOT).free,
                'pending': [n for n in PENDING if (STATE / n).exists()], 'https': self.health()}
        # Free space is a gate, not a fingerprint that changes with unrelated disk writes.
        require(data['free_bytes'] >= 8 * 1024**3, 'espaco_insuficiente')
        data['free_bytes'] = 8 * 1024**3
        validate_inventory(data)
        return data

    def inspect_image(self, image):
        value = self.run('docker', 'image', 'inspect', '--format', '{{.Id}}', image)
        require(IMAGE.fullmatch(value), 'imagem_invalida')
        return value

    def main_sha(self):
        value = self.run('git', 'ls-remote', REPOSITORY, 'refs/heads/main').split()
        require(len(value) == 2 and SHA.fullmatch(value[0]), 'main_indisponivel')
        return value[0]

    def verify_ci(self, sha):
        require(SHA.fullmatch(sha), 'sha_invalido')
        url = 'https://api.github.com/repos/conradodeita/markina-gallery/actions/runs?head_sha=' + sha + '&per_page=100'
        try:
            with urlopen(url, timeout=20) as response:
                require(response.url.startswith('https://api.github.com/'), 'fonte_ci_divergente')
                payload = response.read(2 * 1024**2 + 1)
                require(len(payload) <= 2 * 1024**2, 'resposta_ci_excessiva')
                runs = json.loads(payload)['workflow_runs']
        except (OSError, ValueError, KeyError):
            raise GateError('consulta_ci_falhou') from None
        relevant = [r for r in runs if r.get('path') == '.github/workflows/ci.yml'
                    and r.get('head_sha') == sha and r.get('event') == 'push' and r.get('head_branch') == 'main']
        require(bool(relevant), 'ci_main_ausente')
        latest = max(relevant, key=lambda r: (r['run_number'], r.get('run_attempt', 1)))
        require(latest['status'] == 'completed' and latest['conclusion'] == 'success', 'ci_nao_aprovado')
        return latest['id']

    def dump(self, path):
        require(not path.exists() and not path.is_symlink(), 'backup_ja_existe')
        command = ['docker', 'exec', 'markina-gallery-db-1', 'sh', '-c',
                   'exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
        self.file_command(command, path, output=True)
        require(path.stat().st_size > 0, 'backup_vazio')
        self.file_command(['docker', 'exec', '-i', 'markina-gallery-db-1', 'pg_restore', '--list'], path)

    def shutdown_rehearsal(self, inventory, candidate):
        for service in ('worker-old', 'worker') + SPECIALIZED:
            name = 'markina-gallery-orders-signal-' + uuid4().hex
            image = (candidate if service == 'worker' else inventory['services'][
                'worker' if service == 'worker-old' else service]['image'])
            if service in {'worker', 'worker-old'}:
                code = ('import signal; from app.worker import _request_worker_stop,run_worker_until_stopped; '
                        'signal.signal(signal.SIGTERM,_request_worker_stop); '
                        'run_worker_until_stopped(cycle=lambda:False)')
            else:
                # Exercise the actual Python binary/signal disposition, without starting any engine or queue.
                code = ('import signal,sys,select; '
                        'signal.signal(signal.SIGTERM,lambda *a:sys.exit(0)); select.poll().poll(60000)')
            ident = self.run('docker', 'run', '-d', '--name', name, '--network', 'none', '--read-only',
                 '--restart', 'unless-stopped' if service in SPECIALIZED else 'no',
                 '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1',
                 '--label', 'com.docker.compose.project=markina-gallery-orders-signal',
                 '--tmpfs', '/tmp:rw,nosuid,size=32m', '-e', 'APP_ENV=test',
                 '-e', 'DATABASE_URL=sqlite:////tmp/signal.sqlite', '-e', 'PYTHONDONTWRITEBYTECODE=1',
                 '--entrypoint', 'python', image, '-B', '-c', code)
            item = {'id': ident, 'image': image, 'restart_policy': {
                'Name': 'unless-stopped' if service in SPECIALIZED else 'no', 'MaximumRetryCount': 0}}
            try:
                end = time.monotonic() + 20
                while True:
                    require(self.inspect(ident)['State']['Status'] == 'running', 'processo_de_ensaio_falhou')
                    channel = self.run('docker', 'exec', ident, 'python', '-B', '-c',
                        "from pathlib import Path; print(Path('/proc/1/wchan').read_text().strip())")
                    if channel in ({'hrtimer_nanosleep'} if service in {'worker', 'worker-old'} else {'do_sys_poll'}):
                        break
                    require(time.monotonic() < end, 'processo_de_ensaio_nao_ocioso')
                    time.sleep(0.1)
                self.disable_restart(item)
                self.run('docker', 'kill', '--signal=SIGTERM' if service in {'worker', 'worker-old'} else '--signal=SIGINT', ident)
                wait_exit(self, ident, service, seconds=10)
                if service in SPECIALIZED:
                    self.run('docker', 'start', ident)
                    self.restore_restart(item)
                    require(self.inspect(ident)['HostConfig']['RestartPolicy'] == item['restart_policy'],
                            'politica_de_reinicio_nao_restaurada')
                    end = time.monotonic() + 10
                    while self.run('docker', 'exec', ident, 'python', '-B', '-c',
                        "from pathlib import Path; print(Path('/proc/1/wchan').read_text().strip())") != 'do_sys_poll':
                        require(time.monotonic() < end, 'ensaio_de_retomada_nao_ocioso')
                        time.sleep(0.1)
            finally:
                d = self.inspect(ident)
                require(d['Image'] == image and d['Config']['Labels'].get('com.docker.compose.project')
                        == 'markina-gallery-orders-signal', 'container_de_ensaio_divergente')
                if d['State']['Status'] == 'running':
                    self.disable_restart(item)
                    self.run('docker', 'kill', '--signal=SIGTERM', ident)
                    wait_exit(self, ident, 'worker', seconds=10)
                self.run('docker', 'rm', ident)

    def callback_rehearsal(self, inventory):
        image = inventory['services']['evolution-api']['image']
        result = json.loads(self.run('docker', 'run', '--rm', '--network', 'none', '--read-only',
             '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1',
             '--label', 'com.docker.compose.project=markina-gallery-orders-callback-rehearsal',
             '--entrypoint', 'node', image, '-e', CALLBACK_REHEARSAL, timeout=45))
        require(all(result.get(k) is True for k in ('retry503', 'retryRefused', 'nonRetryable400')),
                'continuidade_de_callback_nao_comprovada')
        require(HASH.fullmatch(result.get('source_sha256', '')), 'codigo_de_callback_invalido')
        result['image'] = image
        return result

    def guard_rehearsal(self, inventory, work, candidate):
        source = self.run('docker', 'exec', inventory['services']['nginx']['id'],
                          'cat', '/etc/nginx/conf.d/default.conf')
        config = work / ('nginx-guard-rehearsal-' + uuid4().hex + '.conf')
        with os.fdopen(os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as file:
            file.write(maintenance_configuration(source))
        image = inventory['services']['nginx']['image']
        ident = self.run('docker', 'run', '-d', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
             '--cap-add', 'CHOWN', '--cap-add', 'SETUID', '--cap-add', 'SETGID', '--cap-add', 'NET_BIND_SERVICE',
             '--cap-add', 'KILL', '--cap-add', 'DAC_OVERRIDE',
             '--security-opt', 'no-new-privileges', '--memory', '128m', '--cpus', '0.5',
             '--label', 'com.docker.compose.project=markina-gallery-orders-guard',
             '--add-host', 'api:127.0.0.1', '--add-host', 'web:127.0.0.1',
             '--tmpfs', '/var/run:rw,nosuid,size=8m', '--tmpfs', '/var/cache/nginx:rw,nosuid,size=8m',
             '-v', str(config) + ':/orders-guard.conf:ro', '--entrypoint', 'nginx', image,
             '-c', '/orders-guard.conf', '-g', 'daemon off;')
        code = ("from urllib.request import urlopen,Request; from urllib.error import HTTPError; "
                "codes=[]\nfor p in ['/healthz','/admin','/api/mercadopago/webhooks/synthetic']:\n"
                " try:\n  r=urlopen(Request('http://127.0.0.1'+p,method='GET' if p=='/healthz' else 'POST'),timeout=3); codes.append(r.status)\n"
                " except HTTPError as e: codes.append(e.code)\n"
                "assert codes==[200,503,503], codes\nprint('passed')")
        try:
            self.run('docker', 'exec', ident, 'nginx', '-c', '/orders-guard.conf', '-t')
            require(isolated(self, candidate, code, network='container:' + ident) == 'passed', 'barreira_nao_validada')
        except GateError:
            # This container has only synthetic requests and no operational secrets/data.
            log = subprocess.run(['docker', 'logs', ident], capture_output=True, text=True, timeout=10, check=False)
            save(work / ('nginx-guard-diagnostic-' + ident[:12] + '.json'),
                 {'stdout': log.stdout[-8192:], 'stderr': log.stderr[-8192:]}, exclusive=True)
            raise
        finally:
            d = self.inspect(ident)
            require(d['Image'] == image and d['Config']['Labels'].get('com.docker.compose.project')
                    == 'markina-gallery-orders-guard', 'container_de_ensaio_divergente')
            if d['State']['Status'] == 'running':
                self.run('docker', 'kill', '--signal=SIGTERM', ident)
                wait_exit(self, ident, 'api', seconds=10)
            self.run('docker', 'rm', ident)
        return 'passed'

    def web_shutdown_rehearsal(self, image):
        ident = self.run('docker', 'run', '-d', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
             '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1',
             '--label', 'com.docker.compose.project=markina-gallery-orders-web-signal',
             '--tmpfs', '/tmp:rw,nosuid,size=64m', '--entrypoint', 'node', image, 'server.js')
        try:
            self.run('docker', 'exec', ident, 'node', '-e',
                "(async()=>{for(let i=0;i<30;i++){try{let r=await fetch('http://127.0.0.1:3000/api/health');if(r.status===200)return}catch(e){}await new Promise(r=>setTimeout(r,200))}process.exit(1)})()")
            self.run('docker', 'kill', '--signal=SIGTERM', ident)
            wait_exit(self, ident, 'web', seconds=15)
        finally:
            d = self.inspect(ident)
            require(d['Image'] == image and d['Config']['Labels'].get('com.docker.compose.project')
                    == 'markina-gallery-orders-web-signal', 'container_de_ensaio_divergente')
            if d['State']['Status'] == 'running':
                self.run('docker', 'kill', '--signal=SIGTERM', ident)
                wait_exit(self, ident, 'web', seconds=15)
            self.run('docker', 'rm', ident)

    def file_command(self, command, path, *, output=False):
        timeout = 120
        if getattr(self, 'deadline', None) is not None:
            timeout = min(timeout, self.deadline - time.monotonic())
            require(timeout > 0, 'janela_de_manutencao_excedida')
        try:
            if output:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as file:
                    subprocess.run(command, stdout=file, stderr=subprocess.PIPE, check=True, timeout=timeout)
                    file.flush()
                    os.fsync(file.fileno())
            else:
                with path.open('rb') as file:
                    subprocess.run(command, stdin=file, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, check=True, timeout=timeout)
        except (subprocess.SubprocessError, OSError):
            raise GateError('validacao_de_backup_falhou') from None

    def rehearse(self, archive, key, image, *, expected=None):
        name = 'markina-gallery-orders-rehearsal-' + uuid4().hex
        db_image = self.inspect('markina-gallery-db-1')['Image']
        require(IMAGE.fullmatch(db_image), 'imagem_postgresql_divergente')
        self.run('docker', 'run', '-d', '--name', name, '--network', 'none', '--memory', '2g', '--cpus', '1',
                 '--label', 'com.docker.compose.project=markina-gallery-orders-rehearsal',
                 '--tmpfs', '/var/lib/postgresql/data:rw,nosuid,size=1g', '-e', 'POSTGRES_DB=orders_rehearsal',
                 '-e', 'POSTGRES_USER=postgres', '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', db_image,
                 'postgres', '-c', 'listen_addresses=127.0.0.1')
        try:
            end = time.monotonic() + 40
            while True:
                try:
                    if self.pg('SELECT 1', name) == 1:
                        break
                except GateError:
                    pass
                require(time.monotonic() < end, 'postgresql_de_ensaio_indisponivel')
                time.sleep(0.5)
            self.file_command(['docker', 'exec', '-i', name, 'pg_restore', '--exit-on-error', '--no-owner',
                               '--no-privileges', '-U', 'postgres', '-d', 'orders_rehearsal'], archive)
            require(self.schema(name) == [SCHEMA], 'schema_restaurado_divergente')
            before = self.financial(name)
            require(expected is None or before == expected, 'backup_nao_preservou_financas')
            code = ("import subprocess; from app.integration_secrets import IntegrationCipher; "
                    "from uuid import uuid4; c=IntegrationCipher(); t=uuid4(); a=uuid4(); "
                    "e=c.encrypt('synthetic-recovery-check',tenant_id=t,credential_id=a); "
                    "assert c.decrypt(e,tenant_id=t,credential_id=a)=='synthetic-recovery-check'; "
                    "subprocess.run(['python','-B','-m','alembic','upgrade','" + TARGET_SCHEMA + "'],check=True)")
            isolated(self, image, code, network='container:' + name,
                     env=('--env-file', str(key), '-e', 'APP_ENV=staging', '-e',
                          'DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/orders_rehearsal'))
            require(self.schema(name) == [TARGET_SCHEMA] and self.financial(name) == before,
                    'ensaio_alterou_financas_ou_schema')
            return 'passed'
        finally:
            d = self.inspect(name)
            require(d['Image'] == db_image and d['Config']['Labels'].get('com.docker.compose.project')
                    == 'markina-gallery-orders-rehearsal', 'container_de_ensaio_divergente')
            self.run('docker', 'kill', '--signal=SIGTERM', d['Id'])
            wait_exit(self, d['Id'], 'api', seconds=40)
            self.run('docker', 'rm', d['Id'])

    def compose(self, work, *args):
        command = ['docker', 'compose', '--env-file', str(ROOT / 'docker/.env.homolog'),
                   '-p', PROJECT, '-f', str(CONFIGS[0])]
        for p in EXTRAS:
            command += ['-f', str(p)]
        command += ['-f', str(work / 'active.compose.json'), '--profile', '*']
        return self.run(*command, *args, timeout=240)

    def maintenance(self, work, enabled, *, reuse=False):
        name = 'markina-gallery-nginx-1'
        backup = work / 'nginx-original.conf'
        if enabled:
            require(reuse or not backup.exists(), 'barreira_ja_existe')
            source = self.run('docker', 'exec', name, 'cat', '/etc/nginx/conf.d/default.conf')
            original = self.run('docker', 'exec', name, 'cat', '/etc/nginx/nginx.conf', binary=True).decode('utf-8')
            config = maintenance_configuration(source)
            if not reuse:
                with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
                    out.write(original)
                    out.flush()
                    os.fsync(out.fileno())
            else:
                require(backup.is_file() and not backup.is_symlink(), 'backup_nginx_ausente')
            self.run('docker', 'exec', '-i', name, 'sh', '-c', 'cat > /etc/nginx/nginx.conf', data=config)
        else:
            require(backup.is_file() and not backup.is_symlink(), 'backup_nginx_ausente')
            self.run('docker', 'exec', '-i', name, 'sh', '-c', 'cat > /etc/nginx/nginx.conf', data=backup.read_text())
        self.run('docker', 'exec', name, 'nginx', '-t')
        self.run('docker', 'exec', name, 'nginx', '-s', 'reload')
        if enabled:
            end = time.monotonic() + 5
            while self.run('curl', '--silent', '--max-time', '2', '--output', '/dev/null',
                           '--write-out', '%{http_code}', 'http://127.0.0.1:8080/admin') != '503':
                require(time.monotonic() < end, 'barreira_nao_ativada')
                time.sleep(0.1)

    def activate_source(self, source, sha):
        self.run('git', 'fetch', '--quiet', '--no-tags', str(source), sha)
        self.run('git', 'switch', '--detach', sha)

    def wait_healthy(self, ident):
        end = time.monotonic() + 120
        while True:
            d = self.inspect(ident)
            if d['State'].get('Health', {}).get('Status') == 'healthy':
                return d
            require(d['State']['Status'] == 'running' and time.monotonic() < end, 'servico_nao_retornou_saudavel')
            time.sleep(1)

    def wait_new(self, receipt, *, enabled=True):
        for service in ('api', 'web', 'worker'):
            expected = receipt['images']['web' if service == 'web' else 'api']
            d = self.wait_healthy('markina-gallery-' + service + '-1')
            require(d['Image'] == expected, 'imagem_ativa_divergente')
            if service != 'web':
                env = dict(x.split('=', 1) for x in d['Config']['Env'] if '=' in x)
                require(env.get('APP_VERSION') == receipt['sha'] and env.get('APP_ENV') == 'staging'
                        and env.get('MERCADOPAGO_ALLOW_LIVE_PAYMENTS') == 'false', 'gate_operacional_divergente')
                if service == 'api':
                    require((json.loads(env.get('MERCADOPAGO_TEST_CUSTOMERS', 'null')) == [receipt['pair']])
                            if enabled else env.get('MERCADOPAGO_TEST_CUSTOMERS') == '',
                            'par_de_teste_divergente')
                require(self.run('docker', 'exec', d['Id'], 'python', '-B', '-c',
                     "from app.integration_secrets import IntegrationCipher; IntegrationCipher(); print('valid')")
                        == 'valid', 'cofre_nao_disponivel_no_runtime')

    def disable_restart(self, item):
        d = self.inspect(item['id'])
        require(d['Image'] == item['image'] and d['HostConfig']['RestartPolicy'] in
                (item['restart_policy'], {'Name': 'no', 'MaximumRetryCount': 0}), 'politica_de_reinicio_mudou')
        require(item['restart_policy'] in ({'Name': 'no', 'MaximumRetryCount': 0},
                {'Name': 'unless-stopped', 'MaximumRetryCount': 0}), 'politica_de_reinicio_invalida')
        if d['HostConfig']['RestartPolicy']['Name'] != 'no':
            self.run('docker', 'update', '--restart=no', item['id'])
        require(self.inspect(item['id'])['HostConfig']['RestartPolicy'] == {'Name': 'no', 'MaximumRetryCount': 0},
                'reinicio_automatico_nao_suspenso')

    def restore_restart(self, item):
        d = self.inspect(item['id'])
        require(d['Image'] == item['image'] and d['State']['Status'] == 'running', 'container_anterior_nao_ativo')
        require(item['restart_policy'] in ({'Name': 'no', 'MaximumRetryCount': 0},
                {'Name': 'unless-stopped', 'MaximumRetryCount': 0}), 'politica_de_reinicio_invalida')
        if d['HostConfig']['RestartPolicy'] != item['restart_policy']:
            self.run('docker', 'update', '--restart=' + item['restart_policy']['Name'], item['id'])
        require(self.inspect(item['id'])['HostConfig']['RestartPolicy'] == item['restart_policy'],
                'politica_de_reinicio_nao_restaurada')

    def start_existing(self, item, *, ensure_stop=False, service=None):
        d = self.inspect(item['id'])
        require(d['Image'] == item['image'], 'imagem_anterior_divergente')
        if ensure_stop and d['State']['Status'] == 'running':
            self.disable_restart(item)
            if service in SPECIALIZED:
                idle_queues(self.queues())
                channel = self.run('docker', 'exec', item['id'], 'python', '-B', '-c',
                    "from pathlib import Path; print(Path('/proc/1/wchan').read_text().strip())")
                require(channel in {'hrtimer_nanosleep', 'do_sys_poll'}, 'worker_legado_nao_ocioso')
            self.run('docker', 'kill', '--signal=SIGINT' if service in SPECIALIZED else '--signal=SIGTERM', item['id'])
            wait_exit(self, item['id'], service)
            d = self.inspect(item['id'])
        if d['State']['Status'] == 'exited':
            self.run('docker', 'start', item['id'])
        self.restore_restart(item)
        self.wait_healthy(item['id'])

    def verify_restored(self, inventory, *, specialized_only=False):
        for service in SPECIALIZED if specialized_only else WRITERS + ('web',):
            item = inventory['services'][service]
            d = self.wait_healthy(item['id'])
            require(d['Image'] == item['image'] and d['Config']['Cmd'] == item['command']
                    and d['HostConfig']['RestartPolicy'] == item['restart_policy'],
                    'runtime_anterior_nao_preservado')
        for service in ('db', 'redis', 'nginx', 'evolution-api', 'evolution-db', 'evolution-redis'):
            item = inventory['services'][service]
            d = self.wait_healthy(item['id'])
            require(d['Image'] == item['image'] and d['State']['StartedAt'] == item['started_at'],
                    'servico_fora_do_escopo_foi_reiniciado')

    def restore_before_ddl(self, inventory, work):
        require(self.schema() == [SCHEMA], 'recuperacao_exige_schema_original')
        if self.run('git', 'rev-parse', 'HEAD') != inventory['checkout_sha']:
            require(not self.run('git', 'status', '--porcelain'), 'checkout_mudou_durante_recuperacao')
            self.run('git', 'switch', '--detach', inventory['checkout_sha'])
        pending = load(work / 'stage.json').get('stop_requests', {})
        for service in WRITERS + ('web',):
            item = inventory['services'][service]
            self.start_existing(item, service=service, ensure_stop=item['id'] in pending)
        self.verify_restored(inventory)
        if (work / 'nginx-original.conf').exists():
            self.maintenance(work, False)
        require(self.health() == [200, 200, 200], 'recuperacao_pre_ddl_inconclusiva')


def save(path, data, *, exclusive=False):
    path = Path(path)
    require(not path.is_symlink(), 'artefato_inseguro')
    require(not exclusive or not path.exists(), 'artefato_ja_existe')
    temporary = path.parent / ('.orders-atomic-' + uuid4().hex)
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
        json.dump(data, out, sort_keys=True, indent=2)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)
    if os.name == 'posix':
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def load(path):
    path = Path(path)
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o600
            and st.st_uid == os.getuid(), 'artefato_inseguro')
    return json.loads(path.read_text())


def extract(archive, root):
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar:
            p = Path(member.name)
            require(not p.is_absolute() and '..' not in p.parts
                    and p.parts[0] in {'backend', 'frontend', 'docker'}, 'archive_inseguro')
            if member.isdir():
                continue
            require(member.isfile(), 'archive_inseguro')
            dest = root / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(tar.extractfile(member).read())


def isolated(h, image, code, *, network='none', env=(), mounts=()):
    return h.run('docker', 'run', '--rm', '--network', network, '--read-only', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--memory', '1g', '--cpus', '1', '--pids-limit', '128',
        '--tmpfs', '/tmp:rw,nosuid,size=256m', '-e', 'PYTHONDONTWRITEBYTECODE=1',
        '-e', 'APP_ENV=test', '-e', 'DATABASE_URL=sqlite:////tmp/startup.sqlite',
        '-e', 'GALLERY_CAPABILITY_SIGNING_KEY=synthetic-orders-release-capability-key',
        *env, *mounts, '--entrypoint', 'python', image, '-B', '-c', code, timeout=180)


def prepare(h, target, pair):
    require(SHA.fullmatch(target), 'sha_invalido')
    inventory = h.inventory()
    print('preparation_stage=inventory_validated', flush=True)
    pair = pilot_pair(pair)
    owner_check(h, pair)
    work = STATE / ('orders-prepare-' + uuid4().hex)
    work.mkdir(mode=0o700)
    source = work / 'source'
    h.run('git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(source))
    h.run('git', '-C', str(source), 'remote', 'set-url', 'origin', REPOSITORY)
    h.run('git', '-C', str(source), 'fetch', '--quiet', '--no-tags', 'origin', target, timeout=180)
    h.run('git', '-C', str(source), 'update-ref', 'refs/heads/orders-candidate', target)
    h.run('git', '-C', str(source), 'merge-base', '--is-ancestor', inventory['checkout_sha'], target)
    h.run('git', '-C', str(source), 'merge-base', '--is-ancestor', APPROVED_RUNTIME, target)
    # This operator procedure cannot smuggle a later runtime change into the financial release.
    require(not h.run('git', '-C', str(source), 'diff', '--name-only', APPROVED_RUNTIME, target,
                      '--', 'backend', 'frontend', 'docker'), 'runtime_fora_do_candidato_revisado')
    archive = h.run('git', '-C', str(source), 'archive', target, 'backend', 'frontend', 'docker', binary=True)
    context = work / 'context'
    context.mkdir(mode=0o700)
    extract(archive, context)
    # No broad update: reuse the API's actual image and add the single authorized wheel offline.
    base = inventory['services']['api']['image']
    front = inventory['services']['web']['image']
    before = json.loads(isolated(h, base, METADATA))
    wheels = context / 'wheels'
    wheels.mkdir()
    h.run('docker', 'run', '--rm', '--memory', '512m', '--cpus', '1', '--pids-limit', '128',
          '-v', str(wheels) + ':/output', '--entrypoint', 'python', base, '-m', 'pip', 'download',
          '--only-binary=:all:', '--no-deps', '--dest', '/output', 'mercadopago==3.6.0', timeout=120)
    base_tag = PROJECT + '-orders-base:' + base[7:]
    front_tag = PROJECT + '-orders-web-base:' + front[7:]
    h.run('docker', 'image', 'tag', base, base_tag)
    h.run('docker', 'image', 'tag', front, front_tag)
    (context / 'Dockerfile.backend').write_text('FROM ' + base_tag + '\nCOPY wheels /orders-wheels\n'
        'RUN python -m pip install --no-cache-dir --no-index --no-deps /orders-wheels/*.whl\n'
        'COPY backend /app\n')
    api_tag = PROJECT + '-orders-api:' + target
    h.run('docker', 'build', '--network', 'none', '--pull=false', '-f', str(context / 'Dockerfile.backend'),
          '-t', api_tag, str(context), timeout=300)
    api_image = h.inspect_image(api_tag)
    package_parity(before, json.loads(isolated(h, api_image, METADATA)))
    isolated(h, api_image, "import subprocess; subprocess.run(['python','-m','pip','check'],check=True)")
    isolated(h, api_image, STARTUP)
    print('preparation_stage=api_native_validated', flush=True)
    h.run('docker', 'run', '--rm', '--memory', '2g', '--cpus', '1', '--pids-limit', '512',
          '-v', str(context / 'frontend') + ':/build', '-w', '/build', '--entrypoint', 'sh', front,
          '-c', 'npm ci --include=dev && NODE_ENV=production npm run build', timeout=1200)
    (context / 'Dockerfile.web').write_text('FROM ' + front_tag + '\nWORKDIR /orders-app\n'
        'COPY frontend/.next/standalone ./\nCOPY frontend/.next/static ./.next/static\n'
        'COPY frontend/public ./public\nCMD ["node","server.js"]\n')
    (context / '.dockerignore').write_text('**\n!Dockerfile.web\n!frontend\n!frontend/.next\n'
        '!frontend/.next/standalone\n!frontend/.next/standalone/**\n!frontend/.next/static\n'
        '!frontend/.next/static/**\n!frontend/public\n!frontend/public/**\n')
    web_tag = PROJECT + '-orders-web:' + target
    h.run('docker', 'build', '--network', 'none', '--pull=false', '-f', str(context / 'Dockerfile.web'),
          '-t', web_tag, str(context), timeout=300)
    images = {'api': api_image, 'web': h.inspect_image(web_tag)}
    for image in images.values():
        require(h.run('docker', 'image', 'inspect', '--format', '{{.Architecture}}', image) == 'arm64', 'arquitetura_divergente')
    node = lambda image: h.run('docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'node', image, '--version')
    require(node(images['web']) == node(front), 'node_divergente')
    h.shutdown_rehearsal(inventory, images['api'])
    h.web_shutdown_rehearsal(images['web'])
    callbacks = h.callback_rehearsal(inventory)
    guard = h.guard_rehearsal(inventory, work, images['api'])
    print('preparation_stage=images_shutdown_callbacks_validated', flush=True)
    key_copy = work / 'integration-secrets.backup.env'
    with key_copy.open('xb') as out:
        os.chmod(key_copy, 0o600)
        out.write(KEY_TARGET.read_bytes())
        out.flush()
        os.fsync(out.fileno())
    backup = work / 'database.custom'
    h.dump(backup)
    backup_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
    rehearsal = h.rehearse(backup, key_copy, images['api'])
    receipt = {'format': 1, 'sha': target, 'build_sha': target, 'inventory': inventory, 'baseline_fingerprint': validate_inventory(inventory),
               'pair': pair, 'images': images, 'work': str(work), 'backup': str(backup), 'backup_sha256': backup_hash,
               'key_backup': str(key_copy), 'rehearsal': rehearsal, 'callbacks': callbacks, 'guard': guard,
               'restart_policy_rehearsal': 'passed'}
    save(work / 'prepared.json', receipt, exclusive=True)
    print('prepared_receipt=' + str(work / 'prepared.json'))
    print('approval_fingerprint=' + fingerprint(receipt))
    return receipt


def seal(h, receipt, target):
    """Vincular os mesmos binários ao merge somente se todos os fontes de runtime forem idênticos."""
    require(SHA.fullmatch(target or '') and h.main_sha() == target, 'candidato_nao_e_main')
    h.verify_ci(target)
    work = Path(receipt['work'])
    require(work.parent == STATE and work.name.startswith('orders-prepare-') and not work.is_symlink(), 'artefato_inseguro')
    source = work / 'source'
    h.run('git', '-C', str(source), 'fetch', '--quiet', '--no-tags', 'origin', target, timeout=180)
    require(not h.run('git', '-C', str(source), 'diff', '--name-only', receipt['build_sha'], target,
                      '--', 'backend', 'frontend', 'docker'), 'runtime_integrado_divergente')
    h.run('git', '-C', str(source), 'merge-base', '--is-ancestor', APPROVED_RUNTIME, target)
    h.run('git', '-C', str(source), 'update-ref', 'refs/heads/orders-candidate', target)
    result = {**receipt, 'sha': target, 'inventory': h.inventory()}
    result['baseline_fingerprint'] = validate_inventory(result['inventory'])
    owner_check(h, result['pair'])
    save(work / 'prepared-main.json', result, exclusive=True)
    print('prepared_receipt=' + str(work / 'prepared-main.json'))
    print('approval_fingerprint=' + fingerprint(result))
    return result


def owner_check(h, pair):
    # UUID constructor above makes these two SQL literals unambiguous.
    pair = pilot_pair(pair)
    value = h.pg("SELECT count(*) FROM client c JOIN tenant t ON t.id=c.tenant_id "
                 "WHERE c.id='" + pair['client_id'] + "' AND c.tenant_id='" + pair['tenant_id'] +
                 "' AND t.status='active' AND EXISTS(SELECT 1 FROM tenant_admin a "
                 'JOIN platform_owner p ON p.admin_user_id=a.admin_user_id '
                 'WHERE a.tenant_id=t.id AND a.active)')
    require(value == 1, 'cliente_nao_e_do_proprietario')


def wait_exit(h, ident, service, seconds=120):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        d = h.inspect(ident)['State']
        if d['Status'] != 'running':
            stopped(service, d['Status'], d['ExitCode'])
            return
        time.sleep(0.5)
    raise GateError('timeout_de_parada_sem_sigkill')


def quiesce(h, inventory, *, legacy, record=None):
    require(legacy is True, 'opt_in_legado_obrigatorio')
    # Public ingress is already 503; finish the API's existing requests first.
    for service in ('api', 'worker', 'web'):
        item = inventory['services'][service]
        require(h.inspect(item['id'])['Image'] == item['image'], 'imagem_divergente')
        if record:
            record(item['id'], service)
        h.disable_restart(item)
        h.run('docker', 'kill', '--signal=SIGTERM', item['id'])
        wait_exit(h, item['id'], service)
    idle_queues(h.queues())
    for service in SPECIALIZED:
        item = inventory['services'][service]
        d = h.inspect(item['id'])
        require(d['Image'] == item['image'] and d['Config']['Cmd'] == item['command'], 'identidade_legada_divergente')
        idle_queues(h.queues())
        channel = h.run('docker', 'exec', item['id'], 'python', '-B', '-c',
                        "from pathlib import Path; print(Path('/proc/1/wchan').read_text().strip())")
        require(channel in {'hrtimer_nanosleep', 'do_sys_poll'}, 'worker_legado_nao_ocioso')
        if record:
            record(item['id'], service)
        h.disable_restart(item)
        h.run('docker', 'kill', '--signal=SIGINT', item['id'])
        wait_exit(h, item['id'], service)
    for service in WRITERS + ('web',):
        stopped(service, h.inspect(inventory['services'][service]['id'])['State']['Status'],
                h.inspect(inventory['services'][service]['id'])['State']['ExitCode'])
    idle_queues(h.queues())
    require(h.pg("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                 "AND pid<>pg_backend_pid() AND state IN ('active','idle in transaction','idle in transaction (aborted)')")
            == 0, 'escritor_de_banco_ainda_ativo')


@contextlib.contextmanager
def release_lock():
    import fcntl
    path = STATE / 'production-release.lock'
    require(path.is_file() and not path.is_symlink(), 'lock_inseguro')
    with path.open('rb') as file:
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GateError('outro_release_em_andamento') from None
        yield


def apply(h, receipt, approval, *, legacy):
    require(HASH.fullmatch(approval or '') and fingerprint(receipt) == approval, 'fingerprint_nao_aprovado')
    require(receipt.get('rehearsal') == 'passed', 'ensaio_pendente')
    require(receipt.get('guard') == 'passed', 'ensaio_de_barreira_pendente')
    require(receipt.get('restart_policy_rehearsal') == 'passed', 'ensaio_de_politica_de_reinicio_pendente')
    callbacks = receipt.get('callbacks', {})
    require(all(callbacks.get(k) is True for k in ('retry503', 'retryRefused', 'nonRetryable400'))
            and HASH.fullmatch(callbacks.get('source_sha256', ''))
            and callbacks.get('image') == receipt['inventory']['services']['evolution-api']['image'],
            'ensaio_de_callbacks_pendente')
    require(SHA.fullmatch(receipt.get('sha', '')), 'sha_invalido')
    work = Path(receipt['work'])
    require(work.parent == STATE and work.name.startswith('orders-prepare-') and not work.is_symlink(), 'artefato_inseguro')
    require(Path(receipt['backup']) == work / 'database.custom'
            and Path(receipt['key_backup']) == work / 'integration-secrets.backup.env', 'artefato_inseguro')
    require(validate_inventory(receipt.get('inventory', {})) == receipt['baseline_fingerprint'], 'recibo_divergente')
    require(hashlib.sha256(Path(receipt['backup']).read_bytes()).hexdigest() == receipt['backup_sha256'], 'backup_divergente')
    require(hashlib.sha256(Path(receipt['key_backup']).read_bytes()).hexdigest() == receipt['inventory']['key']['sha256'],
            'backup_do_cofre_divergente')
    require(h.main_sha() == receipt['sha'], 'candidato_nao_e_main')
    h.verify_ci(receipt['sha'])
    with release_lock():
        current = h.inventory()
        require(validate_inventory(current) == receipt['baseline_fingerprint'], 'inventario_mudou')
        owner_check(h, receipt['pair'])
        require(legacy is True, 'opt_in_legado_obrigatorio')
        for image in receipt['images'].values():
            require(h.inspect_image(image) == image, 'imagem_candidata_ausente')
        stage = {'sha': receipt['sha'], 'schema_started': False, 'baseline': current, 'stop_requests': {}}
        def record_stop(ident, service):
            stage['stop_requests'][ident] = service
            save(work / 'stage.json', stage)
        save(work / 'stage.json', stage, exclusive=True)
        marker = STATE / 'app-in-flight.sha'
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as out:
            out.write(receipt['sha'] + '\n')
        try:
            h.deadline = time.monotonic() + 300
            h.maintenance(work, True)
            quiesce(h, current, legacy=legacy, record=record_stop)
            require(h.schema() == [SCHEMA], 'schema_mudou_antes_da_migration')
            before = h.financial()
            # Fresh final backup under the writer barrier; do not replace the rehearsed archive.
            h.dump(work / 'pre-migration.custom')
            require(h.rehearse(work / 'pre-migration.custom', Path(receipt['key_backup']), receipt['images']['api'],
                              expected=before)
                    == 'passed', 'backup_final_sem_restauracao')
            save(work / 'before-financial.json', before, exclusive=True)
            h.activate_source(work / 'source', receipt['sha'])
            overlay = release_overlay(receipt['images'], receipt['pair'])
            for name in ('api', 'worker'):
                overlay['services'][name]['environment']['APP_VERSION'] = receipt['sha']
            save(work / 'active.compose.json', overlay, exclusive=True)
            h.compose(work, 'config', '--quiet')
            stage['schema_started'] = True
            save(work / 'stage.json', stage)
            h.compose(work, 'run', '--rm', '--no-deps', 'api', 'python', '-B', '-m', 'alembic',
                      'upgrade', TARGET_SCHEMA)
            require(h.schema() == [TARGET_SCHEMA] and before == h.financial(), 'schema_ou_financas_divergentes')
            h.compose(work, 'up', '-d', '--no-deps', '--no-build', '--force-recreate', 'api', 'web', 'worker')
            h.wait_new(receipt)
            for name in SPECIALIZED:
                h.start_existing(current['services'][name])
            h.verify_restored(current, specialized_only=True)
            h.maintenance(work, False)
            require(h.health() == [200, 200, 200], 'smoke_final_falhou')
            stage['completed'] = True
            save(work / 'stage.json', stage)
            save(STATE / 'orders-current.identity.json', {'sha': receipt['sha'], 'images': receipt['images'],
                 'schema': TARGET_SCHEMA, 'receipt': str(work / 'prepared-main.json'), 'emission': 'owner_test'}, exclusive=True)
            marker.unlink()
        except Exception:
            h.deadline = None
            if not stage['schema_started']:
                h.restore_before_ddl(current, work)
                marker.unlink()
            else:
                stage['maintenance_rearmed'] = False
                try:
                    h.maintenance(work, True, reuse=True)
                    stage['maintenance_rearmed'] = True
                except GateError:
                    pass
                save(work / 'stage.json', stage)
            # DDL boundary: leave maintenance and marker, never restore 0087 automatically.
            raise
        finally:
            h.deadline = None


def resume(h, receipt, approval):
    """Recuperação da mesma versão 0088 com emissão fechada; não restaura dados."""
    require(HASH.fullmatch(approval or '') and fingerprint(receipt) == approval, 'fingerprint_nao_aprovado')
    work = Path(receipt['work'])
    require(work.parent == STATE and work.name.startswith('orders-prepare-') and not work.is_symlink(), 'artefato_inseguro')
    h.verify_ci(receipt['sha'])
    with release_lock():
        stage = load(work / 'stage.json')
        marker = STATE / 'app-in-flight.sha'
        require(stage.get('sha') == receipt['sha'] and stage.get('schema_started') is True
                and marker.is_file() and not marker.is_symlink() and marker.read_text().strip() == receipt['sha'],
                'recuperacao_nao_corresponde_a_tentativa')
        require(h.schema() == [TARGET_SCHEMA] and h.run('git', 'rev-parse', 'HEAD') == receipt['sha']
                and not h.run('git', 'status', '--porcelain'), 'recuperacao_exige_versao_compativel')
        for image in receipt['images'].values():
            require(h.inspect_image(image) == image, 'imagem_candidata_ausente')
        h.maintenance(work, True, reuse=True)
        for service in ('api', 'worker', 'web'):
            ids = h.run('docker', 'ps', '-aq', '--filter', 'name=^/markina-gallery-' + service + '-1$').split()
            require(len(ids) <= 1, 'servico_duplicado')
            if not ids:
                continue
            d = h.inspect(ids[0])
            require(d['Config'].get('Labels', {}).get('com.docker.compose.project') == PROJECT,
                    'container_fora_do_projeto')
            if d['State']['Status'] == 'running':
                expected = receipt['images']['web' if service == 'web' else 'api']
                require(d['Image'] == expected, 'recuperacao_recusa_binario_antigo_ativo')
                h.run('docker', 'kill', '--signal=SIGTERM', d['Id'])
                wait_exit(h, d['Id'], service)
        overlay = release_overlay(receipt['images'], receipt['pair'], enabled=False)
        for name in ('api', 'worker'):
            overlay['services'][name]['environment']['APP_VERSION'] = receipt['sha']
        save(work / 'active.compose.json', overlay)
        h.compose(work, 'up', '-d', '--no-deps', '--no-build', '--force-recreate', 'api', 'web', 'worker')
        h.wait_new(receipt, enabled=False)
        for name in SPECIALIZED:
            h.start_existing(stage['baseline']['services'][name])
        h.verify_restored(stage['baseline'], specialized_only=True)
        h.maintenance(work, False)
        require(h.health() == [200, 200, 200], 'smoke_de_recuperacao_falhou')
        stage.update(completed=True, recovered_emission_closed=True)
        save(work / 'stage.json', stage)
        save(STATE / 'orders-current.identity.json', {'sha': receipt['sha'], 'images': receipt['images'],
             'schema': TARGET_SCHEMA, 'receipt': str(work / 'prepared-main.json'), 'emission': 'closed'})
        marker.unlink()


def recover(h, receipt, approval):
    """Recuperação após interrupção do executor antes de DDL; não exige rede externa."""
    require(HASH.fullmatch(approval or '') and fingerprint(receipt) == approval, 'fingerprint_nao_aprovado')
    work = Path(receipt['work'])
    require(work.parent == STATE and work.name.startswith('orders-prepare-') and not work.is_symlink(), 'artefato_inseguro')
    with release_lock():
        stage = load(work / 'stage.json')
        marker = STATE / 'app-in-flight.sha'
        require(stage.get('sha') == receipt['sha'] and stage.get('schema_started') is False
                and marker.is_file() and not marker.is_symlink() and marker.read_text().strip() == receipt['sha'],
                'recuperacao_nao_corresponde_a_tentativa')
        require(h.schema() == [SCHEMA], 'recuperacao_exige_schema_original')
        h.restore_before_ddl(stage['baseline'], work)
        stage['recovered_before_ddl'] = True
        save(work / 'stage.json', stage)
        marker.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inventory', 'prepare', 'seal', 'apply', 'recover', 'resume'), nargs='?', default='inventory')
    parser.add_argument('--sha')
    parser.add_argument('--pair', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--approval-fingerprint')
    parser.add_argument('--allow-legacy-interruption', action='store_true')
    args = parser.parse_args()
    h = Host()
    if args.mode == 'inventory':
        data = h.inventory()
        print(json.dumps(data, sort_keys=True))
        print('inventory_fingerprint=' + validate_inventory(data))
    elif args.mode == 'prepare':
        require(args.pair is not None and args.sha is not None, 'sha_e_par_obrigatorios')
        prepare(h, args.sha, load(args.pair))
    else:
        require(args.receipt is not None, 'recibo_obrigatorio')
        receipt = load(args.receipt)
        if args.mode == 'seal':
            seal(h, receipt, args.sha)
        elif args.mode == 'recover':
            recover(h, receipt, args.approval_fingerprint)
        elif args.mode == 'resume':
            resume(h, receipt, args.approval_fingerprint)
        else:
            apply(h, receipt, args.approval_fingerprint, legacy=args.allow_legacy_interruption)


if __name__ == '__main__':
    try:
        main()
    except GateError as error:
        raise SystemExit('orders-release: ' + str(error)) from None
