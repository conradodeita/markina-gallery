"""Fail the required CI aggregate when a classified validation did not pass."""

from __future__ import annotations

import os
import sys


def validate_results(values: dict[str, str]) -> list[str]:
    """Return blocking diagnostics for missing, skipped, or failed CI checks."""
    errors: list[str] = []
    if values.get("CI_SCOPE_RESULT") != "success":
        errors.append("CI scope classifier did not succeed")

    scopes = {
        "backend": "BACKEND",
        "frontend": "FRONTEND",
        "gemma": "GEMMA",
        "runtime-images": "RUNTIME_IMAGES",
    }
    for scope, prefix in scopes.items():
        required = values.get(f"{prefix}_REQUIRED")
        result = values.get(f"{prefix}_RESULT")
        if required not in {"true", "false"}:
            errors.append(f"Unknown or missing scope classification: {scope}")
        elif required == "true" and result != "success":
            errors.append(f"Required validation did not succeed: {scope} ({result or 'missing'})")
        elif result not in {"success", "skipped"}:
            errors.append(f"Validation failed: {scope} ({result or 'missing'})")

    for check in ("OPENSPEC_RESULT", "GITLEAKS_RESULT"):
        if values.get(check) != "success":
            errors.append(f"Always-required validation did not succeed: {check.removesuffix('_RESULT').lower()}")
    return errors


def main() -> int:
    errors = validate_results(dict(os.environ))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("All required and applicable CI validations succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
