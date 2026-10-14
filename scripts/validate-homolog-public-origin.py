"""Valida HOMOLOG_PUBLIC_BASE_URL sem revelar seu valor nos logs."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlsplit


def valid_https_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        explicit_port = parsed.port
    except ValueError:
        return False

    if not hostname or explicit_port is not None:
        return False
    if parsed.scheme.lower() != "https" or parsed.username or parsed.password:
        return False
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return False
    if parsed.netloc.lower() != hostname.lower():
        return False
    return bool(
        re.fullmatch(
            r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
            hostname,
            re.IGNORECASE,
        )
    )


value = os.environ.get("HOMOLOG_PUBLIC_BASE_URL", "")
if not value or not valid_https_origin(value):
    print("Origem pública homologada ausente ou inválida", file=sys.stderr)
    raise SystemExit(1)
