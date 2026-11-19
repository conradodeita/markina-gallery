"""Synthetic contracts for the root-only API/web Compose bridge."""

import contextlib
import copy
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import production_app_compose_bridge as bridge
import prove_app_engine_promotion as engine_proof

SHA = "a" * 40
FINGERPRINT = "b" * 64
CONTAINER_ID = "c" * 64
IMAGE_ID = "sha256:" + "d" * 64
COMPOSE_HASH = "e" * 64
SECRET_SENTINEL = "SYNTHETIC_SECRET_MUST_NOT_LEAK"


def container(service="api", *, secret=SECRET_SENTINEL, health="healthy", status="running"):
    return {
        "Id": CONTAINER_ID,
        "Image": IMAGE_ID,
        "Config": {
            "Labels": {
                "com.docker.compose.project": bridge.PROJECT,
                "com.docker.compose.service": service,
                "com.docker.compose.config-hash": COMPOSE_HASH,
            },
            "Env": [
                "APP_VERSION=" + SHA,
                "APP_ENV=production",
                "FACIAL_PROCESSING_ENABLED=true",
                "DATABASE_URL=" + secret,
            ],
        },
        "State": {"Status": status, "Health": {"Status": health}},
    }


class RunnerDockerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.original_docker = bridge._docker
        self.original_run = bridge._run
        self.original_project_root = bridge.PROJECT_ROOT
        self.original_project = bridge.PROJECT
        self.original_selector = bridge.select_api_web
        self.addCleanup(setattr, bridge, "_docker", self.original_docker)
        self.addCleanup(setattr, bridge, "_run", self.original_run)
        self.addCleanup(setattr, bridge, "PROJECT_ROOT", self.original_project_root)
        self.addCleanup(setattr, bridge, "PROJECT", self.original_project)
        self.addCleanup(setattr, bridge, "select_api_web", self.original_selector)

    def test_synthetic_original_revision_matches_pinned_bootstrap_revision(self):
        self.assertEqual(engine_proof.OLD_REVISION, bridge.ENGINE_BOOTSTRAP_SHA)

    def test_prefers_fixed_production_cli_when_executable(self):
        with patch.object(engine_proof.Path, "is_file", return_value=True), \
                patch.object(engine_proof.os, "access", return_value=True), \
                patch.object(engine_proof.shutil, "which") as which:
            engine_proof.configure_runner_context()
        self.assertIs(bridge._docker, self.original_docker)
        which.assert_not_called()

    def test_runner_context_rebinds_default_working_directory_to_checkout(self):
        runner_root = Path(engine_proof.__file__).resolve().parent.parent
        with patch.object(bridge, "_run", return_value="synthetic") as run, \
                patch.object(engine_proof.Path, "is_file", return_value=True), \
                patch.object(engine_proof.os, "access", return_value=True):
            engine_proof.configure_runner_context()
            self.assertEqual(bridge.PROJECT_ROOT, runner_root)
            self.assertEqual(bridge._run(["git", "status"]), "synthetic")
        run.assert_called_once_with(["git", "status"], cwd=runner_root, app_version="", input_text=None,
                                    timeout=120, max_output=bridge.MAX_COMMAND_OUTPUT_BYTES)

    def test_runner_context_preserves_explicit_working_directory(self):
        runner_root = Path(engine_proof.__file__).resolve().parent.parent
        explicit_cwd = runner_root / "scripts"
        with patch.object(bridge, "_run", return_value="synthetic") as run, \
                patch.object(engine_proof.Path, "is_file", return_value=True), \
                patch.object(engine_proof.os, "access", return_value=True):
            engine_proof.configure_runner_context()
            self.assertEqual(bridge._run(["git", "status"], cwd=explicit_cwd), "synthetic")
        run.assert_called_once_with(["git", "status"], cwd=explicit_cwd, app_version="", input_text=None,
                                    timeout=120, max_output=bridge.MAX_COMMAND_OUTPUT_BYTES)

    def test_runner_selector_uses_current_synthetic_project_when_omitted(self):
        with patch.object(bridge, "_run", return_value="synthetic"), \
                patch.object(engine_proof.Path, "is_file", return_value=True), \
                patch.object(engine_proof.os, "access", return_value=True):
            engine_proof.configure_runner_context()
            bridge.PROJECT = "markina-gallery-engine-proof-test"
            selected = bridge.select_api_web([container("api"), container("web")])
        self.assertEqual(set(selected), set(bridge.SERVICES))

    def test_runner_selector_preserves_explicit_project(self):
        with patch.object(bridge, "_run", return_value="synthetic"), \
                patch.object(engine_proof.Path, "is_file", return_value=True), \
                patch.object(engine_proof.os, "access", return_value=True):
            engine_proof.configure_runner_context()
            bridge.PROJECT = "current-synthetic-project"
            containers = [container("api"), container("web")]
            for item in containers:
                item["Config"]["Labels"]["com.docker.compose.project"] = "explicit-synthetic-project"
            selected = bridge.select_api_web(containers, project="explicit-synthetic-project")
        self.assertEqual(set(selected), set(bridge.SERVICES))

    def test_runner_adapter_uses_resolved_absolute_cli_through_bounded_runner(self):
        with patch.object(engine_proof.Path, "is_file", side_effect=[False, True]), \
                patch.object(engine_proof.os, "access", return_value=True), \
                patch.object(engine_proof.shutil, "which", return_value="/opt/hostedtoolcache/docker"):
            engine_proof.configure_runner_context()
        with patch.object(bridge, "_run", return_value="synthetic") as run:
            result = bridge._docker(["ps"], timeout=30)
        self.assertEqual(result, "synthetic")
        run.assert_called_once_with(["/opt/hostedtoolcache/docker", "ps"], input_text=None,
                                   timeout=30, max_output=bridge.MAX_COMMAND_OUTPUT_BYTES)

    def test_runner_adapter_falls_back_when_fixed_cli_is_not_executable(self):
        with patch.object(engine_proof.Path, "is_file", side_effect=[True, True]), \
                patch.object(engine_proof.os, "access", side_effect=[False, True]), \
                patch.object(engine_proof.shutil, "which", return_value="/usr/local/bin/docker"):
            engine_proof.configure_runner_context()
        with patch.object(bridge, "_run", return_value="synthetic") as run:
            bridge._docker(["version"])
        run.assert_called_once_with(["/usr/local/bin/docker", "version"], input_text=None,
                                   timeout=120, max_output=bridge.MAX_COMMAND_OUTPUT_BYTES)

    def test_runner_adapter_rejects_relative_cli_path(self):
        with patch.object(engine_proof.Path, "is_file", return_value=False), \
                patch.object(engine_proof.shutil, "which", return_value="docker"), \
                self.assertRaisesRegex(SystemExit, "CLI Docker absoluto"):
            engine_proof.configure_runner_context()


