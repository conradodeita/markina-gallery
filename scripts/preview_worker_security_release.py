#!/usr/bin/env python3
"""Preflight/release/recovery entrypoint for preview worker security update.

No mode is executed as part of local tests. Release requires an exact approved
fingerprint, callback policy and explicit maintenance-window acknowledgement.
"""

from __future__ import annotations

import argparse
import json
import re

from preview_worker_maintenance_flow import Approval, MaintenanceError, execute
from preview_worker_security_release_host import HostError, PreviewWorkerSecurityHost


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("mode", choices=("inventory", "release", "recover"))
    value.add_argument("--source-sha", default="")
    value.add_argument("--candidate-image-id", default="")
    value.add_argument(
        "--expected-compose-version", choices=("2.35.1", "5.6.1"), default="2.35.1"
    )
    value.add_argument(
        "--callback-policy",
        choices=("provider_retry_proven", "callback_outage_accepted", "unreviewed"),
        default="unreviewed",
    )
    value.add_argument("--approve-window", action="store_true")
    value.add_argument("--approval-fingerprint", default="")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    host = PreviewWorkerSecurityHost(
        expected_sha=args.source_sha,
        candidate_image_id=args.candidate_image_id,
        callback_policy=args.callback_policy,
        window_approved=args.approve_window,
        expected_compose_version=args.expected_compose_version,
    )
    try:
        if args.mode == "inventory":
            with host.lock():
                report = host.preflight()
            print(
                "preview_worker_inventory="
                + json.dumps(report, sort_keys=True, separators=(",", ":"))
            )
            print("approval_fingerprint=" + report["fingerprint"])
            return 0
        if args.mode == "recover":
            with host.lock():
                host.recover_inflight()
            print("preview_worker_recovery=success")
            return 0
        if not re.fullmatch(r"[0-9a-f]{64}", args.approval_fingerprint):
            raise HostError("fingerprint_aprovado_ausente_ou_invalido")
        approval = Approval(
            args.approval_fingerprint,
            args.callback_policy,
            args.approve_window,
        )
        execute(host, approval)
        print("preview_worker_security_release=success")
        return 0
    except (HostError, MaintenanceError) as exc:
        print("preview_worker_security_release=blocked")
        print("criterion=" + str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - sanitize unexpected failures at the CLI boundary
        safe_type = (
            type(exc).__name__
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,39}", type(exc).__name__)
            else "Exception"
        )
        print("preview_worker_security_release=blocked")
        print("criterion=unexpected_error;class=" + safe_type)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
