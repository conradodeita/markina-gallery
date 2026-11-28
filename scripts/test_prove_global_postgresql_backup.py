from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prove_global_postgresql_backup import (
    APPLICATION_FIXTURE_DOMAINS,
    ProofFailure,
    _copy_synthetic_repository,
    _fixture_row_summary,
    _fixture_uuid,
    _inventory_delta_summary,
    _no_owner_profile_summary,
    _normalize_varchar_text_array_casts,
    _restore,
    _row_inventory_difference_summary,
    _schema_catalog_difference_summary,
    _verify_release_archive_member,
)


class ApplicationFixtureDomainTests(unittest.TestCase):
    def test_fixture_inventories_additional_safe_gallery_states(self) -> None:
        self.assertEqual(
            APPLICATION_FIXTURE_DOMAINS["gallery_processing_settings"],
            ("gallery_preview_settings", "folder_processing_settings"),
        )
        self.assertEqual(
            APPLICATION_FIXTURE_DOMAINS["gallery_access_lifecycle"],
            (
                "notification_milestone",
                "gallery_reopening_request",
                "gallery_reopening_notification_outbox",
            ),
        )
        tables = [
            table for group in APPLICATION_FIXTURE_DOMAINS.values() for table in group
        ]
        self.assertEqual(len(tables), len(set(tables)))


class SyntheticFixtureIdTests(unittest.TestCase):
    def test_fixture_ids_are_deterministic_and_tenant_scoped(self) -> None:
        first_tenant = uuid.UUID("00000000-0000-0000-0000-000000000001")
        second_tenant = uuid.UUID("00000000-0000-0000-0000-000000000002")

        first = _fixture_uuid("a1b2c3d4e5f6", first_tenant, "photo")

        self.assertEqual(first, _fixture_uuid("a1b2c3d4e5f6", first_tenant, "photo"))
        self.assertNotEqual(
            first, _fixture_uuid("a1b2c3d4e5f6", first_tenant, "client")
        )
        self.assertNotEqual(
            first, _fixture_uuid("a1b2c3d4e5f6", second_tenant, "photo")
        )

    def test_fixture_summary_hides_tenant_ids_and_keeps_counts(self) -> None:
        tenant_id = "00000000-0000-0000-0000-000000000001"

        summary = _fixture_row_summary({"client": {tenant_id: 1, "tenant-two": 2}})

        self.assertEqual(
            summary["client"],
            {"tenants_with_rows": 2, "rows_per_tenant": [1, 2], "total_rows": 3},
        )
        self.assertNotIn(tenant_id, repr(summary))