class RootIdentityTests(unittest.TestCase):
    def test_non_root_is_rejected_before_protected_operations(self):
        original_check = bridge.require_root
        with patch.object(bridge, "require_root", side_effect=lambda: original_check(1000, 1000)), \
                patch.object(bridge, "_discover_context") as discover:
            result = bridge.main(["--mode", "inventory", "--sha", SHA, "hashes"])
        self.assertEqual(result, 1)
        discover.assert_not_called()

    def test_root_identity_requires_both_effective_ids(self):
        bridge.require_root(0, 0)
        for uid, gid in ((1000, 0), (0, 1000), (1000, 1000)):
            with self.subTest(uid=uid, gid=gid), self.assertRaises(bridge.BridgeError):
                bridge.require_root(uid, gid)


class SnapshotPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="app-compose-bridge-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "allowed"
        self.root.mkdir()
        self.file = self.root / "compose.yml"
        self.file.write_text("services: {}\n", encoding="utf-8")

    def test_accepts_only_regular_absolute_files_inside_one_root(self):
        self.assertEqual(bridge.validate_snapshot_path(self.file, (self.root,)), self.file.resolve())
        with self.assertRaises(bridge.BridgeError):
            bridge.validate_snapshot_path("relative.yml", (self.root,))
        with self.assertRaises(bridge.BridgeError):
            bridge.validate_snapshot_path(self.root / ".." / "outside.yml", (self.root,))
        with self.assertRaises(bridge.BridgeError):
            bridge.validate_snapshot_path(self.root, (self.root,))

    def test_rejects_symlinks_and_duplicate_label_paths(self):
        link = self.root / "linked.yml"
        try:
            link.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this filesystem")
        with self.assertRaises(bridge.BridgeError):
            bridge.validate_snapshot_path(link, (self.root,))
        with self.assertRaises(bridge.BridgeError):
            bridge.parse_compose_file_paths(f"{self.file},{self.file}", (self.root,))

    def test_duplicate_paths_are_rejected_without_symlink_support(self):
        with self.assertRaisesRegex(bridge.BridgeError, "compose_files_label_ambiguous"):
            bridge.parse_compose_file_paths(f"{self.file},{self.file}", (self.root,))

    def test_symlink_guard_is_checked_before_resolving_the_path(self):
        original = Path.lstat
        def metadata(path, *args, **kwargs):
            if path == self.file:
                return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)
            return original(path, *args, **kwargs)
        with patch.object(Path, "lstat", metadata), self.assertRaisesRegex(bridge.BridgeError, "snapshot_symlink"):
            bridge.validate_snapshot_path(self.file, (self.root,))

    def test_hash_is_stable_and_matches_sha256(self):
        expected = hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.assertEqual(bridge.snapshot_sha256(self.file), expected)

    def test_metadata_rejects_links_writable_modes_and_wrong_owner(self):
        safe = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_size=5, st_uid=1000)
        bridge.validate_snapshot_metadata(safe, allowed_owners={1000})
        bad_modes = (
            SimpleNamespace(st_mode=stat.S_IFREG | 0o622, st_nlink=1, st_size=5, st_uid=1000),
            SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=2, st_size=5, st_uid=1000),
            SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_size=5, st_uid=2000),
        )
        for metadata in bad_modes:
            with self.subTest(metadata=metadata), self.assertRaises(bridge.BridgeError):
                bridge.validate_snapshot_metadata(metadata, allowed_owners={1000})
        with self.assertRaises(bridge.BridgeError):
            bridge.validate_snapshot_metadata(safe, allowed_owners={1000}, root_only=True)

    def test_private_deploy_state_accepts_root_or_checkout_owner(self):
        for owner in (0, 1000):
            with self.subTest(owner=owner):
                directory = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=owner)
                snapshot = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_size=5, st_uid=owner)
                bridge.validate_private_snapshot_directory_metadata(directory, allowed_owners={0, 1000})
                bridge.validate_private_snapshot_file_metadata(snapshot, allowed_owners={0, 1000})

    def test_private_deploy_state_rejects_shared_modes_wrong_owners_and_exec_files(self):
        for mode in (0o710, 0o705, 0o777):
            directory = SimpleNamespace(st_mode=stat.S_IFDIR | mode, st_uid=1000)
            with self.subTest(directory_mode=oct(mode)), self.assertRaisesRegex(
                    bridge.BridgeError, "snapshot_parent_permissions_invalid"):
                bridge.validate_private_snapshot_directory_metadata(directory, allowed_owners={0, 1000})
        for owner, mode in ((2000, 0o600), (1000, 0o640), (1000, 0o604), (1000, 0o700)):
            snapshot = SimpleNamespace(st_mode=stat.S_IFREG | mode, st_nlink=1, st_size=5, st_uid=owner)
            with self.subTest(owner=owner, mode=oct(mode)), self.assertRaisesRegex(
                    bridge.BridgeError, "snapshot_file_permissions_invalid"):
                bridge.validate_private_snapshot_file_metadata(snapshot, allowed_owners={0, 1000})


class ContainerAndDisclosureTests(unittest.TestCase):
    def test_selects_exactly_one_running_api_and_web(self):
        api = container("api")
        web = container("web")
        selected = bridge.select_api_web([api, web])
        self.assertEqual(set(selected), {"api", "web"})
        with self.assertRaises(bridge.BridgeError):
            bridge.select_api_web([api])
        with self.assertRaises(bridge.BridgeError):
            bridge.select_api_web([api, container("api"), web])

    def test_health_and_environment_are_allowlisted(self):
        record = bridge.minimized_service_record("api", container())
        rendered = str(record)
        self.assertNotIn(SECRET_SENTINEL, rendered)
        self.assertEqual(record["facial_processing_enabled"], "true")
        self.assertEqual(record["app_env"], "production")
        self.assertEqual(record["app_version"], SHA)
        self.assertEqual(set(record), {"service", "container_id", "image_id", "compose_hash",
                                       "health", "app_version", "app_env", "facial_processing_enabled"})
        self.assertEqual(bridge.allowlisted_environment({"DATABASE_URL": SECRET_SENTINEL}), {})

    def test_selects_running_unhealthy_container_for_explicit_rollback_diagnosis(self):
        selected = bridge.select_api_web([container("api", health="unhealthy"), container("web")])
        self.assertEqual(selected["api"]["State"]["Health"]["Status"], "unhealthy")

    def test_only_the_approved_profile_pair_is_accepted(self):
        self.assertEqual(bridge.resolve_profile_set(), ("facial", "preview-adjustment"))
        for profiles in (("facial",), ("preview-adjustment",), ("gemma",),
                         ("facial", "preview-adjustment", "other")):
            with self.subTest(profiles=profiles), self.assertRaises(bridge.BridgeError):
                bridge.resolve_profile_set(profiles)


