#!/usr/bin/env python3
"""Atualizacao pontual do piloto Orders existente 0088 -> 0089.

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

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
PROJECT = 'markina-gallery'
ORIGIN = 'https://markina.pickyourpic.com.br'
REPOSITORY = 'https://github.com/conradodeita/markina-gallery.git'
SCHEMA = '20261024_0088'
TARGET_SCHEMA = '20261025_0089'
LIVE_SCHEMA = '20261026_0090'
LIVE_MINIMUM_SHA = '0dd015a62447e0c8d4c6af16b381140c8118f2ec'
BASELINE_SHA = '9bd66c48d7d43462886652b8fe85fdcbff877f64'
BASELINE_IDENTITY_SHA256 = 'bb4998f77656691b2436c1d5ec635a9cf0e914c1d453eb4ad7595f2f318c8438'
BASELINE_RECEIPT_SHA256 = '40d03be0c88f84ad634838837380e19622eac4a0eee0b6813be278d85a1dc289'
BASELINE_ORDERS_WORK = STATE / 'orders-prepare-ed5c1242020a45ce8772d68756a4c363'
BASELINE_ORDERS_OVERLAY = BASELINE_ORDERS_WORK / 'active.compose.json'
BASELINE_OVERLAY_SHA256 = 'd7458bb91b221de791692efe4d09f86fd7e3916c4610234a9edfc010277ed490'
BASELINE_IMAGES = {
    'api': 'sha256:0b4d4fcd1f0a23f958c18db5d4dd661739dc027fdccd5c3692861c132bfd6aa8',
    'web': 'sha256:360f1ca8d6422d4a61adade971acb849a0d73c95b0a25cc2d5cf05443d4b5f10',
}
APPROVED_RUNTIME = 'b69a95c526912d725863a57a13f8735a62f671ed'
PILLOW_SOURCE = '3d2ac6e7fb2e621e6ad468f9fd1233ffc909c7a3'
PILLOW_APPROVAL = 'cf1c0d5227f9218519acd741ffe596032dc38c932b90ddb79ec4469fa70ab3a9'
PILLOW_WORK = STATE / 'pillow-prepare-20261025-01'
PILLOW_OVERLAY = PILLOW_WORK / 'active.compose.json'
PILLOW_RECEIPT = PILLOW_WORK / 'published.json'
PILLOW_IMAGES = {
    'face-index-worker': 'sha256:1b34cf3b21957c3e1cd26e84ca462dd66196579809dcb0a8981b40c317613e22',
    'face-search-worker': 'sha256:ae32bc36c0d6b0eaca0bba0b86ff4e4647486cd66a6882141e735575041ce6be',
    'face-maintenance-worker': 'sha256:dd9a526e220a6bd8fd79dadb55ea8b28df20f7d56ccce4908a75514f998cd6c3',
    'face-gemma-index-worker': 'sha256:adca63778e0da8daebc56cf3f1a87fceefac9bf1d688d6c237d34d260ff56117',
    'preview-adjustment-worker': 'sha256:c7ded32123eeaf348ae2c9b911797edd017949664633dfe1ccb2a77338a28e5e',
    'raw-development-worker': 'sha256:ec62cb836dad36b18f59340ab3774247d5f77ebc6ca57ebd6ea26fa314481b03',
}
SHA = re.compile(r'[0-9a-f]{40}')
HASH = re.compile(r'[0-9a-f]{64}')
IMAGE = re.compile(r'sha256:[0-9a-f]{64}')
SPECIALIZED = ('face-index-worker', 'face-gemma-index-worker', 'face-search-worker',
               'face-maintenance-worker', 'preview-adjustment-worker', 'raw-development-worker')
WRITERS = ('api', 'worker') + SPECIALIZED
SERVICES = set(WRITERS) | {'web', 'nginx', 'db', 'redis', 'evolution-api', 'evolution-db', 'evolution-redis'}
EXTRAS = (STATE / 'branding.compose.yml', ROOT / 'docker/docker-compose.raw-development.yml',
          ROOT / 'docker/docker-compose.preview-adjustment.yml', ROOT / 'docker/docker-compose.system-monitor.yml',
    STATE / 'system-monitor.compose.yml', PILLOW_OVERLAY, BASELINE_ORDERS_OVERLAY)
CONFIGS = (ROOT / 'docker/docker-compose.yml',) + EXTRAS
KEY_BINDING = ROOT / 'docker/.env.integration-secrets'
KEY_TARGET = STATE / 'integration-secrets.env'
PENDING = ('app-in-flight.sha', 'app-rollback-in-flight.sha', 'web-in-flight.sha',
           'web-pending.identity', 'infinitepay-retirement-in-flight.sha', 'pillow-in-flight.json')
LIVE_PENDING = PENDING + ('orders-in-flight.json', 'preview-adjustment-migration-in-flight.json',
                          'preview-adjustment-migration-in-flight.json.tmp')
FINANCIAL = ('sale_order', 'sale_order_item', 'payment_group', 'provider_payment',
             'provider_payment_attempt', 'provider_payment_receipt', 'provider_payment_correction',
             'payment_confirmation_correction', 'payment_communication', 'global_pix_settings',
             'notification_delivery', 'whatsapp_delivery', 'mercadopago_account',
             'mercadopago_payment', 'mercadopago_webhook', 'payment_preferences')
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
    require(before['packages'].get('mercadopago') == '3.6.0'
            and after['packages'] == before['packages'], 'distribuicoes_divergentes')


def validate_inventory(data):
    require(data.get('host') == 'clearbudget-vnic' and data.get('root') == str(ROOT), 'host_ou_raiz_divergente')
    require(data.get('project') == PROJECT and data.get('origin') == ORIGIN, 'projeto_ou_origem_divergente')
    require(data.get('checkout_sha') == BASELINE_SHA and data.get('clean') is True, 'checkout_divergente')
    require(data.get('schema') == SCHEMA and data.get('orders_tables') == 4, 'schema_divergente')
    identity = data.get('orders_identity', {})
    require(identity.get('sha256') == BASELINE_IDENTITY_SHA256
            and identity.get('overlay_sha256') == BASELINE_OVERLAY_SHA256
            and identity.get('receipt_sha256') == BASELINE_RECEIPT_SHA256, 'identidade_orders_divergente')
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
    require(services['worker'].get('version') == data['checkout_sha'], 'versao_ativa_divergente')
    for name in ('api', 'worker', 'web'):
        require(services[name]['image'] == BASELINE_IMAGES['web' if name == 'web' else 'api']
                and str(BASELINE_ORDERS_OVERLAY) in services[name].get('compose_files', '').split(','),
                'runtime_orders_divergente')
    require(set(data.get('files', {})) == {str(p) for p in CONFIGS + (ROOT / 'docker/.env.homolog',)},
            'configuracao_incompleta')
    require(all(HASH.fullmatch(h) for h in data['files'].values()), 'hash_de_configuracao_invalido')
    require(data.get('https') == [200, 200, 200], 'https_indisponivel')
    pillow = data.get('pillow', {})
    require(pillow.get('source_sha') == PILLOW_SOURCE and pillow.get('approval') == PILLOW_APPROVAL
            and HASH.fullmatch(pillow.get('receipt_sha256', '')), 'publicacao_pillow_nao_comprovada')
    for service, image in PILLOW_IMAGES.items():
        require(services[service]['image'] == image, 'imagem_pillow_divergente')
        require(str(PILLOW_OVERLAY) in (services[service].get('compose_files') or '').split(','),
                'overlay_pillow_ausente')
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
    def current_test_pair(self):
        path = STATE / 'orders-current.identity.json'
        require(path.resolve(strict=True) == path and not path.is_symlink(), 'identidade_orders_insegura')
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600, 'identidade_orders_insegura')
        identity = load(path)
        require(identity.get('emission') == 'owner_test' and identity.get('schema') == TARGET_SCHEMA,
                'identidade_orders_divergente')
        receipt_path = Path(identity.get('receipt', ''))
        require(receipt_path.is_absolute() and receipt_path.parent.parent == STATE
                and receipt_path.name == 'prepared-main.json' and not receipt_path.is_symlink()
                and receipt_path.resolve(strict=True) == receipt_path, 'recibo_orders_inseguro')
        receipt_info = receipt_path.lstat()
        require(stat.S_ISREG(receipt_info.st_mode) and receipt_info.st_nlink == 1
                and receipt_info.st_uid == os.getuid() and stat.S_IMODE(receipt_info.st_mode) == 0o600,
                'recibo_orders_inseguro')
        receipt = load(receipt_path)
        require(receipt.get('sha') == identity.get('sha') and receipt.get('images') == identity.get('images'),
                'recibo_orders_divergente')
        pair = pilot_pair(receipt.get('pair'))
        pair_fingerprint = hashlib.sha256(json.dumps(pair, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return pair, pair_fingerprint

    def published_orders(self):
        path = STATE / 'orders-current.identity.json'
        require(path.resolve(strict=True) == path, 'identidade_orders_insegura')
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid()
                and stat.S_IMODE(info.st_mode) == 0o600, 'identidade_orders_insegura')
        identity_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        require(identity_hash == BASELINE_IDENTITY_SHA256, 'identidade_orders_divergente')
        identity = load(path)
        receipt_path = BASELINE_ORDERS_WORK / 'prepared-main.json'
        require(identity.get('sha') == BASELINE_SHA and identity.get('schema') == SCHEMA
                and identity.get('images') == BASELINE_IMAGES and identity.get('receipt') == str(receipt_path)
                and identity.get('emission') == 'owner_test', 'identidade_orders_divergente')
        receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        require(receipt_hash == BASELINE_RECEIPT_SHA256, 'recibo_orders_divergente')
        receipt = load(receipt_path)
        require(receipt.get('sha') == BASELINE_SHA and receipt.get('images') == BASELINE_IMAGES,
                'recibo_orders_divergente')
        overlay_hash = hashlib.sha256(BASELINE_ORDERS_OVERLAY.read_bytes()).hexdigest()
        require(BASELINE_ORDERS_OVERLAY.resolve(strict=True) == BASELINE_ORDERS_OVERLAY
                and overlay_hash == BASELINE_OVERLAY_SHA256, 'overlay_orders_divergente')
        return identity, pilot_pair(receipt['pair']), {'sha256': identity_hash,
            'overlay_sha256': overlay_hash,
            'receipt_sha256': receipt_hash}

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
            result[table] = self.pg("SELECT json_build_object('count',count(*),'digest',"
                "md5(coalesce(string_agg(md5(to_jsonb(t)::text),'' ORDER BY "
                "to_jsonb(t)::text),''))) FROM " + table + ' t', db)
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

    def public_ready(self):
        end = time.monotonic() + 15
        while self.health() != [200, 200, 200]:
            require(time.monotonic() < end, 'smoke_publico_persistente')
            time.sleep(0.5)

    def pillow(self):
        proof = load(PILLOW_RECEIPT)
        expected = {'services': {name: {'image': image} for name, image in PILLOW_IMAGES.items()}}
        require(proof.get('security_fixed') is True and proof.get('financial_preserved') is True
                and proof.get('fingerprint') == PILLOW_APPROVAL and proof.get('source_sha') == PILLOW_SOURCE
                and proof.get('schema') == ['20261022_0087'] and proof.get('services') == expected,
                'recibo_pillow_divergente')
        require(load(PILLOW_OVERLAY) == expected, 'overlay_pillow_divergente')
        return {'source_sha': PILLOW_SOURCE, 'approval': PILLOW_APPROVAL,
                'receipt_sha256': hashlib.sha256(PILLOW_RECEIPT.read_bytes()).hexdigest()}

    def inventory(self):
        require(socket.gethostname() == 'clearbudget-vnic' and ROOT.resolve() == ROOT, 'host_ou_raiz_divergente')
        current_schema = self.schema()
        if current_schema == [LIVE_SCHEMA]:
            return self.live_gate_inventory()
        _, pair, orders_identity = self.published_orders()
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
            if name in ('api', 'worker'):
                require(env.get('MERCADOPAGO_ALLOW_LIVE_PAYMENTS') == 'false', 'cobrancas_reais_nao_bloqueadas')
            if name == 'api':
                try:
                    allowed = json.loads(env.get('MERCADOPAGO_TEST_CUSTOMERS', '[]'))
                except ValueError:
                    raise GateError('par_de_teste_divergente') from None
                require(allowed == [pair], 'par_de_teste_divergente')
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
                'pending': [n for n in PENDING if (STATE / n).exists()], 'https': self.health(),
                'pillow': self.pillow(), 'orders_identity': orders_identity}
        # Free space is a gate, not a fingerprint that changes with unrelated disk writes.
        require(data['free_bytes'] >= 8 * 1024**3, 'espaco_insuficiente')
        data['free_bytes'] = 8 * 1024**3
        validate_inventory(data)
        return data

    def live_gate_inventory(self):
        """Snapshot read-only of the deployed 0090 runtime, with tenant counts only."""
        require(self.run('git', 'remote', 'get-url', 'origin') in {
            REPOSITORY, REPOSITORY[:-4], 'git@github.com:conradodeita/markina-gallery.git'},
            'repositorio_divergente')
        main_sha = self.main_sha()
        checkout_sha = self.run('git', 'rev-parse', 'HEAD')
        require(SHA.fullmatch(main_sha) and SHA.fullmatch(checkout_sha), 'sha_invalido')
        # The inventory script is fetched from the exact current-main SHA and its
        # blob is pinned by the forced-command wrapper. The deployed source tree
        # may legitimately lag support-only commits; it must remain clean and be
        # an ancestor of that reviewed candidate.
        self.run('git', 'merge-base', '--is-ancestor', checkout_sha, main_sha)
        require(not self.run('git', 'status', '--porcelain'), 'checkout_sujo')
        active_versions = []
        ids = self.run('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + PROJECT).split()
        services = {}
        api_env = None
        for ident in ids:
            d = self.inspect(ident)
            labels = d['Config'].get('Labels') or {}
            name = labels.get('com.docker.compose.service')
            require(name in SERVICES and name not in services, 'servico_duplicado_ou_desconhecido')
            env = dict(x.split('=', 1) for x in d['Config'].get('Env', []) if '=' in x)
            status = d['State'].get('Status')
            health = d['State'].get('Health', {}).get('Status')
            require(status == 'running' and health in (None, 'healthy'), 'servico_nao_saudavel')
            ports = d['NetworkSettings'].get('Ports') or {}
            published = {port: bindings for port, bindings in ports.items() if bindings}
            expected = {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if name == 'nginx' else {}
            require(published == expected, 'porta_publicada_divergente')
            services[name] = {
                'image': d['Image'], 'status': status, 'health': health,
                'version': env.get('APP_VERSION'), 'ports': published,
                'compose_files': labels.get('com.docker.compose.project.config_files'),
                'config_hash': labels.get('com.docker.compose.config-hash'),
            }
            if name in {'api', 'web', 'worker'}:
                active_versions.append(env.get('APP_VERSION'))
            if name == 'api':
                api_env = env
        require(set(services) == SERVICES and api_env is not None, 'servicos_incompletos')
        require(api_env.get('APP_ENV') == 'production', 'ambiente_divergente')
        gate = api_env.get('MERCADOPAGO_ALLOW_LIVE_PAYMENTS')
        require(gate in {'true', 'false'}, 'gate_live_invalido')
        try:
            pairs = json.loads(api_env.get('MERCADOPAGO_TEST_CUSTOMERS', ''))
            require(isinstance(pairs, list) and len(pairs) == 1, 'par_de_teste_divergente')
            configured_pair = pilot_pair(pairs[0])
        except (ValueError, TypeError, AttributeError):
            raise GateError('par_de_teste_divergente') from None
        current_pair, pair_fingerprint = self.current_test_pair()
        require(configured_pair == current_pair, 'par_de_teste_divergente')
        require(len(active_versions) == 3 and len(set(active_versions)) == 1
                and isinstance(active_versions[0], str) and SHA.fullmatch(active_versions[0]),
                'versao_ativa_divergente')
        active_sha = active_versions[0]
        self.run('git', 'merge-base', '--is-ancestor', LIVE_MINIMUM_SHA, active_sha)
        self.run('git', 'merge-base', '--is-ancestor', active_sha, checkout_sha)
        require(self.schema() == [LIVE_SCHEMA], 'schema_divergente')
        key_probe = "from app.integration_secrets import IntegrationCipher; IntegrationCipher(); print('valid')"
        require(self.run('docker', 'exec', next(i for i in ids if
                self.inspect(i)['Config'].get('Labels', {}).get('com.docker.compose.service') == 'api'),
                'python', '-B', '-c', key_probe) == 'valid', 'cofre_indisponivel')
        matrix = self.pg("""SELECT json_build_object(
          'preference_tenants', count(*),
          'pix_enabled', count(*) FILTER (WHERE pix_enabled),
          'mercadopago_enabled', count(*) FILTER (WHERE mercadopago_enabled),
          'mp_enabled_production_active', count(*) FILTER (WHERE mercadopago_enabled
            AND account_status = 'active' AND test_account IS FALSE),
          'mp_enabled_test_active', count(*) FILTER (WHERE mercadopago_enabled
            AND account_status = 'active' AND test_account IS TRUE),
          'mp_enabled_unavailable', count(*) FILTER (WHERE mercadopago_enabled
            AND (account_status IS DISTINCT FROM 'active' OR test_account IS NULL)),
          'mp_disabled', count(*) FILTER (WHERE NOT mercadopago_enabled)
        ) FROM (
          SELECT p.tenant_id, p.pix_enabled, p.mercadopago_enabled,
                 a.status AS account_status, a.test_account
          FROM payment_preferences p
          LEFT JOIN mercadopago_account a ON a.id = p.account_id AND a.tenant_id = p.tenant_id
        ) tenant_settings""")
        require(isinstance(matrix, dict) and set(matrix) == {
            'preference_tenants', 'pix_enabled', 'mercadopago_enabled',
            'mp_enabled_production_active', 'mp_enabled_test_active',
            'mp_enabled_unavailable', 'mp_disabled'}
            and all(type(value) is int and value >= 0 for value in matrix.values()),
            'matriz_tenants_invalida')
        https = self.health()
        require(https == [200, 200, 200], 'smoke_https_falhou')
        pending = [name for name in LIVE_PENDING if (STATE / name).exists()]
        require(not pending, 'operacao_pendente')
        data = {
            'inventory_kind': 'mercadopago-live-gate-read-only', 'checkout_sha': checkout_sha,
            'main_sha': main_sha, 'active_sha': active_sha, 'schema': LIVE_SCHEMA, 'project': PROJECT,
            'origin': ORIGIN, 'nginx_bind': '127.0.0.1:8080', 'https': https,
            'live_gate': gate, 'test_allowlist_pairs': len(pairs),
            'test_allowlist_pair_fingerprint': pair_fingerprint,
            'tenant_configuration_matrix': matrix, 'services': services, 'pending_markers': pending,
        }
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
        from prepare_emergency_api_image import maintenance_configuration

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
            code = ("import subprocess\nfrom sqlalchemy import select\n"
                    "from app.auth import SessionLocal,MercadoPagoAccount\n"
                    "from app.integration_secrets import IntegrationCipher,SecretEnvelope\n"
                    "c=IntegrationCipher()\nwith SessionLocal() as db:\n"
                    " for account in db.scalars(select(MercadoPagoAccount)):\n"
                    "  for envelope in (account.access_token_envelope,account.webhook_secret_envelope):\n"
                    "   assert c.decrypt(SecretEnvelope.from_payload(envelope),"
                    "tenant_id=account.tenant_id,credential_id=account.id)\n"
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
        from prepare_emergency_api_image import maintenance_configuration

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
        self.public_ready()


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
    from prepare_emergency_api_image import METADATA, STARTUP

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
    # The SDK is already deployed. Reuse every installed distribution unchanged.
    base = inventory['services']['api']['image']
    front = inventory['services']['web']['image']
    before = json.loads(isolated(h, base, METADATA))
    package_parity(before, before)
    base_tag = PROJECT + '-orders-base:' + base[7:]
    front_tag = PROJECT + '-orders-web-base:' + front[7:]
    h.run('docker', 'image', 'tag', base, base_tag)
    h.run('docker', 'image', 'tag', front, front_tag)
    (context / 'Dockerfile.backend').write_text('FROM ' + base_tag + '\nCOPY backend /app\n')
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
    previous_identity = work / 'baseline-orders.identity.json'
    with previous_identity.open('xb') as out:
        os.chmod(previous_identity, 0o600)
        out.write((STATE / 'orders-current.identity.json').read_bytes())
        out.flush()
        os.fsync(out.fileno())
    require(hashlib.sha256(previous_identity.read_bytes()).hexdigest() == BASELINE_IDENTITY_SHA256,
            'identidade_orders_mudou')
    h.dump(backup)
    backup_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
    rehearsal = h.rehearse(backup, key_copy, images['api'])
    receipt = {'format': 2, 'operation': 'orders-0088-to-0089', 'previous_identity': str(previous_identity),
               'sha': target, 'build_sha': target, 'inventory': inventory, 'baseline_fingerprint': validate_inventory(inventory),
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
    require(pair == h.published_orders()[1], 'par_de_teste_divergente')
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


def validate_upgrade_receipt(receipt):
    require(receipt.get('format') == 2 and receipt.get('operation') == 'orders-0088-to-0089',
            'recibo_de_atualizacao_obrigatorio')
    previous = Path(receipt.get('previous_identity', ''))
    work = Path(receipt['work'])
    require(previous == work / 'baseline-orders.identity.json' and not previous.is_symlink()
            and previous.is_file() and previous.stat().st_nlink == 1,
            'copia_da_identidade_insegura')
    info = previous.stat()
    if os.name == 'posix':
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600,
                'copia_da_identidade_insegura')
    require(hashlib.sha256(previous.read_bytes()).hexdigest() == BASELINE_IDENTITY_SHA256,
            'copia_da_identidade_divergente')


def publish_identity(receipt, *, emission):
    validate_upgrade_receipt(receipt)
    path = STATE / 'orders-current.identity.json'
    current = load(path)
    require(hashlib.sha256(path.read_bytes()).hexdigest() == BASELINE_IDENTITY_SHA256
            or (current.get('sha') == receipt['sha'] and current.get('schema') == TARGET_SCHEMA
                and current.get('images') == receipt['images']), 'identidade_orders_mudou')
    save(path, {'sha': receipt['sha'], 'images': receipt['images'], 'schema': TARGET_SCHEMA,
                'receipt': str(Path(receipt['work']) / 'prepared-main.json'), 'emission': emission})


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
    validate_upgrade_receipt(receipt)
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
            h.public_ready()
            stage['completed'] = True
            save(work / 'stage.json', stage)
            publish_identity(receipt, emission='owner_test')
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
            # DDL boundary: leave maintenance and marker, never restore 0088 automatically.
            raise
        finally:
            h.deadline = None


def resume(h, receipt, approval):
    """Recuperação da versão 0089 com emissão fechada; não restaura dados."""
    require(HASH.fullmatch(approval or '') and fingerprint(receipt) == approval, 'fingerprint_nao_aprovado')
    validate_upgrade_receipt(receipt)
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
        h.public_ready()
        stage.update(completed=True, recovered_emission_closed=True)
        save(work / 'stage.json', stage)
        publish_identity(receipt, emission='closed')
        marker.unlink()


def recover(h, receipt, approval):
    """Recuperação após interrupção do executor antes de DDL; não exige rede externa."""
    require(HASH.fullmatch(approval or '') and fingerprint(receipt) == approval, 'fingerprint_nao_aprovado')
    validate_upgrade_receipt(receipt)
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
        if args.sha is not None:
            require(SHA.fullmatch(args.sha), 'sha_invalido')
            require(h.main_sha() == args.sha, 'candidato_nao_e_main')
        data = h.inventory()
        if args.sha is not None:
            data['target_sha'] = args.sha
        print(json.dumps(data, sort_keys=True))
        result_fingerprint = (fingerprint(data) if data.get('inventory_kind') ==
                              'mercadopago-live-gate-read-only' else validate_inventory(data))
        print('inventory_fingerprint=' + result_fingerprint)
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
