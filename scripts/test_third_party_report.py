from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scripts import third_party_report as monitor


class ThirdPartyReportTests(unittest.TestCase):
    def test_pins_are_read_from_current_code_and_keep_gemma_as_revision(self):
        pins = monitor.pinned_versions()
        self.assertEqual(pins["LightCraft"], "0.6.0")
        self.assertEqual(pins["RawTherapee"], "5.9")
        self.assertRegex(pins["EmbeddingGemma 2"], r"^[0-9a-f]{40}$")
        self.assertEqual(monitor.inventory_count(), 68)

    def test_specialized_versions_compare_semver_and_model_revision_without_guessing(self):
        release = {"tag_name": "v5.12.1"}
        self.assertTrue(monitor.parse_specialized_candidate(monitor.WATCHLIST[1], "5.9", release)["newer"])
        same = {"tag_name": "v0.6.0"}
        self.assertFalse(monitor.parse_specialized_candidate(monitor.WATCHLIST[0], "0.6.0", same)["newer"])
        model = {"sha": "b" * 40}
        self.assertTrue(monitor.parse_specialized_candidate(monitor.WATCHLIST[2], "a" * 40, model)["newer"])
        with self.assertRaises(monitor.SourceError):
            monitor.parse_specialized_candidate(monitor.WATCHLIST[1], "stable", {"tag_name": "latest"})

    def test_digest_image_and_range_versions_are_not_used_as_runtime_evidence(self):
        compose = (monitor.ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8")
        image_lines = [line.strip().split("image:", 1)[1].strip() for line in compose.splitlines() if "image:" in line]
        self.assertTrue(any("@sha256:" in line for line in image_lines))
        self.assertTrue(any("nginx:1.27-alpine" in line for line in image_lines))
        self.assertIn("fastapi>=", (monitor.ROOT / "backend/requirements.txt").read_text(encoding="utf-8"))
        image, tag, digest = monitor.parse_image_reference(
            "evoapicloud/evolution-api:v2.3.7@sha256:" + "a" * 64
        )
        self.assertEqual((image, tag, digest), ("evoapicloud/evolution-api", "v2.3.7", "sha256:" + "a" * 64))
        self.assertEqual(monitor.parse_image_reference("nginx:1.27-alpine"), ("nginx", "1.27-alpine", None))
        self.assertEqual(monitor.parse_image_reference("registry.example:5000/team/image"), ("registry.example:5000/team/image", "latest", None))
        with self.assertRaises(monitor.SourceError):
            monitor.parse_image_reference("nginx:tag@sha256:invalid")
        # The report labels local pins and upstream candidates; it never queries production runtime.

    def test_pagination_follows_all_pages_and_rejects_incomplete_result(self):
        calls = []

        def fake_fetch(url, token):
            calls.append(url)
            if url.endswith("page=1"):
                return [{"id": index} for index in range(100)]
            return [{"id": 100}]

        self.assertEqual(len(monitor.paginate_github("https://api.github.com/test", "token", fake_fetch)), 101)
        self.assertEqual(len(calls), 2)

        def endless(url, token):
            return [{}] * 100

        with self.assertRaisesRegex(monitor.SourceError, "limite de páginas"):
            monitor.paginate_github("https://api.github.com/test", "token", endless)

    def test_report_groups_security_alerts_and_dependabot_candidates_with_risk(self):
        def fake_fetch(url, token):
            if "/pulls?" in url:
                return [{"user": {"login": "dependabot[bot]"}, "title": "Bump next from 16.4.0 to 17.0.0", "html_url": "https://github.com/org/repo/pull/3"}]
            if "/dependabot/alerts?" in url:
                return [{
                    "dependency": {"package": {"name": "cryptography", "ecosystem": "pip"}},
                    "security_vulnerability": {"vulnerable_version_range": "< 46.0", "first_patched_version": {"identifier": "46.0"}},
                    "security_advisory": {"severity": "high"},
                    "html_url": "https://github.com/org/repo/security/dependabot/1",
                }]
            if "storytold/lightcraft" in url:
                return {"tag_name": "v0.6.0"}
            if "RawTherapee" in url:
                return {"tag_name": "v5.9"}
            if "huggingface.co" in url:
                return {"sha": monitor.pinned_versions()["EmbeddingGemma 2"]}
            raise AssertionError("unexpected source")

        report, failed = monitor.build_report("org/repo", "synthetic-token", fake_fetch, datetime(2026, 10, 19, tzinfo=timezone.utc))
        self.assertFalse(failed)
        self.assertIn("2026-10-19T00:00:00+00:00", report)
        self.assertIn("P1 · HIGH · cryptography (pip)", report)
        self.assertIn("`16.4.0` → `17.0.0`", report)
        self.assertIn("testar api, build", report.lower())
        self.assertIn("nenhuma versão/revisão diferente", report)
        self.assertNotIn("merge --auto", report)

    def test_source_failure_is_distinct_from_zero_candidates_and_safe_to_print(self):
        def failing_fetch(url, token):
            raise monitor.SourceError("consulta falhou (HTTP 403)")

        report, failed = monitor.build_report("org/repo", "synthetic-token", failing_fetch)
        self.assertTrue(failed)
        self.assertIn("NÃO CONFIRMADO", report)
        self.assertIn("HTTP 403", report)
        self.assertNotIn("synthetic-token", report)
        with self.assertRaises(monitor.SourceError):
            monitor.build_report("invalid repo", "token", failing_fetch)

    def test_disabled_alert_endpoint_is_not_reported_as_zero_alerts_or_query_failure(self):
        def fake_fetch(url, token):
            if "/pulls?" in url:
                return []
            if "/dependabot/alerts?" in url:
                raise monitor.SourceError("consulta falhou (HTTP 403)", state="disabled")
            if "storytold/lightcraft" in url:
                return {"tag_name": "v0.6.0"}
            if "RawTherapee" in url:
                return {"tag_name": "v5.9"}
            if "huggingface.co" in url:
                return {"sha": monitor.pinned_versions()["EmbeddingGemma 2"]}
            raise AssertionError("unexpected source")

        report, failed = monitor.build_report("org/repo", "synthetic-token", fake_fetch)
        self.assertFalse(failed)
        self.assertIn("DESABILITADO / NÃO CONFIRMADO", report)
        self.assertIn("Ação pendente: habilitar Dependabot alerts/security updates", report)
        self.assertNotIn("Nenhum alerta aberto foi retornado", report)

    def test_monitoring_files_cannot_write_workflows_or_enable_automerging(self):
        workflow = (monitor.ROOT / ".github/workflows/third-party-weekly-report.yml").read_text(encoding="utf-8")
        config = (monitor.ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertIn("security-events: read", workflow)
        self.assertNotRegex(workflow + config, r"(?i)enable-auto-merge|mergeable|gh pr merge")
        triggers = workflow.split("on:", 1)[1].split("permissions:", 1)[0]
        self.assertIn("schedule:", triggers)
        self.assertIn("workflow_dispatch:", triggers)
        self.assertNotRegex(workflow, r"(?i)ssh\s|docker compose|alembic|deploy-homolog|deploy-prod")
        self.assertIn("package-ecosystem: pip", config)
        self.assertIn("package-ecosystem: npm", config)
        self.assertIn("package-ecosystem: docker", config)
        self.assertIn("package-ecosystem: github-actions", config)
        self.assertIn("specialized-runtime:", config)
        self.assertIn("update-types:", config)

    def test_inventory_distinguishes_gemma_service_assets_and_actual_inference(self):
        inventory = (monitor.ROOT / "docs/THIRD-PARTY-INVENTORY.md").read_text(encoding="utf-8")
        self.assertIn("11/10/2026", inventory)
        self.assertIn("zero jobs", inventory)
        self.assertIn("não prova", inventory.lower())
        self.assertIn("carrega o modelo sob demanda", inventory)
        self.assertIn("68 itens rastreáveis", inventory)


if __name__ == "__main__":
    unittest.main()
