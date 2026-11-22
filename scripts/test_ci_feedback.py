import unittest

from scripts.ci_feedback import build_report, first_relevant_error, redact_line


class CIFeedbackTests(unittest.TestCase):
    def test_redacts_secrets_urls_tokens_and_emails(self):
        github_token = "ghp_" + "a" * 32
        bearer = "eyJ" + "a" * 12
        aws_access_key = "AKIA" + "A" * 16
        jwt = ".".join(("eyJ" + "a" * 10, "b" * 12, "c" * 12))
        openai_key = "sk-" + "x" * 24
        database_url = "postgresql://" + "user" + ":" + "pass" + "@db.invalid/pyp"
        url = "https://" + "user" + ":" + "pass" + "@example.test/path"
        email = "owner" + "@" + "example.test"
        value = (
            f"TOKEN={github_token} Authorization: Bearer {bearer} "
            f"PRODUCTION_SSH_PRIVATE_KEY={openai_key} AWS_SECRET_ACCESS_KEY={aws_access_key} "
            f"DATABASE_URL={database_url} {url} {email} {jwt}"
        )
        result = redact_line(value)
        for sensitive in (github_token, bearer, openai_key, aws_access_key, database_url, jwt,
                          url.split("//", 1)[1].split("@", 1)[0], email):
            self.assertNotIn(sensitive, result)
        self.assertIn("<redacted>", result)

    def test_private_key_material_is_removed_and_traceback_keeps_exception(self):
        self.assertEqual("<redacted-key-material>",
                         redact_line("-----BEGIN OPENSSH PRIVATE KEY-----"))
        log = "Traceback (most recent call last):\n" + "".join(
            f'  File "module.py", line {number}, in run\n' for number in range(1, 10)
        ) + "RuntimeError: useful failure\n"
        lines = first_relevant_error(log)
        self.assertLessEqual(len(lines), 6)
        self.assertIn("RuntimeError: useful failure", lines[-1])

    def test_extracts_the_first_error_context_with_redaction(self):
        log = (
            "step output TOKEN=synthetic-secret\n"
            "Traceback (most recent call last):\n"
            "  File \"scripts/check.py\", line 10, in main\n"
            "RuntimeError: failed for owner@example.test password=hunter2\n"
            "##[error]Process completed with exit code 1.\n"
        )
        lines = first_relevant_error(log)
        joined = "\n".join(lines)
        self.assertIn("Traceback (most recent call last)", joined)
        self.assertIn("RuntimeError", joined)
        for sensitive in ("synthetic-secret", "owner@example.test", "hunter2"):
            self.assertNotIn(sensitive, joined)

    def test_report_includes_sha_job_stage_durations_and_artifact_links(self):
        run = {
            "id": 12,
            "name": "CI",
            "event": "pull_request",
            "head_branch": "feature/test",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-11-18T10:00:00Z",
            "run_started_at": "2026-11-18T10:00:20Z",
            "updated_at": "2026-11-18T10:03:00Z",
            "html_url": "https://github.com/acme/repo/actions/runs/12",
        }
        jobs = [{
            "id": 34,
            "name": "backend-quality",
            "conclusion": "failure",
            "started_at": "2026-11-18T10:00:30Z",
            "completed_at": "2026-11-18T10:02:30Z",
            "html_url": "https://github.com/acme/repo/actions/runs/12/job/34",
            "steps": [{
                "name": "Backend lint",
                "conclusion": "success",
                "started_at": "2026-11-18T10:00:30Z",
                "completed_at": "2026-11-18T10:01:00Z",
            }, {
                "name": "Contract test",
                "conclusion": "failure",
                "started_at": "2026-11-18T10:01:00Z",
                "completed_at": "2026-11-18T10:02:00Z",
            }],
        }]
        artifacts = [{"id": 56, "name": "backend-shard-0", "expired": False,
                      "size_in_bytes": 256, "archive_download_url": "private-do-not-copy"}]
        report = build_report(run, jobs, artifacts, "acme/repo",
                              lambda job_id: "Traceback (most recent call last):\nRuntimeError: failed")
        self.assertEqual("a" * 40, report["sha"])
        self.assertEqual(20, report["queue_seconds"])
        self.assertEqual(160, report["duration_seconds"])
        self.assertEqual("Contract test", report["jobs"][0]["failed_stage"]["name"])
        self.assertEqual(60, report["jobs"][0]["failed_stage"]["duration_seconds"])
        self.assertIn("RuntimeError", "\n".join(report["jobs"][0]["first_error_lines"]))
        self.assertEqual("https://github.com/acme/repo/actions/runs/12/artifacts/56",
                         report["artifacts"][0]["url"])
        self.assertNotIn("private-do-not-copy", str(report))


if __name__ == "__main__":
    unittest.main()
