from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_adjustment_migration_inventory import (  # noqa: E402
    BASE_SCHEMA,
    PROJECT,
    ROOT,
    TARGET_SHA,
    TARGET_SCHEMA,
    canonical_fingerprint,
    select_candidate_ci,
    validate_inventory,
)


def valid_inventory():
    services = {}
    for index, name in enumerate(('api', 'web', 'worker', 'db', 'redis', 'nginx'), 1):
        services[name] = {
            'container_id': f'{index:064x}',
            'image': 'sha256:' + f'{index:064x}',
            'status': 'running',
            'health': 'healthy',
            'config_hash': f'{index + 10:064x}',
            'version': 'c1944189761799be96eeeb921cad9906484d8b09' if name in ('api', 'worker') else None,
            'compose_files': ['docker/docker-compose.yml'],
            'restart_policy': {'Name': 'no', 'MaximumRetryCount': 0},
            'started_at': '2026-10-26T00:00:00Z',
            'ports': {'80/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if name == 'nginx' else {},
        }
    return {
        'host': 'clearbudget-vnic', 'project': PROJECT, 'root': str(ROOT),
        'repository': 'conradodeita/markina-gallery', 'support_sha': 'a' * 40,
        'target_sha': TARGET_SHA, 'main_sha': 'a' * 40,
        'checkout_sha': 'c1944189761799be96eeeb921cad9906484d8b09',
        'active_sha': 'c1944189761799be96eeeb921cad9906484d8b09', 'checkout_clean': True,
        'database_revision': BASE_SCHEMA,
        'migration_chain': {'base_revision_present': True, 'target_revision': TARGET_SCHEMA,
                            'target_down_revision': BASE_SCHEMA, 'single_head': True},
        'public_url': 'https://markina.pickyourpic.com.br',
        'nginx_bind': '127.0.0.1:8080->80/tcp', 'services': services,
        'ci': {'run_id': 40362799810, 'conclusion': 'success'},
        'compose_files': {'docker/docker-compose.yml': 'f' * 64},
        'compose_order': ['docker/docker-compose.yml'], 'pending_markers': [],
        'backup': {'schema': BASE_SCHEMA, 'sha256': 'e' * 64, 'bytes': 1024,
                   'format': 'pg_dump_custom', 'restorable': True},
        'https_health': {'healthz': 200, 'api_health': 200, 'web': 200},
    }


class PreviewMigrationInventoryTests(unittest.TestCase):
    def test_complete_minimized_inventory_has_deterministic_fingerprint(self):
        data = valid_inventory()
        ready, reason, fingerprint = validate_inventory(data)
        self.assertTrue(ready)
        self.assertEqual(reason, 'inventario_apto_a_apresentacao')
        self.assertEqual(fingerprint, canonical_fingerprint(copy.deepcopy(data)))
        self.assertEqual(len(fingerprint), 64)

    def test_rejects_missing_or_secret_extra_fields(self):
        data = valid_inventory()
        del data['backup']
        self.assertEqual(validate_inventory(data)[1], 'inventario_com_campos_ausentes_ou_extras')
        data = valid_inventory()
        data['environment'] = {'DATABASE_URL': 'must-not-be-emitted'}
        self.assertEqual(validate_inventory(data),
                         (False, 'inventario_com_campos_ausentes_ou_extras', None))

    def test_rejects_schema_runtime_pending_or_migration_divergence(self):
        for field, mutation, expected in (
            ('database_revision', '20261024_0088', 'inventario_diverge:database_revision'),
            ('active_sha', '1' * 40, 'inventario_diverge:checkout_sha'),
            ('checkout_clean', False, 'inventario_diverge:checkout_clean'),
            ('pending_markers', ['web-in-flight.sha'], 'operacao_producao_pendente'),
        ):
            data = valid_inventory()
            data[field] = mutation
            with self.subTest(field=field):
                self.assertEqual(validate_inventory(data)[1], expected)
        data = valid_inventory()
        data['migration_chain']['target_down_revision'] = 'wrong'
        self.assertEqual(validate_inventory(data)[1], 'cadeia_alembic_divergente')

    def test_rejects_unhealthy_services_or_any_public_db_redis_port(self):
        data = valid_inventory()
        data['services']['api']['health'] = 'starting'
        self.assertEqual(validate_inventory(data)[1], 'servico_ausente_ou_nao_saudavel')
        data = valid_inventory()
        data['services']['db']['ports'] = {'5432/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '5432'}]}
        self.assertEqual(validate_inventory(data)[1], 'servico_ausente_ou_nao_saudavel')

    def test_rejects_bad_backup_compose_and_https(self):
        data = valid_inventory()
        data['backup']['restorable'] = False
        self.assertEqual(validate_inventory(data)[1], 'backup_nao_verificavel')
        data = valid_inventory()
        data['compose_files']['docker/docker-compose.preview-adjustment.yml'] = 'bad'
        self.assertEqual(validate_inventory(data)[1], 'compose_ativo_invalido')
        data = valid_inventory()
        data['https_health']['web'] = 503
        self.assertEqual(validate_inventory(data)[1], 'smoke_https_falhou')

    def test_requires_successful_ci_for_the_exact_candidate(self):
        data = valid_inventory()
        data['ci']['conclusion'] = 'failure'
        self.assertEqual(validate_inventory(data)[1], 'ci_candidato_nao_verde')

    def test_candidate_ci_ignores_other_sha_and_rejects_pending_or_failed_main_runs(self):
        run = {'path': '.github/workflows/ci.yml', 'head_sha': TARGET_SHA, 'event': 'push',
               'head_branch': 'main', 'run_number': 501, 'run_attempt': 1, 'id': 40384426091,
               'status': 'completed', 'conclusion': 'success'}
        self.assertEqual(select_candidate_ci([dict(run, head_sha='f' * 40), run]),
                         {'run_id': 40384426091, 'conclusion': 'success'})
        for changes in ({'status': 'in_progress', 'conclusion': None},
                        {'status': 'completed', 'conclusion': 'failure'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, 'ci_candidato_nao_verde'):
                select_candidate_ci([dict(run, **changes)])


if __name__ == '__main__':
    unittest.main()
