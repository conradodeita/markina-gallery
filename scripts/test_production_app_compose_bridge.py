"""Synthetic contracts for the root-only API/web Compose bridge."""

import contextlib
import copy
import hashlib
import io
import json
import os
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
