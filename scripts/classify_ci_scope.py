"""Classify changed repository paths into the CI validations they require."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath
import sys
from typing import Iterable


SCOPES = ("backend", "frontend", "backend_image", "frontend_image", "preview")


def classify(paths: Iterable[str], *, full: bool = False) -> dict[str, bool]:
    """Return conservative CI scopes; unknown and infrastructure paths run all."""
    result = {scope: bool(full) for scope in SCOPES}
    if full:
        return result

    for raw_path in paths:
        normalized = raw_path.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        path = PurePosixPath(normalized)
        name = path.as_posix()

        if (
            name.startswith(".github/workflows/")
            or name == ".github/dependabot.yml"
            or name == "scripts/classify_ci_scope.py"
            or name.startswith("scripts/")
            or name.startswith("docker/")
            or name in {"pyproject.toml", "package.json", "package-lock.json"}
        ):
            return {scope: True for scope in SCOPES}

        if name.startswith(("openspec/", "docs/")) or name in {
            "README.md",
            "ROADMAP_ARQUITETURA.md",
            "INSTRUCOES_EXECUTOR_CLAUDE_CODE.md",
            "DIRETRIZES_FRONTEND_MARKINA_GALLERY.md",
        }:
            continue

        if name.startswith("frontend/"):
            result["frontend"] = True
            result["frontend_image"] = True

        if name.startswith("backend/"):
            result["backend"] = True

            if name == "backend/Dockerfile.preview-adjustment":
                result["preview"] = True
            if name.startswith("backend/app/preview_adjustment/"):
                result["preview"] = True

            if name in {"backend/requirements.txt", "backend/requirements-push.txt"}:
                result["backend_image"] = True
                result["preview"] = True
            if name == "backend/Dockerfile":
                result["backend_image"] = True

            continue

        if name.startswith("frontend/"):
            continue

        # Any newly introduced top-level/runtime area must opt into an explicit
        # rule before it can avoid the full validation matrix.
        return {scope: True for scope in SCOPES}

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Run every CI scope")
    parser.add_argument("--output", help="Write GitHub Actions output variables here")
    parser.add_argument("paths", nargs="*", help="Changed repository paths")
    args = parser.parse_args()
    paths = args.paths or (line.rstrip("\n") for line in sys.stdin)
    result = classify(paths, full=args.full)

    if args.output:
        with open(args.output, "a", encoding="utf-8") as output:
            for scope, required in result.items():
                output.write(f"{scope}={'true' if required else 'false'}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
