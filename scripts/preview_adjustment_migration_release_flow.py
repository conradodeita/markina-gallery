"""Orquestração fail-closed da migration 0090 com recovery por fase."""
from __future__ import annotations

from contextlib import nullcontext
import json

from preview_adjustment_migration_inventory import (
    BASE_SCHEMA, TARGET_SCHEMA, canonical_fingerprint, validate_backup_preparation, validate_inventory,
)


class ReleaseError(RuntimeError):
    pass


def prepare_backup(host, support_sha: str):
    """Only an online dump and manifest; never enter release/DDL callbacks."""
    with host.lock():
        print('backup_prepare_phase=inventory', flush=True)
        initial = host.inventory(support_sha, include_backup=False)
        ready, reason, fingerprint = validate_backup_preparation(initial)
        if not ready:
            raise ReleaseError(reason)
        print('inventario_preparacao_backup=' + json.dumps(initial, sort_keys=True))
        print('backup_prepare_phase=schema-before', flush=True)
        if host.database_revision_before_ddl() != BASE_SCHEMA:
            raise ReleaseError('schema_origem_divergente_antes_backup')
        print('backup_prepare_phase=directory', flush=True)
        host.ensure_backup_directory()
        print('backup_prepare_phase=dump-and-verify', flush=True)
        backup = host.backup_and_verify(initial, record=False)
        host.assert_backup(backup, initial)
        print('backup_prepare_phase=revalidate', flush=True)
        refreshed = host.inventory(support_sha, include_backup=False)
        if canonical_fingerprint(refreshed) != fingerprint:
            raise ReleaseError('inventario_mudou_durante_preparacao_backup')
        if host.database_revision_before_ddl() != BASE_SCHEMA:
            raise ReleaseError('schema_mudou_durante_preparacao_backup')
        host.assert_historical_preserved(initial)
        print('backup_prepare_phase=complete', flush=True)
        return backup


def execute(host, support_sha: str, approval_fingerprint: str) -> None:
    """Executa callbacks host-scoped; não transforma falhas pós-DDL em rollback."""
    with host.lock() if hasattr(host, 'lock') else nullcontext():
        print('release_phase=inventory', flush=True)
        initial = host.inventory(support_sha)
        ready, reason, current_fingerprint = validate_inventory(initial)
        if not ready:
            raise ReleaseError(reason)
        if approval_fingerprint != current_fingerprint:
            raise ReleaseError('fingerprint_aprovado_divergente')
        refreshed = host.inventory(support_sha)
        if canonical_fingerprint(refreshed) != current_fingerprint:
            raise ReleaseError('inventario_mudou_apos_aprovacao')
        print('release_phase=journal', flush=True)
        host.start_journal(current_fingerprint)

        previous = {}
        candidate = {}
        stopped = []
        migration_started = False
        barrier = False
        backup = None
        try:
            # Build and preserve every replacement image before closing ingress.
            previous = host.preserve_images(initial)
            print('release_phase=build', flush=True)
            candidate = host.stage_candidate(initial)
            host.assert_support_sha(support_sha)
            host.assert_historical_preserved(initial)
            print('release_phase=maintenance', flush=True)
            host.maintenance(True)
            barrier = True
            stopped = host.stop_writers(initial)
            host.assert_writers_idle(initial, stopped)
            backup = host.backup_and_verify(initial)
            host.assert_backup(backup, initial)
            host.assert_historical_preserved(initial)
            print('release_phase=ddl', flush=True)
            migration_started = True
            host.apply_migration(candidate['api'], TARGET_SCHEMA)
            if host.database_revision() != TARGET_SCHEMA:
                raise ReleaseError('schema_0090_nao_confirmado')
            print('release_phase=publish', flush=True)
            host.publish_api_web(candidate)
            host.start_writers(initial, stopped)
            host.assert_runtime(candidate, initial, previous, stopped)
            host.assert_historical_preserved(initial)
            host.maintenance(False)
            barrier = False
            host.assert_https_healthy()
            host.write_success_receipt(current_fingerprint, candidate, backup)
            host.finish_journal()
            print('release_phase=complete', flush=True)
        except Exception as exc:
            if not migration_started:
                # No DDL call has begun; restore only the exact stopped containers
                # and the captured Markina ingress configuration.
                try:
                    host.restore_before_migration(initial, stopped, previous, barrier)
                    host.finish_journal()
                except Exception as recovery_error:
                    raise ReleaseError('falha_pre_ddl_recuperacao_incompleta') from recovery_error
            else:
                # Once Alembic is invoked, preserve schema and backup, retain the
                # maintenance fence, and require a separately reviewed recovery.
                host.write_interrupted_receipt(current_fingerprint, candidate, backup)
            if isinstance(exc, ReleaseError):
                raise
            raise ReleaseError('release_falhou; consulte recibo operacional privado') from exc
