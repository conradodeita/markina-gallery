"""Failure-boundary tests for the approved app preflight support contract."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import production_app_preflight_support as support

SHA_OLD = "1" * 40
SHA_MAIN = "2" * 40
SHA_CONNECTION = "3" * 64
SHA_CONTAINERS = "4" * 64


def state(content: bytes | None) -> dict:
    if content is None:
        return {"present": False}
    return {"present": True, "sha256": hashlib.sha256(content).hexdigest(),
            "uid": 0, "gid": 0, "mode": 0o755, "links": 1}


class FakeHost:
    def __init__(self, *, ref: str | None = SHA_OLD, bridge: bytes | None = b"old-bridge",
                 wrapper: bytes | None = b"old-wrapper") -> None:
        self.ref = ref
        self.remote_sha = SHA_MAIN
        self.connection = SHA_CONNECTION
        self.containers = SHA_CONTAINERS
        self.contents = {"bridge": bridge, "wrapper": wrapper}
        self.receipts: dict[str, dict] = {}
        self.backups: dict[str, bytes] = {}
        self.failpoint: str | None = None
        self.unknown_on_failure: str | None = None
        self.ancestor = True
        self.old_commit_exists = True
        self.other_refs_digest = "refs-stable"
        self.state_directory_state = "ready"
        self.backup_directory_state = "ready"
        self.candidates_loaded = 0
        self.preserve_calls = 0
        self.lock_count = 0

    @contextlib.contextmanager
    def lock(self):
        self.lock_count += 1
        yield

    def collect_snapshot(self, sha: str, binding: str) -> dict:
        if sha != self.remote_sha:
            raise support.SupportError("support_main_changed")
        return {"host": "fixed-host", "repository": "fixed-repository", "support_sha": sha,
                "remote_main_sha": self.remote_sha, "connection_binding": binding,
                "origin_main_ref": self.ref, "bridge": state(self.contents["bridge"]),
                "wrapper": state(self.contents["wrapper"]),
                "state_directory_state": self.state_directory_state,
                "backup_directory_state": self.backup_directory_state,
                "containers_sha256": self.containers}

    def check_no_staging(self):
        return None

    def refs_digest(self):
        return self.other_refs_digest

    def load_candidates(self, sha: str) -> dict:
        self.candidates_loaded += 1
        if sha != self.remote_sha:
            raise support.SupportError("support_main_changed")
        bridge = b"candidate-bridge"
        wrapper = b"candidate-wrapper"
        return {"bridge": {"blob": "a" * 40, "content": bridge, "sha256": state(bridge)["sha256"],
                            "state": state(bridge)},
                "wrapper": {"blob": "b" * 40, "content": wrapper, "sha256": state(wrapper)["sha256"],
                            "state": state(wrapper)}}

    def assert_no_other_refs_changed(self, digest: str):
        if digest != self.other_refs_digest:
            raise support.SupportError("support_other_refs_changed")

    def validate_candidates(self, candidates: dict):
        if set(candidates) != {"bridge", "wrapper"}:
            raise support.SupportError("support_candidate_invalid")

    def assert_previous_ref_ancestor(self, old_ref: str | None, target_sha: str):
        if old_ref is not None and not self.old_commit_exists:
            raise support.SupportError("support_previous_ref_object_missing")
        if old_ref is not None and not self.ancestor:
            raise support.SupportError("support_previous_ref_not_ancestor")

    def assert_previous_ref_object(self, ref_sha: str | None):
        if ref_sha is not None and not self.old_commit_exists:
            raise support.SupportError("support_previous_ref_object_missing")

    def preserve_targets(self, snapshot: dict, operation_id: str, label: str) -> dict:
        self.preserve_calls += 1
        result = {}
        for name in support.TARGETS:
            content = self.contents[name]
            if content is None:
                result[name] = None
                continue
            filename = f"preflight-support-{label}-{operation_id}-{name}"
            self.backups[filename] = content
            result[name] = filename
        return result

    def create_receipt(self, payload: dict) -> str:
        data = support._canonical_json(payload) + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.receipts:
            raise support.SupportError("support_receipt_or_staging_exists")
        self.receipts[digest] = copy.deepcopy(payload)
        return digest

    def read_receipt(self, digest: str) -> dict:
        if digest not in self.receipts:
            raise support.SupportError("support_receipt_missing_or_ambiguous")
        return copy.deepcopy(self.receipts[digest])

    def read_preparation(self, digest: str) -> tuple[dict, dict]:
        complete = self.read_receipt(digest)
        if complete.get("kind") != "preparation-complete" or complete.get("status") != "complete":
            raise support.SupportError("support_preparation_receipt_invalid")
        intent = self.read_receipt(complete["intent_sha256"])
        if intent.get("kind") != "preparation-intent" or intent.get("status") != "pending":
            raise support.SupportError("support_preparation_receipt_invalid")
        for name in support.TARGETS:
            original = intent["snapshot"][name]
            filename = intent["backup_names"][name]
            if original["present"] and (filename not in self.backups
                                        or state(self.backups[filename]) != original):
                raise support.SupportError("support_preparation_backup_invalid")
        return complete, intent

    def current_ref(self):
        return self.ref

    def update_ref(self, expected: str | None, desired: str | None):
        if self.ref != expected:
            raise support.SupportError("support_ref_changed")
        self.ref = desired
        self._fail("after_ref")

    def target_state(self, name: str):
        return state(self.contents[name])

    def install_file(self, name: str, expected: dict, content: bytes, phase: str):
        if self.target_state(name) != expected:
            raise support.SupportError("support_target_changed")
        self.contents[name] = content
        self._fail(f"after_{phase}_{name}")

    def restore_file(self, name: str, expected: dict, desired: dict, backup_name: str | None, phase: str):
        if self.target_state(name) != expected:
            raise support.SupportError("support_target_unexpected")
        if desired["present"]:
            if backup_name not in self.backups or state(self.backups[backup_name]) != desired:
                raise support.SupportError("support_backup_invalid")
            self.contents[name] = self.backups[backup_name]
        else:
            self.contents[name] = None
        self._fail(f"after_{phase}_{name}")

    def validate_installed(self, sha: str, expected_states: dict, containers_sha256: str):
        if self.ref != sha or self.containers != containers_sha256:
            raise support.SupportError("support_post_swap_failed")
        if any(self.target_state(name) != expected_states[name] for name in support.TARGETS):
            raise support.SupportError("support_post_swap_failed")
        self._fail("post_prepare")

    def validate_restored(self, desired: dict, containers_sha256: str):
        if self.ref != desired["origin_main_ref"] or self.containers != containers_sha256:
            raise support.SupportError("support_restore_unverified")
        if any(self.target_state(name) != desired[name] for name in support.TARGETS):
            raise support.SupportError("support_restore_unverified")
        self._fail("post_restore")

    def assert_state(self, expected: dict):
        if self.ref != expected["origin_main_ref"] or self.containers != expected["containers_sha256"]:
            raise support.SupportError("support_state_verification_failed")
        if any(self.target_state(name) != expected[name] for name in support.TARGETS):
            raise support.SupportError("support_state_verification_failed")

    def _fail(self, point: str):
        if self.failpoint == point:
            self.failpoint = None
            if self.unknown_on_failure:
                self.contents[self.unknown_on_failure] = b"unexpected-external-state"
            raise support.SupportError("injected_failure")


class LocalSupportHostAdapterTests(unittest.TestCase):
    def test_refs_digest_is_exposed_for_prepare_coordinator(self):
        host = object.__new__(support.LocalSupportHost)
        with patch.object(support.LocalSupportHost, "_refs_digest", return_value="refs-stable") as digest:
            self.assertEqual(host.refs_digest(), "refs-stable")
            digest.assert_called_once_with()

    def test_fixed_directory_state_classifies_safe_missing_and_blocked_states(self):
        class Node:
            def __init__(self, name, mode=None, uid=0, gid=0, parent=None, error=None):
                self.name = name
                self.mode = mode
                self.uid = uid
                self.gid = gid
                self.parent = parent if parent is not None else self
                self.error = error

            def lstat(self):
                if self.error is not None:
                    raise self.error
                if self.mode is None:
                    raise FileNotFoundError
                return SimpleNamespace(st_mode=self.mode, st_uid=self.uid, st_gid=self.gid)

            def __eq__(self, other):
                return isinstance(other, Node) and self.name == other.name

        root = Node("/", stat.S_IFDIR | 0o755)
        parent = Node("/var/lib/markina-gallery", stat.S_IFDIR | 0o755, parent=root)
        ready = Node("/var/lib/markina-gallery/app-compose-bridge",
                     stat.S_IFDIR | 0o700, parent=parent)
        creatable = Node("/var/lib/markina-gallery/app-compose-bridge",
                         None, parent=parent)
        bad_parent = Node("/var/lib/markina-gallery", stat.S_IFDIR | 0o755,
                          uid=0, gid=1000, parent=root)
        bad_child = Node("/var/lib/markina-gallery/app-compose-bridge",
                         stat.S_IFDIR | 0o750, parent=parent)
        unavailable = Node("/var/lib/markina-gallery/app-compose-bridge",
                           None, parent=parent, error=PermissionError)
        unavailable_parent = Node("/var/lib/markina-gallery", stat.S_IFDIR | 0o755,
                                  parent=root, error=PermissionError)
        parent_unavailable_child = Node("/var/lib/markina-gallery/app-compose-bridge",
                                        None, parent=unavailable_parent)
        symlink_parent = Node("/var/lib/markina-gallery", stat.S_IFLNK | 0o777,
                              parent=root)
        symlink_parent_child = Node("/var/lib/markina-gallery/app-compose-bridge",
                                    None, parent=symlink_parent)
        classify = support.LocalSupportHost._fixed_directory_state
        self.assertEqual(classify(ready, mode=0o700, check_parent_chain=True), "ready")
        self.assertEqual(classify(creatable, mode=0o700, check_parent_chain=True), "creatable")
        self.assertEqual(classify(Node("bad-parent-child", stat.S_IFDIR | 0o700,
                                       parent=bad_parent), mode=0o700, check_parent_chain=True),
                         "parent_invalid")
        self.assertEqual(classify(bad_child, mode=0o700, check_parent_chain=True), "directory_invalid")
        self.assertEqual(classify(unavailable, mode=0o700, check_parent_chain=True), "unavailable")
        self.assertEqual(classify(parent_unavailable_child, mode=0o700, check_parent_chain=True), "unavailable")
        self.assertEqual(classify(symlink_parent_child, mode=0o700, check_parent_chain=True), "parent_invalid")

    def test_state_directory_creation_revalidates_all_parent_directories(self):
        class Node:
            def __init__(self, name, mode=None, parent=None):
                self.name = name
                self.mode = mode
                self.parent = parent if parent is not None else self
                self.created_mode = None

            def lstat(self):
                if self.mode is None:
                    raise FileNotFoundError
                return SimpleNamespace(st_mode=self.mode, st_uid=0, st_gid=0)

            def mkdir(self, *, mode):
                self.created_mode = mode
                self.mode = stat.S_IFDIR | mode

            def __eq__(self, other):
                return isinstance(other, Node) and self.name == other.name

        root = Node("/", stat.S_IFDIR | 0o755)
        var = Node("/var", stat.S_IFDIR | 0o755, parent=root)
        lib = Node("/var/lib", stat.S_IFDIR | 0o755, parent=var)
        markina = Node("/var/lib/markina-gallery", stat.S_IFDIR | 0o755, parent=lib)
        target = Node("/var/lib/markina-gallery/app-compose-bridge", parent=markina)

        with patch.object(support, "STATE_DIR", target):
            self.assertEqual(support.LocalSupportHost.state_directory_state(), "creatable")
            support.LocalSupportHost().ensure_state_directories()
            self.assertEqual(target.created_mode, 0o700)
            self.assertEqual(support.LocalSupportHost.state_directory_state(), "ready")


class SupportCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.host = FakeHost()
        self.coordinator = support.SupportCoordinator(self.host)

    def inventory_fingerprint(self):
        return self.coordinator.inventory(SHA_MAIN, SHA_CONNECTION)[0]

    def prepared(self):
        fingerprint = self.inventory_fingerprint()
        receipt = self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, fingerprint)
        return fingerprint, receipt

    def test_inventory_fingerprint_binds_sha_and_connection_without_exposing_state(self):
        fingerprint, snapshot = self.coordinator.inventory(SHA_MAIN, SHA_CONNECTION)
        changed, _ = self.coordinator.inventory(SHA_MAIN, "5" * 64)
        self.assertEqual(len(fingerprint), 64)
        self.assertNotEqual(fingerprint, changed)
        self.assertIn("bridge", snapshot)
        self.assertNotIn("container_ids", snapshot)
        self.assertEqual(self.host.lock_count, 2)

    def test_inventory_fingerprint_binds_fixed_directory_readiness(self):
        self.host.state_directory_state = "creatable"
        first, snapshot = self.coordinator.inventory(SHA_MAIN, SHA_CONNECTION)
        self.assertEqual(snapshot["state_directory_state"], "creatable")
        self.assertEqual(snapshot["backup_directory_state"], "ready")
        self.host.backup_directory_state = "directory_invalid"
        second, _ = self.coordinator.inventory(SHA_MAIN, SHA_CONNECTION)
        self.assertNotEqual(first, second)

    def test_prepare_rejects_unsafe_directory_before_fetch_or_any_persistence(self):
        for field, value, error in (
            ("state_directory_state", "parent_invalid", "support_state_directory_invalid"),
            ("backup_directory_state", "directory_invalid", "support_backup_directory_invalid"),
        ):
            with self.subTest(field=field):
                self.host = FakeHost()
                self.coordinator = support.SupportCoordinator(self.host)
                setattr(self.host, field, value)
                fingerprint = self.inventory_fingerprint()
                original = copy.deepcopy(self.host.contents)
                with self.assertRaisesRegex(support.SupportError, error):
                    self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, fingerprint)
                self.assertEqual(self.host.ref, SHA_OLD)
                self.assertEqual(self.host.contents, original)
                self.assertEqual(self.host.candidates_loaded, 0)
                self.assertEqual(self.host.preserve_calls, 0)
                self.assertFalse(self.host.receipts)
                self.assertFalse(self.host.backups)

    def test_cli_inventory_reports_only_static_storage_states(self):
        output = io.StringIO()
        self.host.state_directory_state = "creatable"
        self.host.backup_directory_state = "directory_invalid"
        with patch.object(support, "LocalSupportHost", return_value=self.host), patch("sys.stdout", output):
            result = support.main([
                "--mode", "support-inventory", "--support-sha", SHA_MAIN,
                "--connection-binding", SHA_CONNECTION,
            ])
        self.assertEqual(result, 0)
        self.assertIn("support_state_directory=creatable", output.getvalue())
        self.assertIn("support_backup_directory=directory_invalid", output.getvalue())
        self.assertNotIn("/var/", output.getvalue())
        self.assertNotIn("st_uid", output.getvalue())
        self.assertNotIn("st_mode", output.getvalue())
        self.assertFalse(self.host.candidates_loaded)
        self.assertFalse(self.host.preserve_calls)
        self.assertFalse(self.host.receipts)
        self.assertFalse(self.host.backups)

    def test_cli_restore_inventory_reports_only_static_storage_states(self):
        _, receipt = self.prepared()
        output = io.StringIO()
        backups_before = copy.deepcopy(self.host.backups)
        receipts_before = copy.deepcopy(self.host.receipts)
        with patch.object(support, "LocalSupportHost", return_value=self.host), patch("sys.stdout", output):
            result = support.main([
                "--mode", "restore-support-inventory", "--support-sha", SHA_MAIN,
                "--connection-binding", SHA_CONNECTION, "--receipt-sha256", receipt,
            ])
        self.assertEqual(result, 0)
        self.assertIn("support_state_directory=ready", output.getvalue())
        self.assertIn("support_backup_directory=ready", output.getvalue())
        self.assertNotIn("/var/", output.getvalue())
        self.assertNotIn("st_uid", output.getvalue())
        self.assertNotIn("st_mode", output.getvalue())
        self.assertEqual(self.host.backups, backups_before)
        self.assertEqual(self.host.receipts, receipts_before)

    def test_restore_rejects_unsafe_directory_before_new_persistence(self):
        _, receipt = self.prepared()
        self.host.backup_directory_state = "directory_invalid"
        fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        contents_before = copy.deepcopy(self.host.contents)
        backups_before = copy.deepcopy(self.host.backups)
        receipts_before = copy.deepcopy(self.host.receipts)
        preserve_calls_before = self.host.preserve_calls

        with self.assertRaisesRegex(support.SupportError, "support_backup_directory_invalid"):
            self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)

        self.assertEqual(self.host.contents, contents_before)
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(self.host.backups, backups_before)
        self.assertEqual(self.host.receipts, receipts_before)
        self.assertEqual(self.host.preserve_calls, preserve_calls_before)

    def test_prepare_requires_exact_preflight_fingerprint(self):
        before = copy.deepcopy(self.host.contents)
        with self.assertRaisesRegex(support.SupportError, "support_fingerprint_changed"):
            self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, "f" * 64)
        self.assertEqual(self.host.ref, SHA_OLD)
        self.assertEqual(self.host.contents, before)
        self.assertFalse(self.host.backups)

    def test_prepare_updates_only_fixed_targets_and_returns_receipt_digest(self):
        fingerprint, receipt = self.prepared()
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(self.host.contents["bridge"], b"candidate-bridge")
        self.assertEqual(self.host.contents["wrapper"], b"candidate-wrapper")
        self.assertEqual(len(receipt), 64)
        complete = self.host.read_receipt(receipt)
        self.assertEqual(complete["kind"], "preparation-complete")
        self.assertEqual(complete["status"], "complete")
        intent = self.host.read_receipt(complete["intent_sha256"])
        self.assertEqual(intent["support_fingerprint"], fingerprint)

    def test_prepare_accepts_absent_baseline_and_records_absence(self):
        self.host.ref = None
        self.host.contents = {"bridge": None, "wrapper": None}
        fingerprint, receipt = self.prepared()
        _complete, intent = self.host.read_preparation(receipt)
        self.assertIsNone(intent["snapshot"]["origin_main_ref"])
        self.assertIsNone(intent["backup_names"]["bridge"])
        self.assertIsNone(intent["backup_names"]["wrapper"])
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(len(fingerprint), 64)

    def test_prepare_compensates_absent_baseline_without_leaving_candidates(self):
        self.host.ref = None
        self.host.contents = {"bridge": None, "wrapper": None}
        fingerprint = self.inventory_fingerprint()
        self.host.failpoint = "after_prepare_wrapper"
        with self.assertRaisesRegex(support.SupportError, "support_preparation_failed_rolled_back"):
            self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, fingerprint)
        self.assertIsNone(self.host.ref)
        self.assertEqual(self.host.contents, {"bridge": None, "wrapper": None})
        self.assertTrue(self.host.receipts)

    def test_prepare_rejects_missing_or_nonancestor_baseline_object(self):
        self.host.old_commit_exists = False
        with self.assertRaisesRegex(support.SupportError, "support_previous_ref_object_missing"):
            self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, self.inventory_fingerprint())
        self.assertEqual(self.host.ref, SHA_OLD)
        self.assertFalse(self.host.backups)
        self.host.old_commit_exists = True
        self.host.ancestor = False
        with self.assertRaisesRegex(support.SupportError, "support_previous_ref_not_ancestor"):
            self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, self.inventory_fingerprint())
        self.assertEqual(self.host.ref, SHA_OLD)
        self.assertFalse(self.host.backups)

    def test_prepare_compensates_each_mutation_boundary_and_post_swap_failure(self):
        for failure in ("after_ref", "after_prepare_bridge", "after_prepare_wrapper", "post_prepare"):
            with self.subTest(failure=failure):
                self.host = FakeHost()
                self.coordinator = support.SupportCoordinator(self.host)
                fingerprint = self.inventory_fingerprint()
                self.host.failpoint = failure
                with self.assertRaisesRegex(support.SupportError, "support_preparation_failed_rolled_back"):
                    self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, fingerprint)
                self.assertEqual(self.host.ref, SHA_OLD)
                self.assertEqual(self.host.contents, {"bridge": b"old-bridge", "wrapper": b"old-wrapper"})

    def test_prepare_preserves_unexpected_state_when_compensation_cannot_be_proved(self):
        fingerprint = self.inventory_fingerprint()
        self.host.failpoint = "after_prepare_wrapper"
        self.host.unknown_on_failure = "bridge"
        with self.assertRaisesRegex(support.SupportError, "support_preparation_rollback_unverified"):
            self.coordinator.prepare(SHA_MAIN, SHA_CONNECTION, fingerprint)
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(self.host.contents["bridge"], b"unexpected-external-state")
        self.assertEqual(self.host.contents["wrapper"], b"old-wrapper")
        self.assertTrue(self.host.backups)

    def test_restore_inventory_and_restore_return_exact_previous_state(self):
        _, receipt = self.prepared()
        fingerprint, view = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        self.assertEqual(fingerprint, support._digest(view))
        restored_receipt = self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
        self.assertEqual(self.host.ref, SHA_OLD)
        self.assertEqual(self.host.contents, {"bridge": b"old-bridge", "wrapper": b"old-wrapper"})
        self.assertEqual(self.host.containers, SHA_CONTAINERS)
        self.assertEqual(self.host.read_receipt(restored_receipt)["kind"], "restoration-complete")

    def test_restore_returns_to_absent_baseline(self):
        self.host.ref = None
        self.host.contents = {"bridge": None, "wrapper": None}
        _, receipt = self.prepared()
        fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
        self.assertIsNone(self.host.ref)
        self.assertEqual(self.host.contents, {"bridge": None, "wrapper": None})
        self.assertEqual(self.host.containers, SHA_CONTAINERS)

    def test_restore_inventory_rejects_missing_previous_ref_object(self):
        _, receipt = self.prepared()
        self.host.old_commit_exists = False
        with self.assertRaisesRegex(support.SupportError, "support_previous_ref_object_missing"):
            self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(self.host.contents,
                         {"bridge": b"candidate-bridge", "wrapper": b"candidate-wrapper"})

    def test_restore_rejects_missing_previous_ref_object_before_preserving_or_mutating(self):
        _, receipt = self.prepared()
        fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        prior_backups = copy.deepcopy(self.host.backups)
        self.host.old_commit_exists = False
        with self.assertRaisesRegex(support.SupportError, "support_previous_ref_object_missing"):
            self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
        self.assertEqual(self.host.ref, SHA_MAIN)
        self.assertEqual(self.host.contents,
                         {"bridge": b"candidate-bridge", "wrapper": b"candidate-wrapper"})
        self.assertEqual(self.host.backups, prior_backups)

    def test_restore_divergent_state_or_fingerprint_aborts_before_backup(self):
        _, receipt = self.prepared()
        fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        self.host.contents["bridge"] = b"unexpected"
        before = copy.deepcopy(self.host.backups)
        with self.assertRaisesRegex(support.SupportError, "support_prepared_state_changed"):
            self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
        self.assertEqual(self.host.backups, before)

    def test_restore_rejects_invalid_receipt_and_corrupt_backup(self):
        with self.assertRaisesRegex(support.SupportError, "support_receipt_missing_or_ambiguous"):
            self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, "f" * 64)
        _, receipt = self.prepared()
        _complete, intent = self.host.read_preparation(receipt)
        filename = intent["backup_names"]["bridge"]
        self.host.backups[filename] = b"tampered"
        with self.assertRaisesRegex(support.SupportError, "support_preparation_backup_invalid"):
            self.host.read_preparation(receipt)

    def test_restore_compensates_each_mutation_boundary_and_post_restore_failure(self):
        for failure in ("after_restore_wrapper", "after_restore_bridge", "after_ref", "post_restore"):
            with self.subTest(failure=failure):
                self.host = FakeHost()
                self.coordinator = support.SupportCoordinator(self.host)
                _, receipt = self.prepared()
                fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
                self.host.failpoint = failure
                with self.assertRaisesRegex(support.SupportError, "support_restore_failed_rolled_back"):
                    self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
                self.assertEqual(self.host.ref, SHA_MAIN)
                self.assertEqual(self.host.contents,
                                 {"bridge": b"candidate-bridge", "wrapper": b"candidate-wrapper"})

    def test_restore_preserves_unknown_target_when_compensation_fails(self):
        _, receipt = self.prepared()
        fingerprint, _ = self.coordinator.restore_inventory(SHA_MAIN, SHA_CONNECTION, receipt)
        self.host.failpoint = "after_restore_bridge"
        self.host.unknown_on_failure = "wrapper"
        with self.assertRaisesRegex(support.SupportError, "support_restore_fallback_unverified"):
            self.coordinator.restore(SHA_MAIN, SHA_CONNECTION, fingerprint, receipt)
        self.assertEqual(self.host.contents["wrapper"], b"unexpected-external-state")
        self.assertTrue(self.host.backups)

    def test_container_inspect_fields_are_type_checked_before_pattern_operations(self):
        container_id = "a" * 64
        record = {
            "Id": container_id,
            "Image": f"sha256:{'b' * 64}",
            "State": {"Status": "running", "StartedAt": "2026-11-23T00:00:00Z"},
        }
        malformed_records = (
            ("Id", lambda item: item.update({"Id": None})),
            ("Image", lambda item: item.update({"Image": {"private": "value"}})),
            ("State.Status", lambda item: item["State"].update({"Status": []})),
            ("State.StartedAt", lambda item: item["State"].update({"StartedAt": ["private"]})),
        )

        for field, mutate in malformed_records:
            with self.subTest(field=field):
                candidate = copy.deepcopy(record)
                mutate(candidate)
                host = support.LocalSupportHost()
                ps = subprocess.CompletedProcess(["docker", "ps"], 0, f"{container_id}\n".encode(), b"")
                inspect = subprocess.CompletedProcess(
                    ["docker", "inspect"], 0, json.dumps([candidate]).encode(), b"")
                with (
                    patch.object(host, "_run", side_effect=[ps, inspect]),
                    self.assertRaises(support.SupportError) as caught,
                ):
                    host._container_digest()
                self.assertEqual(caught.exception.code, "support_container_inventory_invalid")
                self.assertNotIn("private", str(caught.exception))

    def test_malformed_container_fields_emit_sanitized_error_without_fingerprint(self):
        container_id = "a" * 64
        record = {
            "Id": None,
            "Image": f"sha256:{'b' * 64}",
            "State": {"Status": "running", "StartedAt": "2026-11-23T00:00:00Z"},
        }
        ps = subprocess.CompletedProcess(["docker", "ps"], 0, f"{container_id}\n".encode(), b"")
        inspect = subprocess.CompletedProcess(
            ["docker", "inspect"], 0, json.dumps([record]).encode(), b"")
        output = io.StringIO()
        with (
            patch.object(support.LocalSupportHost, "lock", return_value=contextlib.nullcontext()),
            patch.object(support.LocalSupportHost, "_assert_host_repository", return_value="fixed-repository"),
            patch.object(support.LocalSupportHost, "_remote_main_sha", return_value=SHA_MAIN),
            patch.object(support.LocalSupportHost, "_ref_sha", return_value=SHA_OLD),
            patch.object(support.LocalSupportHost, "target_state", return_value={"present": False}),
            patch.object(support.LocalSupportHost, "_run", side_effect=[ps, inspect]),
            patch("sys.stdout", output),
        ):
            result = support.main([
                "--mode", "support-inventory",
                "--support-sha", SHA_MAIN,
                "--connection-binding", SHA_CONNECTION,
            ])

        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue().strip(), "support_error=support_container_inventory_invalid")
        self.assertNotIn("support_fingerprint=", output.getvalue())
        self.assertNotIn(container_id, output.getvalue())

    def test_container_digest_reads_completed_process_stdout(self):
        container_id = "a" * 64
        record = {
            "Id": container_id,
            "Image": f"sha256:{'b' * 64}",
            "State": {"Status": "running", "StartedAt": "2026-11-23T00:00:00Z"},
        }
        ps = subprocess.CompletedProcess(["docker", "ps"], 0, f"{container_id}\n".encode(), b"")
        inspect = subprocess.CompletedProcess(["docker", "inspect"], 0, json.dumps([record]).encode(), b"")
        host = support.LocalSupportHost()
        with patch.object(host, "_run", side_effect=[ps, inspect]):
            digest = host._container_digest()
        self.assertEqual(len(digest), 64)

    def test_cli_errors_are_static_and_do_not_echo_untrusted_argument(self):
        output = io.StringIO()
        with patch("sys.stdout", output):
            result = support.main(["--mode", "support-inventory", "--support-sha", "private-input",
                                   "--connection-binding", SHA_CONNECTION])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue().strip(), "support_error=support_sha_invalid")
        self.assertNotIn("private-input", output.getvalue())

    def test_cli_classifies_allowlisted_unhandled_errors_without_exposing_details(self):
        cases = (
            (TypeError("private helper path"), "support_internal_type_error"),
            (PermissionError("private filesystem path"), "support_internal_io_error"),
            (subprocess.CalledProcessError(1, "private-command"), "support_internal_command_error"),
            (KeyError("private field"), "support_internal_lookup_error"),
        )
        for error, expected in cases:
            output = io.StringIO()
            with self.subTest(expected=expected), patch.object(
                    support.SupportCoordinator, "inventory", side_effect=error), patch("sys.stdout", output):
                result = support.main(["--mode", "support-inventory", "--support-sha", SHA_MAIN,
                                       "--connection-binding", SHA_CONNECTION])
            self.assertEqual(result, 1)
            self.assertEqual(output.getvalue().strip(), f"support_error={expected}")
            self.assertNotIn("private", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())
            self.assertNotIn("support_fingerprint=", output.getvalue())

    def test_cli_keeps_unknown_unhandled_errors_generic(self):
        class UnlistedFailure(Exception):
            pass

        output = io.StringIO()
        with patch.object(support.SupportCoordinator, "inventory",
                          side_effect=UnlistedFailure("private diagnostic")), patch("sys.stdout", output):
            result = support.main(["--mode", "support-inventory", "--support-sha", SHA_MAIN,
                                   "--connection-binding", SHA_CONNECTION])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue().strip(), "support_error=support_internal_error")
        self.assertNotIn("private diagnostic", output.getvalue())
        self.assertNotIn("UnlistedFailure", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())
        self.assertNotIn("support_fingerprint=", output.getvalue())

    def test_cli_rejects_unlisted_operation_without_echoing_it(self):
        output = io.StringIO()
        with patch("sys.stdout", output):
            result = support.main(["--mode", "private-operation", "--support-sha", SHA_MAIN,
                                   "--connection-binding", SHA_CONNECTION])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue().strip(), "support_error=support_arguments_invalid")
        self.assertNotIn("private-operation", output.getvalue())

    def test_cli_rejects_arguments_outside_each_mode_before_host_access(self):
        invalid_mode_arguments = (
            ("support-inventory", "--approval-fingerprint", SHA_CONNECTION),
            ("support-inventory", "--receipt-sha256", SHA_CONNECTION),
            ("prepare-support",),
            ("prepare-support", "--approval-fingerprint", SHA_CONNECTION,
             "--receipt-sha256", SHA_CONNECTION),
            ("restore-support-inventory",),
            ("restore-support-inventory", "--receipt-sha256", SHA_CONNECTION,
             "--approval-fingerprint", SHA_CONNECTION),
            ("restore-support", "--approval-fingerprint", SHA_CONNECTION),
            ("restore-support", "--receipt-sha256", SHA_CONNECTION),
        )
        with patch.object(support, "LocalSupportHost", side_effect=AssertionError("host access must not occur")):
            for mode_args in invalid_mode_arguments:
                mode, *extra = mode_args
                output = io.StringIO()
                with self.subTest(mode_args=mode_args), patch("sys.stdout", output):
                    result = support.main(["--mode", mode, "--support-sha", SHA_MAIN,
                                           "--connection-binding", SHA_CONNECTION, *extra])
                self.assertEqual(result, 1)
                self.assertEqual(output.getvalue().strip(), "support_error=support_arguments_invalid")

    def test_bridge_allowlist_check_uses_only_the_fixed_denied_command(self):
        denied = subprocess.CompletedProcess([], 2, b"", b"arguments_invalid")
        with patch.object(support.subprocess, "run", return_value=denied) as run:
            support.LocalSupportHost._validate_bridge_allowlist(b"candidate", SHA_MAIN)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-8:], ["--sha", SHA_MAIN, "compose", "--", "exec", "-T", "api", "sh"])

    def test_bridge_allowlist_check_rejects_a_command_that_runs(self):
        accepted = subprocess.CompletedProcess([], 0, b"uid=0(root)", b"")
        with patch.object(support.subprocess, "run", return_value=accepted), \
                self.assertRaisesRegex(support.SupportError, "support_bridge_arbitrary_command_accepted"):
            support.LocalSupportHost._validate_bridge_allowlist(b"candidate", SHA_MAIN)

    def test_installed_bridge_smoke_uses_fixed_inventory_and_denied_command(self):
        successful_inventory = subprocess.CompletedProcess([], 0, b"", b"")
        denied_command = subprocess.CompletedProcess([], 2, b"", b"arguments_invalid")
        host = support.LocalSupportHost()
        with patch.object(support.subprocess, "run", side_effect=(successful_inventory, denied_command)) as run, \
                patch.dict(support.TARGET_PATHS, {"wrapper": SimpleNamespace(read_bytes=lambda: b"wrapper")}), \
                patch.object(support.LocalSupportHost, "_validate_wrapper_content") as validate_wrapper:
            host._smoke_installed(SHA_MAIN)
        self.assertEqual(run.call_count, 2)
        first = run.call_args_list[0].args[0]
        second = run.call_args_list[1].args[0]
        self.assertEqual(first[0:4], ["sudo", "-n", "/usr/bin/python3.10", "-B"])
        self.assertEqual(first[-5:], ["--mode", "inventory", "--sha", SHA_MAIN, "hashes"])
        self.assertEqual(second[-8:], ["--sha", SHA_MAIN, "compose", "--", "exec", "-T", "api", "sh"])
        self.assertTrue(all(call.kwargs.get("capture_output") for call in run.call_args_list))
        validate_wrapper.assert_called_once_with(b"wrapper")

    def test_installed_bridge_smoke_rejects_arbitrary_command_execution(self):
        successful_inventory = subprocess.CompletedProcess([], 0, b"", b"")
        accepted_command = subprocess.CompletedProcess([], 0, b"uid=0(root)", b"")
        with patch.object(support.subprocess, "run", side_effect=(successful_inventory, accepted_command)), \
                self.assertRaisesRegex(support.SupportError, "support_bridge_arbitrary_command_accepted"):
            support.LocalSupportHost()._smoke_installed(SHA_MAIN)

    def test_wrapper_candidate_allowlist_smoke_runs_as_unprivileged_user(self):
        syntax = subprocess.CompletedProcess([], 0, b"", b"")
        denied = subprocess.CompletedProcess([], 1, b"", b"command_not_allowed")
        with patch.object(support.LocalSupportHost, "_run", return_value=syntax), \
                patch.object(support.subprocess, "run", return_value=denied) as run:
            support.LocalSupportHost._validate_wrapper_content(b"candidate")
        self.assertEqual(run.call_args.args[0], [
            "sudo", "-n", "-H", "-u", "ubuntu", "env", "SSH_ORIGINAL_COMMAND=id", "bash", "-s",
        ])

    def test_backup_directory_requires_root_only_permissions(self):
        class FakePath:
            def __init__(self, mode: int):
                self.parent = SimpleNamespace(lstat=lambda: SimpleNamespace(
                    st_mode=stat.S_IFDIR | 0o755, st_uid=0, st_gid=0,
                ))
                self._info = SimpleNamespace(st_mode=stat.S_IFDIR | mode, st_uid=0, st_gid=0)

            def lstat(self):
                return self._info

        with patch.object(support, "BACKUPS_DIR", FakePath(0o700)):
            self.assertEqual(support.LocalSupportHost.backup_directory_state(), "ready")
            support.LocalSupportHost._ensure_backups_directory(create=False)
        with patch.object(support, "BACKUPS_DIR", FakePath(0o750)), \
                self.assertRaisesRegex(support.SupportError, "support_backup_directory_invalid"):
            self.assertEqual(support.LocalSupportHost.backup_directory_state(), "directory_invalid")
            support.LocalSupportHost._ensure_backups_directory(create=False)

    def test_backup_directory_creation_revalidates_after_mkdir(self):
        class FakePath:
            def __init__(self):
                self.mode = None
                self.created_mode = None
                self.parent = SimpleNamespace(lstat=lambda: SimpleNamespace(
                    st_mode=stat.S_IFDIR | 0o755, st_uid=0, st_gid=0,
                ))

            def lstat(self):
                if self.mode is None:
                    raise FileNotFoundError
                return SimpleNamespace(st_mode=stat.S_IFDIR | self.mode, st_uid=0, st_gid=0)

            def mkdir(self, *, mode):
                self.created_mode = mode
                self.mode = mode

        path = FakePath()
        with patch.object(support, "BACKUPS_DIR", path):
            self.assertEqual(support.LocalSupportHost.backup_directory_state(), "creatable")
            support.LocalSupportHost._ensure_backups_directory()
            self.assertEqual(path.created_mode, 0o700)
            self.assertEqual(support.LocalSupportHost.backup_directory_state(), "ready")


class SupportGitFetchTests(unittest.TestCase):
    @staticmethod
    def git(args: list[str], cwd: Path | None = None) -> str:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError("synthetic_git_fixture_failed")
        return result.stdout.strip()

    def test_object_fetch_preserves_missing_stale_or_diverged_tracking_refs(self):
        for ref_state in ("behind", "missing", "diverged"):
            with self.subTest(ref_state=ref_state), tempfile.TemporaryDirectory(prefix="pyp-support-fetch-") as directory:
                root = Path(directory)
                remote = root / "remote.git"
                seed = root / "seed"
                client = root / "client"
                self.git(["git", "init", "--bare", "-b", "main", str(remote)])
                self.git(["git", "init", "-b", "main", str(seed)])
                self.git(["git", "config", "user.name", "Fixture"], cwd=seed)
                self.git(["git", "config", "user.email", "fixture@example.invalid"], cwd=seed)
                (seed / "file.txt").write_text("one\n", encoding="utf-8")
                self.git(["git", "add", "file.txt"], cwd=seed)
                self.git(["git", "commit", "-m", "one"], cwd=seed)
                self.git(["git", "remote", "add", "origin", str(remote)], cwd=seed)
                self.git(["git", "push", "-u", "origin", "main"], cwd=seed)
                self.git(["git", "clone", str(remote), str(client)])
                self.git(["git", "config", "user.name", "Fixture"], cwd=client)
                self.git(["git", "config", "user.email", "fixture@example.invalid"], cwd=client)
                (seed / "file.txt").write_text("two\n", encoding="utf-8")
                self.git(["git", "commit", "-am", "two"], cwd=seed)
                target = self.git(["git", "rev-parse", "HEAD"], cwd=seed)
                self.git(["git", "push", "origin", "main"], cwd=seed)
                if ref_state == "missing":
                    self.git(["git", "update-ref", "-d", "refs/remotes/origin/main"], cwd=client)
                elif ref_state == "diverged":
                    first = self.git(["git", "rev-parse", "refs/remotes/origin/main"], cwd=client)
                    tree = self.git(["git", "rev-parse", f"{first}^{{tree}}"], cwd=client)
                    local_only = self.git(
                        ["git", "commit-tree", tree, "-p", first, "-m", "local-only"], cwd=client,
                    )
                    self.git(["git", "update-ref", "refs/remotes/origin/main", local_only], cwd=client)
                refs_before = self.git(["git", "for-each-ref", "--format=%(refname) %(objectname)"], cwd=client)
                fetch_head = client / ".git" / "FETCH_HEAD"
                fetch_head_before = fetch_head.read_bytes() if fetch_head.exists() else None
                self.git([
                    "git", "fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", "origin", "refs/heads/main",
                ], cwd=client)
                refs_after = self.git(["git", "for-each-ref", "--format=%(refname) %(objectname)"], cwd=client)
                fetch_head_after = fetch_head.read_bytes() if fetch_head.exists() else None
                self.assertEqual(refs_after, refs_before)
                self.assertEqual(fetch_head_after, fetch_head_before)
                self.git(["git", "cat-file", "-e", f"{target}^{{commit}}"], cwd=client)


class SupportReceiptStorageTests(unittest.TestCase):
    @staticmethod
    def write_receipt(directory: Path, operation_id: str) -> tuple[dict, str]:
        payload = {
            "schema": "pyp-app-preflight-support-v1",
            "kind": "preparation-complete",
            "operation_id": operation_id,
            "status": "complete",
        }
        content = support._canonical_json(payload) + b"\n"
        (directory / f"preflight-support-preparation-complete-{operation_id}.json").write_bytes(content)
        return payload, hashlib.sha256(content).hexdigest()

    def test_receipt_reader_ignores_existing_bridge_state_files(self):
        with tempfile.TemporaryDirectory(prefix="pyp-support-receipt-") as directory:
            root = Path(directory)
            (root / "bridge-snapshot.json").write_text("existing bridge state", encoding="utf-8")
            payload, digest = self.write_receipt(root, "a" * 32)
            with patch.object(support, "STATE_DIR", root), \
                    patch.object(support.LocalSupportHost, "_assert_directory", staticmethod(lambda *a, **k: None)), \
                    patch.object(support.LocalSupportHost, "_assert_file", staticmethod(lambda *a, **k: None)):
                self.assertEqual(support.LocalSupportHost().read_receipt(digest), payload)

    def test_receipt_reader_rejects_support_staging_and_ambiguous_digest(self):
        with tempfile.TemporaryDirectory(prefix="pyp-support-receipt-") as directory:
            root = Path(directory)
            _payload, digest = self.write_receipt(root, "a" * 32)
            with patch.object(support, "STATE_DIR", root), \
                    patch.object(support.LocalSupportHost, "_assert_directory", staticmethod(lambda *a, **k: None)), \
                    patch.object(support.LocalSupportHost, "_assert_file", staticmethod(lambda *a, **k: None)):
                staging = root / f".preflight-support-preparation-complete-{'b' * 32}.json.new"
                staging.write_text("incomplete", encoding="utf-8")
                with self.assertRaisesRegex(support.SupportError, "support_receipt_invalid"):
                    support.LocalSupportHost().read_receipt(digest)
                staging.unlink()
                (root / f"preflight-support-preparation-complete-{'c' * 32}.json").write_bytes(
                    (root / f"preflight-support-preparation-complete-{'a' * 32}.json").read_bytes()
                )
                with self.assertRaisesRegex(support.SupportError, "support_receipt_missing_or_ambiguous"):
                    support.LocalSupportHost().read_receipt(digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
