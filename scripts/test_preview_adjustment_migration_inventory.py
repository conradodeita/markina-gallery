from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
        'historical_containers': [], 'compose_version': '2.35.1',
    }


class PreviewMigrationInventoryTests(unittest.TestCase):
    def test_candidate_chain_fetches_pinned_migration_and_rejects_divergence(self):
        from preview_adjustment_migration_inventory import Host, InventoryError, MIGRATION

        class Response:
            def __init__(self, url, content):
                self.url, self.content = url, content

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self):
                return self.url

            def read(self, _size):
                return self.content

        comparison = ('{"status":"ahead","base_commit":{"sha":"' + TARGET_SHA
                      + '"},"merge_base_commit":{"sha":"' + TARGET_SHA + '"}}').encode()
        source = b'revision = "20261026_0090"\ndown_revision = "20261025_0089"\n'
        urls = []

        def fetch(request, timeout):
            url = request.full_url if hasattr(request, 'full_url') else request
            urls.append(url)
            return Response(url, comparison if 'api.github.com' in url else source)

        with patch('preview_adjustment_migration_inventory.urlopen', side_effect=fetch):
            self.assertEqual(Host().candidate_commit_chain('a' * 40), source.decode())
        self.assertTrue(urls[1].endswith('/' + TARGET_SHA + '/' + MIGRATION))
        source = b'revision = "20261026_0090"\ndown_revision = "wrong"\n'
        with patch('preview_adjustment_migration_inventory.urlopen', side_effect=fetch):
            with self.assertRaisesRegex(InventoryError, 'cadeia_migration_alvo_divergente'):
                Host().candidate_commit_chain('a' * 40)

    def test_duplicate_diagnostic_is_fail_closed_and_never_prints_raw_unknown_values(self):
        from preview_adjustment_migration_inventory import InventoryError, validate_service_identity

        validate_service_identity('api', {}, 'running')
        with self.assertRaisesRegex(InventoryError, 'servico=api;contagem_ao_menos=2;estados=running,exited'):
            validate_service_identity('api', {'api': {'status': 'running'}}, 'exited')
        with self.assertRaisesRegex(InventoryError, 'servico=ausente'):
            validate_service_identity(None, {}, 'running')
        with self.assertRaises(InventoryError) as error:
            validate_service_identity('sensitive-label', {'sensitive-label': {'status': 'secret'}}, 'secret')
        self.assertEqual(str(error.exception), 'servico_markina_duplicado;servico=desconhecido;'
                         'contagem_ao_menos=2;estados=desconhecido,desconhecido')

    def test_duplicate_web_diagnostic_classifies_without_leaking_raw_values(self):
        from preview_adjustment_migration_inventory import InventoryError, validate_service_identity

        active = {'Name': '/markina-gallery-web-1', 'Image': 'sha256:' + 'a' * 64,
                  'Config': {'Labels': {'com.docker.compose.oneoff': 'False',
                                        'com.docker.compose.container-number': '1'}},
                  'HostConfig': {'RestartPolicy': {'Name': 'unless-stopped'}}}
        stopped = {'Name': 'PRIVATE-NAME', 'Image': 'sha256:' + 'b' * 64,
                   'Config': {'Labels': {'com.docker.compose.oneoff': 'PRIVATE-LABEL',
                                         'com.docker.compose.container-number': 'PRIVATE-NUMBER'}},
                   'HostConfig': {'RestartPolicy': {'Name': 'PRIVATE-RESTART'}}}
        with self.assertRaises(InventoryError) as error:
            validate_service_identity('web', {'web': {'status': 'running'}}, 'exited', active, stopped)
        message = str(error.exception)
        self.assertIn('estados=running,exited;diagnostico=', message)
        self.assertIn('"mesma_imagem":"nao"', message)
        self.assertIn('"nome_canonico":"sim"', message)
        self.assertNotIn('PRIVATE', message)
        self.assertNotIn('sha256:', message)
        self.assertNotIn('approval_fingerprint', message)

    def test_web_inspection_outputs_only_bounded_identifiers_and_categories(self):
        from preview_adjustment_migration_inventory import InventoryError, validate_service_identity

        active = {'Id': 'a' * 64, 'Name': '/markina-gallery-web-1', 'Image': 'sha256:' + 'a' * 64,
                  'State': {'ExitCode': 0}, 'Mounts': [{'RW': True, 'Source': '/secret/path'}],
                  'Config': {'Image': 'markina-gallery-web', 'Labels': {'com.docker.compose.oneoff': 'False'}},
                  'HostConfig': {'RestartPolicy': {'Name': 'no'}}}
        old = {'Id': 'b' * 64, 'Name': '/secret-container-name', 'Image': 'sha256:' + 'b' * 64,
               'State': {'ExitCode': 137}, 'Mounts': [{'RW': False, 'Source': '/secret/backup'}],
               'Config': {'Image': 'secret/test:private', 'Labels': {}},
               'HostConfig': {'RestartPolicy': {'Name': 'no'}}}
        with self.assertRaises(InventoryError) as error:
            validate_service_identity('web', {'web': {'status': 'running'}}, 'exited', active, old, 'v2.32.4')
        message = str(error.exception)
        self.assertIn('"id_prefixo":"bbbbbbbbbbbb"', message)
        self.assertIn('"montagens_gravaveis":"0"', message)
        self.assertIn('"codigo_saida":"137"', message)
        self.assertIn('"referencia_imagem":"nome_sugere_teste"', message)
        self.assertIn('"compose_version":"v2.32.4"', message)
        self.assertNotIn('secret', message)
        self.assertNotIn('b' * 64, message)
        with self.assertRaises(InventoryError) as error:
            validate_service_identity('web', {'web': {'status': 'running'}}, 'exited', active, old, 'secret')
        self.assertNotIn('secret', str(error.exception))
        self.assertIn('"compose_version":"desconhecida"', str(error.exception))

    def test_container_summary_is_project_bound_sanitized_and_unambiguous(self):
        from preview_adjustment_migration_inventory import InventoryError, sanitized_container_summary

        def container(ident, project=PROJECT):
            return {'Id': ident, 'Name': '/private-name', 'Image': 'sha256:' + 'f' * 64,
                    'Config': {'Image': 'secret/test:private', 'Env': ['PASSWORD=private-secret'],
                               'Labels': {'com.docker.compose.project': project,
                                          'com.docker.compose.service': 'web'}},
                    'State': {'Status': 'exited', 'ExitCode': 0},
                    'Mounts': [{'RW': True, 'Source': '/private-path'}],
                    'HostConfig': {'RestartPolicy': {'Name': 'no'}}}

        records = sanitized_container_summary([container('b' * 64), container('a' * 64)])
        self.assertEqual([row['id_prefixo'] for row in records], ['a' * 12, 'b' * 12])
        self.assertEqual(records[0]['servico'], 'web')
        self.assertEqual(records[0]['estado'], 'exited')
        self.assertEqual(records[0]['montagens_gravaveis'], '1')
        self.assertEqual(records[0]['rotulo_config_hash'], 'ausente')
        labelled = container('c' * 64)
        labelled['Config']['Labels']['com.docker.compose.config-hash'] = 'private-invalid'
        labelled['Config']['Labels']['com.docker.compose.oneoff'] = 'private-invalid'
        labelled['Config']['Labels']['com.docker.compose.container-number'] = 'private-invalid'
        classified = sanitized_container_summary([labelled])[0]
        self.assertEqual(classified['rotulo_config_hash'], 'presente')
        self.assertEqual(classified['rotulo_oneoff'], 'presente')
        self.assertEqual(classified['rotulo_numero'], 'presente')
        self.assertNotIn('private', str(classified))
        self.assertNotIn('private', str(records))
        self.assertNotIn('secret', str(records))
        with self.assertRaisesRegex(InventoryError, 'projeto_container_divergente'):
            sanitized_container_summary([container('a' * 64, project='firefly_telegram')])
        with self.assertRaisesRegex(InventoryError, 'identidade_container_ambigua'):
            sanitized_container_summary([container('a' * 64), container('a' * 12 + 'b' * 52)])
        with self.assertRaisesRegex(InventoryError, 'identidade_container_ambigua'):
            sanitized_container_summary([container('not-a-docker-id')])
        with self.assertRaisesRegex(InventoryError, 'muitos_containers_markina'):
            sanitized_container_summary([container('a' * 64)] * 101)

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
            ('active_sha', '1' * 40, 'inventario_diverge:active_sha'),
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
        data = valid_inventory()
        data['pending_markers'] = ['preview-adjustment-migration-0090-published.json']
        self.assertEqual(validate_inventory(data)[1], 'operacao_producao_pendente')

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