class RunnerToolProvenanceTests(unittest.TestCase):
    def test_release_archive_digest_and_extracted_executable_must_match(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pyp-runner-tool-test-") as directory:
            root = Path(directory)
            archive_path = root / "release.zip"
            executable_path = root / "runner.exe"
            release_bytes = b"synthetic official executable fixture"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("tools/runner.exe", release_bytes)
            executable_path.write_bytes(release_bytes)
            archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()

            _verify_release_archive_member(
                archive_path,
                executable_path,
                expected_archive_sha256=archive_sha256,
            )

            executable_path.write_bytes(b"different executable")
            with self.assertRaisesRegex(
                ProofFailure, "runner_executable_not_from_release_archive"
            ):
                _verify_release_archive_member(
                    archive_path,
                    executable_path,
                    expected_archive_sha256=archive_sha256,
                )

    def test_release_archive_digest_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pyp-runner-tool-test-") as directory:
            root = Path(directory)
            archive_path = root / "release.zip"
            executable_path = root / "runner.exe"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("runner.exe", b"synthetic")
            executable_path.write_bytes(b"synthetic")

            with self.assertRaisesRegex(
                ProofFailure, "runner_release_archive_digest_mismatch"
            ):
                _verify_release_archive_member(
                    archive_path,
                    executable_path,
                    expected_archive_sha256="0" * 64,
                )


class SyntheticRepositoryPortabilityTests(unittest.TestCase):
    def test_copy_preserves_repository_bytes_at_a_distinct_temp_root_path(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="pyp-restic-relocation-test-"
        ) as directory:
            root = Path(directory)
            source = root / "repository-source"
            source.mkdir()
            (source / "config").write_bytes(b"synthetic encrypted repo config")
            pack = source / "data" / "pack"
            pack.mkdir(parents=True)
            (pack / "synthetic-pack").write_bytes(b"synthetic encrypted pack bytes")
            destination = root / "repository-relocated"

            copied_count = _copy_synthetic_repository(
                source, destination, temp_root=root
            )

            self.assertEqual(copied_count, 2)
            self.assertEqual(
                (source / "config").read_bytes(),
                (destination / "config").read_bytes(),
            )
            self.assertEqual(
                (pack / "synthetic-pack").read_bytes(),
                (destination / "data" / "pack" / "synthetic-pack").read_bytes(),
            )

    def test_copy_rejects_destination_outside_temp_root(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="pyp-restic-relocation-test-"
        ) as directory:
            root = Path(directory)
            source = root / "repository-source"
            source.mkdir()
            (source / "config").write_bytes(b"synthetic")

            with self.assertRaisesRegex(ProofFailure, "runner_repository_path_invalid"):
                _copy_synthetic_repository(
                    source,
                    root.parent / "repository-outside",
                    temp_root=root,
                )

    def test_copy_rejects_existing_destination_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="pyp-restic-relocation-test-"
        ) as directory:
            root = Path(directory)
            source = root / "repository-source"
            destination = root / "repository-existing"
            source.mkdir()
            destination.mkdir()
            (source / "config").write_bytes(b"synthetic source")
            (destination / "keep").write_bytes(b"preserve destination")

            with self.assertRaisesRegex(ProofFailure, "runner_repository_path_invalid"):
                _copy_synthetic_repository(source, destination, temp_root=root)

            self.assertEqual(
                (destination / "keep").read_bytes(), b"preserve destination"
            )


