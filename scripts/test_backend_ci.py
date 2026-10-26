"""Coverage safety and real pytest integration for isolated backend shards."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.backend_ci import partition, verify

ROOT = Path(__file__).resolve().parents[1]
IDS = [f"tests/test_{module}.py::test_case[{case}]"
       for module, size in (("a", 8), ("b", 5), ("c", 4), ("d", 3), ("e", 2))
       for case in range(size)]


def reports():
    return [{"version": 1, "revision": "synthetic", "count": 3, "index": index,
             "exit_code": 0, "collected": IDS, "selected": items}
            for index, items in enumerate(partition(IDS, 3))]


class PartitionTests(unittest.TestCase):
    def test_all_items_exactly_once_and_module_fixtures_stay_together(self):
        parts = partition(IDS, 3)
        self.assertEqual(sorted(IDS), sorted(item for part in parts for item in part))
        for module in {node.split("::")[0] for node in IDS}:
            self.assertEqual(1, sum(any(node.startswith(module + "::") for node in part)
                                    for part in parts))
        self.assertLessEqual(max(map(len, parts)) - min(map(len, parts)), 2)
        self.assertEqual(parts, partition(IDS, 3))

    def test_new_tests_are_automatically_included(self):
        expanded = IDS + ["tests/test_new.py::test_added"]
        self.assertEqual(set(expanded), {item for part in partition(expanded, 3) for item in part})

    def test_invalid_or_ambiguous_collections_fail(self):
        for ids, count in (([], 3), (IDS + [IDS[0]], 3), (IDS, 0), (IDS, -1),
                           (IDS, True), (IDS, 6), (["bad-id"], 1)):
            with self.subTest(ids=ids[:1], count=count), self.assertRaises(ValueError):
                partition(ids, count)

    def test_complete_reports_pass(self):
        self.assertEqual(len(IDS), verify(reports(), 3, "synthetic"))

    def test_missing_extra_or_duplicate_shard_fails(self):
        data = reports()
        for invalid in (data[:2], data + [data[0]], [data[0], data[0], data[2]]):
            with self.assertRaises(ValueError):
                verify(invalid, 3, "synthetic")

    def test_bad_metadata_or_failed_pytest_cannot_pass(self):
        for field, value in (("revision", "other-sha"), ("count", 2), ("version", 2),
                             ("exit_code", 1), ("exit_code", 2), ("exit_code", 5),
                             ("exit_code", None), ("exit_code", False), ("index", True)):
            data = reports()
            data[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                verify(data, 3, "synthetic")

    def test_different_collection_omission_and_overlap_fail(self):
        original = reports()
        variants = []
        data = deepcopy(original)
        data[0]["collected"] = IDS[:-1]
        variants.append(data)
        data = deepcopy(original)
        data[0]["selected"] = data[0]["selected"][:-1]
        variants.append(data)
        data = deepcopy(original)
        data[0]["selected"] += data[1]["selected"][:1]
        variants.append(data)
        data = deepcopy(original)
        data[0]["selected"] = []
        variants.append(data)
        for invalid in variants:
            with self.assertRaises(ValueError):
                verify(invalid, 3, "synthetic")


class PytestIntegrationTests(unittest.TestCase):
    def run_shard(self, root, index, *, count=3):
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        env.pop("PYTEST_ADDOPTS", None)
        output = root / "reports" / f"shard-{index}.json"
        result = subprocess.run([
            sys.executable, str(ROOT / "scripts/backend_ci.py"), "run",
            "--index", str(index), "--count", str(count), "--output", str(output),
            "--revision", "synthetic", "--tests", str(root / "tests"),
        ], cwd=root, env=env, capture_output=True, text=True, timeout=60, check=False)
        return result, output

    def test_real_pytest_preserves_parametrization_module_fixtures_and_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            for module in ("a", "b", "c"):
                (tests / f"test_{module}.py").write_text(
                    "import pytest\n"
                    "@pytest.fixture(scope='module')\n"
                    "def state(): return []\n"
                    "@pytest.mark.parametrize('number', range(3))\n"
                    "def test_sequence(state, number):\n"
                    "    assert len(state) == number\n"
                    "    state.append(number)\n"
                    "@pytest.mark.skip(reason='synthetic existing skip')\n"
                    "def test_skipped(): pass\n", encoding="utf-8")
            data = []
            for index in range(3):
                result, output = self.run_shard(root, index)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertTrue(output.with_suffix(".xml").is_file())
                data.append(json.loads(output.read_text(encoding="utf-8")))
            self.assertEqual(12, verify(data, 3, "synthetic"))

    def test_real_pytest_failure_replaces_old_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_fail.py").write_text("def test_failure(): assert False\n")
            output = root / "reports" / "shard-0.json"
            output.parent.mkdir()
            output.write_text(json.dumps(reports()[0]))
            result, output = self.run_shard(root, 0, count=1)
            self.assertEqual(1, result.returncode)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(1, data["exit_code"])
            with self.assertRaises(ValueError):
                verify([data], 1, "synthetic")


if __name__ == "__main__":
    unittest.main()
