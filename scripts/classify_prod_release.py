#!/usr/bin/env python3
"""Classify main changes so app and facial releases never share approval."""

from __future__ import annotations

import argparse
import os
import subprocess

APP_RUNTIME = {
    "backend/app/main.py",
    "backend/app/statistics_report.py",
    "frontend/app/globals.css",
    "frontend/app/admin/statistics/page.tsx",
}
FACIAL_RUNTIME = {
    "backend/app/auth.py",
    "backend/app/facial/config.py",
    "backend/app/facial/provider.py",
    "backend/app/facial/reference.py",
    "backend/app/facial/search.py",
    "backend/app/facial/search_worker.py",
    "backend/migrations/versions/20261016_0082_facial_conditional_consent.py",
    "frontend/app/facial-search-client.ts",
    "frontend/app/public-galleries/facial-search-panel.tsx",
}


def changed_paths(base: str, target: str) -> set[str]:
    result = subprocess.run(["git", "diff", "--name-only", base, target], check=True,
                            capture_output=True, text=True)
    return set(result.stdout.splitlines())


def classify(changed: set[str]) -> str:
    app = bool(changed & APP_RUNTIME)
    facial = bool(changed & FACIAL_RUNTIME)
    if app and facial:
        return "mixed"
    if app:
        return "app"
    if facial:
        return "facial"
    return "none"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    scope = classify(changed_paths(args.base, args.target))
    print(f"release_scope={scope}")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"release_scope={scope}\n")
    return 1 if scope == "mixed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
