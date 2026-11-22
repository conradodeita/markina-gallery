from __future__ import annotations

import re
import unittest
from datetime import UTC, datetime

from scripts import third_party_report as monitor


class ThirdPartyReportTests(unittest.TestCase):
    def test_rawtherapee_pin_is_read_from_the_preview_worker_image(self):
        pins = monitor.pinned_versions()
        self.assertEqual(pins, {"RawTherapee": "5.13"})
        self.assertEqual(monitor.inventory_count(), 72)

    def test_specialized_versions_compare_semver_and_model_revision_without_guessing(self):
        release = {"tag_name": "v5.14"}
        self.assertTrue(monitor.parse_specialized_candidate(monitor.WATCHLIST[0], "5.13", release)["newer"])
        same = {"tag_name": "v5.13"}
        self.assertFalse(monitor.parse_specialized_candidate(monitor.WATCHLIST[0], "5.13", same)["newer"])
        with self.assertRaises(monitor.SourceError):
            monitor.parse_specialized_candidate(monitor.WATCHLIST[0], "5.13", {"tag_name": "latest"})

    def test_nginx_image_is_version_independent_and_remains_monitored(self):
        compose = (monitor.ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8")
        nginx_image = monitor.nginx_image_reference(compose)
        self.assertRegex(nginx_image, r"^nginx:\d+\.\d+(?:\.\d+)?-alpine$")
        inventory = (monitor.ROOT / "docs/THIRD-PARTY-INVENTORY.md").read_text(encoding="utf-8")
        self.assertRegex(inventory, r"(?m)^\| 05 \| Nginx \| `nginx:[^`]+`, Compose \|")
        dependabot = (monitor.ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        compose_ecosystem = re.search(
            r"(?ms)^  - package-ecosystem: docker-compose\s+directory: /docker\s+schedule:",
            dependabot,
        )
        self.assertIsNotNone(compose_ecosystem)

        image_lines = [line.strip().split("image:", 1)[1].strip() for line in compose.splitlines() if "image:" in line]
        self.assertTrue(any("@sha256:" in line for line in image_lines))
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

    def test_nginx_image_reference_accepts_future_numeric_alpine_versions(self):
        for tag in ("1.27-alpine", "1.31-alpine", "1.31.2-alpine"):
            with self.subTest(tag=tag):
                compose = f"services:\n  nginx:\n    image: nginx:{tag}\n"
                self.assertEqual(monitor.nginx_image_reference(compose), f"nginx:{tag}")

    def test_nginx_image_reference_rejects_missing_or_policy_violating_declarations(self):
        missing_service = "services:\n  web:\n    image: nginx:1.31-alpine\n"
        missing_image = "services:\n  nginx:\n    ports:\n      - 8080:80\n"
        for compose in (missing_service, missing_image):
            with self.subTest(compose=compose), self.assertRaises(monitor.SourceError):
                monitor.nginx_image_reference(compose)

        invalid_references = (
            "nginx",
            "nginx:latest",
            "nginx:1.31",
            "nginx:one-alpine",
            "nginx:1.31-alpine3.22",
            "example/nginx:1.31-alpine",
            "nginx:1.31-alpine@sha256:invalid",
        )
        for reference in invalid_references:
            with self.subTest(reference=reference), self.assertRaises(monitor.SourceError):
                monitor.nginx_image_reference(f"services:\n  nginx:\n    image: {reference}\n")

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
            if "RawTherapee" in url:
                return {"tag_name": "v5.13"}
            raise AssertionError("unexpected source")

        report, failed = monitor.build_report("org/repo", "synthetic-token", fake_fetch, datetime(2026, 10, 19, tzinfo=UTC))
        self.assertFalse(failed)
        self.assertIn("2026-10-19T00:00:00+00:00", report)
        self.assertIn("P1 · HIGH · cryptography (pip)", report)
        self.assertIn("`16.4.0` → `17.0.0`", report)
        self.assertIn("declarado `5.13` em `backend/Dockerfile.preview-adjustment`", report)
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
            if "RawTherapee" in url:
                return {"tag_name": "v5.13"}
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
        self.assertIn("package-ecosystem: docker-compose\n    directory: /docker", config)
        self.assertIn("package-ecosystem: github-actions", config)
        self.assertNotIn("package-ecosystem: docker\n    directory: /docker", config)
        compose_manifest_pattern = re.compile(r"^(docker-)?compose(-[\w]+)?(\.[\w-]+)?\.ya?ml$", re.IGNORECASE)
        compose_manifests = sorted(
            path.name for path in (monitor.ROOT / "docker").iterdir()
            if path.is_file() and compose_manifest_pattern.fullmatch(path.name)
        )
        self.assertEqual(
            compose_manifests,
            [
                "docker-compose.local.yml",
                "docker-compose.preview-adjustment.yml",
                "docker-compose.system-monitor.yml",
                "docker-compose.yml",
            ],
        )
        for group in (
            "next-react-compatible:",
            "frontend-testing-compatible:",
            "web-push-compatible:",
            "face-runtime-compatible:",
        ):
            self.assertIn(group, config)
        self.assertEqual(config.count("open-pull-requests-limit: 1"), 6)
        self.assertNotIn("actions-compatible:", config)
        self.assertNotIn("security-updates", config)
        self.assertNotRegex(config, r"(?m)^\s+- major$")
        self.assertIn("update-types:", config)

    def test_inventory_records_historical_engine_retirement_and_current_runtime(self):
        inventory = (monitor.ROOT / "docs/THIRD-PARTY-INVENTORY.md").read_text(encoding="utf-8")
        self.assertIn("aposentado", inventory.lower())
        self.assertIn("5.13", inventory)
        self.assertIn("72 itens rastreáveis", inventory)


if __name__ == "__main__":
    unittest.main()