class SchemaComparisonTests(unittest.TestCase):
    def test_row_inventory_difference_summary_reports_only_metadata(self) -> None:
        expected = {"proof_fixture.snapshot": {"count": 2, "sha256": "a" * 64}}
        actual = {"proof_fixture.snapshot": {"count": 1, "sha256": "b" * 64}}

        summary = _row_inventory_difference_summary(expected, actual)

        self.assertIn("proof_fixture.snapshot:count=2->1", summary)
        self.assertIn("sha256_equal=False", summary)
        self.assertNotIn("a" * 64, summary)
        self.assertNotIn("b" * 64, summary)

    def test_no_owner_profile_options_are_passed_to_pg_restore(self) -> None:
        result = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout=b"", stderr=b""
        )
        with patch(
            "scripts.prove_global_postgresql_backup._docker", return_value=result
        ) as docker_call:
            _restore(
                "synthetic-target",
                "synthetic-db",
                b"synthetic-archive",
                case="no_owner_restore",
                restore_options=("--no-owner", "--no-privileges"),
            )

        args = docker_call.call_args.args
        self.assertEqual(
            args[4:9],
            ("-U", "postgres", "--exit-on-error", "--no-owner", "--no-privileges"),
        )
        self.assertEqual(args[-2:], ("--dbname", "synthetic-db"))

    def test_no_owner_diagnostic_exposes_counts_without_role_names(self) -> None:
        source = [
            (
                "proof_fixture",
                "tenant_record",
                "r",
                "p",
                False,
                "private_synthetic_role",
            )
        ]
        restored = [
            (
                "proof_fixture",
                "tenant_record",
                "r",
                "p",
                False,
                "private_synthetic_role",
            )
        ]

        summary = _no_owner_profile_summary(source, restored)

        self.assertIn("source_non_postgres=1", summary)
        self.assertIn("restored_other=1", summary)
        self.assertNotIn("private_synthetic_role", summary)

    def test_inventory_delta_reports_only_sanitized_category_metadata(self) -> None:
        before = {
            "context": "desktop-linux",
            "containers": ["private-container-name"],
            "networks": [],
            "volumes": [],
        }
        after = {
            "context": "desktop-linux",
            "containers": ["private-container-name", "new-container-name"],
            "networks": [],
            "volumes": [],
        }

        summary = _inventory_delta_summary(before, after)

        self.assertIn("containers:before=1,after=2,added=1,removed=0", summary)
        self.assertNotIn("private-container-name", summary)
        self.assertNotIn("new-container-name", summary)

    def test_equivalent_varchar_array_cast_forms_normalize(self) -> None:
        source = (
            "CHECK (((purpose)::text = ANY ((ARRAY["
            "'queued'::character varying, 'owner''s, ready'::character varying"
            "])::text[])))"
        )
        restored = (
            "CHECK (((purpose)::text = ANY (ARRAY["
            "('queued'::character varying)::text, "
            "('owner''s, ready'::character varying)::text])))"
        )

        normalized_source, source_count = _normalize_varchar_text_array_casts(source)
        normalized_restored, restored_count = _normalize_varchar_text_array_casts(
            restored
        )

        self.assertEqual(source_count, 1)
        self.assertEqual(restored_count, 1)
        self.assertEqual(normalized_source, normalized_restored)

    def test_different_literal_values_remain_different(self) -> None:
        source, source_count = _normalize_varchar_text_array_casts(
            "CHECK (state = ANY ((ARRAY['queued'::character varying])::text[]))"
        )
        restored, restored_count = _normalize_varchar_text_array_casts(
            "CHECK (state = ANY (ARRAY[('verified'::character varying)::text]))"
        )

        self.assertEqual(source_count, 1)
        self.assertEqual(restored_count, 1)
        self.assertNotEqual(source, restored)

    def test_different_array_target_type_is_not_normalized(self) -> None:
        definition = "CHECK (state = ANY ((ARRAY['queued'::character varying])::character varying[]))"

        normalized, count = _normalize_varchar_text_array_casts(definition)

        self.assertEqual(count, 0)
        self.assertEqual(normalized, definition)

    def test_array_like_text_inside_sql_string_is_not_normalized(self) -> None:
        definition = "SELECT 'ARRAY[''queued''::character varying]::text[]' AS label"

        normalized, count = _normalize_varchar_text_array_casts(definition)

        self.assertEqual(count, 0)
        self.assertEqual(normalized, definition)

    def test_array_like_text_inside_dollar_quoted_function_is_not_normalized(
        self,
    ) -> None:
        definition = (
            "CREATE FUNCTION proof_fixture.example() RETURNS text "
            "LANGUAGE sql AS $function$ SELECT ARRAY['queued'::character varying]::text[] "
            "$function$"
        )

        normalized, count = _normalize_varchar_text_array_casts(definition)

        self.assertEqual(count, 0)
        self.assertEqual(normalized, definition)

    def test_array_like_text_inside_sql_comment_is_not_normalized(self) -> None:
        definition = "SELECT 1 /* ARRAY['queued'::character varying]::text[] */"

        normalized, count = _normalize_varchar_text_array_casts(definition)

        self.assertEqual(count, 0)
        self.assertEqual(normalized, definition)

    def test_visible_column_reordering_remains_a_schema_difference(self) -> None:
        def column(position: int, name: str) -> tuple[object, ...]:
            return (
                "public",
                "demo",
                position,
                name,
                "bigint",
                "pg_catalog",
                "int8",
                "NO",
                None,
                None,
                64,
                0,
                None,
                "NO",
                None,
                "NEVER",
                "",
            )

        categories = {
            name: []
            for name in (
                "columns",
                "constraints",
                "indexes",
                "views",
                "routines",
                "triggers",
                "policies",
                "types",
            )
        }
        expected = {**categories, "columns": [column(1, "id"), column(2, "name")]}
        actual = {**categories, "columns": [column(2, "id"), column(1, "name")]}

        summary = _schema_catalog_difference_summary(expected, actual)

        self.assertIn("position=1->2", summary)
        self.assertIn("position=2->1", summary)


if __name__ == "__main__":
    unittest.main()