class ComposeAllowlistTests(unittest.TestCase):
    def test_read_only_queries_are_narrow(self):
        for service in ("api", "web", "nginx"):
            self.assertEqual(bridge._classify_compose_args(["ps", "-q", service], "inventory"), "ps")
        self.assertEqual(bridge._classify_compose_args(["config", "--quiet"], "release"), "quiet-config")
        self.assertEqual(bridge._classify_compose_args(
            ["exec", "-T", "-e", "PYTHONDONTWRITEBYTECODE=1", "api", "python", "-B", "-m", "alembic", "current"],
            "inventory"), "database-revision")

    def test_mutating_commands_are_limited_to_api_and_web_release(self):
        self.assertEqual(bridge._classify_compose_args(["build", "api", "web"], "release"), "build")
        self.assertEqual(bridge._classify_compose_args(["build", "web"], "release"), "build")
        release_up = ["up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", "api", "web"]
        rollback_up = ["up", "-d", "--no-build", "--no-deps", "--force-recreate", "--wait",
                       "--wait-timeout", "120", "api", "web"]
        self.assertEqual(bridge._classify_compose_args(release_up, "release"), "up")
        self.assertEqual(bridge._classify_compose_args(rollback_up, "rollback"), "up")
        forbidden = (
            (["build", "worker"], "release"),
            (["build", "nginx"], "release"),
            (release_up + ["worker"], "release"),
            (rollback_up, "release"),
            (["down"], "release"),
            (["exec", "-T", "api", "sh"], "release"),
            (["exec", "-T", "nginx", "nginx", "-s", "reload"], "inventory"),
        )
        for argv, mode in forbidden:
            with self.subTest(argv=argv, mode=mode), self.assertRaises(bridge.BridgeError):
                bridge._classify_compose_args(argv, mode)

    def test_cli_rejects_extra_paths_and_malformed_sha(self):
        with self.assertRaises(bridge.BridgeError):
            bridge._parse_args(["--mode", "inventory", "--sha", "../" + SHA, "hashes"])
        with self.assertRaises(bridge.BridgeError):
            bridge._parse_args(["--mode", "inventory", "--sha", SHA, "hashes", "extra"])
        with self.assertRaises(bridge.BridgeError):
            bridge._parse_args(["--mode", "release", "--sha", SHA, "--app-version", "bad", "compose"])

    def test_database_revision_output_is_reduced_to_a_single_revision(self):
        self.assertEqual(bridge.REVISION_RE.fullmatch("20261113_0126 (head)").group(1), "20261113_0126")
        self.assertIsNone(bridge.REVISION_RE.fullmatch("DATABASE_URL=" + SECRET_SENTINEL))


def semantic_fixture():
    model = {
        "image": IMAGE_ID, "environment": {"APP_ENV": "production", "FACIAL_PROCESSING_ENABLED": "true",
                                            "APP_VERSION": SHA, "DATABASE_URL": SECRET_SENTINEL},
        "expose": ["8000"], "networks": {"internal": {}},
        "healthcheck": {"test": ["CMD", "probe"], "interval": "10s"},
        "volumes": [{"type": "volume", "source": "media", "target": "/media"}],
    }
    document = {"services": {"api": model}, "networks": {"internal": {"name": "markina-gallery_internal"}},
                "volumes": {"media": {"name": "markina-gallery_media"}}}
    item = container()
    item["Config"].update({"Cmd": ["server"], "Entrypoint": None, "User": "", "WorkingDir": "/app",
                           "Healthcheck": {"Test": ["CMD", "probe"], "Interval": 10000000000},
                           "Hostname": CONTAINER_ID[:12], "ExposedPorts": {"8000/tcp": {}}})
    item["HostConfig"] = {"RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                          "NetworkMode": "markina-gallery_internal",
                          "LogConfig": {"Type": "json-file", "Config": {}}}
    item["Mounts"] = [{"Type": "volume", "Name": "markina-gallery_media", "Destination": "/media",
                        "RW": True, "Propagation": ""}]
    item["NetworkSettings"] = {"Networks": {"markina-gallery_internal": {"Aliases": ["api"]}}}
    image = {"Id": IMAGE_ID, "Config": {"Cmd": ["server"], "Entrypoint": None, "User": "", "WorkingDir": "/app",
                                         "Env": ["PATH=/usr/bin"], "Labels": {}}}
    item["Config"]["Env"].append("PATH=/usr/bin")
    return model, document, item, image


class SemanticProofTests(unittest.TestCase):
    def test_proves_snapshot_with_missing_compose_hash_and_keeps_secrets_inside(self):
        model, document, item, image = semantic_fixture()
        del item["Config"]["Labels"]["com.docker.compose.config-hash"]
        result = bridge.prove_service_model("api", model, document, item, image)
        self.assertRegex(result, r"^[a-f0-9]{64}$")
        self.assertNotIn(SECRET_SENTINEL, result)

    def test_rejects_effective_runtime_drift_in_every_covered_boundary(self):
        mutations = (
            lambda m, d, c, i: c["Config"]["Env"].append("EXTRA=" + SECRET_SENTINEL),
            lambda m, d, c, i: c["Config"].update(Cmd=["other-server"]),
            lambda m, d, c, i: c["Config"].update(User="root"),
            lambda m, d, c, i: c["Config"]["Healthcheck"].update(Interval=20000000000),
            lambda m, d, c, i: c["Config"]["Labels"].update(unexpected=SECRET_SENTINEL),
            lambda m, d, c, i: c["Mounts"][0].update(RW=False),
            lambda m, d, c, i: c["Mounts"][0].update(Name="other-tenant-volume"),
            lambda m, d, c, i: c["NetworkSettings"]["Networks"].update(other_project={}),
            lambda m, d, c, i: c["NetworkSettings"]["Networks"]["markina-gallery_internal"].update(Aliases=["api", "unexpected-tenant"]),
            lambda m, d, c, i: c["NetworkSettings"]["Networks"]["markina-gallery_internal"].update(GwPriority=10),
            lambda m, d, c, i: c["HostConfig"].update(Mounts=[{"Target": "/media", "VolumeOptions": {"NoCopy": True}}]),
            lambda m, d, c, i: c["HostConfig"].update(Privileged=True),
            lambda m, d, c, i: c["HostConfig"].update(Memory=123456),
            lambda m, d, c, i: c["HostConfig"].update(SecurityOpt=["seccomp=unconfined"]),
            lambda m, d, c, i: c["HostConfig"].update(PortBindings={"8000/tcp": [{"HostPort": "8000"}]}),
            lambda m, d, c, i: c["HostConfig"]["RestartPolicy"].update(Name="always"),
            lambda m, d, c, i: c["HostConfig"].update(LogConfig={"Type": "none", "Config": {}}),
            lambda m, d, c, i: m.update(unknown_property=SECRET_SENTINEL),
        )
        for mutation in mutations:
            values = semantic_fixture()
            mutation(*values)
            with self.subTest(mutation=mutation), self.assertRaises(bridge.BridgeError) as error:
                bridge.prove_service_model("api", *values)
            self.assertNotIn(SECRET_SENTINEL, str(error.exception))

    def test_image_defaults_must_be_included_and_duplicate_environment_is_rejected(self):
        model, document, item, image = semantic_fixture()
        item["Config"]["Env"].remove("PATH=/usr/bin")
        with self.assertRaisesRegex(bridge.BridgeError, "semantic_mismatch_environment"):
            bridge.prove_service_model("api", model, document, item, image)
        with self.assertRaisesRegex(bridge.BridgeError, "environment_contract_ambiguous"):
            bridge.environment_map(["TOKEN=first", "TOKEN=second"])

    def test_proof_does_not_modify_input_models_or_runtime(self):
        values = semantic_fixture()
        original = copy.deepcopy(values)
        bridge.prove_service_model("api", *values)
        self.assertEqual(values, original)

    def test_replacement_preserves_effective_defaults_and_changes_only_allowed_version(self):
        _model, document, item, image = semantic_fixture()
        original = copy.deepcopy((document, item))
        candidate = bridge.replacement_document("api", document, item, IMAGE_ID, "f" * 40)
        expected = copy.deepcopy(item)
        env = bridge.environment_map(expected["Config"]["Env"])
        env["APP_VERSION"] = "f" * 40
        expected["Config"]["Env"] = [f"{k}={v}" for k, v in env.items()]
        bridge.prove_service_model("api", candidate["services"]["api"], candidate, expected, image)
        self.assertEqual((document, item), original)
        self.assertEqual(set(candidate["services"]), {"api"})
        self.assertTrue(candidate["networks"]["internal"]["external"])
        self.assertTrue(candidate["volumes"]["media"]["external"])
        self.assertEqual(bridge.runtime_semantic_identity(item), bridge.runtime_semantic_identity(expected))

    def test_new_image_default_cannot_silently_change_environment(self):
        _model, document, item, image = semantic_fixture()
        candidate = bridge.replacement_document("api", document, item, IMAGE_ID, SHA)
        image["Config"]["Env"].append("NEW_RUNTIME_FLAG=changed")
        with self.assertRaisesRegex(bridge.BridgeError, "semantic_mismatch_environment"):
            bridge.prove_service_model("api", candidate["services"]["api"], candidate, item, image)


