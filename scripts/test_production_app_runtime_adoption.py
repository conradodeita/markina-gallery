"""Synthetic runtime adoption contracts; no production configuration fixtures."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import production_app_compose_bridge as bridge
from test_production_app_compose_bridge import IMAGE_ID, SHA, semantic_fixture


class AdoptionTranslationTests(unittest.TestCase):
    def fixture(self):
        _, _, item, image = semantic_fixture()
        item["Config"]["User"] = "10001:10001"
        item["Config"]["Env"].extend([
            'ADMIN_TOTP_KEYS={"synthetic":"never-a-real-key"}',
            "ADMIN_TOTP_ACTIVE_KEY_ID=synthetic", "ADMIN_TOTP_SECRET_ENV=production",
            "ADMIN_TOTP_LEGACY_DUAL_WRITE=false",
        ])
        item["Config"]["Labels"]["io.pickyourpic.release"] = SHA
        item["HostConfig"].update(Tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"}, CgroupnsMode="host")
        item["Mounts"].append({"Type": "bind", "Source": "/synthetic/photos", "Destination": "/photos",
                               "RW": False, "Propagation": "rprivate"})
        return item, image

    def test_protected_workflow_binds_code_fingerprint_and_destination(self):
        workflow = Path(os.environ.get("APP_ADOPTION_WORKFLOW", Path(__file__).parents[1] /
                                      ".github/workflows/production-app-runtime-adoption.yml"))
        text = workflow.read_text(encoding="utf-8")
        for contract in (
            "--app-runtime-adoption", "environment: production-preflight", "environment: production",
            "MARKINA_APP_ADOPTION_TARGET_SHA=$GITHUB_SHA", "approval_fingerprint",
            '"$REQUESTED_FINGERPRINT" == "$INVENTORY_FINGERPRINT"',
            'deploy_binding" == "$PREFLIGHT_CONNECTION_BINDING"',
            "--mode adopt --sha '$GITHUB_SHA' --approval-fingerprint '$APPROVAL_FINGERPRINT'",
            "inputs.operation == 'adopt'",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)
        self.assertNotIn("PRODUCTION_APP_ARTIFACT_SSH_PRIVATE_KEY", text)

    def test_preserves_active_configuration_without_historical_defaults(self):
        item, image = self.fixture()
        original = copy.deepcopy(item)
        document = bridge.adoption_document("api", item, image)
        model = document["services"]["api"]
        self.assertEqual(model["image"], IMAGE_ID)
        self.assertEqual(model["user"], "10001:10001")
        self.assertEqual(model["environment"]["ADMIN_TOTP_KEYS"], '{"synthetic":"never-a-real-key"}')
        self.assertEqual(model["environment"]["APP_VERSION"], SHA)
        self.assertEqual(model["command"], ["server"])
        self.assertEqual(model["entrypoint"], [])
        self.assertEqual(model["cgroup"], "host")
        self.assertEqual(model["tmpfs"], ["/tmp:rw,noexec,nosuid,size=64m"])
        self.assertIn({"type": "bind", "source": "/synthetic/photos", "target": "/photos",
                       "read_only": True, "bind": {"propagation": "rprivate", "create_host_path": False}}, model["volumes"])
        self.assertTrue(all(v["external"] for v in document["volumes"].values()))
        self.assertTrue(all(v["external"] for v in document["networks"].values()))
        self.assertEqual(item, original)
        bridge.prove_service_model("api", model, document, item, image)

    def test_rejects_unsupported_runtime_features_without_secret_in_error(self):
        for mutation in (
            lambda c: c["HostConfig"].update(Devices=[{"PathOnHost": "/secret-device"}]),
            lambda c: c["HostConfig"].update(Tmpfs={"/tmp": "unknown=secret"}),
            lambda c: c["HostConfig"].update(CgroupnsMode="unknown"),
            lambda c: c["HostConfig"].update(PortBindings={"8000/tcp": [{"HostPort": "9000"}]}),
            lambda c: c["HostConfig"].update(UnknownSafetyOption="secret"),
        ):
            item, image = self.fixture()
            mutation(item)
            with self.subTest(mutation=mutation), self.assertRaises(bridge.BridgeError) as raised:
                bridge.adoption_document("api", item, image)
            self.assertNotIn("secret", str(raised.exception))

    def test_proof_rejects_lost_credentials_mounts_or_policy(self):
        item, image = self.fixture()
        document = bridge.adoption_document("api", item, image)
        for field in ("environment", "volumes", "tmpfs", "cgroup"):
            changed = copy.deepcopy(document)
            changed["services"]["api"].pop(field)
            with self.subTest(field=field), self.assertRaises(bridge.BridgeError):
                bridge.prove_service_model("api", changed["services"]["api"], changed, item, image)

    def test_tmpfs_size_normalization_preserves_flags_and_rejects_ambiguity(self):
        self.assertEqual(bridge.tmpfs_options("rw,noexec,size=64m"), bridge.tmpfs_options("size=67108864,noexec,rw"))
        for value in ("rw,ro", "size=1m,size=2m", "mode=888", "unknown=sentinel", "size=-1"):
            with self.subTest(value=value), self.assertRaises(bridge.BridgeError):
                bridge.tmpfs_options(value)

    def test_invalid_adoption_modes_cannot_reach_mutating_dispatch(self):
        for argv in (["--mode", "inventory", "--sha", SHA, "adopt"],
                     ["--mode", "adopt", "--sha", SHA, "hashes"],
                     ["--mode", "adopt", "--sha", SHA, "adopt"],
                     ["--mode", "inventory", "--sha", SHA, "adoption-inventory", "/arbitrary"]):
            with self.subTest(argv=argv), self.assertRaises(bridge.BridgeError):
                bridge._parse_args(argv)

    def test_web_preserves_runtime_node_version_and_explicit_empty_entrypoint(self):
        _, _, item, image = semantic_fixture()
        item["Config"]["Labels"]["com.docker.compose.service"] = "web"
        item["Config"]["Env"].append("NODE_VERSION=22.synthetic")
        item["Config"].update(Cmd=["node", "server.js"], Entrypoint=[], User="10001")
        item["Mounts"] = []
        item["HostConfig"]["CgroupnsMode"] = "host"
        item["NetworkSettings"]["Networks"]["markina-gallery_internal"]["Aliases"] = ["web"]
        image["Config"]["Env"].append("NODE_VERSION=20.historical")
        model = bridge.adoption_document("web", item, image)["services"]["web"]
        self.assertEqual(model["environment"]["NODE_VERSION"], "22.synthetic")
        self.assertEqual(model["command"], ["node", "server.js"])
        self.assertEqual(model["entrypoint"], [])
        self.assertEqual(model["volumes"], [])


@unittest.skipUnless(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0,
                     "root Linux private filesystem contract")
class PrivateBaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pyp-adoption-contract-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        checkout, state, base = root / "checkout", root / "state", root / "bridge"
        for path in (checkout, state, base):
            path.mkdir(mode=0o700)
        env = checkout / ".env"
        env.write_text("SYNTHETIC_ONLY=yes\n")
        env.chmod(0o600)
        source = state / "old.json"
        source.write_text('{"historical":"preserved"}')
        source.chmod(0o600)
        for name, value in (("PROJECT_ROOT", checkout), ("STATE_DIR", state), ("MARKINA_STATE_ROOT", root),
                            ("BRIDGE_STATE", base), ("ENV_FILE", env)):
            self.enterContext(patch.object(bridge, name, value))
        self.containers, self.models = {}, {}
        for service, char in (("api", "c"), ("web", "e")):
            _, _, item, image = semantic_fixture()
            item["Id"] = char * 64
            item["Config"]["Hostname"] = item["Id"][:12]
            item["Config"]["Labels"]["com.docker.compose.service"] = service
            item["NetworkSettings"]["Networks"]["markina-gallery_internal"]["Aliases"] = [service]
            self.containers[service] = item
            self.models[service] = bridge.adoption_document(service, item, image)
        self.context = {"containers": self.containers, "paths": [source], "digests": {str(source): bridge.snapshot_sha256(source)},
                        "environment_digest": bridge.snapshot_sha256(env),
                        "sources": {s: {"paths": [source], "workdir": checkout, "config_hash": None} for s in bridge.SERVICES},
                        "config_hashes": {s: None for s in bridge.SERVICES}}
        self.enterContext(patch.object(bridge, "_inspect_api_web", side_effect=lambda: copy.deepcopy(self.containers)))
        self.enterContext(patch.object(bridge, "_assert_common_lock_held"))
        self.proof = {"domain": "app-runtime-adoption-v1", "target_sha": SHA, "test": "synthetic"}
        self.approval = bridge.digest(self.proof)

    def publish(self):
        bridge._publish_runtime_base(self.context, self.models, self.proof, self.approval)

    def test_private_base_can_be_selected_without_altering_sources(self):
        source = self.context["paths"][0]
        before = source.read_bytes()
        self.publish()
        selected = bridge._select_adopted_sources(copy.deepcopy(self.context))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual((bridge.BRIDGE_STATE.stat().st_mode & 0o777), 0o700)
        for service in bridge.SERVICES:
            path = selected["sources"][service]["paths"][0]
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_uid, 0)
            self.assertNotEqual(path, source)
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_base_already_exists"):
            self.publish()

    def test_wrong_approval_and_changed_runtime_do_not_activate_a_base(self):
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_approval_mismatch"):
            bridge._publish_runtime_base(self.context, self.models, self.proof, "f" * 64)
        changed = copy.deepcopy(self.containers)
        changed["api"]["Config"]["Env"].append("NEW=synthetic")
        with patch.object(bridge, "_inspect_api_web", return_value=changed), self.assertRaisesRegex(bridge.BridgeError, "adoption_runtime_changed"):
            self.publish()
        self.assertFalse((bridge.BRIDGE_STATE / "active-base.json").exists())

    def test_tampered_model_and_stale_container_fail_without_fallback(self):
        self.publish()
        changed = copy.deepcopy(self.context)
        changed["containers"]["web"]["Id"] = "f" * 64
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_registry_runtime_mismatch"):
            bridge._select_adopted_sources(changed)
        selected = bridge._select_adopted_sources(copy.deepcopy(self.context))
        selected["sources"]["api"]["paths"][0].write_text("tampered")
        with self.assertRaises(bridge.BridgeError):
            bridge._select_adopted_sources(copy.deepcopy(self.context))

    def test_failed_private_write_never_activates_incomplete_state(self):
        original = bridge._write_private_file
        def fail_manifest(path, content):
            if path.name == "manifest.json":
                raise bridge.BridgeError("synthetic_write_failure")
            return original(path, content)
        with patch.object(bridge, "_write_private_file", side_effect=fail_manifest), self.assertRaises(bridge.BridgeError):
            self.publish()
        self.assertFalse((bridge.BRIDGE_STATE / "active-base.json").exists())

    def test_registry_rejects_symlink_mode_and_arbitrary_directory(self):
        self.publish()
        pointer = bridge.BRIDGE_STATE / "active-base.json"
        original = pointer.read_bytes()
        pointer.chmod(0o644)
        with self.assertRaises(bridge.BridgeError):
            bridge._read_base_pointer()
        pointer.chmod(0o600)
        pointer.write_text(json.dumps({"base": "../../outside", "manifest_sha256": "a" * 64}))
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_registry_invalid"):
            bridge._read_base_pointer()
        pointer.write_bytes(original)
        saved = bridge.BRIDGE_STATE / "saved-pointer"
        pointer.rename(saved)
        pointer.symlink_to(saved)
        with self.assertRaises(bridge.BridgeError):
            bridge._read_base_pointer()

    def test_probe_requires_independent_resolution_and_schema_without_persistence(self):
        documents = {}
        for service in bridge.SERVICES:
            _, document, _, image = semantic_fixture()
            document["services"][service] = document["services"].pop("api")
            self.containers[service]["Config"]["Labels"]["io.pickyourpic.release"] = SHA
            document["services"][service]["labels"] = {"io.pickyourpic.release": SHA}
            documents[service] = document
        temporary = Path(self.temp.name) / "probe"
        temporary.mkdir(mode=0o700)
        context = bridge._prepare_compose_context(self.context, "inventory", SHA, "", temporary)
        with patch.object(bridge, "_git", return_value=SHA), \
                patch.object(bridge, "_docker", return_value=json.dumps([image])), \
                patch.object(bridge, "_resolved_config", side_effect=lambda c, v, s: documents[s]) as resolver, \
                patch.object(bridge, "_execute_compose", return_value="20261113_0126\n"):
            models, proof = bridge._prepare_adoption(context, SHA)
        self.assertEqual(resolver.call_count, 2)
        self.assertEqual(set(models), {"api", "web"})
        self.assertEqual(proof["domain"], "app-runtime-adoption-v1")
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(proof))
        self.assertFalse((bridge.BRIDGE_STATE / "active-base.json").exists())

    def interrupted_transition(self):
        self.publish()
        context = bridge._select_adopted_sources(copy.deepcopy(self.context))
        target = "b" * 40
        directory = bridge._operation_directory("release", target, self.approval)
        directory.mkdir(mode=0o700)
        manifest = {"version": 1, "models": self.models, "containers": self.containers, "files": [],
                    "target_sha": target, "fingerprint": self.approval}
        bridge._write_private_file(directory / "manifest.json", json.dumps(manifest).encode())
        candidates = copy.deepcopy(self.models)
        candidates["api"]["services"]["api"]["image"] = "sha256:" + "f" * 64
        candidates["api"]["services"]["api"]["environment"]["APP_VERSION"] = target
        for service in bridge.SERVICES:
            bridge._write_private_file(directory / f"apply-{service}.compose.json",
                                       json.dumps(bridge._escape_compose(candidates[service]), sort_keys=True).encode())
        bridge._record_transition(context, "release", target, self.approval, candidates)
        marker = bridge.STATE_DIR / "app-in-flight.sha"
        bridge._write_private_file(marker, target.encode())
        current = copy.deepcopy(self.context)
        api = current["containers"]["api"]
        api["Id"] = "f" * 64
        api["Image"] = "sha256:" + "f" * 64
        api["Config"]["Hostname"] = "f" * 12
        api["Config"]["Env"] = ["APP_VERSION=" + target if v.startswith("APP_VERSION=") else v for v in api["Config"]["Env"]]
        api["State"]["Health"]["Status"] = "unhealthy"
        return target, current, directory

    def recovery_image(self, args, **kwargs):
        image = semantic_fixture()[3]
        image["Id"] = args[-1]
        return json.dumps([image])

    def test_only_explicit_recovery_can_select_proven_mixed_state(self):
        target, current, _ = self.interrupted_transition()
        before = (bridge.BRIDGE_STATE / "active-base.json").read_bytes()
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_registry_runtime_mismatch"):
            bridge._select_adopted_sources(copy.deepcopy(current))
        with self.assertRaisesRegex(bridge.BridgeError, "recovery_mode_required"):
            bridge._select_recovery_sources(copy.deepcopy(current), "inventory", target)
        with patch.object(bridge, "_docker", side_effect=self.recovery_image):
            recovered = bridge._select_recovery_sources(copy.deepcopy(current), "rollback-inventory", target)
        self.assertEqual(recovered["recovery_transition"]["states"], {"api": "candidate", "web": "previous"})
        self.assertEqual((bridge.BRIDGE_STATE / "active-base.json").read_bytes(), before)
        self.assertIn("runtime", recovered["recovery_transition"])

    def test_recovery_rejects_unknown_image_and_tampered_transition(self):
        target, current, directory = self.interrupted_transition()
        changed = copy.deepcopy(current)
        changed["containers"]["api"]["Image"] = "sha256:" + "9" * 64
        with patch.object(bridge, "_docker", side_effect=self.recovery_image), self.assertRaisesRegex(bridge.BridgeError, "recovery_runtime_outside_transition"):
            bridge._select_recovery_sources(changed, "rollback-inventory", target)
        (directory / "apply-api.compose.json").write_text("tampered")
        with patch.object(bridge, "_docker", side_effect=self.recovery_image), self.assertRaises(bridge.BridgeError):
            bridge._select_recovery_sources(copy.deepcopy(current), "rollback-inventory", target)

    def apply_fixture(self, *, fail_web=False):
        self.publish()
        context = bridge._select_adopted_sources(copy.deepcopy(self.context))
        target = "b" * 40
        directory = bridge._operation_directory("release", target, self.approval)
        directory.mkdir(mode=0o700)
        manifest = {"version": 1, "models": self.models, "containers": self.containers, "files": [],
                    "target_sha": target, "fingerprint": self.approval}
        bridge._write_private_file(directory / "manifest.json", json.dumps(manifest).encode())
        bridge._write_private_file(bridge.STATE_DIR / "app-in-flight.sha", target.encode())
        target_images = {"api": "sha256:" + "f" * 64, "web": "sha256:" + "9" * 64}
        calls = []
        def docker(args, **kwargs):
            if "--format" in args:
                return target_images[args[-1].removeprefix(bridge.PROJECT + "-")] + "\n"
            return self.recovery_image(args)
        def execute(args, **kwargs):
            service = args[-1]
            calls.append(service)
            self.assertIn("--no-build", args)
            self.assertIn("--no-deps", args)
            self.assertEqual(args[args.index("--pull") + 1], "never")
            if service == "web" and fail_web:
                raise bridge.BridgeError("synthetic_recreation_failure")
            self.containers[service]["Id"] = ("1" if service == "api" else "2") * 64
            self.containers[service]["Image"] = target_images[service]
            self.containers[service]["Config"]["Hostname"] = self.containers[service]["Id"][:12]
            if service == "api":
                self.containers[service]["Config"]["Env"] = ["APP_VERSION=" + target if e.startswith("APP_VERSION=") else e
                                                            for e in self.containers[service]["Config"]["Env"]]
            return ""
        def discover():
            found = copy.deepcopy(self.context)
            found["containers"] = copy.deepcopy(self.containers)
            found["paths"] = [directory / f"apply-{s}.compose.json" for s in bridge.SERVICES]
            found["digests"] = {str(p): bridge.snapshot_sha256(p) for p in found["paths"]}
            found["sources"] = {s: {"paths": [directory / f"apply-{s}.compose.json"], "workdir": bridge.PROJECT_ROOT,
                                     "config_hash": None} for s in bridge.SERVICES}
            found.pop("base_pointer_digest", None)
            return found
        before = (bridge.BRIDGE_STATE / "active-base.json").read_bytes()
        with patch.object(bridge, "_docker", side_effect=docker), patch.object(bridge, "_run", side_effect=execute), \
                patch.object(bridge, "_discover_context", side_effect=discover):
            if fail_web:
                with self.assertRaisesRegex(bridge.BridgeError, "synthetic_recreation_failure"):
                    bridge._apply_models(context, "release", target, target, self.approval)
            else:
                bridge._apply_models(context, "release", target, target, self.approval)
        self.assertEqual(calls, ["api", "web"])
        return before, discover(), target

    def test_successful_recreation_rebinds_the_private_base(self):
        before, current, _ = self.apply_fixture()
        self.assertNotEqual((bridge.BRIDGE_STATE / "active-base.json").read_bytes(), before)
        selected = bridge._select_adopted_sources(current)
        self.assertEqual(set(selected["sources"]), {"api", "web"})

    def test_partial_recreation_keeps_previous_base_and_requires_recovery(self):
        before, current, target = self.apply_fixture(fail_web=True)
        self.assertEqual((bridge.BRIDGE_STATE / "active-base.json").read_bytes(), before)
        with self.assertRaisesRegex(bridge.BridgeError, "adoption_registry_runtime_mismatch"):
            bridge._select_adopted_sources(copy.deepcopy(current))
        with patch.object(bridge, "_docker", side_effect=self.recovery_image):
            recovered = bridge._select_recovery_sources(current, "rollback-inventory", target)
        self.assertEqual(recovered["recovery_transition"]["states"], {"api": "candidate", "web": "previous"})


@unittest.skipUnless(os.environ.get("APP_ADOPTION_TEST_IMAGE"), "explicit local Docker lab image required")
class ComposeCompatibilityTests(unittest.TestCase):
    def test_resolved_model_preserves_engine_configuration(self):
        project = "pyp-adoption-test-" + uuid.uuid4().hex[:12]
        def docker(*args):
            return subprocess.check_output(["docker", *args], text=True, stderr=subprocess.PIPE)
        image = os.environ["APP_ADOPTION_TEST_IMAGE"]
        inspected_image = json.loads(docker("image", "inspect", image))[0]
        self.assertFalse(inspected_image["Config"].get("Volumes"), "lab image must not create anonymous volumes")
        identity = None
        try:
            identity = docker("create", "--name", project, "--network", "bridge", "--cgroupns", "host",
                              "--tmpfs", "/scratch:rw,noexec,nosuid,nodev,size=64m", "--user", "10001:10001",
                              "--label", "com.docker.compose.project=" + project,
                              "--label", "com.docker.compose.service=api", "--env", "APP_VERSION=" + SHA,
                              "--env", "ADMIN_TOTP_KEYS=synthetic-$literal", "--env", "LITERAL2=$${missing}",
                              "--label", "synthetic.literal=$${missing}",
                              "--entrypoint", "/bin/true", image, "arg-${missing}", "arg-$$literal").strip()
            item = json.loads(docker("inspect", identity))[0]
            with patch.object(bridge, "PROJECT", project):
                document = bridge.adoption_document("api", item, inspected_image)
            with tempfile.TemporaryDirectory(prefix=project) as directory:
                source = Path(directory) / "compose.json"
                source.write_text(json.dumps(bridge._escape_compose(document)), encoding="utf-8")
                binary = os.environ.get("APP_ADOPTION_COMPOSE_BINARY")
                if binary:
                    output = docker("run", "--rm", "--network", "none",
                                    "--mount", f"type=bind,source={Path(binary).resolve()},target=/compose,readonly",
                                    "--mount", f"type=bind,source={source},target=/case.json,readonly",
                                    "--entrypoint", "/compose", image, "-p", project, "-f", "/case.json",
                                    "config", "--format", "json")
                else:
                    output = docker("compose", "-p", project, "-f", str(source), "config", "--format", "json")
                resolved = json.loads(output)
                resolved = bridge._decode_compose_literals(resolved)
                self.assertEqual(resolved["services"]["api"]["environment"]["ADMIN_TOTP_KEYS"], "synthetic-$literal")
                self.assertEqual(resolved["services"]["api"].get("working_dir", inspected_image["Config"].get("WorkingDir")) or "", item["Config"].get("WorkingDir") or "")
                bridge.prove_service_model("api", resolved["services"]["api"], resolved, item, inspected_image)
            after = json.loads(docker("inspect", identity))[0]
            self.assertEqual(after["Config"], item["Config"])
            self.assertEqual(after["HostConfig"], item["HostConfig"])
            self.assertFalse(after["State"]["Running"])
        finally:
            if identity:
                # Only the exact stopped lab container created above; no prune.
                docker("rm", identity)


if __name__ == "__main__":
    unittest.main()
