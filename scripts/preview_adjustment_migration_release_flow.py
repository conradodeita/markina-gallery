"""Orquestração fail-closed da migration 0090 com recovery por fase."""
from __future__ import annotations

from contextlib import nullcontext

from preview_adjustment_migration_inventory import TARGET_SCHEMA, canonical_fingerprint, validate_inventory


class ReleaseError(RuntimeError):
    pass


def execute(host, support_sha: str, approval_fingerprint: str) -> None:
    """Executa callbacks host-scoped; não transforma falhas pós-DDL em rollback."""
    with host.lock() if hasattr(host, 'lock') else nullcontext():
        initial = host.inventory(support_sha)
        ready, reason, current_fingerprint = validate_inventory(initial)
        if not ready:
            raise ReleaseError(reason)
        if approval_fingerprint != current_fingerprint:
            raise ReleaseError('fingerprint_aprovado_divergente')
        refreshed = host.inventory(support_sha)
        if canonical_fingerprint(refreshed) != current_fingerprint:
            raise ReleaseError('inventario_mudou_apos_aprovacao')
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
            candidate = host.stage_candidate(initial)
            host.assert_support_sha(support_sha)
            host.maintenance(True)
            barrier = True
            stopped = host.stop_writers(initial)
            host.assert_writers_idle(initial, stopped)
            backup = host.backup_and_verify(initial)
            host.assert_backup(backup, initial)
            migration_started = True
            host.apply_migration(candidate['api'], TARGET_SCHEMA)
            if host.database_revision() != TARGET_SCHEMA:
                raise ReleaseError('schema_0090_nao_confirmado')
            host.publish_api_web(candidate)
            host.start_writers(initial, stopped)
            host.assert_runtime(candidate, initial, previous, stopped)
            host.maintenance(False)
            barrier = False
            host.assert_https_healthy()
            host.write_success_receipt(current_fingerprint, candidate, backup)
            host.finish_journal()
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
