"""Importação mantém config/layers; nomes locais não substituem identidade."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facial_runtime_image_import import (
    LAYER_TYPE,
    MANIFEST_TYPE,
    ImageBinding,
    ImageImportError,
    digest,
    normalize_archive,
)


def encoded(data):
    return json.dumps(data, separators=(",", ":")).encode()


class ImageImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.tar"
        self.destination = self.root / "normalized.tar"
        self.layer = b"synthetic layer bytes"
        layer_id = digest(self.layer)
        self.files = {"blobs/" + layer_id.replace(":", "/"): self.layer,
                      "oci-layout": encoded({"imageLayoutVersion": "1.0.0"})}
        self.bindings, descriptors, legacy = [], [], []
        for command in ["index", "search"]:
            config = encoded({"architecture": "arm64", "os": "linux", "created": "2026-11-02T00:00:00Z",
                              "config": {"Cmd": [command], "Env": ["SENTINEL=synthetic-not-a-real-secret"]},
                              "rootfs": {"type": "layers", "diff_ids": [layer_id]}})
            config_id = digest(config)
            manifest = encoded({"schemaVersion": 2, "mediaType": MANIFEST_TYPE,
                                "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                                           "digest": config_id, "size": len(config)},
                                "layers": [{"mediaType": LAYER_TYPE, "digest": layer_id, "size": len(self.layer)}]})
            manifest_id = digest(manifest)
            self.files["blobs/" + config_id.replace(":", "/")] = config
            self.files["blobs/" + manifest_id.replace(":", "/")] = manifest
            self.bindings.append(ImageBinding(config_id, manifest, config))
            descriptors.append({"mediaType": MANIFEST_TYPE, "digest": manifest_id, "size": len(manifest)})
            legacy.append({"Config": "blobs/" + config_id.replace(":", "/"), "RepoTags": None,
                           "Layers": ["blobs/" + layer_id.replace(":", "/")]})
        self.files["index.json"] = encoded({"schemaVersion": 2, "manifests": descriptors})
        self.files["manifest.json"] = encoded(legacy)
        self.expected = {x.source_image for x in self.bindings}
        self.write_source()

    def write_source(self):
        with tarfile.open(self.source, "w") as archive:
            for name, payload in self.files.items():
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

    def inspect(self, binding):
        config = json.loads(binding.config_blob)
        return {"Id": binding.local_image, "Descriptor": {"digest": binding.local_image},
                "Os": "linux", "Architecture": "arm64", "Created": config["created"],
                "Config": config["config"],
                "RootFS": {"Type": "layers", "Layers": config["rootfs"]["diff_ids"]}}

    def rejected(self):
        with self.assertRaises(ImageImportError):
            normalize_archive(self.source, self.destination, self.expected)
        self.assertFalse(self.destination.exists())

    def test_unique_names_preserve_all_configs_and_blob_bytes(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        result = normalize_archive(self.source, self.destination, self.expected)
        self.assertEqual(set(result), self.expected)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)
        with tarfile.open(self.destination) as archive:
            index = json.load(archive.extractfile("index.json"))
            legacy = json.load(archive.extractfile("manifest.json"))
            names = {d["annotations"]["io.containerd.image.name"] for d in index["manifests"]}
            self.assertEqual(len(names), 2)
            self.assertTrue(all(x.startswith("docker.io/library/pyp-facial-restore-import:") for x in names))
            self.assertEqual({x["RepoTags"][0] for x in legacy}, {x.local_tag for x in self.bindings})
            for name, data in self.files.items():
                if name.startswith("blobs/"):
                    self.assertEqual(archive.extractfile(name).read(), data)

    def test_rebuilds_oci_entries_missing_from_docker_multi_image_index(self):
        index = json.loads(self.files["index.json"])
        index["manifests"] = index["manifests"][:1]
        self.files["index.json"] = encoded(index)
        self.write_source()

        result = normalize_archive(self.source, self.destination, self.expected)
        self.assertEqual(set(result), self.expected)
        with tarfile.open(self.destination) as archive:
            index = json.load(archive.extractfile("index.json"))
            self.assertEqual(len(index["manifests"]), len(self.expected))
            for descriptor in index["manifests"]:
                manifest = json.load(archive.extractfile(
                    "blobs/" + descriptor["digest"].replace(":", "/")
                ))
                self.assertIn(manifest["config"]["digest"], self.expected)
                self.assertEqual(descriptor["digest"], digest(encoded(manifest)))

    def test_rejects_legacy_layer_order_or_digest_divergence(self):
        legacy = json.loads(self.files["manifest.json"])
        legacy[0]["Layers"][0] = legacy[0]["Layers"][0].replace(
            legacy[0]["Layers"][0].rsplit("/", 1)[-1], "f" * 64
        )
        self.files["manifest.json"] = encoded(legacy)
        self.write_source()
        self.rejected()

    def test_local_manifest_identity_requires_config_and_layers(self):
        proof = self.bindings[0]
        proof.verify_inspect(self.inspect(proof))
        classic = self.inspect(proof)
        classic["Id"] = proof.source_image
        classic.pop("Descriptor")
        proof.verify_inspect(classic)
        self.assertNotIn("SENTINEL", json.dumps(proof.public_record()))
        self.assertNotIn("SENTINEL", repr(proof))

    def test_equal_layers_do_not_allow_different_config(self):
        first, second = self.bindings
        observation = self.inspect(second)
        observation["Id"] = first.local_image
        observation["Descriptor"] = {"digest": first.local_image}
        with self.assertRaises(ImageImportError):
            first.verify_inspect(observation)

    def test_unproven_digest_mapping_rejected(self):
        original = self.bindings[0]
        fake = ImageBinding(original.source_image, self.bindings[1].manifest_blob, original.config_blob)
        with self.assertRaises(ImageImportError):
            fake.validate()

    def test_missing_or_additional_config_rejected(self):
        self.expected.add("sha256:" + "e" * 64)
        self.rejected()

    def test_config_byte_tampering_rejected(self):
        path = "blobs/" + self.bindings[0].source_image.replace(":", "/")
        self.files[path] += b" "
        self.write_source()
        self.rejected()

    def test_layer_byte_tampering_rejected(self):
        self.files["blobs/" + digest(self.layer).replace(":", "/")] = b"changed layer"
        self.write_source()
        self.rejected()

    def test_descriptor_substitution_rejected(self):
        index = json.loads(self.files["index.json"])
        index["manifests"][0]["digest"] = "sha256:" + "f" * 64
        self.files["index.json"] = encoded(index)
        self.write_source()
        self.rejected()

    def test_unknown_path_rejected(self):
        self.files["../outside"] = b"unreviewed"
        self.write_source()
        self.rejected()

    def test_existing_destination_preserved(self):
        self.destination.write_bytes(b"prior-backup")
        with self.assertRaises(ImageImportError):
            normalize_archive(self.source, self.destination, self.expected)
        self.assertEqual(self.destination.read_bytes(), b"prior-backup")


if __name__ == "__main__":
    unittest.main()
