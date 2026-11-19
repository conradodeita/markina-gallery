"""Summarize an exact GitHub Actions CI run with redacted failure details."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b[A-Za-z0-9_.-]*(?:token|password|passwd|secret|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|credential|database[_-]?url|dsn)[A-Za-z0-9_.-]*)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
TOKEN_VALUE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
COMMON_SECRET = re.compile(
    r"\b(?:(?:AKIA|ASIA)[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|(?:sk|npm)_[A-Za-z0-9_-]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,})\b"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
EMAIL_VALUE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
TRACEBACK_END = re.compile(
    r"(?:^|[\t ])(?:[A-Za-z_][\w.]*\s*:\s*\S|AssertionError(?:\b|:))"
)
URL_CREDENTIALS = re.compile(r"(?i)(https?://)[^/\s:@]+:[^@\s/]+@")
ERROR_MARKER = re.compile(
    r"Traceback \(most recent call last\)|##\[error\]|\b(?:AssertionError|RuntimeError|TimeoutError|FAILED|FAILURE|ERROR)\b",
    re.IGNORECASE,
)


def timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def elapsed_seconds(start: str | None, end: str | None) -> int | None:
    begin, finish = timestamp(start), timestamp(end)
    if begin is None or finish is None:
        return None
    return max(0, int((finish - begin).total_seconds()))


def redact_line(value: str) -> str:
    line = ANSI.sub("", value).rstrip()
    if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", line):
        return "<redacted-key-material>"
    line = SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", line)
    line = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer <redacted>", line)
    line = TOKEN_VALUE.sub("<redacted-token>", line)
    line = COMMON_SECRET.sub("<redacted-token>", line)
    line = URL_CREDENTIALS.sub(r"\1<redacted>@", line)
    line = EMAIL_VALUE.sub("<redacted-email>", line)
    return line[:1000]


def first_relevant_error(log: str, *, max_lines: int = 6) -> list[str]:
    lines = ANSI.sub("", log).splitlines()
    index = next((i for i, line in enumerate(lines)
                  if ERROR_MARKER.search(line)
                  and "Process completed with exit code" not in line), None)
    if index is None:
        index = next((i for i, line in enumerate(lines)
                      if "Process completed with exit code" in line), None)
    if index is None:
        return []
    end = index
    if "Traceback (most recent call last)" in lines[index]:
        exception_index = next(
            (position for position in range(index + 1, len(lines))
             if TRACEBACK_END.search(lines[position])),
            None,
        )
        if exception_index is not None:
            end = exception_index
    is_traceback = "Traceback (most recent call last)" in lines[index]
    if is_traceback:
        start = max(index, end - max_lines + 1)
    else:
        start = max(0, index - 1)
        end = min(len(lines) - 1, start + max_lines - 1)
    return [redact_line(line) for line in lines[start:end + 1]]


def summarize_job(job: dict, log_reader: Callable[[int], str] | None = None) -> dict:
    steps = job.get("steps") or []
    failed_steps = [step for step in steps if step.get("conclusion") in {
        "failure", "timed_out", "action_required",
    }]
    failure = failed_steps[0] if failed_steps else None
    error_lines: list[str] = []
    if job.get("conclusion") in {"failure", "timed_out"} and log_reader:
        try:
            error_lines = first_relevant_error(log_reader(int(job["id"])))
        except (OSError, subprocess.SubprocessError, ValueError):
            error_lines = []
    return {
        "name": job.get("name"),
        "conclusion": job.get("conclusion"),
        "duration_seconds": elapsed_seconds(job.get("started_at"), job.get("completed_at")),
        "url": job.get("html_url"),
        "failed_stage": ({
            "name": failure.get("name"),
            "duration_seconds": elapsed_seconds(failure.get("started_at"), failure.get("completed_at")),
        } if failure else None),
        "first_error_lines": error_lines,
    }


def build_report(run: dict, jobs: list[dict], artifacts: list[dict], repo: str,
                 log_reader: Callable[[int], str] | None = None) -> dict:
    summarized_jobs = [summarize_job(job, log_reader) for job in jobs]
    summarized_jobs.sort(key=lambda item: item["duration_seconds"] or -1, reverse=True)
    return {
        "workflow": run.get("name"),
        "run_id": run.get("id"),
        "event": run.get("event"),
        "branch": run.get("head_branch"),
        "sha": run.get("head_sha"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "queue_seconds": elapsed_seconds(run.get("created_at"), run.get("run_started_at")),
        "duration_seconds": elapsed_seconds(run.get("run_started_at"), run.get("updated_at")),
        "url": run.get("html_url"),
        "jobs": summarized_jobs,
        "artifacts": [
            {
                "name": artifact.get("name"),
                "expired": artifact.get("expired"),
                "size_bytes": artifact.get("size_in_bytes"),
                "url": f"https://github.com/{repo}/actions/runs/{run.get('id')}/artifacts/{artifact.get('id')}",
            }
            for artifact in artifacts
        ],
    }


def gh_json(*args: str) -> object:
    result = subprocess.run(["gh", *args], capture_output=True, text=True,
                            timeout=90, check=False)
    if result.returncode != 0:
        raise RuntimeError("GitHub CLI request failed; check `gh auth status` and repository access")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("GitHub CLI returned invalid JSON") from error


def repository_name() -> str:
    result = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
                            capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Unable to identify the current GitHub repository")
    return result.stdout.strip()


def find_run_id(sha: str, workflow: str) -> int:
    runs = gh_json("run", "list", "--workflow", workflow, "--commit", sha,
                   "--limit", "100", "--json", "databaseId,headSha,createdAt")
    if not isinstance(runs, list):
        raise TypeError("GitHub returned an invalid run list")
    matching = [run for run in runs if run.get("headSha", "").lower() == sha.lower()]
    if not matching:
        raise RuntimeError(f"No {workflow} run found for exact head SHA {sha}")
    matching.sort(key=lambda run: run.get("createdAt", ""), reverse=True)
    return int(matching[0]["databaseId"])


def read_failed_job_log(run_id: int, job_id: int) -> str:
    result = subprocess.run(["gh", "run", "view", str(run_id), "--job", str(job_id), "--log-failed"],
                            capture_output=True, text=True, timeout=90, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def collect(run_id: int, repo: str) -> dict:
    prefix = f"repos/{repo}/actions/runs/{run_id}"
    run = gh_json("api", prefix)
    job_data = gh_json("api", f"{prefix}/jobs?per_page=100")
    artifact_data = gh_json("api", f"{prefix}/artifacts?per_page=100")
    if not isinstance(run, dict) or not isinstance(job_data, dict) or not isinstance(artifact_data, dict):
        raise TypeError("GitHub returned an invalid Actions run response")
    jobs = job_data.get("jobs")
    artifacts = artifact_data.get("artifacts")
    if not isinstance(jobs, list) or not isinstance(artifacts, list):
        raise TypeError("GitHub run response is missing jobs or artifacts")
    return build_report(run, jobs, artifacts, repo,
                       lambda job_id: read_failed_job_log(run_id, job_id))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-id", type=int, help="Read one specific Actions run")
    source.add_argument("--sha", help="Find the newest CI run for this exact head SHA")
    parser.add_argument("--workflow", default="CI", help="Workflow name when resolving --sha")
    args = parser.parse_args()
    if args.run_id is not None and args.run_id < 1:
        parser.error("--run-id must be positive")
    if args.sha is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", args.sha):
        parser.error("--sha must be a full 40-character Git SHA")
    try:
        run_id = args.run_id if args.run_id is not None else find_run_id(args.sha, args.workflow)
        report = collect(run_id, repository_name())
    except (RuntimeError, OSError, subprocess.SubprocessError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("conclusion") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
