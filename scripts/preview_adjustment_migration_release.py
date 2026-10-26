#!/usr/bin/env python3
"""Executor exclusivo para publicar a migration de ajuste de prévias 0090."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from preview_adjustment_migration_inventory import (
    BASE_SCHEMA, PROJECT, ROOT, STATE, TARGET_SCHEMA, TARGET_SHA,
    Host as InventoryHost, InventoryError, canonical_fingerprint, require, validate_inventory,
)
from preview_adjustment_migration_release_flow import execute

PUBLIC_URL = 'https://markina.pickyourpic.com.br'
ENV_FILE = ROOT / 'docker/.env.homolog'
JOURNAL = STATE / 'preview-adjustment-migration-in-flight.json'
RECEIPT = STATE / 'preview-adjustment-migration-0090-published.json'
WRITERS = {'api', 'worker', 'face-index-worker', 'face-search-worker', 'face-maintenance-worker',
           'face-gemma-index-worker', 'preview-adjustment-worker', 'raw-development-worker'}
QUEUE_TABLES = ('media_job', 'whatsapp_delivery', 'email_delivery', 'notification_delivery',
                'gallery_lifecycle_operation', 'asset_file_cleanup', 'facial_job', 'raw_development_job',
                'preview_adjustment', 'payment_notification_outbox', 'gallery_reopening_notification_outbox',
                'gallery_membership_notification_outbox', 'facial_search_notification_outbox')
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class ReleaseHost(InventoryHost):
    def __init__(self):
        self.inventory_data: dict[str, Any] | None = None
        self.work: Path | None = None
        self.worktree_added = False
        self.journal: dict[str, Any] = {}
        self.barrier = False

    def command(self, args, *, timeout=300, input_data=None, stdout=subprocess.DEVNULL, stdin=None,
                app_version: bool = False):
        try:
            return subprocess.run(args, cwd=ROOT, input=input_data, stdout=stdout, stdin=stdin,
                                  stderr=subprocess.DEVNULL, timeout=timeout, check=True,
                                  env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0',
                                       **({'APP_VERSION': TARGET_SHA} if app_version else {})})
        except (OSError, subprocess.SubprocessError):
            raise InventoryError('acao_operacional_falhou; verificar recibo privado') from None

    def record(self, phase: str, **fields: Any) -> None:
        self.journal.update(fields)
        self.journal['phase'] = phase
        tmp = JOURNAL.with_name(JOURNAL.name + '.tmp')
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(self.journal, stream, sort_keys=True, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, JOURNAL)
        directory_fd = os.open(str(STATE), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def start_journal(self, fingerprint: str) -> None:
        require(not JOURNAL.exists() and not JOURNAL.is_symlink(), 'release_anterior_necessita_recuperacao')
        self.journal = {'format': 1, 'target_sha': TARGET_SHA, 'fingerprint': fingerprint,
                        'previous': self.inventory_data, 'phase': 'approved'}
        self.record('approved')

    def finish_journal(self) -> None:
        require(JOURNAL.is_file() and not JOURNAL.is_symlink(), 'recibo_intermediario_ausente')
        if self.work and self.worktree_added:
            self.command(['git', 'worktree', 'remove', '--force', str(self.work)], timeout=120)
            self.worktree_added = False
        if self.work and self.work.exists():
            shutil.rmtree(self.work)
        JOURNAL.unlink()
        fd = os.open(str(STATE), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def inventory(self, support_sha: str) -> dict[str, Any]:
        value = super().inventory(support_sha)
        self.inventory_data = value
        return value

    def assert_support_sha(self, support_sha: str) -> None:
        current = self.run('git', 'ls-remote', 'origin', 'refs/heads/main').split()
        require(len(current) == 2 and current[0] == support_sha, 'main_mudou_apos_aprovacao')

    def compose_command(self, inventory: dict[str, Any], root: Path, image_overlay: Path | None = None):
        require(ENV_FILE.is_file() and not ENV_FILE.is_symlink(), 'env_file_homolog_ausente')
        api_files = inventory['services']['api']['compose_files']
        require(api_files and api_files[0].endswith('docker-compose.yml'), 'compose_base_nao_identificado')
        command = ['docker', 'compose', '--env-file', str(ENV_FILE), '-p', PROJECT,
                   '-f', str(root / 'docker/docker-compose.yml')]
        for raw in api_files[1:]:
            command += ['-f', raw]
        if image_overlay:
            command += ['-f', str(image_overlay)]
        return command + ['--profile', '*']

    def preserve_images(self, inventory: dict[str, Any]) -> dict[str, str]:
        previous = {}
        for service in ('api', 'web'):
            image = inventory['services'][service]['image']
            tag = f'markina-gallery-preview-migration-rollback:{service}-{uuid.uuid4().hex}'
            self.command(['docker', 'image', 'tag', image, tag])
            actual = self.run('docker', 'image', 'inspect', '--format', '{{.Id}}', tag)
            require(actual == image, 'imagem_anterior_nao_preservada')
            previous[service] = image
        self.record('previous-images-preserved', previous_images=previous)
        return previous

    def stage_candidate(self, inventory: dict[str, Any]) -> dict[str, str]:
        self.work = Path(tempfile.mkdtemp(prefix='preview-adjustment-0090-', dir=STATE))
        self.work.rmdir()
        self.command(['git', 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head', 'origin', TARGET_SHA],
                     timeout=300)
        self.command(['git', 'worktree', 'add', '--detach', str(self.work), TARGET_SHA], timeout=180)
        self.worktree_added = True
        build_overlay = self.work / 'preview-migration-build.compose.json'
        tags = {service: f'markina-gallery-preview-migration:{service}-{TARGET_SHA[:12]}'
                for service in ('api', 'web')}
        build_overlay.write_text(json.dumps({'services': {name: {'image': tag}
            for name, tag in tags.items()}}, sort_keys=True), encoding='utf-8')
        os.chmod(build_overlay, 0o600)
        self.record('candidate-worktree-ready', work=str(self.work), candidate_tags=tags)
        cmd = self.compose_command(inventory, self.work, build_overlay)
        self.command(cmd + ['build', 'api', 'web'], timeout=1800, app_version=True)
        images = {name: self.run('docker', 'image', 'inspect', '--format', '{{.Id}}', tag)
                  for name, tag in tags.items()}
        require(all(re.fullmatch(r'sha256:[0-9a-f]{64}', image) for image in images.values()),
                'imagem_candidata_sem_digest')
        for service, image in images.items():
            require(self.run('docker', 'image', 'inspect', '--format', '{{.Os}}/{{.Architecture}}', image)
                    == self.run('docker', 'image', 'inspect', '--format', '{{.Os}}/{{.Architecture}}',
                                inventory['services'][service]['image']), 'arquitetura_candidata_divergente')
        self.record('candidate-images-built', candidate_images=images)
        return images

    @staticmethod
    def maintenance_configuration(server: str) -> str:
        if server.count('server {') != 1:
            raise InventoryError('nginx_server_config_ambiguo')
        guarded = server.replace('server {',
            'server {\n    if ($uri !~ "^/(healthz|api/health)$") { return 503; }', 1)
        return 'worker_processes auto;\nevents { worker_connections 1024; }\nhttp {\n' + guarded + '\n}\n'

    def maintenance(self, enabled: bool) -> None:
        nginx_id = self.inventory_data['services']['nginx']['container_id']
        if enabled:
            self.work = self.work or Path(tempfile.mkdtemp(prefix='preview-adjustment-0090-', dir=STATE))
            backup = self.work / 'nginx-original.conf'
            if not backup.exists():
                source = self.run('docker', 'exec', nginx_id, 'cat', '/etc/nginx/conf.d/default.conf')
                original = subprocess.check_output(['docker', 'exec', nginx_id, 'cat', '/etc/nginx/nginx.conf'])
                fd = os.open(str(backup), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(original)
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                require(backup.is_file() and not backup.is_symlink(), 'nginx_backup_inseguro')
                source = self.run('docker', 'exec', nginx_id, 'cat', '/etc/nginx/conf.d/default.conf')
            candidate = self.maintenance_configuration(source).encode()
            self.barrier = True
        else:
            require(self.work is not None, 'nginx_backup_nao_localizado')
            backup = self.work / 'nginx-original.conf'
            require(backup.is_file() and not backup.is_symlink(), 'nginx_backup_ausente')
            candidate = backup.read_bytes()
        self.command(['docker', 'exec', '-i', nginx_id, 'sh', '-c', 'cat > /etc/nginx/nginx.conf'],
                     input_data=candidate)
        self.command(['docker', 'exec', nginx_id, 'nginx', '-t'])
        self.command(['docker', 'exec', nginx_id, 'nginx', '-s', 'reload'])
        if enabled:
            require(self.run('curl', '--silent', '--max-time', '3', '--output', '/dev/null',
                             '--write-out', '%{http_code}', 'http://127.0.0.1:8080/admin') == '503',
                    'barreira_de_ingress_nao_confirmada')
            self.barrier = True
            self.record('maintenance-active', maintenance_backup=str(backup))
        else:
            self.barrier = False

    def stop_writers(self, inventory: dict[str, Any]) -> list[str]:
        stopped = []
        services = inventory['services']
        targets = [name for name in services if name == 'api' or name in WRITERS or name.endswith('-worker')]
        require(set(targets).issubset(WRITERS), 'writer_markina_sem_classificacao')
        for name in targets:
            item = services[name]
            ident = item['container_id']
            require(self.inspect(ident)['Image'] == item['image'], 'writer_image_mudou')
            attempted = self.journal.get('attempted', [])
            if name not in attempted:
                attempted.append(name)
            self.record('writer-stop-requested', attempted=attempted)
            self.command(['docker', 'update', '--restart=no', ident])
            self.command(['docker', 'kill', '--signal=SIGTERM', ident])
            deadline = time.monotonic() + 120
            while True:
                d = self.inspect(ident)['State']
                if d['Status'] != 'running':
                    require(d['Status'] == 'exited' and d.get('ExitCode') in (0, 143),
                            'writer_nao_encerrou_graciosamente')
                    stopped.append(name)
                    self.record('writer-stopped', stopped=stopped)
                    break
                require(time.monotonic() < deadline, 'timeout_parada_graciosa_sem_sigkill')
                time.sleep(0.5)
        return stopped

    def pg_scalar(self, sql: str) -> int:
        db_id = self.inventory_data['services']['db']['container_id']
        command = ['docker', 'exec', '-i', db_id, 'sh', '-c',
                   'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
        try:
            result = subprocess.run(command, cwd=ROOT, input=('BEGIN READ ONLY; SET LOCAL statement_timeout='
                "'15s'; " + sql + '; ROLLBACK;').encode(), capture_output=True, timeout=30, check=True)
            value = result.stdout.decode().strip()
            require(value.isdigit(), 'consulta_db_sem_contagem_inteira')
            return int(value)
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
            raise InventoryError('consulta_db_somente_leitura_falhou') from None

    def assert_writers_idle(self, inventory: dict[str, Any], stopped: list[str]) -> None:
        expected = {name for name in inventory['services'] if name == 'api' or name in WRITERS or name.endswith('-worker')}
        require(set(stopped) == expected, 'parada_incompleta_dos_writers')
        for table in QUEUE_TABLES:
            column = 'external_status' if table == 'gallery_membership_notification_outbox' else 'status'
            active = self.pg_scalar(f"SELECT count(*) FROM {table} WHERE {column}='processing'")
            require(active == 0, 'job_duravel_ainda_em_processamento')
        other_sessions = self.pg_scalar("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
            "AND pid<>pg_backend_pid() AND state IN ('active','idle in transaction','idle in transaction (aborted)')")
        require(other_sessions == 0, 'sessao_de_escrita_ou_transacao_aberta')
        self.record('writers-idle', stopped=stopped)

    def backup_and_verify(self, inventory: dict[str, Any]) -> dict[str, Any]:
        require(inventory['database_revision'] == BASE_SCHEMA, 'schema_origem_divergente_antes_backup')
        directory = BACKUPS
        require(directory.is_dir() and not directory.is_symlink(), 'diretorio_backup_inseguro')
        directory_mode = stat.S_IMODE(directory.stat().st_mode)
        require(directory_mode & 0o022 == 0, 'diretorio_backup_com_permissao_aberta')
        required_space = self.pg_scalar('SELECT pg_database_size(current_database())') * 2
        require(shutil.disk_usage(directory).free > required_space, 'espaco_backup_insuficiente')
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        archive = directory / f'preview-adjustment-0090-{stamp}-{TARGET_SHA[:12]}.dump'
        manifest = archive.with_suffix('.manifest')
        require(not archive.exists() and not manifest.exists(), 'backup_nome_ja_existe')
        db_id = inventory['services']['db']['container_id']
        command = ['docker', 'exec', db_id, 'sh', '-ceu',
                   'exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
        try:
            with archive.open('xb') as stream:
                os.chmod(archive, 0o600)
                subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.DEVNULL,
                               timeout=900, check=True)
                stream.flush()
                os.fsync(stream.fileno())
            size = archive.stat().st_size
            require(size > 0, 'backup_vazio')
            with archive.open('rb') as stream:
                subprocess.run(['docker', 'exec', '-i', db_id, 'pg_restore', '--list'], cwd=ROOT,
                               stdin=stream, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=180, check=True)
        except (OSError, subprocess.SubprocessError):
            raise InventoryError('backup_nao_validado') from None
        digest_builder = hashlib.sha256()
        with archive.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest_builder.update(chunk)
        digest = digest_builder.hexdigest()
        result = {'path': str(archive), 'schema': BASE_SCHEMA, 'sha256': digest, 'bytes': size,
                  'format': 'pg_dump_custom', 'restorable': True}
        fd = os.open(str(manifest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            for key, value in (('format', result['format']), ('schema', BASE_SCHEMA),
                               ('target_sha', TARGET_SHA), ('sha256', digest), ('bytes', size)):
                stream.write(f'{key}={value}\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.record('backup-verified', backup=result)
        return result

    def assert_backup(self, backup: dict[str, Any], _inventory: dict[str, Any]) -> None:
        require(backup.get('restorable') is True and HEX64.fullmatch(backup.get('sha256', ''))
                and backup.get('schema') == BASE_SCHEMA, 'backup_receipt_divergente')

    def apply_migration(self, api_image: str, revision: str) -> None:
        require(revision == TARGET_SCHEMA, 'revision_migration_nao_permitida')
        overlay = self.work / 'preview-migration-release.compose.json'
        overlay.write_text(json.dumps({'services': {'api': {'image': api_image}}},
                                      sort_keys=True), encoding='utf-8')
        os.chmod(overlay, 0o600)
        cmd = self.compose_command(self.inventory_data, self.work, overlay)
        self.record('migration-command-started', migration_started=True)
        self.command(cmd + ['run', '--rm', '--no-deps', '-T', 'api',
                            'python', '-B', '-m', 'alembic', 'upgrade', TARGET_SCHEMA],
                     timeout=600, app_version=True)

    def database_revision(self) -> str:
        return self.database_revision_before_ddl()

    def publish_api_web(self, candidate: dict[str, str]) -> None:
        overlay = self.work / 'preview-migration-release.compose.json'
        overlay.write_text(json.dumps({'services': {name: {'image': image}
            for name, image in candidate.items()}}, sort_keys=True), encoding='utf-8')
        os.chmod(overlay, 0o600)
        self.record('publishing-api-web', candidate_images=candidate)
        cmd = self.compose_command(self.inventory_data, self.work, overlay)
        self.command(cmd + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'api', 'web'],
                     timeout=600, app_version=True)

    def start_writers(self, inventory: dict[str, Any], stopped: list[str]) -> None:
        for name in stopped:
            if name == 'api':
                continue
            ident = inventory['services'][name]['container_id']
            policy = inventory['services'][name]['restart_policy']['Name']
            self.command(['docker', 'update', '--restart=' + policy, ident])
            self.command(['docker', 'start', ident])
        self.record('writers-resumed', stopped=stopped)

    def assert_runtime(self, candidate: dict[str, str], inventory: dict[str, Any], previous: dict[str, str],
                       stopped: list[str]) -> None:
        for service, image in candidate.items():
            ids = self.run('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                           '--filter', 'label=com.docker.compose.service=' + service).split()
            require(len(ids) == 1, 'runtime_candidato_ausente_ou_duplicado')
            d = self.inspect(ids[0])
            require(d['Image'] == image and d['State']['Status'] == 'running'
                    and d['State'].get('Health', {}).get('Status') == 'healthy', 'runtime_candidato_nao_saudavel')
            require(d['HostConfig']['RestartPolicy'] == inventory['services'][service]['restart_policy'],
                    'restart_policy_candidato_divergente')
            env = dict(part.split('=', 1) for part in d['Config'].get('Env', []) if '=' in part)
            if service == 'api':
                require(env.get('APP_VERSION') == TARGET_SHA, 'api_sha_candidato_divergente')
        for name, before in inventory['services'].items():
            if name in ('api', 'web'):
                continue
            current = self.inspect(before['container_id'])
            require(current['Id'] == before['container_id'] and current['Image'] == before['image'],
                    'servico_markina_preservado_divergente')
            require(current['State']['Status'] == 'running', 'servico_markina_nao_retornado')
            require(current['State'].get('Health', {}).get('Status', 'none') == before['health'],
                    'health_servico_markina_divergente')
            if name not in stopped:
                require(current['State']['StartedAt'] == before['started_at'],
                        'servico_markina_nao_alvo_foi_reiniciado')
            else:
                require(current['State']['StartedAt'] != before['started_at'],
                        'writer_markina_nao_foi_retornado')
            require(current['Config']['Labels'].get('com.docker.compose.config-hash') == before['config_hash'],
                    'config_hash_servico_markina_divergente')
            require(current['HostConfig']['RestartPolicy'] == before['restart_policy'],
                    'restart_policy_servico_markina_divergente')
        require(self.database_revision() == TARGET_SCHEMA, 'schema_pos_release_divergente')
        self.record('runtime-verified', previous_images=previous)

    def assert_https_healthy(self) -> None:
        for path in ('/healthz', '/api/health', '/'):
            code = self.run('curl', '--proto', '=https', '--tlsv1.2', '--silent', '--show-error',
                '--max-time', '15', '--output', '/dev/null', '--write-out', '%{http_code}', PUBLIC_URL + path)
            require(code == '200', 'smoke_https_falhou')

    def write_success_receipt(self, fingerprint: str, candidate: dict[str, str], backup: dict[str, Any]) -> None:
        value = {'format': 1, 'fingerprint': fingerprint, 'target_sha': TARGET_SHA,
                 'schema': TARGET_SCHEMA, 'candidate_images': candidate,
                 'backup': {key: backup[key] for key in ('schema', 'sha256', 'bytes', 'format')},
                 'https_health': {'healthz': 200, 'api_health': 200, 'web': 200}}
        require(not RECEIPT.exists() and not RECEIPT.is_symlink(), 'recibo_release_ja_existe')
        fd = os.open(str(RECEIPT), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, sort_keys=True, separators=(',', ':'))
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())

    def write_interrupted_receipt(self, fingerprint: str, candidate: dict[str, str], backup: Any) -> None:
        if not self.barrier:
            self.maintenance(True)
        self.record('recovery-required-after-migration-start', fingerprint=fingerprint,
                    candidate_images=candidate, backup=backup)

    def restore_before_migration(self, inventory: dict[str, Any], stopped: list[str],
                                 previous: dict[str, str], barrier: bool) -> None:
        # If stop_writers failed partway, the durable journal contains the exact
        # subset that exited; use it instead of trusting the caller's list.
        attempted = self.journal.get('attempted', stopped)
        for name in reversed(attempted):
            ident = inventory['services'][name]['container_id']
            state = self.inspect(ident)['State']['Status']
            policy = inventory['services'][name]['restart_policy']['Name']
            self.command(['docker', 'update', '--restart=' + policy, ident])
            if state == 'exited':
                self.command(['docker', 'start', ident])
        if barrier or self.barrier:
            self.maintenance(False)
        require(self.database_revision_before_ddl() == BASE_SCHEMA, 'schema_mudou_antes_do_ddl')
        self.record('recovered-before-migration')

    def database_revision_before_ddl(self) -> str:
        db_id = self.inventory_data['services']['db']['container_id']
        try:
            result = subprocess.run(['docker', 'exec', db_id, 'sh', '-c',
                'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                "-c 'SELECT version_num FROM alembic_version'"], cwd=ROOT, capture_output=True,
                timeout=30, check=True)
            value = result.stdout.decode().strip()
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
            raise InventoryError('consulta_schema_somente_leitura_falhou') from None
        return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inventory', 'release'))
    parser.add_argument('--support-sha', required=True)
    parser.add_argument('--approval-fingerprint', default='')
    args = parser.parse_args()
    host = ReleaseHost()
    try:
        if args.mode == 'inventory':
            with host.lock():
                value = host.inventory(args.support_sha)
            ready, reason, fingerprint = validate_inventory(value)
            print('preview_migration_preflight_ready=' + str(ready).lower())
            print('criterio=' + reason)
            if not ready:
                return 1
            print('inventario_sanitizado=' + json.dumps(value, sort_keys=True, separators=(',', ':')))
            print('approval_fingerprint=' + fingerprint)
            return 0
        if not re.fullmatch(r'[0-9a-f]{64}', args.approval_fingerprint):
            raise InventoryError('fingerprint_aprovado_ausente_ou_invalido')
        execute(host, args.support_sha, args.approval_fingerprint)
        print('preview_adjustment_migration_release=success')
        print('schema=' + TARGET_SCHEMA)
        return 0
    except (InventoryError, Exception) as exc:
        # Do not expose command output, environment, customer data or connection details.
        print('preview_adjustment_migration_release=failed')
        print('criterio=' + (str(exc) if isinstance(exc, InventoryError) else 'falha_operacional; consultar recibo privado'))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
