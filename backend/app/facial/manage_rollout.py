"""CLI da operação protegida de rollout facial."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.auth import SessionLocal
from app.facial.config import facial_settings_from_environment
from app.facial.rollout_operation import (
    REQUIRED_GATES,
    FacialRolloutOperationProof,
    execute_protected_rollout_operation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("activate", "suspend"), required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument(
        "--stage", choices=("dark", "canary", "limited", "general"), required=True
    )
    parser.add_argument("--sha", required=True)
    parser.add_argument("--inventory-ref", required=True)
    parser.add_argument("--backup-ref", required=True)
    parser.add_argument("--gate-set-version", required=True)
    parser.add_argument("--approved-gates", required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--actor-admin-id", type=UUID, required=True)
    args = parser.parse_args()
    proof = FacialRolloutOperationProof(
        action=args.action,
        environment=args.environment,
        stage=args.stage,
        deployment_sha=args.sha,
        inventory_reference=args.inventory_ref,
        backup_reference=args.backup_ref,
        gate_set_version=args.gate_set_version,
        approved_gates=frozenset(
            value.strip() for value in args.approved_gates.split(",") if value.strip()
        ),
        allowlist=tuple(
            UUID(value.strip()) for value in args.allowlist.split(",") if value.strip()
        ),
        confirmation=args.confirmation,
        actor_admin_id=args.actor_admin_id,
    )
    settings = facial_settings_from_environment(verify_runtime_assets=False)
    with SessionLocal() as db:
        operation = execute_protected_rollout_operation(
            db, proof=proof, settings=settings
        )
        db.commit()
        print(
            json.dumps(
                {
                    "operation_id": str(operation.id),
                    "action": operation.action,
                    "environment": operation.environment,
                    "stage": operation.stage,
                    "allowlist_count": operation.allowlist_count,
                    "required_gate_count": len(REQUIRED_GATES),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
