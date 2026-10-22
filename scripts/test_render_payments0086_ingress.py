import unittest
from pathlib import Path

from render_payments0086_ingress import render

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "docker/nginx/nginx.conf").read_text(encoding="utf-8")


class IngressTests(unittest.TestCase):
    def test_initial_barrier_defers_webhook_without_opening_writes(self):
        result = render(SOURCE, defer_webhook=True)
        self.assertIn("api/infinitepay/return|api/infinitepay/webhook", result)
        self.assertIn("location = /api/infinitepay/webhook { return 400; }", result)
        self.assertIn("return 503", result)
        self.assertEqual(result.count("proxy_pass http://api:8000;"), 2)

    def test_temporary_api_accepts_callbacks_without_retry_override(self):
        result = render(SOURCE, upstream="payments0086-api-canary")
        self.assertNotIn("return 400", result)
        self.assertEqual(
            result.count("proxy_pass http://payments0086-api-canary:8000;"), 2
        )
        self.assertNotIn("proxy_pass http://api:8000;", result)

    def test_arbitrary_target_or_unreviewed_server_is_rejected(self):
        for target in ("evil.example", "api:9000", "http://api", "api; return 200"):
            with self.assertRaises(ValueError):
                render(SOURCE, upstream=target)
        for source in (
            "http {" + SOURCE,
            SOURCE + "server {",
            SOURCE.replace("api:8000", "api:9999"),
        ):
            with self.assertRaises(ValueError):
                render(source)
        with self.assertRaises(ValueError):
            render(SOURCE, upstream="payments0086-api-canary", defer_webhook=True)


if __name__ == "__main__":
    unittest.main()
