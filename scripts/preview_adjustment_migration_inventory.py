#!/usr/bin/env python3
"""Inventário read-only e sanitizado para o release único de schema 0090."""
from __future__ import annotations

import hashlib
import contextlib
import json
import os
import re
import socket
import stat
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path('/opt/markina-gallery')
STATE = Path('/var/lib/markina-gallery/deploy-state')
BACKUPS = Path('/var/lib/markina-gallery/backups')
PROJECT = 'markina-gallery'
PUBLIC_URL = 'https://markina.pickyourpic.com.br'
BASE_SHA = 'c1944189761799be96eeeb921cad9906484d8b09'
TARGET_SHA = '0dd015a62447e0c8d4c6af16b381140c8118f2ec'
BASE_SCHEMA = '20261025_0089'
TARGET_SCHEMA = '20261026_0090'
MIGRATION = 'backend/migrations/versions/20261026_0090_preview_adjustment_strength_100.py'
SHA1 = re.compile(r'^[0-9a-f]{40}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
IMAGE = re.compile(r'^sha256:[0-9a-f]{64}$')
REQUIRED_SERVICES = {'api', 'web', 'worker', 'db', 'redis', 'nginx'}
KNOWN_SERVICES = REQUIRED_SERVICES | {'migrate', 'seed-admin', 'evolution-api', 'evolution-db',
                                     'evolution-redis', 'face-search-worker', 'face-index-worker',
                                     'face-maintenance-worker', 'preview-adjustment-worker'}
DOCKER_STATES = {'created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead'}
PENDING_MARKERS = ('web-in-flight.sha', 'app-in-flight.sha', 'app-rollback-in-flight.sha',
                   'web-pending.identity', 'infinitepay-retirement-in-flight.sha',
                   'pillow-in-flight.json', 'orders-in-flight.json',
                   'preview-adjustment-migration-in-flight.json',
                   'preview-adjustment-migration-in-flight.json.tmp',
                   'preview-adjustment-migration-0090-published.json')


class InventoryError(RuntimeError):
    """Erro sanitizado: não propaga saída de subprocessos nem conteúdo sensível."""


def require(condition: bool, category: str) -> None:
    if not condition:
        raise InventoryError(category)


def web_classification(container: dict[str, Any]) -> dict[str, str]:
    """Classify only fixed, non-sensitive Docker metadata without echoing raw values."""
    labels = container.get('Config', {}).get('Labels') or {}
    restart = container.get('HostConfig', {}).get('RestartPolicy', {}).get('Name')
    oneoff = labels.get('com.docker.compose.oneoff')
    number = labels.get('com.docker.compose.container-number')
    ident = container.get('Id')
    image_reference = container.get('Config', {}).get('Image')
    exit_code = container.get('State', {}).get('ExitCode')
    mounts = container.get('Mounts')
    mounts_valid = isinstance(mounts, list) and all(isinstance(m, dict) and type(m.get('RW')) is bool for m in mounts)
    if isinstance(image_reference, str) and image_reference in ('markina-gallery-web', 'markina-gallery-web:latest'):
        image_kind = 'markina_web'
    elif isinstance(image_reference, str) and re.search(r'(^|[/:_.-])(test|teste|synthetic)([/:_.-]|$)', image_reference, re.I):
        image_kind = 'nome_sugere_teste'
    else:
        image_kind = 'outra_ou_ausente'
    return {
        'id_prefixo': ident[:12] if isinstance(ident, str) and SHA256.fullmatch(ident) else 'desconhecido',
        'nome_canonico': 'sim' if container.get('Name') == '/markina-gallery-web-1' else 'nao',
        'oneoff': ({'True': 'sim', 'False': 'nao', 'true': 'sim', 'false': 'nao'}.get(oneoff, 'outro')
                   if isinstance(oneoff, str) else 'ausente_ou_outro'),
        'numero': 'padrao' if number == '1' else ('ausente' if number is None else 'outro'),
        'restart': restart if restart in ('no', 'always', 'unless-stopped', 'on-failure') else 'desconhecido',
        'config_hash': 'presente' if isinstance(labels.get('com.docker.compose.config-hash'), str)
                       and SHA256.fullmatch(labels['com.docker.compose.config-hash']) else 'ausente_ou_invalido',
        'referencia_imagem': image_kind,
        'codigo_saida': str(exit_code) if type(exit_code) is int and 0 <= exit_code <= 255 else 'desconhecido',
        'montagens_gravaveis': str(sum(m['RW'] for m in mounts)) if mounts_valid and len(mounts) <= 100 else 'desconhecido',
    }


def validate_service_identity(name: object, services: dict[str, Any], state: object,
                              previous: dict[str, Any] | None = None,
                              current: dict[str, Any] | None = None,
                              compose_version: str = 'desconhecida') -> None:
    """Report bounded, safe diagnostics while preserving the duplicate guard."""
    if not isinstance(name, str) or not name:
        raise InventoryError('servico_markina_duplicado;servico=ausente')
    if name in services:
        safe_name = name if name in KNOWN_SERVICES else 'desconhecido'
        old_state = services[name].get('status')
        old_state = old_state if isinstance(old_state, str) and old_state in DOCKER_STATES else 'desconhecido'
        new_state = state if isinstance(state, str) and state in DOCKER_STATES else 'desconhecido'
        detail = ''
        if name == 'web' and previous is not None and current is not None:
            previous_image, current_image = previous.get('Image'), current.get('Image')
            valid_images = all(isinstance(image, str) and IMAGE.fullmatch(image)
                               for image in (previous_image, current_image))
            same = ('sim' if previous_image == current_image else 'nao') if valid_images else 'desconhecido'
            safe = {'primeiro': web_classification(previous), 'segundo': web_classification(current),
                    'mesma_imagem': same,
                    'compose_version': compose_version if isinstance(compose_version, str)
                    and re.fullmatch(r'v?\d{1,3}\.\d{1,3}\.\d{1,3}', compose_version) else 'desconhecida'}
            detail = ';diagnostico=' + json.dumps(safe, sort_keys=True, separators=(',', ':'))
        raise InventoryError(f'servico_markina_duplicado;servico={safe_name};'
                             f'contagem_ao_menos=2;estados={old_state},{new_state}' + detail)


def canonical_fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def select_candidate_ci(runs: list[dict[str, Any]]) -> dict[str, Any]:
    relevant = [run for run in runs if run.get('path') == '.github/workflows/ci.yml'
                and run.get('head_sha') == TARGET_SHA and run.get('event') == 'push'
                and run.get('head_branch') == 'main']
    require(bool(relevant), 'ci_candidato_ausente')
    latest = max(relevant, key=lambda run: (run.get('run_number', 0), run.get('run_attempt', 1)))
    require(latest.get('status') == 'completed' and latest.get('conclusion') == 'success'
            and isinstance(latest.get('id'), int), 'ci_candidato_nao_verde')
    return {'run_id': latest['id'], 'conclusion': latest['conclusion']}


def validate_inventory(value: dict[str, Any]) -> tuple[bool, str, str | None]:
    fields = {'host', 'project', 'root', 'repository', 'support_sha', 'target_sha', 'main_sha',
              'checkout_sha', 'active_sha', 'checkout_clean', 'database_revision', 'migration_chain',
              'public_url', 'nginx_bind', 'ci', 'services', 'compose_files', 'compose_order',
              'pending_markers', 'backup', 'https_health'}
    if not isinstance(value, dict) or set(value) != fields:
        return False, 'inventario_com_campos_ausentes_ou_extras', None
    for name in ('support_sha', 'target_sha', 'main_sha', 'checkout_sha', 'active_sha'):
        if not isinstance(value[name], str) or not SHA1.fullmatch(value[name]):
            return False, f'sha_invalido:{name}', None
    for name, expected in (('host', 'clearbudget-vnic'), ('project', PROJECT), ('root', str(ROOT)),
                           ('repository', 'conradodeita/markina-gallery'),
                           ('target_sha', TARGET_SHA), ('main_sha', value['support_sha']),
                           ('checkout_sha', value['active_sha']), ('checkout_clean', True),
                           ('database_revision', BASE_SCHEMA), ('public_url', PUBLIC_URL),
                           ('nginx_bind', '127.0.0.1:8080->80/tcp')):
        if value[name] != expected:
            return False, f'inventario_diverge:{name}', None
    chain = value['migration_chain']
    if chain != {'base_revision_present': True, 'target_revision': TARGET_SCHEMA,
                 'target_down_revision': BASE_SCHEMA, 'single_head': True}:
        return False, 'cadeia_alembic_divergente', None
    ci = value['ci']
    if not isinstance(ci, dict) or set(ci) != {'run_id', 'conclusion'} \
            or not isinstance(ci['run_id'], int) or ci['run_id'] <= 0 or ci['conclusion'] != 'success':
        return False, 'ci_candidato_nao_verde', None
    services = value['services']
    if not isinstance(services, dict) or not REQUIRED_SERVICES.issubset(services) or not services:
        return False, 'servicos_incompletos', None
    for name, item in services.items():
        if not isinstance(name, str) or not isinstance(item, dict) or set(item) != {
                'container_id', 'image', 'status', 'health', 'config_hash', 'version', 'compose_files',
                'ports', 'restart_policy', 'started_at'}:
            return False, 'identidade_servico_incompleta', None
        expected_ports = {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if name == 'nginx' else {}
        if (not isinstance(item['container_id'], str) or not SHA256.fullmatch(item['container_id'])
                or not isinstance(item['image'], str) or not IMAGE.fullmatch(item['image'])
                or item['status'] != 'running' or item['health'] not in ('healthy', 'none')
                or (item['health'] == 'none' and name in REQUIRED_SERVICES)
                or not isinstance(item['config_hash'], str) or not SHA256.fullmatch(item['config_hash'])
                or not isinstance(item['compose_files'], list)
                or not isinstance(item['started_at'], str) or not item['started_at']
                or item['ports'] != expected_ports):
            return False, 'servico_ausente_ou_nao_saudavel', None
        restart = item['restart_policy']
        if (not isinstance(restart, dict) or set(restart) != {'Name', 'MaximumRetryCount'}
                or restart['Name'] not in ('no', 'unless-stopped', 'always', 'on-failure')
                or not isinstance(restart['MaximumRetryCount'], int)
                or isinstance(restart['MaximumRetryCount'], bool) or restart['MaximumRetryCount'] < 0):
            return False, 'politica_restart_invalida', None
        if name in ('api', 'worker') and item['version'] != value['active_sha']:
            return False, 'runtime_markina_divergente', None
    compose = value['compose_files']
    order = value['compose_order']
    if (not isinstance(compose, dict) or 'docker/docker-compose.yml' not in compose
            or any(not isinstance(path, str) or not path.startswith(('docker/', '/var/lib/markina-gallery/deploy-state/'))
                   or not isinstance(digest, str) or not SHA256.fullmatch(digest) for path, digest in compose.items())):
        return False, 'compose_ativo_invalido', None
    if (not isinstance(order, list) or not order or not order[0].endswith('docker/docker-compose.yml')
            or any(not isinstance(path, str) or not path for path in order)
            or any(item['compose_files'] != order for item in services.values())):
        return False, 'ordem_compose_ativa_invalida', None
    if value['pending_markers'] != []:
        return False, 'operacao_producao_pendente', None
    backup = value['backup']
    if (not isinstance(backup, dict) or set(backup) != {'schema', 'sha256', 'bytes', 'format', 'restorable'}
            or backup['schema'] != BASE_SCHEMA or not isinstance(backup['sha256'], str)
            or not SHA256.fullmatch(backup['sha256'])
            or not isinstance(backup['bytes'], int) or isinstance(backup['bytes'], bool) or backup['bytes'] <= 0
            or backup['format'] != 'pg_dump_custom' or backup['restorable'] is not True):
        return False, 'backup_nao_verificavel', None
    if value['https_health'] != {'healthz': 200, 'api_health': 200, 'web': 200}:
        return False, 'smoke_https_falhou', None
    return True, 'inventario_apto_a_apresentacao', canonical_fingerprint(value)


class Host:
    @contextlib.contextmanager
    def lock(self):
        import fcntl
        lock_path = STATE / 'production-release.lock'
        try:
            info = lock_path.lstat()
            require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode), 'lock_producao_inseguro')
            with lock_path.open('r') as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
        except BlockingIOError:
            raise InventoryError('outro_release_em_andamento') from None
        except OSError:
            raise InventoryError('lock_producao_indisponivel') from None

    def run(self, *args: str, data: bytes | None = None, timeout: int = 60) -> str:
        try:
            proc = subprocess.run(list(args), cwd=ROOT, input=data, capture_output=True,
                                  timeout=timeout, check=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
        except (OSError, subprocess.SubprocessError):
            raise InventoryError('consulta_somente_leitura_falhou') from None
        try:
            return proc.stdout.decode('utf-8').strip()
        except UnicodeDecodeError:
            raise InventoryError('resposta_somente_leitura_invalida') from None

    def inspect(self, container_id: str) -> dict[str, Any]:
        try:
            return json.loads(self.run('docker', 'inspect', container_id)[1:-1])
        except (ValueError, IndexError):
            raise InventoryError('inspecao_container_invalida') from None

    def compose_files(self, services: dict[str, dict[str, Any]]) -> dict[str, str]:
        paths = set()
        for item in services.values():
            paths.update(item['compose_files'])
        result = {}
        for raw in sorted(paths):
            p = Path(raw)
            try:
                resolved = p.resolve(strict=True)
                info = p.lstat()
                require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode), 'compose_path_inseguro')
            except OSError:
                raise InventoryError('compose_path_ausente_ou_inseguro') from None
            try:
                name = str(resolved.relative_to(ROOT)).replace('\\', '/')
            except ValueError:
                try:
                    resolved.relative_to(STATE)
                except ValueError:
                    raise InventoryError('compose_path_fora_das_raizes_aprovadas') from None
                name = str(resolved)
            result[name] = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return result

    def backup(self, db_container_id: str) -> dict[str, Any]:
        manifests = sorted(BACKUPS.glob('*.manifest'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
        for manifest in manifests[:20]:
            try:
                info = manifest.lstat()
                require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode), 'backup_recibo_inseguro')
                values = dict(line.split('=', 1) for line in manifest.read_text().splitlines() if '=' in line)
                archive = BACKUPS / manifest.name[:-len('.manifest')]
                if archive.suffix != '.dump':
                    archive = Path(values.get('archive', ''))
                if (values.get('format') != 'pg_dump_custom' or values.get('schema') != BASE_SCHEMA
                        or not archive.is_file() or archive.is_symlink()):
                    continue
                resolved_archive = archive.resolve(strict=True)
                resolved_archive.relative_to(BACKUPS.resolve(strict=True))
                st = archive.lstat()
                require(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode)
                        and stat.S_IMODE(st.st_mode) == 0o600, 'backup_permissoes_inseguras')
                require(time.time() - st.st_mtime <= 7 * 24 * 60 * 60, 'backup_expirado')
                hasher = hashlib.sha256()
                with archive.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
                if st.st_size == 0 or digest != values.get('sha256') or str(st.st_size) != values.get('bytes'):
                    continue
                try:
                    with archive.open('rb') as stream:
                        subprocess.run(['docker', 'exec', '-i', db_container_id, 'pg_restore', '--list'],
                                       cwd=ROOT, stdin=stream, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=120, check=True)
                except (OSError, subprocess.SubprocessError):
                    raise InventoryError('backup_pg_restore_list_falhou') from None
                return {'schema': BASE_SCHEMA, 'sha256': digest, 'bytes': st.st_size,
                        'format': 'pg_dump_custom', 'restorable': True}
            except (OSError, InventoryError, ValueError):
                continue
        raise InventoryError('backup_0089_restauravel_indisponivel')

    def candidate_ci(self) -> dict[str, Any]:
        url = ('https://api.github.com/repos/conradodeita/markina-gallery/actions/runs?head_sha='
               + TARGET_SHA + '&per_page=100')
        request = Request(url, headers={'Accept': 'application/vnd.github+json',
                                        'X-GitHub-Api-Version': '2022-11-28'})
        try:
            with urlopen(request, timeout=20) as response:
                require(response.geturl().startswith('https://api.github.com/'), 'fonte_ci_divergente')
                payload = response.read(2 * 1024 * 1024 + 1)
            require(len(payload) <= 2 * 1024 * 1024, 'resposta_ci_excessiva')
            runs = json.loads(payload)['workflow_runs']
        except InventoryError:
            raise
        except Exception:
            raise InventoryError('consulta_ci_candidato_falhou') from None
        return select_candidate_ci(runs)

    def candidate_commit_chain(self, support_sha: str) -> str:
        url = ('https://api.github.com/repos/conradodeita/markina-gallery/compare/'
               + TARGET_SHA + '...' + support_sha)
        request = Request(url, headers={'Accept': 'application/vnd.github+json',
                                        'X-GitHub-Api-Version': '2022-11-28'})
        try:
            with urlopen(request, timeout=20) as response:
                require(response.geturl().startswith('https://api.github.com/'), 'fonte_ancestralidade_divergente')
                payload = response.read(512 * 1024 + 1)
            require(len(payload) <= 512 * 1024, 'resposta_ancestralidade_excessiva')
            result = json.loads(payload)
        except InventoryError:
            raise
        except Exception:
            raise InventoryError('consulta_ancestralidade_candidato_falhou') from None
        require(result.get('status') in ('ahead', 'identical')
                and result.get('base_commit', {}).get('sha') == TARGET_SHA
                and result.get('merge_base_commit', {}).get('sha') == TARGET_SHA,
                'candidato_nao_ancestral_da_main')
        raw_url = ('https://raw.githubusercontent.com/conradodeita/markina-gallery/'
                   + TARGET_SHA + '/' + MIGRATION)
        try:
            with urlopen(raw_url, timeout=20) as response:
                require(response.geturl().startswith('https://raw.githubusercontent.com/'),
                        'fonte_migration_divergente')
                source = response.read(64 * 1024 + 1).decode('utf-8')
            require(len(source) <= 64 * 1024, 'migration_alvo_excessiva')
        except InventoryError:
            raise
        except Exception:
            raise InventoryError('migration_candidata_indisponivel') from None
        require(re.search(rf'^revision\s*=\s*[\"\']{TARGET_SCHEMA}[\"\']\s*$', source, re.M)
                and re.search(rf'^down_revision\s*=\s*[\"\']{BASE_SCHEMA}[\"\']\s*$', source, re.M),
                'cadeia_migration_alvo_divergente')
        return source

    def inventory(self, support_sha: str) -> dict[str, Any]:
        require(socket.gethostname() == 'clearbudget-vnic' and ROOT.resolve() == ROOT, 'host_ou_raiz_divergente')
        require(SHA1.fullmatch(support_sha), 'support_sha_invalido')
        repository = self.run('git', 'remote', 'get-url', 'origin')
        require(repository in ('https://github.com/conradodeita/markina-gallery.git',
                               'https://github.com/conradodeita/markina-gallery',
                               'git@github.com:conradodeita/markina-gallery.git'), 'repositorio_divergente')
        checkout = self.run('git', 'rev-parse', 'HEAD')
        clean = self.run('git', 'status', '--porcelain') == ''
        main_sha = self.run('git', 'ls-remote', 'origin', 'refs/heads/main').split()[0]
        require(main_sha == support_sha, 'support_sha_nao_e_main_atual')
        ids = self.run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + PROJECT).split()
        services: dict[str, Any] = {}
        web_diagnostic: dict[str, Any] | None = None
        active_sha = ''
        for ident in ids:
            d = self.inspect(ident)
            labels = d['Config'].get('Labels') or {}
            name = labels.get('com.docker.compose.service')
            compose_version = 'desconhecida'
            if name == 'web' and name in services:
                try:
                    compose_version = self.run('docker', 'compose', 'version', '--short')
                except InventoryError:
                    pass
            validate_service_identity(name, services, d['State'].get('Status'), web_diagnostic, d, compose_version)
            if name == 'web':
                web_diagnostic = d
            compose_files = (labels.get('com.docker.compose.project.config_files') or '').split(',')
            env = dict(part.split('=', 1) for part in d['Config'].get('Env', []) if '=' in part)
            if name == 'api':
                active_sha = env.get('APP_VERSION', '')
            health = d['State'].get('Health', {}).get('Status', 'none')
            ports = {port: bindings for port, bindings in (d['NetworkSettings'].get('Ports') or {}).items()
                     if bindings}
            services[name] = {'container_id': d['Id'], 'image': d['Image'], 'status': d['State']['Status'],
                              'health': health, 'config_hash': labels.get('com.docker.compose.config-hash', ''),
                              'version': env.get('APP_VERSION'), 'compose_files': compose_files, 'ports': ports,
                              'restart_policy': d['HostConfig']['RestartPolicy'],
                              'started_at': d['State']['StartedAt']}
        self.candidate_commit_chain(support_sha)
        schema_out = self.run('docker', 'exec', 'markina-gallery-api-1', 'python', '-B', '-m', 'alembic', 'current')
        schema_matches = re.findall(r'(?m)^([0-9]{8}_[0-9]{4})(?:\s|$)', schema_out)
        compose = self.compose_files(services)
        pending = [name for name in PENDING_MARKERS
                   if (STATE / name).exists() or (STATE / name).is_symlink()]
        https = {}
        for key, path in (('healthz', '/healthz'), ('api_health', '/api/health'), ('web', '/')):
            try:
                with urlopen(PUBLIC_URL + path, timeout=10) as response:
                    require(response.geturl().startswith(PUBLIC_URL + '/'), 'smoke_https_redirecionado')
                    https[key] = response.status
            except InventoryError:
                raise
            except Exception:
                https[key] = 0
        value = {'host': socket.gethostname(), 'project': PROJECT, 'root': str(ROOT),
            'repository': 'conradodeita/markina-gallery', 'support_sha': support_sha,
            'target_sha': TARGET_SHA, 'main_sha': main_sha, 'checkout_sha': checkout,
            'active_sha': active_sha, 'checkout_clean': clean,
            'database_revision': schema_matches[0] if len(schema_matches) == 1 else '',
            'migration_chain': {'base_revision_present': True, 'target_revision': TARGET_SCHEMA,
                'target_down_revision': BASE_SCHEMA, 'single_head': True},
            'public_url': PUBLIC_URL, 'nginx_bind': '127.0.0.1:8080->80/tcp',
            'ci': self.candidate_ci(),
            'services': services, 'compose_files': compose,
            'compose_order': services.get('api', {}).get('compose_files', []), 'pending_markers': pending,
            'backup': self.backup(services['db']['container_id']), 'https_health': https}
        return value


def main() -> int:
    try:
        support_sha = os.environ.get('MARKINA_PREVIEW_MIGRATION_SUPPORT_SHA', '')
        host = Host()
        with host.lock():
            inventory = host.inventory(support_sha)
        ready, reason, fingerprint = validate_inventory(inventory)
    except InventoryError as exc:
        print('preview_migration_preflight_ready=false')
        print('criterio=' + str(exc))
        return 1
    print(f'preview_migration_preflight_ready={str(ready).lower()}')
    print('criterio=' + reason)
    if not ready:
        return 1
    print('inventario_sanitizado=' + json.dumps(inventory, sort_keys=True, separators=(',', ':')))
    print('approval_fingerprint=' + str(fingerprint))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
