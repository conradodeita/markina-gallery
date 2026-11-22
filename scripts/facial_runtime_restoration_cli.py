"""CLI restrita do operador de restauração facial."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from facial_runtime_restoration import (
    HEX,
    OPERATION,
    SHA,
    Approval,
    RestorationError,
    digest,
    execute,
    prepare,
)
from facial_runtime_restoration_host import RestorationHost


def _support_sha(value: str) -> str:
    if not SHA.fullmatch(value):
        raise argparse.ArgumentTypeError("SHA de suporte inválido")
    return value


def _operation(value: str) -> str:
    if not OPERATION.fullmatch(value):
        raise argparse.ArgumentTypeError("identificador de operação inválido")
    return value


def _fingerprint(value: str) -> str:
    if not HEX.fullmatch(value):
        raise argparse.ArgumentTypeError("fingerprint inválido")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="facial-runtime-restoration")
    commands = parser.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory", help="coleta fingerprint sanitizado")
    inventory.add_argument("--support-sha", required=True, type=_support_sha)

    staged = commands.add_parser("prepare", help="valida e sela o candidato revisado")
    staged.add_argument("--support-sha", required=True, type=_support_sha)
    staged.add_argument("--operation", required=True, type=_operation)

    phase = commands.add_parser("execute", help="executa uma fase fixa do operador")
    phase.add_argument("--support-sha", required=True, type=_support_sha)
    phase.add_argument("--operation", required=True, type=_operation)
    phase.add_argument("--phase", required=True, choices=("dark", "activate", "verify", "recover", "align-notifications", "rollback-notifications"))
    phase.add_argument("--fingerprint", required=True, type=_fingerprint)
    phase.add_argument("--allowlist", nargs="*", default=[])
    phase.add_argument("--stage", choices=("canary", "limited", "general"), default="canary")
    return parser


def _confirm(action: str, operation: str, input_fn: Callable[[str], str]) -> None:
    expected = f"CONFIRMO {action.upper()} {operation}"
    if input_fn is input and not sys.stdin.isatty():
        raise RestorationError("confirmacao_interativa_ausente")
    if input_fn(f"Digite exatamente: {expected}: ") != expected:
        raise RestorationError("confirmacao_divergente")


def _inventory_summary(value: dict) -> dict:
    services = value.get("services", {})
    return {
        "status": "inventoried",
        "operation": "inventory",
        "fingerprint": digest(value),
        "schema": value.get("schema"),
        "architecture": value.get("architecture"),
        "services": {
            name: {
                "status": item.get("status"),
                "health": item.get("health"),
                "image_id": item.get("image_id"),
            }
            for name, item in sorted(services.items())
            if isinstance(item, dict)
        },
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    host_factory: Callable[[str], object] | None = None,
    input_fn: Callable[[str], str] = input,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    try:
        args = build_parser().parse_args(argv)
        factory = host_factory or (lambda support_sha: RestorationHost(support_sha=support_sha))
        host = factory(args.support_sha)
        if args.command == "inventory":
            result = _inventory_summary(host.inventory())
        elif args.command == "prepare":
            _confirm("prepare", args.operation, input_fn)
            result = prepare(host, args.operation, host.candidate_manifest())
        else:
            if len(args.allowlist) > 1000:
                raise RestorationError("allowlist_excessiva")
            approval = Approval(args.fingerprint, tuple(args.allowlist), args.stage)
            _confirm(args.phase, args.operation, input_fn)
            result = execute(host, args.operation, args.phase, approval)
        print(json.dumps(result, sort_keys=True), file=output)
        return 0
    except RestorationError as error:
        print(json.dumps({"status": "refused", "reason": str(error)}, sort_keys=True), file=errors)
        return 2
    except (OSError, ValueError, TypeError, UnicodeError):
        print(json.dumps({"status": "refused", "reason": "entrada_ou_host_invalido"}, sort_keys=True), file=errors)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