ENGINE_NETWORK = "markina-gallery_internal"
ENGINE_NETWORK_ID = "1" * 64
ENGINE_TARGET_SHA = "2" * 40
ENGINE_TARGET_IMAGE = "sha256:" + "3" * 64
ENGINE_CONFIG_BIND = "/etc/pyp-google-drive/oauth-client.json"
ENGINE_CONFIG_TARGET = "/run/secrets/google-drive-oauth-client.json"
ENGINE_VOLUME_NAME = "markina-gallery_media-source"
ENGINE_VOLUME_TARGET = "/var/lib/markina/source"
ENGINE_VOLUME_MOUNT = {
    "Type": "volume",
    "Source": ENGINE_VOLUME_NAME,
    "Target": ENGINE_VOLUME_TARGET,
    "ReadOnly": False,
    "VolumeOptions": {"NoCopy": True},
}


def engine_fixture(*, shadow=False):
    item = container()
    item["Id"] = "4" * 64 if shadow else CONTAINER_ID
    item["Image"] = ENGINE_TARGET_IMAGE if shadow else IMAGE_ID
    if shadow:
        item["State"] = {"Status": "created", "Running": False}
    name = "markina-gallery-api-shadow" if shadow else "markina-gallery-api-previous"
    item["Name"] = "/" + name
    config = item["Config"]
    del config["Labels"]["com.docker.compose.config-hash"]
    config["Labels"].update({
        "com.docker.compose.project.config_files": "/var/lib/markina-gallery/deploy-state/historical-api.json",
        "com.docker.compose.project.working_dir": "/opt/markina-gallery/docker",
        "io.pickyourpic.release": ENGINE_TARGET_SHA if shadow else SHA,
    })
    if shadow:
        config["Env"][0] = "APP_VERSION=" + ENGINE_TARGET_SHA
    config.update({
        "Image": item["Image"],
        "Hostname": item["Id"][:12],
        "Entrypoint": ["/usr/local/bin/load-custody"],
        "Cmd": ["server", "--port", "8000"],
        "User": "1001:1001",
        "WorkingDir": "/app",
        "ExposedPorts": {"8000/tcp": {}},
        "Healthcheck": {"Test": ["CMD", "probe"], "Interval": 10000000000},
    })
    item["HostConfig"] = {
        "Binds": [
            f"{ENGINE_CONFIG_BIND}:{ENGINE_CONFIG_TARGET}:ro",
            f"{ENGINE_VOLUME_NAME}:{ENGINE_VOLUME_TARGET}:rw",
        ],
        "Mounts": [],
        "NetworkMode": ENGINE_NETWORK,
        "PortBindings": {},
        "PublishAllPorts": False,
        "Privileged": False,
        "ReadonlyRootfs": True,
        "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=16m"},
        "CapDrop": ["ALL"],
        "SecurityOpt": ["no-new-privileges:true"],
        "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
        "LogConfig": {"Type": "json-file", "Config": {}},
    }
    if shadow:
        item["HostConfig"]["Binds"].pop()
        item["HostConfig"]["Mounts"] = [copy.deepcopy(ENGINE_VOLUME_MOUNT)]
    item["Mounts"] = [
        {"Type": "bind", "Source": ENGINE_CONFIG_BIND, "Destination": ENGINE_CONFIG_TARGET,
         "Mode": "ro", "RW": False, "Propagation": "rprivate"},
        {"Type": "volume", "Name": ENGINE_VOLUME_NAME, "Driver": "local",
         "Source": f"/var/lib/docker/volumes/{ENGINE_VOLUME_NAME}/_data",
         "Destination": ENGINE_VOLUME_TARGET, "Mode": "" if shadow else "rw", "RW": True,
         "Propagation": ""},
    ]
    item["NetworkSettings"] = {
        "Ports": {"8000/tcp": None},
        "Networks": {
            ENGINE_NETWORK: {
                "NetworkID": ENGINE_NETWORK_ID,
                "EndpointID": "5" * 64 if shadow else "6" * 64,
                "Aliases": [name] if shadow else ["api", name],
                **({"DNSNames": [name, item["Id"][:12]]} if shadow else {}),
                "IPAddress": "172.30.0.11" if shadow else "172.30.0.10",
                "IPAMConfig": None,
            },
        },
    }
    return item


