"""Origem confiável para links públicos gerados no servidor."""

from __future__ import annotations

from ipaddress import ip_address
from os import getenv
from urllib.parse import urlsplit


class PublicOriginError(ValueError):
    """A origem configurada não é segura para links públicos."""


def public_app_origin(environment: str, *, local_fallback: str | None = None) -> str:
    origin = getenv("PUBLIC_APP_ORIGIN", "").strip() or getenv("MARKINA_PUBLIC_URL", "").strip()
    local_environment = environment.strip().lower() in {"development", "test", "local"}
    if not origin and local_environment and local_fallback:
        origin = local_fallback.strip()
    error = "URL pública da aplicação indisponível ou inválida para este ambiente."
    try:
        parsed = urlsplit(origin)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise PublicOriginError(error) from exc
    if (
        not hostname
        or parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query or parsed.fragment
        or any(char.isspace() for char in origin)
        or "\\" in origin or "%" in hostname
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise PublicOriginError(error)
    if not local_environment:
        try:
            public_host = ip_address(hostname).is_global
        except ValueError:
            public_host = (
                "." in hostname
                and not hostname.endswith((".localhost", ".local", ".internal"))
                and not all(part.isdigit() for part in hostname.split("."))
            )
        if parsed.scheme != "https" or not public_host:
            raise PublicOriginError(error)
    return origin.rstrip("/")
