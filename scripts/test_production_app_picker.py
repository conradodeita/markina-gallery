"""Contracts for the approved fixed API-only Picker mount."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_app_compose_bridge as bridge
import test_production_app_handoff_engine as engine

SYNTHETIC_KEY = "synthetic-" + "x" * 24


class PickerModelContracts(unittest.TestCase):
    def test_only_fixed_mount_changes_and_input_is_preserved(self):
        original = {"services": {"api": {"image": "sha256:" + "a" * 64, "environment": {"APP_VERSION": "b" * 40}, "volumes": []}}}
        before = copy.deepcopy(original)
        candidate = bridge.picker_document(original)
        mount = candidate["services"]["api"]["volumes"].pop()
        self.assertEqual(candidate, before)
        self.assertEqual(original, before)
        self.assertEqual(mount, {"type": "bind", "source": "/etc/pyp-google-drive/picker-config.json",
            "target": "/run/secrets/google-drive-picker-config.json", "read_only": True, "bind": {"create_host_path": False, "propagation": "rprivate"}})

    def test_rejects_other_services_or_existing_source_or_target(self):
        for document in ({"services": {"web": {}}}, {"services": {"api": {}, "web": {}}},
                {"services": {"api": {"volumes": [{"target": bridge.PICKER_TARGET}]}}},
                {"services": {"api": {"volumes": [{"source": bridge.PICKER_CONFIG.as_posix()}]}}}):
            with self.subTest(document=document), self.assertRaises(bridge.BridgeError):
                bridge.picker_document(document)

    def test_fixed_operations_reject_arbitrary_parameters(self):
        for operation, mode in (("picker-inventory", "inventory"), ("picker-prepare", "release"), ("picker-apply", "release")):
            args = ["--mode", mode, "--sha", "a" * 40, "--approval-fingerprint", "b" * 64]
            self.assertEqual(bridge._parse_args(args + [operation]).operation, operation)
            for extra in (["--", "web"], ["--", "/tmp/evil.json"]):
                with self.assertRaises(bridge.BridgeError):
                    bridge._parse_args(args + [operation] + extra)


@unittest.skipUnless(os.name == "posix" and getattr(os, "geteuid", lambda: -1)() == 0, "root Linux required")
class PickerFileContracts(unittest.TestCase):
    def test_metadata_and_content_binding_without_secret_in_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); root.chmod(0o700)
            path = root / "picker-config.json"
            path.write_text(json.dumps({"developer_key": SYNTHETIC_KEY, "project_number": "123", "expected_parent_folder_id": "synthetic-root"}))
            path.chmod(0o400)
            with patch.object(bridge, "PICKER_CONFIG", path):
                first = bridge.picker_config_binding()
                self.assertEqual(set(first), {"sha256", "device", "inode", "size"})
                path.chmod(0o600)
                with self.assertRaises(bridge.BridgeError) as error:
                    bridge.picker_config_binding()
                self.assertNotIn(SYNTHETIC_KEY, str(error.exception))
                path.chmod(0o400)
                os.link(path, root / "hardlink")
                with self.assertRaises(bridge.BridgeError):
                    bridge.picker_config_binding()


# Reuse the real Engine laboratory, but run only the Picker cases here.
@unittest.skipUnless(os.environ.get('APP_HANDOFF_ENGINE_IMAGE') and os.name == 'posix', 'explicit Linux Engine lab required')
class PickerEngineContracts(unittest.TestCase):
    setUp = engine.FullHandoffEngineContracts.setUp
    docker = engine.FullHandoffEngineContracts.docker
    inspect = engine.FullHandoffEngineContracts.inspect
    cleanup_engine = engine.FullHandoffEngineContracts.cleanup_engine
    prepare = engine.FullHandoffEngineContracts.prepare
    relevant_items = engine.FullHandoffEngineContracts.relevant_items
    recovery_inventory = engine.FullHandoffEngineContracts.recovery_inventory
    def recover_and_assert(self, identity):
        inventory = self.recovery_inventory(identity)
        recovery, revision = bridge.handoff_recovery_prepare(inventory, bridge.digest(inventory))
        revision = bridge.handoff_recover_service(recovery, revision, 'api')
        bridge.handoff_recover_service(recovery, revision, 'web')
        receipt = bridge.handoff_publish_runtime(recovery, restoring=True)
        self.assertEqual(receipt['api_version'], '1' * 40)
        self.assertEqual(receipt['web_version'], '1' * 40)
        for service in bridge.SERVICES:
            item = self.inspect(self.originals[service]['Id'])
            self.assertTrue(item['State']['Running'])
            self.assertEqual(item['Config'], self.originals[service]['Config'])
        self.assertEqual(self.inspect(self.originals['web']['Id'])['State']['StartedAt'], self.originals['web']['State']['StartedAt'])
        self.assertEqual(self.inspect(self.neighbor)['State']['StartedAt'], self.neighbor_before['State']['StartedAt'])
        self.assertFalse(self.inspect(self.witness)['State']['Running'])


    def picker_prepare(self):
        plan, _, _ = self.prepare(target='1' * 40)
        path = bridge.STATE_DIR / 'picker-config.json'
        path.write_text(json.dumps({"developer_key": SYNTHETIC_KEY, "project_number": "123", "expected_parent_folder_id": "synthetic-root"}))
        path.chmod(0o400)
        self.enterContext(patch.object(bridge, 'PICKER_CONFIG', path))
        # The file is mounted into a synthetic Python image, not the application image.
        # Keep schema and all real Engine proofs; replace only the app-specific config import.
        real_docker = bridge._docker
        def docker(args, **kwargs):
            if args[0] == 'exec' and args[-1].startswith('from app.google_drive_picker import'):
                return real_docker(args[:-1] + ["import json,os,stat; p='/run/secrets/google-drive-picker-config.json'; s=os.stat(p); assert stat.S_IMODE(s.st_mode)==0o400; assert json.load(open(p))['project_number']=='123'; print('picker_config=valid')"], **kwargs)
            return real_docker(args, **kwargs)
        self.enterContext(patch.object(bridge, '_docker', side_effect=docker))
        plan['picker_binding'] = bridge.picker_config_binding()
        plan['web_started_at'] = self.originals['web']['State']['StartedAt']
        plan['original_web_version'] = '1' * 40
        plan['models']['api'] = bridge.picker_document(plan['models']['api'])
        plan['models']['web'] = copy.deepcopy(plan['original_models']['web'])
        for service in bridge.SERVICES:
            plan['services'][service]['candidate_model'] = bridge.digest(plan['models'][service])
        identity, revision = bridge.handoff_journal_create(plan)
        return plan, identity, revision

    def test_picker_changes_only_api_and_recovers_original(self):
        plan, identity, revision = self.picker_prepare()
        web = self.inspect(self.originals['web']['Id'])
        bridge.handoff_execute_service(identity, revision, 'api')
        candidate = self.inspect(self.project + '-api-1'); self.container_ids.add(candidate['Id'])
        self.assertEqual(candidate['Image'], self.originals['api']['Image'])
        self.assertEqual(sorted(candidate['Config']['Env']), sorted(self.originals['api']['Config']['Env']))
        mount = next(m for m in candidate['Mounts'] if m['Destination'] == bridge.PICKER_TARGET)
        self.assertFalse(mount['RW'])
        receipt = bridge.handoff_publish_runtime(identity)
        self.assertEqual(receipt['api_version'], '1' * 40)
        self.assertEqual(receipt['web_version'], '1' * 40)
        self.assertEqual(self.inspect(web['Id'])['State']['StartedAt'], web['State']['StartedAt'])
        self.recover_and_assert(identity)
        self.assertEqual(self.inspect(web['Id'])['State']['StartedAt'], web['State']['StartedAt'])

    def test_picker_changed_config_aborts_before_stop(self):
        _, identity, revision = self.picker_prepare()
        bridge.PICKER_CONFIG.chmod(0o600)
        with self.assertRaises(bridge.BridgeError):
            bridge.handoff_execute_service(identity, revision, 'api')
        self.assertTrue(self.inspect(self.originals['api']['Id'])['State']['Running'])

    def test_picker_interrupted_stop_recovers_without_touching_web(self):
        _, identity, revision = self.picker_prepare()
        real = bridge._docker
        def docker(args, **kwargs):
            result = real(args, **kwargs)
            if args[0] == 'stop':
                raise bridge.BridgeError('synthetic_interruption')
            return result
        with patch.object(bridge, '_docker', side_effect=docker), self.assertRaises(bridge.BridgeError):
            bridge.handoff_execute_service(identity, revision, 'api')
        self.recover_and_assert(identity)

    def picker_interruption(self, operation):
        _, identity, revision = self.picker_prepare()
        real_docker, real_run = bridge._docker, bridge._run
        def docker(args, **kwargs):
            result = real_docker(args, **kwargs)
            if args[0] == operation:
                raise bridge.BridgeError('synthetic_interruption')
            return result
        def run(args, **kwargs):
            result = real_run(args, **kwargs)
            if operation == 'create' and 'compose' in args and 'up' in args:
                raise bridge.BridgeError('synthetic_interruption')
            return result
        with patch.object(bridge, '_docker', side_effect=docker), patch.object(bridge, '_run', side_effect=run), self.assertRaises(bridge.BridgeError):
            bridge.handoff_execute_service(identity, revision, 'api')
        self.recover_and_assert(identity)

    def test_picker_interrupted_rename_recovers(self):
        self.picker_interruption('rename')

    def test_picker_interrupted_creation_recovers(self):
        self.picker_interruption('create')