class EngineBootstrapReceiptTests(unittest.TestCase):
    @staticmethod
    def valid_receipt():
        return {
            "target": bridge.ENGINE_BOOTSTRAP_SHA,
            "phase": "deployed",
            "schema": "20261113_0126",
            "containers": {
                service: {"new_id": identity, "new_image": image}
                for service, (identity, image) in bridge.ENGINE_BOOTSTRAP.items()
            },
        }

    @staticmethod
    def bootstrap_containers():
        return {
            service: {
                "Id": identity,
                "Image": image,
                "Config": {
                    "Env": ["APP_VERSION=" + bridge.ENGINE_BOOTSTRAP_SHA],
                    "Labels": {"io.pickyourpic.release": bridge.ENGINE_BOOTSTRAP_SHA},
                },
            }
            for service, (identity, image) in bridge.ENGINE_BOOTSTRAP.items()
        }

    def test_bootstrap_receipt_uses_the_reviewed_path_hash_and_identity(self):
        checksum = "f" * 64
        with patch.object(bridge, "_engine_private_object", return_value=(self.valid_receipt(), checksum)) as read:
            self.assertEqual(bridge._engine_bootstrap_receipt(), checksum)
        read.assert_called_once_with(
            bridge.STATE_DIR / "google-drive-owner-bfe511f" / "cutover.json",
            pinned_hash=bridge.ENGINE_BOOTSTRAP_RECEIPT_SHA256,
        )

    def test_bootstrap_receipt_rejects_mismatched_or_malformed_container_records(self):
        malformed = self.valid_receipt()
        malformed["containers"]["api"] = None
        with patch.object(bridge, "_engine_private_object", return_value=(malformed, "f" * 64)), \
                self.assertRaisesRegex(bridge.BridgeError, "engine_receipt_identity_mismatch"):
            bridge._engine_bootstrap_receipt()

        mismatched = self.valid_receipt()
        mismatched["containers"]["web"]["new_image"] = IMAGE_ID
        with patch.object(bridge, "_engine_private_object", return_value=(mismatched, "f" * 64)), \
                self.assertRaisesRegex(bridge.BridgeError, "engine_receipt_identity_mismatch"):
            bridge._engine_bootstrap_receipt()

    def test_discovery_selects_only_the_exact_reviewed_bootstrap_pair(self):
        containers = self.bootstrap_containers()
        records = {service: {"id": item["Id"]} for service, item in containers.items()}
        with tempfile.TemporaryDirectory(prefix="engine-bootstrap-discovery-") as temporary, \
                patch.object(bridge, "BRIDGE_STATE", Path(temporary)), \
                patch.object(bridge, "_inspect_api_web", return_value=containers), \
                patch.object(bridge, "_engine_records", return_value=records), \
                patch.object(bridge, "_engine_bootstrap_receipt", return_value="f" * 64):
            selected, proof = bridge._engine_discover("inventory", "a" * 40)
        self.assertIs(selected, containers)
        self.assertEqual(proof["type"], "engine-bootstrap")
        self.assertEqual(proof["containers"], records)

        mixed = self.bootstrap_containers()
        mixed["web"]["Image"] = IMAGE_ID
        with tempfile.TemporaryDirectory(prefix="engine-bootstrap-mismatch-") as temporary, \
                patch.object(bridge, "BRIDGE_STATE", Path(temporary)), \
                patch.object(bridge, "_inspect_api_web", return_value=mixed), \
                patch.object(bridge, "_engine_bootstrap_receipt", return_value="f" * 64), \
                self.assertRaisesRegex(bridge.BridgeError, "engine_original_pair_mismatch"):
            bridge._engine_discover("inventory", "a" * 40)

    def test_discovery_treats_nonbootstrap_runtime_as_a_successor_candidate(self):
        successor = {
            service: {
                "Id": "f" * 64,
                "Image": IMAGE_ID,
                "Config": {"Env": ["APP_VERSION=" + SHA], "Labels": {"io.pickyourpic.release": SHA}},
            }
            for service in bridge.SERVICES
        }
        with tempfile.TemporaryDirectory(prefix="engine-successor-discovery-") as temporary, \
                patch.object(bridge, "BRIDGE_STATE", Path(temporary)), \
                patch.object(bridge, "_inspect_api_web", return_value=successor), \
                patch.object(bridge, "_engine_bootstrap_receipt") as receipt:
            selected, proof = bridge._engine_discover("inventory", "a" * 40)
        self.assertIs(selected, successor)
        self.assertIsNone(proof)
        receipt.assert_not_called()


