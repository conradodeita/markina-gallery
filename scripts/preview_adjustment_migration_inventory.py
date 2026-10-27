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
BACKUPS = STATE / 'preview-adjustment-backups'
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
COMPOSE_VERSION = '2.35.1'
HISTORICAL_OPERATIONAL_FIELDS = ('Name', 'Image', 'Config', 'HostConfig', 'Mounts',
                                 'State_without_Health', 'NetworkSettings')
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


def sanitized_container_summary(containers: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Bounded audit of this project's containers; never return raw Docker fields."""
    require(len(containers) <= 100, 'muitos_containers_markina')
    result = []
    seen: set[str] = set()
    for container in containers:
        labels = container.get('Config', {}).get('Labels') or {}
        require(labels.get('com.docker.compose.project') == PROJECT, 'projeto_container_divergente')
        name = labels.get('com.docker.compose.service')
        safe_name = name if isinstance(name, str) and name in KNOWN_SERVICES else 'desconhecido'
        state = container.get('State', {}).get('Status')
        safe_state = state if isinstance(state, str) and state in DOCKER_STATES else 'desconhecido'
        data = web_classification(container)
        prefix = data['id_prefixo']
        require(prefix != 'desconhecido' and prefix not in seen, 'identidade_container_ambigua')
        seen.add(prefix)
        result.append({'servico': safe_name, 'estado': safe_state, 'id_prefixo': prefix,
                       'oneoff': data['oneoff'], 'restart': data['restart'],
                       'rotulo_config_hash': 'presente' if 'com.docker.compose.config-hash' in labels else 'ausente',
                       'rotulo_oneoff': 'presente' if 'com.docker.compose.oneoff' in labels else 'ausente',
                       'rotulo_numero': 'presente' if 'com.docker.compose.container-number' in labels else 'ausente',
                       'referencia_imagem': data['referencia_imagem'],
                       'codigo_saida': data['codigo_saida'], 'montagens_gravaveis': data['montagens_gravaveis']})
    return sorted(result, key=lambda row: (row['servico'], row['estado'], row['id_prefixo']))


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


def historical_identity(container: dict[str, Any]) -> dict[str, Any]:
    """Bind preserved Docker metadata without disclosing labels, mounts or environment."""
    labels = container.get('Config', {}).get('Labels') or {}
    require(labels.get('com.docker.compose.project') == PROJECT, 'projeto_container_divergente')
    ident, image = container.get('Id'), container.get('Image')
    require(isinstance(ident, str) and SHA256.fullmatch(ident)
            and isinstance(image, str) and IMAGE.fullmatch(image), 'historico_identidade_invalida')
    state = container.get('State', {})
    require(state.get('Status') == 'exited' and state.get('Running') is False
            and state.get('Paused') is False and state.get('Restarting') is False,
            'historico_nao_encerrado')
    require(container.get('HostConfig', {}).get('RestartPolicy') == {'Name': 'no', 'MaximumRetryCount': 0},
            'historico_restart_nao_permitido')
    service = labels.get('com.docker.compose.service')
    require(isinstance(service, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', service),
            'historico_servico_ausente_ou_invalido')
    if service in ('api', 'web'):
        require(all(key not in labels for key in ('com.docker.compose.config-hash',
                'com.docker.compose.oneoff', 'com.docker.compose.container-number')),
                'historico_alvo_selecionavel_pelo_compose')
        require(container.get('Name') != f'/{PROJECT}-{service}-1', 'historico_ocupa_nome_ativo')
    fields = ('Name', 'Image', 'Config', 'HostConfig', 'Mounts', 'State', 'NetworkSettings')
    require(all(key in container for key in fields), 'historico_metadados_incompletos')
    mounts = container['Mounts']
    require(isinstance(mounts, list) and len(mounts) <= 100
            and all(isinstance(mount, dict) and type(mount.get('RW')) is bool for mount in mounts),
            'historico_montagens_invalidas')
    metadata = {key: container[key] for key in fields}
    # Health logs/counters are diagnostic records, not execution identity of an
    # exited container. Keep every other State field so restarts/exits still bind.
    metadata['State'] = {key: value for key, value in state.items() if key != 'Health'}
    operational_values = {
        'Name': container['Name'], 'Image': image, 'Config': container['Config'],
        'HostConfig': container['HostConfig'], 'Mounts': mounts,
        'State_without_Health': metadata['State'], 'NetworkSettings': container['NetworkSettings']}
    field_hashes = {key: canonical_fingerprint(operational_values[key])
                    for key in HISTORICAL_OPERATIONAL_FIELDS}
    return {'container_id': ident, 'image': image, 'status': 'exited',
            'metadata_sha256': canonical_fingerprint(metadata), 'fields_sha256': field_hashes}


def historical_mount_diagnostics(mounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose comparable mount components as hashes and fixed categories only."""
    result = []
    allowed_types = {'bind', 'volume', 'tmpfs', 'image', 'npipe'}
    hashed_fields = ('Source', 'Destination', 'Name', 'Driver', 'Mode', 'Propagation')
    for mount in mounts:
        require(isinstance(mount, dict) and type(mount.get('RW')) is bool,
                'historico_montagens_invalidas')
        kind = mount.get('Type')
        safe_kind = kind if isinstance(kind, str) and kind in allowed_types else 'outro'
        hashes = {f'{field}_sha256': canonical_fingerprint(mount[field]) if field in mount else None
                  for field in hashed_fields}
        result.append({'type': safe_kind,
                       'rw': 'sim' if mount['RW'] else 'nao', **hashes})
    return sorted(result, key=lambda item: json.dumps(item, sort_keys=True, separators=(',', ':')))


def historical_field_hashes(containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for item in containers:
        if item.get('State', {}).get('Status') != 'exited':
            continue
        identity = historical_identity(item)
        fields = ('Name', 'Image', 'Config', 'HostConfig', 'Mounts', 'State', 'NetworkSettings')
        hashes = {key: canonical_fingerprint(item[key]) for key in fields}
        hashes['State_without_Health'] = canonical_fingerprint(
            {key: value for key, value in item['State'].items() if key != 'Health'})
        result.append({'id_prefixo': identity['container_id'][:12], 'campos_sha256': hashes,
                       'montagens_sanitizadas': historical_mount_diagnostics(item['Mounts'])})
    return sorted(result, key=lambda row: row['id_prefixo'])


def partition_containers(containers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    require(len(containers) <= 100, 'muitos_containers_markina')
    active, historical = [], []
    ids, services = set(), set()
    for item in containers:
        labels = item.get('Config', {}).get('Labels') or {}
        require(labels.get('com.docker.compose.project') == PROJECT, 'projeto_container_divergente')
        ident = item.get('Id')
        require(isinstance(ident, str) and SHA256.fullmatch(ident) and ident not in ids,
                'identidade_container_ambigua')
        ids.add(ident)
        if item.get('State', {}).get('Status') == 'exited':
            historical.append(historical_identity(item))
            continue
        require(item.get('State', {}).get('Status') == 'running', 'estado_container_nao_reconciliavel')
        service = labels.get('com.docker.compose.service')
        require(service in KNOWN_SERVICES and service not in ('migrate', 'seed-admin'),
                'servico_ativo_nao_reconhecido')
        require(service not in services, 'servico_ativo_duplicado')
        require(labels.get('com.docker.compose.oneoff') == 'False'
                and labels.get('com.docker.compose.container-number') == '1'
                and item.get('Name') == f'/{PROJECT}-{service}-1', 'identidade_ativa_nao_canonica')
        services.add(service)
        active.append(item)
    return active, sorted(historical, key=lambda item: item['container_id'])


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
    return _validate_inventory(value, require_backup=True)


def validate_backup_preparation(value: dict[str, Any]) -> tuple[bool, str, str | None]:
    """This purpose cannot approve release when the backup is absent."""
    return _validate_inventory(value, require_backup=False)


def _validate_inventory(value: dict[str, Any], *, require_backup: bool) -> tuple[bool, str, str | None]:
    fields = {'host', 'project', 'root', 'repository', 'support_sha', 'target_sha', 'main_sha',
              'checkout_sha', 'active_sha', 'checkout_clean', 'database_revision', 'migration_chain',
              'public_url', 'nginx_bind', 'ci', 'services', 'compose_files', 'compose_order',
              'pending_markers', 'backup', 'https_health', 'historical_containers', 'compose_version'}
    if not isinstance(value, dict) or set(value) != fields:
        return False, 'inventario_com_campos_ausentes_ou_extras', None
    for name in ('support_sha', 'target_sha', 'main_sha', 'checkout_sha', 'active_sha'):
        if not isinstance(value[name], str) or not SHA1.fullmatch(value[name]):
            return False, f'sha_invalido:{name}', None
    for name, expected in (('host', 'clearbudget-vnic'), ('project', PROJECT), ('root', str(ROOT)),
                           ('repository', 'conradodeita/markina-gallery'),
                           ('target_sha', TARGET_SHA), ('main_sha', value['support_sha']),
                           ('active_sha', BASE_SHA),
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
    if value['compose_version'] != COMPOSE_VERSION:
        return False, 'compose_version_nao_validada', None
    historical = value['historical_containers']
    if not isinstance(historical, list) or len(historical) > 100:
        return False, 'historicos_invalidos', None
    historical_ids = set()
    for item in historical:
        if (not isinstance(item, dict) or set(item) != {
                'container_id', 'image', 'status', 'metadata_sha256', 'fields_sha256'}
                or not isinstance(item['container_id'], str) or not SHA256.fullmatch(item['container_id'])
                or item['container_id'] in historical_ids or item['status'] != 'exited'
                or not isinstance(item['image'], str) or not IMAGE.fullmatch(item['image'])
                or not isinstance(item['metadata_sha256'], str) or not SHA256.fullmatch(item['metadata_sha256'])
                or not isinstance(item['fields_sha256'], dict)
                or set(item['fields_sha256']) != set(HISTORICAL_OPERATIONAL_FIELDS)
                or not all(isinstance(value, str) and SHA256.fullmatch(value)
                           for value in item['fields_sha256'].values())):
            return False, 'historicos_invalidos', None
        historical_ids.add(item['container_id'])
    for name, item in services.items():
        if not isinstance(name, str) or not isinstance(item, dict) or set(item) != {
                'container_id', 'image', 'status', 'health', 'config_hash', 'version', 'compose_files',
                'ports', 'restart_policy', 'started_at'}:
            return False, 'identidade_servico_incompleta', None
        if item['container_id'] in historical_ids:
            return False, 'identidade_ativa_historica_sobreposta', None
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
    if (not isinstance(compose, dict) or not compose
            or any(not isinstance(path, str) or not path.startswith(('docker/', '/var/lib/markina-gallery/deploy-state/'))
                   or not isinstance(digest, str) or not SHA256.fullmatch(digest) for path, digest in compose.items())):
        return False, 'compose_ativo_invalido', None
    if (not isinstance(order, list) or not order
            or any(not isinstance(path, str) or not path for path in order)
            or any(services[name]['compose_files'] != order for name in ('api', 'web'))):
        return False, 'ordem_compose_ativa_invalida', None
    normalized_order = [path[len(str(ROOT)) + 1:] if path.startswith(str(ROOT) + '/') else path for path in order]
    if len(set(order)) != len(order) or set(normalized_order) != set(compose):
        return False, 'manifesto_alvo_incompleto', None
    if value['pending_markers'] != []:
        return False, 'operacao_producao_pendente', None
    backup = value['backup']
    if not require_backup:
        if backup is not None:
            return False, 'finalidade_preparacao_backup_divergente', None
    elif (not isinstance(backup, dict) or set(backup) != {'schema', 'sha256', 'bytes', 'format', 'restorable'}
            or backup['schema'] != BASE_SCHEMA or not isinstance(backup['sha256'], str)
            or not SHA256.fullmatch(backup['sha256'])
            or not isinstance(backup['bytes'], int) or isinstance(backup['bytes'], bool) or backup['bytes'] <= 0
            or backup['format'] != 'pg_dump_custom' or backup['restorable'] is not True):
        return False, 'backup_nao_verificavel', None
    if value['https_health'] != {'healthz': 200, 'api_health': 200, 'web': 200}:
        return False, 'smoke_https_falhou', None
    reason = 'inventario_apto_a_apresentacao' if require_backup else 'inventario_apto_somente_a_preparacao_backup'
    return True, reason, canonical_fingerprint(value)


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

    def compose_failure_report(self, services: dict[str, Any], schemas: list[str],
                               checkout: str, active_sha: str, clean: bool, historical_count: int) -> dict[str, Any]:
        """Collect independent read-only blockers, never arbitrary paths or config values."""
        known = {'docker-compose.yml', 'docker-compose.raw-development.yml',
                 'docker-compose.preview-adjustment.yml', 'docker-compose.system-monitor.yml',
                 'docker-compose.local.yml'}
        paths = sorted({path for service in services.values() for path in service['compose_files']})
        require(len(paths) <= 100, 'muitos_paths_compose')
        checks = []
        for raw in paths:
            path = Path(raw)
            category = 'fora_raizes_aprovadas'
            for root, kind in ((ROOT, 'repositorio'), (STATE, 'deploy_state')):
                try:
                    relative = path.relative_to(root)
                    category = kind
                    break
                except ValueError:
                    continue
            name = (relative.as_posix() if category == 'repositorio'
                    and relative.parent == Path('docker') and relative.name in known else category)
            state = 'nao_consultado'
            if category != 'fora_raizes_aprovadas':
                try:
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode):
                        state = 'symlink'
                    elif not stat.S_ISREG(info.st_mode):
                        state = 'nao_regular'
                    else:
                        resolved = path.resolve(strict=True)
                        state = ('regular' if any(root == resolved or root in resolved.parents
                                                 for root in (ROOT, STATE)) else 'resolve_fora_raizes')
                except FileNotFoundError:
                    state = 'ausente'
                except OSError:
                    state = 'inacessivel'
            checks.append({'categoria': name, 'estado': state,
                           'path_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                           'servicos': sorted(name for name, service in services.items()
                                              if name in KNOWN_SERVICES and raw in service['compose_files'])})
        try:
            backup = {'apto': True, 'evidencia': self.backup(services['db']['container_id'])}
        except InventoryError:
            backup = {'apto': False, 'criterio': 'backup_0089_nao_verificado'}
        return {'compose_paths': checks, 'schema': schemas[0] if len(schemas) == 1
                and re.fullmatch(r'[0-9]{8}_[0-9]{4}', schemas[0]) else 'nao_unico',
                'checkout_sha': checkout if SHA1.fullmatch(checkout) else 'invalido',
                'active_sha': active_sha if SHA1.fullmatch(active_sha) else 'invalido',
                'checkout_clean': clean, 'historicos': historical_count, 'backup': backup,
                'servicos': {name: {'saudavel': item['health'] == 'healthy',
                                   'versao_igual_api': item['version'] == active_sha,
                                   'ordem_compose_igual_api': item['compose_files'] == services['api']['compose_files']}
                             for name, item in services.items() if name in KNOWN_SERVICES}}

    def target_compose_command(self, services: dict[str, Any]) -> list[str]:
        order = services['api']['compose_files']
        require(order and order == services['web']['compose_files'], 'ordem_compose_ativa_invalida')
        command = ['docker', 'compose', '--env-file', str(ROOT / 'docker/.env.homolog'), '-p', PROJECT]
        for raw in order:
            command += ['-f', raw]
        return command + ['--profile', '*']

    def assert_target_compose_matches(self, services: dict[str, Any]) -> None:
        command = self.target_compose_command(services)
        for name in ('api', 'web'):
            fields = self.run(*command, 'config', '--hash', name).split()
            require(fields == [name, services[name]['config_hash']], 'manifesto_alvo_diverge_do_runtime')

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
               + TARGET_SHA + '...' + support_sha + '?per_page=1')
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

    def inventory(self, support_sha: str, *, include_backup: bool = True) -> dict[str, Any]:
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
        require(len(ids) <= 100, 'muitos_containers_markina')
        containers = [self.inspect(ident) for ident in ids]
        print('historicos_campos_sanitizados=' + json.dumps(historical_field_hashes(containers), sort_keys=True))
        compose_version = self.run('docker', 'compose', 'version', '--short').lstrip('v')
        require(compose_version == COMPOSE_VERSION, 'compose_version_nao_validada')
        try:
            containers, historical = partition_containers(containers)
        except InventoryError:
            print('inventario_containers_markina=' + json.dumps(sanitized_container_summary(containers),
                  sort_keys=True, separators=(',', ':')))
            raise
        services: dict[str, Any] = {}
        web_diagnostic: dict[str, Any] | None = None
        active_sha = ''
        for d in containers:
            labels = d['Config'].get('Labels') or {}
            name = labels.get('com.docker.compose.service')
            compose_version = 'desconhecida'
            if name == 'web' and name in services:
                try:
                    compose_version = self.run('docker', 'compose', 'version', '--short')
                except InventoryError:
                    pass
            try:
                validate_service_identity(name, services, d['State'].get('Status'), web_diagnostic, d, compose_version)
            except InventoryError:
                if name == 'web' and name in services:
                    summary = sanitized_container_summary(containers)
                    print('inventario_containers_markina=' + json.dumps(summary, sort_keys=True, separators=(',', ':')))
                raise
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
        try:
            compose = self.compose_files({name: services[name] for name in ('api', 'web')})
            self.assert_target_compose_matches(services)
        except InventoryError:
            report = self.compose_failure_report(services, schema_matches, checkout, active_sha, clean, len(historical))
            print('diagnostico_preflight=' + json.dumps(report, sort_keys=True, separators=(',', ':')))
            raise
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
            'backup': self.backup(services['db']['container_id']) if include_backup else None, 'https_health': https,
            'historical_containers': historical, 'compose_version': COMPOSE_VERSION}
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
