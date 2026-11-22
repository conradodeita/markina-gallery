"""Contract tests for the minimized retirement preflight inventory."""

import copy
import unittest

from retirement_inventory_policy import binding_removal_allowed, evaluate


class RetirementInventoryTests(unittest.TestCase):
    def valid_inventory(self):
        return {
            "host": "clearbudget-vnic",
            "project": "markina-gallery",
            "root": "/opt/markina-gallery",
            "target_sha": "a" * 40,
            "main_sha": "a" * 40,
            "checkout_sha": "b" * 40,
            "active_sha": "b" * 40,
            "database_revision": "20261021_0086",
            "public_url": "https://markina.pickyourpic.com.br",
            "nginx_bind": "127.0.0.1:8080->80/tcp",
            "services": {name: "healthy" for name in ("api", "web", "db", "redis", "nginx", "worker")},
            "compose_hashes": {"api": "c" * 64, "web": "d" * 64, "worker": "e" * 64},
            "binding": {
                "path": "/opt/markina-gallery/docker/.env.infinitepay-bindings",
                "type": "regular_file",
                "symlink": False,
                "mode": "0600",
                "size_bytes": 128,
                "link_count": 1,
                "mtime_ns": 100,
                "inode": 123,
                "device": 7,
                "uid": 1000,
                "compose_consumers": ["markina-gallery/api"],
                "host_references": ["/opt/markina-gallery/docker/docker-compose.yml"],
                "target_references": [],
            },
            "https_health": {"healthz": True, "api_health": True, "web": True},
        }

    def test_complete_minimized_inventory_has_deterministic_fingerprint(self):
        inventory = self.valid_inventory()
        self.assertEqual(evaluate(inventory), evaluate(copy.deepcopy(inventory)))
        ready, reason, fingerprint = evaluate(inventory)
        self.assertTrue(ready)
        self.assertEqual(reason, "inventario_apto_a_apresentacao")
        self.assertEqual(len(fingerprint), 64)

    def test_refuses_drifted_host_schema_domain_or_bind(self):
        for key, value in (("host", "other-host"), ("database_revision", "20261017_0084"),
                           ("public_url", "https://other.example"), ("nginx_bind", "0.0.0.0:8080->80/tcp")):
            with self.subTest(key=key):
                inventory = self.valid_inventory()
                inventory[key] = value
                self.assertFalse(evaluate(inventory)[0])

    def test_refuses_unhealthy_services_and_incomplete_smokes(self):
        inventory = self.valid_inventory()
        inventory["services"]["worker"] = "running"
        self.assertEqual(evaluate(inventory)[1], "servico_critico_nao_saudavel")
        inventory["services"]["api"] = "running"
        self.assertEqual(evaluate(inventory)[1], "servico_critico_nao_saudavel")
        inventory = self.valid_inventory()
        del inventory["https_health"]["web"]
        self.assertEqual(evaluate(inventory)[1], "smoke_https_falhou")

    def test_refuses_shared_or_ambiguous_binding_without_exposing_contents(self):
        for change, expected in (
            ({"compose_consumers": ["markina-gallery/api", "other-project/api"]},
             "binding_compartilhado_ou_consumidor_desconhecido"),
            ({"symlink": True}, "binding_nao_e_arquivo_regular"),
            ({"host_references": ["/opt/other/docker-compose.yml"]},
             "binding_referenciado_por_outro_arquivo"),
            ({"link_count": 2}, "binding_compartilhado_por_hardlink"),
            ({"link_count": True}, "binding_compartilhado_por_hardlink"),
            ({"path": "/etc/other-project/secrets.env"}, "caminho_binding_fora_do_projeto"),
        ):
            with self.subTest(change=change):
                inventory = self.valid_inventory()
                inventory["binding"].update(change)
                self.assertEqual(evaluate(inventory)[1], expected)

    def test_only_expected_active_compose_reference_is_allowed_before_release(self):
        active_compose = "/opt/markina-gallery/docker/docker-compose.yml"
        for references in ([], [active_compose, "/opt/other/docker-compose.yml"]):
            with self.subTest(references=references):
                inventory = self.valid_inventory()
                inventory["binding"]["host_references"] = references
                self.assertEqual(evaluate(inventory)[1], "binding_referenciado_por_outro_arquivo")
        inventory = self.valid_inventory()
        inventory["binding"]["target_references"] = ["docker/docker-compose.yml"]
        self.assertEqual(evaluate(inventory)[1], "binding_referenciado_por_outro_arquivo")

    def test_refuses_secret_values_and_extra_fields_in_inventory(self):
        inventory = self.valid_inventory()
        inventory["api_key"] = "must-not-be-accepted"
        self.assertEqual(evaluate(inventory), (False, "inventario_com_campos_ausentes_ou_extras", None))

    def test_binding_removal_requires_post_release_health_exclusivity_and_same_inode(self):
        inventory = self.valid_inventory()
        current = {key: value for key, value in inventory["binding"].items()}
        current["compose_consumers"] = []
        current["host_references"] = []
        current["target_references"] = []
        self.assertEqual(binding_removal_allowed(
            inventory, current, runtime_healthy=True, compose_consumers=[], host_references=[], target_references=[]),
            (True, "binding_exclusivo_apto_a_remocao"))
        changed = dict(current, inode=456)
        self.assertEqual(binding_removal_allowed(
            inventory, changed, runtime_healthy=True, compose_consumers=[], host_references=[], target_references=[])[1],
            "binding_mudou_apos_inventario")
        self.assertEqual(binding_removal_allowed(
            inventory, current, runtime_healthy=False, compose_consumers=[], host_references=[], target_references=[])[1],
            "runtime_nao_saudavel")
        self.assertEqual(binding_removal_allowed(
            inventory, current, runtime_healthy=True, compose_consumers=["markina-gallery:api"], host_references=[], target_references=[])[1],
            "binding_ainda_referenciado")


if __name__ == "__main__":
    unittest.main()
