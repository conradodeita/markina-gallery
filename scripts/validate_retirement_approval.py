"""Validate an explicit production approval against a fresh retirement inventory."""

from __future__ import annotations

import os
import re
import sys

FINGERPRINT = re.compile(r"[0-9a-f]{64}")


def validate_approval(requested: str | None, observed: str | None) -> None:
    """Reject missing, malformed, or stale inventory approval fingerprints."""
    if requested is None or FINGERPRINT.fullmatch(requested) is None:
        raise ValueError("fingerprint aprovado ausente ou inválido")
    if observed is None or FINGERPRINT.fullmatch(observed) is None:
        raise ValueError("fingerprint do inventário ausente ou inválido")
    if requested != observed:
        raise ValueError("inventário mudou desde a aprovação")


def main() -> int:
    try:
        validate_approval(
            os.environ.get("REQUESTED_APPROVAL_FINGERPRINT"),
            os.environ.get("PREFLIGHT_FINGERPRINT"),
        )
    except ValueError as exc:
        print(f"Aposentadoria bloqueada: {exc}", file=sys.stderr)
        return 1
    print("approved_fingerprint_matches=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
