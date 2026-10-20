"""Preparation policy for the official app executor; never operates production.

Simulation receipts are deliberately not production receipts or approval codes.
The legacy processes have no cooperative drain contract: real modes fail closed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PINS = {"aiohttp": "3.14.4", "multidict": "6.9.1", "urllib3": "2.8.0", "yarl": "1.25.1"}
ORDER = (
    "api", "worker", "face-maintenance-worker", "face-search-worker",
    "face-index-worker", "preview-adjustment-worker", "raw-development-worker",
    "face-gemma-index-worker",
)
SPECIALIZED = set(ORDER[2:])
UNAVAILABLE = "Python release blocked: cooperative drain and production executor are not implemented; never use the legacy api/web flow"


class Blocked(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def image_id(value):
    require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value), "invalid image identity")
    return value


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value), "invalid source SHA")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_candidate(baseline, candidate):
    """Full distribution comparison, not just four successful imports."""
    image_id(baseline["image_id"])
    image_id(candidate["image_id"])
    require(candidate["architecture"] == "arm64", "candidate is not ARM64")
    require(candidate["python"] == baseline["python"], "Python base changed")
    require(candidate["layers"][:-2] == baseline["layers"], "base/model/code layers changed")
    require(candidate.get("embedded_pins") == PINS, "embedded requirements differ from approved pins")
    require(candidate["pip_check"] == 0, "pip check failed")
    expected = dict(baseline["packages"], **PINS)
    require(candidate["packages"] == expected, "unrelated distribution drift or missing corrected package")
    return True


def plan(inventory, target, candidates, now=None):
    sha(target)
    require(inventory.get("schema_version") == 1, "unsupported inventory")
    require(inventory.get("project") == "markina-gallery", "wrong Compose project")
    require(inventory.get("host_architecture") in ("aarch64", "arm64"), "wrong host architecture")
    age = ((now or datetime.now(timezone.utc)) - datetime.fromisoformat(inventory["collected_at"])).total_seconds()
    require(0 <= age <= 3600, "stale/future inventory")
    sha(inventory["checkout_sha"])
    services = inventory["services"]
    require("api" in services and "worker" in services, "mandatory consumers missing")
    require("web" in services and services["web"]["health"] == "healthy", "frontend unavailable")
    affected, skipped, blockers = [], [], []
    for service in ORDER:
        item = services.get(service)
        if not item or item["status"] != "running":
            require(service not in ("api", "worker"), "mandatory consumer inactive")
            skipped.append(service)
            continue
        require(item["health"] == "healthy", "unhealthy consumer: " + service)
        image_id(item["image_id"])
        require(item["image"]["architecture"] == "arm64", "consumer architecture differs")
        require(all(p in item.get("packages", {}) for p in PINS), "missing package evidence")
        if all(item["packages"][p] == v for p, v in PINS.items()):
            continue
        affected.append(service)
        proof = candidates.get(service)
        if not proof or proof.get("validated") is not True or proof.get("base_image_id") != item["image_id"]:
            blockers.append({"service": service, "reason": "candidate_not_verified_for_exact_runtime"})
        if service != "api":
            blockers.append({"service": service, "reason": "legacy_worker_has_no_cooperative_drain"})
        if service in SPECIALIZED:
            blockers.append({"service": service, "reason": "specialized_startup_homologation_required"})
    if affected:
        blockers.append({"service": "coordinator", "reason": "operational_executor_and_recovery_not_implemented"})
    inputs = {"target": target, "inventory": inventory, "candidates": candidates}
    return {
        "target_sha": target, "affected_order": affected, "inactive_optional": skipped,
        "protected_services": sorted(set(services) - set(affected)), "blockers": blockers,
        "planning_fingerprint": digest(inputs), "operational_approval_code": None,
        "production_ready": False, "publication_authorized": False,
    }


def simulate(state, operations, expected_sha, expected_fingerprint, *, fail_health=None, concurrent_data=None):
    """Pure contract model. No subprocess, files, Docker, database or network."""
    require(state.get("simulation") is True, "synthetic simulation state required")
    require(state["sha"] == sha(expected_sha), "SHA divergence")
    require(state["fingerprint"] == expected_fingerprint, "fingerprint divergence")
    require(len({op["service"] for op in operations}) == len(operations), "duplicate consumer")
    before = copy.deepcopy(state)
    result = copy.deepcopy(state)
    selected = []
    for op in operations:
        service = op["service"]
        require(service in ORDER, "service outside Python scope")
        if service not in result["services"] or not result["services"][service]["running"]:
            require(service not in ("api", "worker"), "mandatory consumer inactive")
            continue
        current = result["services"][service]
        require(current["image"] == image_id(op["previous"]), "image divergence")
        image_id(op["candidate"])
        require(current["active_tasks"] == 0, "active task cannot be interrupted")
        require(current.get("drain_acknowledged") is True, "no cooperative drain acknowledgement")
        require(current.get("admission_fenced") is True, "new claims/requests are not fenced")
        selected.append(op)
    receipts, events = [], []
    expected_data = {**before["data"], **(concurrent_data or {})}
    try:
        for op in selected:
            s = op["service"]
            # Capture before substitution, including the consumer whose health may fail.
            receipts.append({"service": s, "previous": copy.deepcopy(result["services"][s])})
            events.append("preserve:" + s)
            result["services"][s]["image"] = op["candidate"]
            result["data"].update(concurrent_data or {})
            events.append("replace:" + s)
            if s == fail_health:
                raise Blocked("health failed: " + s)
            events.append("healthy:" + s)
        status = "success"
    except Blocked:
        for receipt in reversed(receipts):
            result["services"][receipt["service"]] = receipt["previous"]
            events.append("restore:" + receipt["service"])
        status = "rolled_back"
    require(result["data"] == expected_data, "data must never be restored by image rollback")
    protected = set(before["services"]) - {op["service"] for op in selected}
    require(all(result["services"][s] == before["services"][s] for s in protected), "protected runtime changed")
    return {"simulation": True, "operational_approval_code": None, "status": status,
            "state": result, "events": events, "receipts": receipts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "inventory", "simulate", "release", "rollback", "rollback-inventory", "recover", "recover-inventory"), required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--simulation", type=Path)
    args = parser.parse_args(argv)
    try:
        sha(args.sha)
        if args.mode in ("release", "rollback", "recover", "rollback-inventory", "recover-inventory"):
            # Must precede all file reads, receipt writes and external commands.
            raise Blocked(UNAVAILABLE)
        if args.mode == "simulate":
            require(args.simulation is not None, "simulation fixture required")
            fixture = json.loads(args.simulation.read_text())
            output = simulate(fixture["state"], fixture["operations"], args.sha, fixture["state"]["fingerprint"], fail_health=fixture.get("fail_health"))
        else:
            require(args.inventory is not None, "real inventory required")
            inventory = json.loads(args.inventory.read_text())
            inventory = inventory.get("runtime_inventory", inventory)
            candidates = json.loads(args.candidates.read_text()) if args.candidates else {}
            # Read approved requirements from Git without importing application code.
            root = Path(__file__).resolve().parents[1]
            content = subprocess.check_output(["git", "show", args.sha + ":backend/requirements-push.txt"], cwd=root, text=True)
            require(all(p + "==" + v in content.splitlines() for p, v in PINS.items()), "approved pins differ")
            output = plan(inventory, args.sha, candidates)
        print(json.dumps(output, sort_keys=True, indent=2))
        return 0
    except (Blocked, KeyError, TypeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print("python-security: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
