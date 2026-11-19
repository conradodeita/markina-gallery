"""Validate the lightweight backend quality gate and optional product suite."""

from __future__ import annotations

import os
import sys


def validate_backend_results(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if values.get("CI_SCOPE_RESULT") != "success":
        errors.append("CI scope classifier did not succeed")
    if values.get("QUALITY_RESULT") != "success":
        errors.append(f"Backend quality gate did not succeed ({values.get('QUALITY_RESULT') or 'missing'})")

    required = values.get("TESTS_REQUIRED")
    result = values.get("TESTS_RESULT")
    if required not in {"true", "false"}:
        errors.append("Unknown or missing backend product-test scope")
    elif required == "true" and result != "success":
        errors.append(f"Required backend product tests did not succeed ({result or 'missing'})")
    elif required == "false" and result != "skipped":
        errors.append(f"Unselected backend product tests did not skip ({result or 'missing'})")
    return errors


def main() -> int:
    errors = validate_backend_results(dict(os.environ))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Backend quality gate and selected product-test scope passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
