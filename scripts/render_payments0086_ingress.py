"""Renderizacao pura da barreira; nunca instala configuracao ou publica servicos."""

import argparse
from pathlib import Path

UPSTREAMS = {"api", "payments0086-api-canary"}
ALLOWED_PATHS = "^/(healthz|api/health|api/infinitepay/return|api/infinitepay/webhook)$"


def render(server: str, *, upstream: str = "api", defer_webhook: bool = False) -> str:
    if upstream not in UPSTREAMS:
        raise ValueError("Upstream fora do plano0086.")
    if defer_webhook and upstream != "api":
        raise ValueError("Adiar webhook somente antes da instancia temporaria.")
    if server.count("server {") != 1 or "http {" in server:
        raise ValueError("Esperado um unico servidor Markina.")
    if server.count("proxy_pass http://api:8000;") != 2:
        raise ValueError("Contrato dos upstreams diverge da fonte revisada.")
    if "location = /api/infinitepay/webhook" in server:
        raise ValueError("A fonte ja tem tratamento proprio de webhook.")
    guard = '\n    if ($uri !~ "' + ALLOWED_PATHS + '") { return 503; }\n'
    if defer_webhook:
        guard += "    location = /api/infinitepay/webhook { return 400; }\n"
    guarded = server.replace("server {", "server {" + guard, 1)
    guarded = guarded.replace(
        "proxy_pass http://api:8000;", "proxy_pass http://" + upstream + ":8000;"
    )
    return (
        "worker_processes auto;\nevents { worker_connections 1024; }\nhttp {\n"
        + guarded
        + "\n}\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--upstream", choices=sorted(UPSTREAMS), default="api")
    parser.add_argument("--defer-webhook", action="store_true")
    args = parser.parse_args()
    print(
        render(
            args.source.read_text(encoding="utf-8"),
            upstream=args.upstream,
            defer_webhook=args.defer_webhook,
        ),
        end="",
    )
