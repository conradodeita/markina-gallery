"""Run the complete pytest collection in isolated CI shards and verify coverage."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


def checked_nodeids(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Empty or invalid pytest collection")
    if any(not isinstance(item, str) or "::" not in item for item in value):
        raise ValueError("Invalid pytest node ID")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate pytest node IDs")
    return value


def partition(nodeids: list[str], count: int) -> list[list[str]]:
    """Balance whole modules by collected item count; never split module fixtures."""
    checked_nodeids(nodeids)
    if type(count) is not int or count < 1:
        raise ValueError("Shard count must be positive")
    modules: dict[str, list[str]] = defaultdict(list)
    for nodeid in nodeids:
        modules[nodeid.split("::", 1)[0]].append(nodeid)
    if len(modules) < count:
        raise ValueError("Not enough test modules for nonempty shards")
    loads = [0] * count
    assignments = {}
    for module in sorted(modules, key=lambda name: (-len(modules[name]), name)):
        index = min(range(count), key=lambda shard: (loads[shard], shard))
        assignments[module] = index
        loads[index] += len(modules[module])
    return [
        [nodeid for nodeid in nodeids if assignments[nodeid.split("::", 1)[0]] == index]
        for index in range(count)
    ]


def verify(reports: list[dict], count: int, revision: str) -> int:
    """Reject missing shards, failed tests, different collections and omissions."""
    if type(count) is not int or count < 1 or len(reports) != count:
        raise ValueError("Missing or extra shard reports")
    if any(not isinstance(report, dict) for report in reports):
        raise ValueError("Invalid shard report")
    indexes = [report.get("index") for report in reports]
    if any(type(index) is not int for index in indexes) or set(indexes) != set(range(count)):
        raise ValueError("Missing or duplicate shard indexes")
    collected = checked_nodeids(reports[0].get("collected"))
    plan = partition(collected, count)
    selected = []
    for report in reports:
        if (report.get("version") != 1 or report.get("count") != count
                or report.get("revision") != revision
                or type(report.get("exit_code")) is not int or report["exit_code"] != 0):
            raise ValueError("Invalid shard metadata or unsuccessful pytest exit")
        if report.get("collected") != collected:
            raise ValueError("Different pytest collections across shards")
        items = checked_nodeids(report.get("selected"))
        if items != plan[report["index"]]:
            raise ValueError("Shard selection differs from the complete partition")
        selected.extend(items)
    if Counter(selected) != Counter(collected):
        raise ValueError("Incomplete or overlapping test coverage")
    return len(collected)


def run_suite(index: int, count: int, output: Path, revision: str,
              tests: str = "backend/tests") -> int:
    import pytest

    if type(index) is not int or type(count) is not int or not 0 <= index < count:
        raise ValueError("Invalid shard index/count")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Do not leave a previous successful report behind if collection now fails.
    output.unlink(missing_ok=True)
    report = {"version": 1, "revision": revision, "index": index, "count": count}

    class ShardPlugin:
        @pytest.hookimpl(trylast=True)
        def pytest_collection_modifyitems(self, config, items):
            collected = [item.nodeid for item in items]
            try:
                selected = partition(collected, count)[index]
            except ValueError as error:
                raise pytest.UsageError(str(error)) from error
            selected_set = set(selected)
            deselected = [item for item in items if item.nodeid not in selected_set]
            items[:] = [item for item in items if item.nodeid in selected_set]
            config.hook.pytest_deselected(items=deselected)
            report.update(collected=collected, selected=selected)
            print(f"\nBackend shard {index + 1}/{count}: {len(selected)}/{len(collected)} items")

    result = pytest.main([
        tests, "-q", "--durations=25", f"--junitxml={output.with_suffix('.xml')}",
    ], plugins=[ShardPlugin()])
    report["exit_code"] = int(result)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return int(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    run = modes.add_parser("run")
    run.add_argument("--index", type=int, required=True)
    run.add_argument("--count", type=int, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--tests", default="backend/tests")
    check = modes.add_parser("verify")
    check.add_argument("--count", type=int, required=True)
    check.add_argument("--artifacts", type=Path, required=True)
    for mode in (run, check):
        mode.add_argument("--revision", default=os.environ.get("GITHUB_SHA", "local"))
    args = parser.parse_args()
    try:
        if args.mode == "run":
            return run_suite(args.index, args.count, args.output, args.revision, args.tests)
        reports = [json.loads(path.read_text(encoding="utf-8"))
                   for path in sorted(args.artifacts.rglob("shard-*.json"))]
        total = verify(reports, args.count, args.revision)
        print(f"All {total} collected backend tests covered exactly once across {args.count} shards.")
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Backend CI rejected: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