class EngineRuntimeProofTests(unittest.TestCase):
    def test_bootstrap_hostname_exception_is_limited_to_the_reviewed_pair(self):
        original = engine_fixture()
        original["Id"] = bridge.ENGINE_BOOTSTRAP["api"][0]
        original["Config"]["Hostname"] = "api"
        with self.assertRaisesRegex(bridge.BridgeError, "engine_legacy_hostname_unproven"):
            bridge._engine_require_generated_hostname("api", original, {"config": original["Config"]})
        original["Config"]["Hostname"] = bridge.ENGINE_BOOTSTRAP_HOSTNAMES["api"]
        bridge._engine_require_generated_hostname("api", original, {"config": original["Config"]})

    def test_recovery_accepts_docker_short_ids_only_for_recorded_participants(self):
        bridge._engine_validate_running_participants(["a" * 12], ["a" * 64, "b" * 64])
        with self.assertRaisesRegex(bridge.BridgeError, "engine_recovery_unknown_participant"):
            bridge._engine_validate_running_participants(["c" * 12], ["a" * 64, "b" * 64])
        with self.assertRaisesRegex(bridge.BridgeError, "engine_recovery_unknown_participant"):
            bridge._engine_validate_running_participants(["a" * 12], ["a" * 12 + "0" * 52,
                                                                        "a" * 12 + "1" * 52])

    def test_engine_api_short_id_alias_is_normalized_before_promotion(self):
        original = engine_fixture()
        _, aliases = bridge.engine_service_endpoint("api", original)
        legacy_api_original = copy.deepcopy(original)
        legacy_api_original["NetworkSettings"]["Networks"][ENGINE_NETWORK]["Aliases"].append(
            original["Id"][:12])
        legacy_id_network, legacy_id_aliases = bridge.engine_service_endpoint("api", legacy_api_original)
        self.assertEqual(legacy_id_network, ENGINE_NETWORK_ID)
        self.assertEqual(legacy_id_aliases, aliases)
        self.assertEqual(bridge.engine_runtime_identity("api", legacy_api_original),
                         bridge.engine_runtime_identity("api", original))

    def test_candidate_config_is_proved_before_it_can_start_or_receive_aliases(self):
        original = engine_fixture()
        candidate = engine_fixture(shadow=True)
        candidate["NetworkSettings"]["Networks"] = {}
        bridge._engine_verify_before_start("api", original, candidate, ENGINE_TARGET_IMAGE,
                                          ENGINE_TARGET_SHA, "markina-gallery-api-shadow")

        routed = engine_fixture(shadow=True)
        routed["NetworkSettings"]["Networks"][ENGINE_NETWORK]["Aliases"].append("api")
        with self.assertRaisesRegex(bridge.BridgeError, "engine_candidate_prestart_dns_invalid"):
            bridge._engine_verify_before_start("api", original, routed, ENGINE_TARGET_IMAGE,
                                              ENGINE_TARGET_SHA, "markina-gallery-api-shadow")

        started = engine_fixture(shadow=True)
        started["State"] = {"Status": "running", "Running": True}
        with self.assertRaisesRegex(bridge.BridgeError, "engine_candidate_not_stopped"):
            bridge._engine_verify_before_start("api", original, started, ENGINE_TARGET_IMAGE,
                                              ENGINE_TARGET_SHA, "markina-gallery-api-shadow")

    def test_shadow_payload_changes_reviewed_image_version_and_release_label_only(self):
        original = engine_fixture()
        before = copy.deepcopy(original)
        payload = bridge.engine_create_payload("api", original, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA)
        self.assertEqual(payload["Image"], ENGINE_TARGET_IMAGE)
        env = bridge.environment_map(original["Config"]["Env"])
        env["APP_VERSION"] = ENGINE_TARGET_SHA
        self.assertEqual(bridge.environment_map(payload["Env"]), env)
        labels = {**original["Config"]["Labels"], "io.pickyourpic.release": ENGINE_TARGET_SHA}
        self.assertEqual(payload["Labels"], labels)
        self.assertEqual(payload["Hostname"], "")  # Docker generates an isolated hostname from the new ID.
        for field in ("Entrypoint", "Cmd", "User", "WorkingDir", "Healthcheck", "ExposedPorts"):
            self.assertEqual(payload[field], original["Config"][field])
        expected_host = copy.deepcopy(original["HostConfig"])
        expected_host["Binds"] = [f"{ENGINE_CONFIG_BIND}:{ENGINE_CONFIG_TARGET}:ro"]
        expected_host["Mounts"] = [ENGINE_VOLUME_MOUNT]
        self.assertEqual(payload["HostConfig"], expected_host)
        endpoints = payload["NetworkingConfig"]["EndpointsConfig"]
        self.assertEqual(set(endpoints), {ENGINE_NETWORK})
        self.assertEqual(endpoints[ENGINE_NETWORK]["Aliases"], [])
        self.assertEqual(original, before)

    def test_shadow_inspect_proves_equivalence_with_no_live_alias(self):
        original = engine_fixture()
        shadow = engine_fixture(shadow=True)
        bridge.engine_verify_candidate("api", original, shadow, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA)

        short_id_alias = copy.deepcopy(shadow)
        short_id_alias["NetworkSettings"]["Networks"][ENGINE_NETWORK]["Aliases"].append(
            short_id_alias["Id"][:12])
        bridge.engine_verify_candidate("api", original, short_id_alias, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA)

        original_network, aliases = bridge.engine_service_endpoint("api", original)
        self.assertEqual(original_network, ENGINE_NETWORK_ID)
        self.assertIn("api", aliases)
        shadow_network, shadow_aliases = bridge.engine_service_endpoint("api", shadow, shadow=True)
        self.assertEqual(shadow_network, original_network)
        self.assertNotIn("api", shadow_aliases)

    def test_promoted_candidate_keeps_original_route_aliases(self):
        original = engine_fixture()
        promoted = engine_fixture(shadow=True)
        endpoint = promoted["NetworkSettings"]["Networks"][ENGINE_NETWORK]
        endpoint["Aliases"] = list(reversed(original["NetworkSettings"]["Networks"][ENGINE_NETWORK]["Aliases"]))
        bridge.engine_verify_candidate("api", original, promoted, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA, shadow=False)
        endpoint["Aliases"].remove("markina-gallery-api-previous")
        with self.assertRaises(bridge.BridgeError):
            bridge.engine_verify_candidate("api", original, promoted, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA,
                                           shadow=False)

    def test_runtime_identity_binds_effective_config_without_exposing_values(self):
        original = engine_fixture()
        identity = bridge.engine_runtime_identity("api", original)
        self.assertRegex(identity, r"^[a-f0-9]{64}$")
        self.assertNotIn(SECRET_SENTINEL, identity)
        changed = copy.deepcopy(original)
        changed["Config"]["Env"].append("ADDITIONAL_CONFIG=" + SECRET_SENTINEL)
        self.assertNotEqual(bridge.engine_runtime_identity("api", changed), identity)
        self.assertEqual(bridge.engine_runtime_identity("api", original), identity)

    def test_creation_refuses_unsafe_original_engine_config(self):
        mutations = {
            "privileged": lambda item: item["HostConfig"].update(Privileged=True),
            "published-port": lambda item: item["HostConfig"].update(
                PortBindings={"8000/tcp": [{"HostPort": "8000"}]},
            ),
            "other-network": lambda item: item["NetworkSettings"]["Networks"].update(
                unexpected={"NetworkID": "7" * 64},
            ),
            "unmatched-bind": lambda item: item["Mounts"][0].update(Source="/etc/unapproved"),
        }
        for boundary, mutate in mutations.items():
            with self.subTest(boundary=boundary):
                original = engine_fixture()
                mutate(original)
                with self.assertRaises(bridge.BridgeError) as error:
                    bridge.engine_create_payload("api", original, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA)
                self.assertNotIn(SECRET_SENTINEL, str(error.exception))

    def test_shadow_proof_rejects_runtime_drift_and_live_aliases(self):
        mutations = {
            "image": lambda item: item.update(Image=IMAGE_ID),
            "version": lambda item: item["Config"]["Env"].__setitem__(0, "APP_VERSION=" + SHA),
            "release-label": lambda item: item["Config"]["Labels"].update({"io.pickyourpic.release": SHA}),
            "effective-environment": lambda item: item["Config"]["Env"].append("EXTRA=" + SECRET_SENTINEL),
            "root-filesystem": lambda item: item["HostConfig"].update(ReadonlyRootfs=False),
            "security-policy": lambda item: item["HostConfig"].update(SecurityOpt=[]),
            "tmpfs": lambda item: item["HostConfig"].update(Tmpfs={}),
            "bind-access": lambda item: item["Mounts"][0].update(RW=True),
            "volume-source": lambda item: item["Mounts"][1].update(Name="other-volume"),
            "volume-copy": lambda item: item["HostConfig"]["Mounts"][0]["VolumeOptions"].update(NoCopy=False),
            "network-id": lambda item: item["NetworkSettings"]["Networks"][ENGINE_NETWORK].update(
                NetworkID="7" * 64,
            ),
            "live-alias": lambda item: item["NetworkSettings"]["Networks"][ENGINE_NETWORK]["Aliases"].append("api"),
        }
        original = engine_fixture()
        for boundary, mutate in mutations.items():
            with self.subTest(boundary=boundary):
                shadow = engine_fixture(shadow=True)
                mutate(shadow)
                with self.assertRaises(bridge.BridgeError) as error:
                    bridge.engine_verify_candidate("api", original, shadow, ENGINE_TARGET_IMAGE, ENGINE_TARGET_SHA)
                self.assertNotIn(SECRET_SENTINEL, str(error.exception))


class ProtectedOperationTests(unittest.TestCase):
    def test_invalid_operation_is_refused_before_discovery_without_echoing_secrets(self):
        captured = io.StringIO()
        with patch.object(bridge, "require_root"), patch.object(bridge, "_discover_context") as discover, \
                contextlib.redirect_stderr(captured):
            result = bridge.main(["--mode", "inventory", "--sha", SHA, "compose", "--", "exec", "-T", "api", SECRET_SENTINEL])
        self.assertEqual(result, 1)
        self.assertNotIn(SECRET_SENTINEL, captured.getvalue())
        discover.assert_not_called()

    def test_private_read_detects_content_change_and_keeps_original_file_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "snapshot.json"
            content = b'{"synthetic":"' + SECRET_SENTINEL.encode() + b'"}'
            source.write_bytes(content)
            expected = hashlib.sha256(content).hexdigest()
            self.assertEqual(bridge._read_private_copy_source(source, expected), content)
            with self.assertRaisesRegex(bridge.BridgeError, "snapshot_changed_during_operation"):
                bridge._read_private_copy_source(source, "0" * 64)
            self.assertEqual(source.read_bytes(), content)

    def test_each_service_retains_its_own_sources_and_working_directory(self):
        context = {"env_path": Path("/private/app.env"),
                   "sources": {"api": {"workdir": Path("/opt/markina-gallery/docker")},
                               "web": {"workdir": Path("/var/lib/markina-gallery/deploy-state/web")}},
                   "compose_paths_by_service": {"api": [Path("/private/api.json")],
                                                "web": [Path("/private/web-1.json"), Path("/private/web-2.json")]}}
        api = bridge._compose_prefix(context, "api")
        web = bridge._compose_prefix(context, "web")
        self.assertIn(str(Path("/private/api.json")), api)
        self.assertNotIn(str(Path("/private/api.json")), web)
        self.assertNotIn(str(Path("/private/web-1.json")), api)
        self.assertEqual(web[web.index("--project-directory") + 1], str(Path("/var/lib/markina-gallery/deploy-state/web")))

    def test_source_archive_rejects_traversal_symlink_and_unapproved_paths(self):
        for name, link in (("../outside.py", False), ("backend/requirements.txt", False), ("backend/app/evil", True)):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w") as archive:
                member = tarfile.TarInfo(name)
                if link:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/etc/passwd"
                archive.addfile(member)
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(bridge.BridgeError):
                bridge.extract_app_archive(data.getvalue(), Path(directory))

    def test_source_archive_extracts_only_tracked_application_bytes(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as archive:
            content = b"synthetic = True\n"
            member = tarfile.TarInfo("backend/app/example.py")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            bridge.extract_app_archive(data.getvalue(), destination)
            self.assertEqual((destination / "backend/app/example.py").read_bytes(), content)

    def test_snapshot_refuses_wrong_approval_before_writes(self):
        context = {"digests": {}, "paths": [], "sources": {s: {"paths": [], "workdir": Path("/fixed")} for s in bridge.SERVICES},
                   "environment_digest": "0" * 64}
        with patch.object(bridge, "_ensure_root_bridge_directory") as create, self.assertRaises(bridge.BridgeError):
            bridge._snapshot_sources(context, "release", SHA, FINGERPRINT, "f" * 64)
        create.assert_not_called()

    def test_snapshot_copies_source_bytes_and_rejects_tampered_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "bridge-state"
            private.mkdir()
            source = root / "active.json"
            content = b'{"synthetic":"' + SECRET_SENTINEL.encode() + b'"}'
            source.write_bytes(content)
            original_metadata = (source.stat().st_mtime_ns, source.read_bytes())
            context = {"paths": [source], "digests": {str(source): hashlib.sha256(content).hexdigest()},
                       "sources": {s: {"paths": [source], "workdir": root} for s in bridge.SERVICES},
                       "environment_digest": "a" * 64, "models": {},
                       "containers": {s: container(s) for s in bridge.SERVICES}}
            def root_metadata(path, **_kwargs):
                metadata = path.stat()
                return SimpleNamespace(st_mode=(stat.S_IFDIR | 0o700) if path.is_dir() else (stat.S_IFREG | 0o600),
                                       st_size=metadata.st_size, st_uid=0, st_gid=0, st_nlink=1)
            approved_source = bridge._sources_fingerprint(context)
            with patch.object(bridge, "BRIDGE_STATE", private), \
                    patch.object(bridge, "_root_metadata", side_effect=root_metadata), \
                    patch.object(bridge, "_assert_common_lock_held"), \
                    patch.object(bridge, "_ensure_root_bridge_directory"), \
                    patch.object(bridge, "_state_value", return_value=SHA):
                bridge._snapshot_sources(context, "release", SHA, FINGERPRINT, approved_source)
                operation = bridge._operation_directory("release", SHA, FINGERPRINT)
                manifest = json.loads((operation / "manifest.json").read_text())
                saved = operation / manifest["files"][0]["saved_name"]
                self.assertEqual(saved.read_bytes(), content)
                self.assertEqual((source.stat().st_mtime_ns, source.read_bytes()), original_metadata)
                bridge._snapshot_sources(context, "release", SHA, FINGERPRINT, approved_source)
                saved.write_bytes(b"tampered")
                with self.assertRaisesRegex(bridge.BridgeError, "snapshot_copy_hash_mismatch"):
                    bridge._snapshot_sources(context, "release", SHA, FINGERPRINT, approved_source)

    def test_installer_rejects_bad_arguments_before_any_privileged_call(self):
        bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
        self.assertTrue(bash)
        installer = Path(__file__).with_name("install-prod-app-compose-bridge.sh")
        env = dict(os.environ, MARKINA_EXPECTED_REPOSITORY="conradodeita/markina-gallery")
        for arguments in (("--support-sha", "bad", "--bridge-blob", SHA), ("--command", "sh")):
            result = subprocess.run([bash, str(installer), *arguments], env=env, capture_output=True, text=True, timeout=15, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertRegex(result.stderr, "app-bridge-install: (arguments_invalid|identity_invalid)")

    def test_installer_accepts_only_exact_canonical_git_origins(self):
        bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
        self.assertTrue(bash)
        installer = Path(__file__).with_name("install-prod-app-compose-bridge.sh").read_text(encoding="utf-8")
        match = re.search(r"(?ms)^origin_is_canonical\(\) \{\n.*?^\}", installer)
        self.assertIsNotNone(match)
        program = (
            'REPOSITORY="conradodeita/markina-gallery"\n'
            + match.group(0)
            + '\norigin_is_canonical "$1"\n'
        )
        accepted = (
            "https://github.com/conradodeita/markina-gallery.git",
            "ssh://github.com/conradodeita/markina-gallery.git",
            "git@github.com:conradodeita/markina-gallery.git",
        )
        rejected = (
            "ssh://git@github.com/conradodeita/markina-gallery.git",
            "ssh://github.com.evil/conradodeita/markina-gallery.git",
            "https://github.com/conradodeita/another-repository.git",
            "https://user@github.com/conradodeita/markina-gallery.git",
            "http://github.com/conradodeita/markina-gallery.git",
            "git@github.com.evil:conradodeita/markina-gallery.git",
            "developer@github.com:conradodeita/markina-gallery.git",
            "git@github.com:conradodeita/another-repository.git",
            "git@github.com:conradodeita/markina-gallery.git/extra",
        )
        for origin in accepted:
            with self.subTest(origin=origin):
                result = subprocess.run([bash, "-c", program, "origin-test", origin], capture_output=True, text=True, timeout=15, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
        for origin in rejected:
            with self.subTest(origin=origin):
                result = subprocess.run([bash, "-c", program, "origin-test", origin], capture_output=True, text=True, timeout=15, check=False)
                self.assertEqual(result.returncode, 1, result.stderr)

    def test_app_executor_pins_exact_root_helper_bytes(self):
        source = Path(__file__).with_name("production_app_compose_bridge.py").read_bytes().replace(b"\r\n", b"\n")
        expected = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
        app = Path(__file__).with_name("deploy-prod-app-services.sh").read_text(encoding="utf-8")
        self.assertIn(f'APP_COMPOSE_BRIDGE_BLOB="{expected}"', app)

    def test_discovers_distinct_snapshots_with_missing_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            state = Path(directory) / "state"
            private = Path(directory) / "bridge"
            working = root / "docker"
            for path in (working, state, private):
                path.mkdir(parents=True)
            api_path, web_path = state / "api.json", state / "web.json"
            api_path.write_text("{}")
            web_path.write_text("{}")
            selected = {s: container(s) for s in bridge.SERVICES}
            for service, source, workdir in (("api", api_path, working), ("web", web_path, state)):
                labels = selected[service]["Config"]["Labels"]
                labels.pop("com.docker.compose.config-hash")
                labels["com.docker.compose.project.config_files"] = str(source)
                labels["com.docker.compose.project.working_dir"] = str(workdir)
            with patch.multiple(bridge, PROJECT_ROOT=root, STATE_DIR=state, WORKING_DIR=working, BRIDGE_STATE=private), \
                    patch.object(bridge, "_validate_env_file", return_value="a" * 64), \
                    patch.object(bridge, "_inspect_api_web", return_value=selected), \
                    patch.object(bridge, "_validate_snapshot_source", side_effect=bridge.snapshot_sha256):
                context = bridge._discover_context()
            self.assertEqual(context["sources"]["api"]["paths"], [api_path])
            self.assertEqual(context["sources"]["web"]["paths"], [web_path])
            self.assertEqual(context["config_hashes"], {"api": None, "web": None})

    def test_resolved_model_and_image_are_proven_before_a_semantic_identity_is_returned(self):
        documents, containers = {}, {}
        for service in bridge.SERVICES:
            model, document, item, image = semantic_fixture()
            document["services"] = {service: model}
            item["Config"]["Labels"]["com.docker.compose.service"] = service
            item["NetworkSettings"]["Networks"]["markina-gallery_internal"]["Aliases"] = [service]
            item["Config"]["Labels"].pop("com.docker.compose.config-hash")
            documents[service], containers[service] = document, item
        context = {"containers": containers, "config_hashes": {s: None for s in bridge.SERVICES}}
        with patch.object(bridge, "_resolved_config", side_effect=lambda c, v, s: documents[s]), \
                patch.object(bridge, "_docker", return_value=json.dumps([image])):
            bridge._prove_context(context)
        self.assertEqual(set(context["semantic_hashes"]), set(bridge.SERVICES))
        self.assertNotIn(SECRET_SENTINEL, json.dumps(context["semantic_hashes"]))
        containers["api"]["Config"]["Env"].append("EXTRA=unexpected")
        with patch.object(bridge, "_resolved_config", side_effect=lambda c, v, s: documents[s]), \
                patch.object(bridge, "_docker", return_value=json.dumps([image])), self.assertRaises(bridge.BridgeError):
            bridge._prove_context(context)

    def test_apply_uses_only_proven_api_web_models_and_never_creates_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            models, containers = {}, {}
            for service in bridge.SERVICES:
                model, document, item, _image = semantic_fixture()
                document["services"] = {service: model}
                item["Config"]["Labels"]["com.docker.compose.service"] = service
                item["NetworkSettings"]["Networks"]["markina-gallery_internal"]["Aliases"] = [service]
                models[service], containers[service] = document, item
            manifest = {"version": 1, "target_sha": SHA, "fingerprint": FINGERPRINT,
                        "models": models, "containers": containers, "files": []}
            operation = private / f"release-{SHA}-{FINGERPRINT[:16]}"
            operation.mkdir()
            (operation / "manifest.json").write_text(json.dumps(manifest))
            target_image = "sha256:" + "f" * 64
            def root_metadata(path, **_kwargs):
                metadata = path.stat()
                return SimpleNamespace(st_mode=(stat.S_IFDIR | 0o700) if path.is_dir() else (stat.S_IFREG | 0o600),
                                       st_size=metadata.st_size, st_uid=0, st_gid=0, st_nlink=1)
            def docker(args, **_kwargs):
                if "--format" in args:
                    return target_image
                image = semantic_fixture()[3]
                image["Id"] = args[-1] if args[-1].startswith("sha256:") else target_image
                return json.dumps([image])
            context = {"containers": containers}
            with patch.object(bridge, "BRIDGE_STATE", private), \
                    patch.object(bridge, "_root_metadata", side_effect=root_metadata), \
                    patch.object(bridge, "_assert_common_lock_held"), \
                    patch.object(bridge, "_assert_sources_unchanged"), \
                    patch.object(bridge, "_docker", side_effect=docker), \
                    patch.object(bridge, "_run", return_value="") as commands:
                bridge._apply_models(context, "release", SHA, "f" * 40, FINGERPRINT)
            calls = [call.args[0] for call in commands.call_args_list]
            self.assertEqual(len(calls), 2)
            self.assertEqual({args[-1] for args in calls}, {"api", "web"})
            for args in calls:
                self.assertIn("--no-deps", args)
                self.assertIn("--no-build", args)
                self.assertEqual(args[args.index("--pull") + 1], "never")
            for service in bridge.SERVICES:
                candidate = json.loads((operation / f"apply-{service}.compose.json").read_text())
                self.assertEqual(set(candidate["services"]), {service})
                self.assertEqual(candidate["services"][service]["image"], target_image)
            self.assertEqual(json.loads((operation / "manifest.json").read_text()), manifest)
            rollback_fingerprint = "9" * 64
            rollback_operation = private / f"rollback-{SHA}-{rollback_fingerprint[:16]}"
            rollback_operation.mkdir()
            current = copy.deepcopy(containers)
            for service in bridge.SERVICES:
                current[service]["Image"] = target_image
            rollback_manifest = copy.deepcopy(manifest)
            rollback_manifest.update(fingerprint=rollback_fingerprint, containers=current)
            (rollback_operation / "manifest.json").write_text(json.dumps(rollback_manifest))
            with patch.object(bridge, "BRIDGE_STATE", private), \
                    patch.object(bridge, "_root_metadata", side_effect=root_metadata), \
                    patch.object(bridge, "_assert_common_lock_held"), \
                    patch.object(bridge, "_assert_sources_unchanged"), \
                    patch.object(bridge, "_docker", side_effect=docker), \
                    patch.object(bridge, "_run", return_value="") as restored:
                bridge._apply_models({"containers": current}, "rollback", SHA, SHA, rollback_fingerprint)
            self.assertEqual(len(restored.call_args_list), 2)
            for service in bridge.SERVICES:
                candidate = json.loads((rollback_operation / f"apply-{service}.compose.json").read_text())
                self.assertEqual(candidate["services"][service]["image"], IMAGE_ID)
            self.assertEqual(json.loads((private / "previous-release.json").read_text())["mode"], "rollback")


if __name__ == "__main__":
    unittest.main()
