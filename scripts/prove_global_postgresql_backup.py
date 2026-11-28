"""Prova local opt-in de dump/restore PostgreSQL, somente com fixture sintética."""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from datetime import time as datetime_time
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
IMAGE = "postgres:17.11-alpine"
EXPECTED_IMAGE_DIGEST = (
    "postgres@sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b"
)
EXPECTED_CONTEXT = "desktop-linux"
PROOF_LABEL = "io.pickyourpic.synthetic-postgresql-proof"
SYSTEM_SCHEMAS = {"information_schema", "pg_catalog"}
APPLICATION_FIXTURE_DOMAINS: dict[str, tuple[str, ...]] = {
    "identity_gallery_access": (
        "client",
        "client_phone",
        "parent_gallery",
        "photo_folder",
        "photo_asset",
        "parent_gallery_registration",
        "gallery_client_state",
        "gallery_access",
        "folder_client_grant",
        "photo_selection",
        "photo_favorite",
        "photo_view",
        "photo_comment",
        "price_rule",
    ),
    "commerce_history": ("payment_group", "sale_order", "sale_order_item"),
    "legacy_payment_without_provider_issue": ("provider_payment",),
    "completed_asset_file_cleanup": ("asset_file_cleanup",),
    "media_processing_queue": ("photo_analysis", "media_derivative", "media_job"),
    "cold_media_catalog": (
        "media_archive_cycle",
        "media_archive_operation",
        "media_archive_object",
        "media_archive_event",
    ),
    "cold_media_recovery_and_credits": (
        "media_archive_recovery_request",
        "media_archive_recovery_credit_reservation",
        "media_archive_recovery_credit_allocation_event",
    ),
    "cold_media_space_reservation": ("media_archive_space_reservation",),
    "cold_media_notices": ("media_archive_notice",),
    "derived_gallery_relationships": (
        "derived_gallery",
        "derived_gallery_membership",
        "derived_gallery_photo",
        "derived_gallery_photo_origin",
    ),
    "private_upload_batches": ("private_upload_batch", "private_upload_batch_asset"),
    "private_gallery_notifications": ("gallery_membership_notification_outbox",),
    "revoked_gallery_capabilities": ("gallery_access_capability",),
    "disabled_payment_preferences": ("payment_preferences",),
    "tenant_credit_wallet_modes": ("tenant_credit_wallet",),
    "tenant_branding": ("branding_settings",),
    "inactive_progressive_pricing": (
        "progressive_pricing_preset",
        "progressive_pricing_tier",
    ),
    "privacy_and_consent": (
        "gallery_facial_policy",
        "facial_search_request",
        "facial_search_consent_proof",
    ),
    "notifications_and_audit": (
        "notification_setting",
        "notification_event",
        "notification_delivery",
        "audit_event",
        "platform_admin_event",
        "photographer_credit_entry",
    ),
    "gallery_processing_settings": (
        "gallery_preview_settings",
        "folder_processing_settings",
    ),
    "gallery_access_lifecycle": (
        "notification_milestone",
        "gallery_reopening_request",
        "gallery_reopening_notification_outbox",
    ),
    "photographer_profile": ("photographer_business_profile",),
    "tenant_membership": ("tenant_admin",),
    "gallery_lifecycle_history": ("gallery_lifecycle_operation",),
    "disabled_legacy_preview_adjustment": ("preview_adjustment_settings",),
}
RUNNER_RESTIC_WINDOWS_ARCHIVE_SHA256 = (
    "bba9061c3dce081701ab353ec8cb73a78be73b71a538aad560f2d1067602b7fe"
)
RUNNER_RCLONE_WINDOWS_ARCHIVE_SHA256 = (
    "8b4fd2737ade4e70c057ef4a49deb7cffe94b0fb9d7587c189d149823f21a1dc"
)


@dataclass(frozen=True)
class RunnerProofOptions:
    temp_root: Path
    restic_executable: Path
    rclone_executable: Path
    restic_archive: Path
    rclone_archive: Path


class ProofFailure(RuntimeError):
    """Falha sanitizada da prova sintética."""


def _run(
    argv: list[str],
    *,
    input_bytes: bytes | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            input=input_bytes,
            capture_output=True,
            check=False,
            env=env,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProofFailure("local_command_unavailable") from exc
    if check and result.returncode:
        raise ProofFailure("local_command_failed")
    return result


def _docker(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    check = kwargs.pop("check", True)
    known_synthetic_roles = kwargs.pop("known_synthetic_roles", ())
    result = _run(["docker", *args], check=False, **kwargs)
    if not check or result.returncode == 0:
        return result
    command = args[0] if args else "unknown"
    diagnostic = "failed"
    if command == "exec":
        executable = next(
            (
                item
                for item in args[1:]
                if item in {"createdb", "pg_dump", "pg_isready", "pg_restore", "psql"}
            ),
            "exec",
        )
        command = f"exec_{executable}"
        if executable == "pg_restore":
            command += "_list" if "--list" in args else "_restore"
            error = result.stderr.decode("utf-8", errors="replace").lower()
            if "role" in error and "does not exist" in error:
                match = re.search(r'role\s+"([^"]+)"\s+does not exist', error)
                if match and match.group(1) in known_synthetic_roles:
                    diagnostic = "missing_expected_role"
                elif match:
                    diagnostic = "missing_unexpected_role"
                else:
                    diagnostic = "missing_role_unclassified"
            elif "extension" in error and (
                "does not exist" in error or "not available" in error
            ):
                diagnostic = "missing_extension"
            elif "already exists" in error:
                diagnostic = "target_conflict"
            elif "permission denied" in error:
                diagnostic = "permission_denied"
            elif (
                "archive" in error or "input file" in error or "unexpected end" in error
            ):
                diagnostic = "invalid_archive"
    elif command == "network" and len(args) > 1:
        command = f"network_{args[1]}"
    raise ProofFailure(f"docker_{command}_{diagnostic}") from None


def _lines(result: subprocess.CompletedProcess[bytes]) -> list[str]:
    return result.stdout.decode("utf-8", errors="replace").splitlines()


def _inventory() -> dict[str, list[str] | str]:
    context = _lines(_docker("context", "show"))[0]
    containers = sorted(
        _lines(
            _docker(
                "ps",
                "-a",
                "--no-trunc",
                "--format",
                "{{.ID}}|{{.Names}}|{{.Image}}|{{.State}}|{{.Ports}}",
            )
        )
    )
    networks = sorted(
        _lines(
            _docker(
                "network",
                "ls",
                "--no-trunc",
                "--format",
                "{{.ID}}|{{.Name}}|{{.Driver}}",
            )
        )
    )
    volumes = sorted(_lines(_docker("volume", "ls", "--format", "{{.Name}}")))
    return {
        "context": context,
        "containers": containers,
        "networks": networks,
        "volumes": volumes,
    }


def _inventory_delta_summary(
    expected: dict[str, list[str] | str], actual: dict[str, list[str] | str]
) -> str:
    differences = []
    for category in ("context", "containers", "networks", "volumes"):
        before = expected[category]
        after = actual[category]
        if before == after:
            continue
        if category == "context":
            differences.append("context:changed")
            continue
        before_rows = before if isinstance(before, list) else []
        after_rows = after if isinstance(after, list) else []
        differences.append(
            f"{category}:before={len(before_rows)},after={len(after_rows)}"
            f",added={len(set(after_rows) - set(before_rows))}"
            f",removed={len(set(before_rows) - set(after_rows))}"
            f",before_sha256={_sha256(chr(10).join(before_rows).encode())}"
            f",after_sha256={_sha256(chr(10).join(after_rows).encode())}"
        )
    return ";".join(differences) or "unchanged"


def _proof_resources(proof_id: str) -> tuple[list[str], list[str]]:
    label_filter = f"label={PROOF_LABEL}={proof_id}"
    containers = _lines(
        _docker("ps", "-a", "--filter", label_filter, "--format", "{{.ID}}")
    )
    networks = _lines(
        _docker("network", "ls", "--filter", label_filter, "--format", "{{.ID}}")
    )
    return containers, networks


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ProofFailure("runner_binary_read_failed") from exc
    return digest.hexdigest()


def _repository_file_hashes(repository: Path, *, temp_root: Path) -> dict[str, str]:
    try:
        resolved_root = temp_root.resolve(strict=True)
        resolved_repository = repository.resolve(strict=True)
        if (
            resolved_repository.parent != resolved_root
            or not resolved_repository.is_dir()
        ):
            raise ProofFailure("runner_repository_path_invalid")
        entries = tuple(resolved_repository.rglob("*"))
        if any(
            entry.is_symlink() or not (entry.is_dir() or entry.is_file())
            for entry in entries
        ):
            raise ProofFailure("runner_repository_entry_invalid")
        files = tuple(entry for entry in entries if entry.is_file())
        if not files:
            raise ProofFailure("runner_repository_empty")
        return {
            entry.relative_to(resolved_repository).as_posix(): _file_sha256(entry)
            for entry in files
        }
    except ProofFailure:
        raise
    except (OSError, RuntimeError, ValueError):
        raise ProofFailure("runner_repository_path_invalid") from None


def _copy_synthetic_repository(
    source: Path, destination: Path, *, temp_root: Path
) -> int:
    try:
        resolved_root = temp_root.resolve(strict=True)
        resolved_source = source.resolve(strict=True)
        resolved_destination = destination.resolve(strict=False)
        if (
            resolved_source.parent != resolved_root
            or resolved_destination.parent != resolved_root
            or resolved_source == resolved_destination
            or resolved_destination.exists()
        ):
            raise ProofFailure("runner_repository_path_invalid")
        source_hashes = _repository_file_hashes(
            resolved_source, temp_root=resolved_root
        )
    except ProofFailure:
        raise
    except (OSError, RuntimeError, ValueError):
        raise ProofFailure("runner_repository_path_invalid") from None

    try:
        shutil.copytree(
            resolved_source, resolved_destination, copy_function=shutil.copy2
        )
    except (OSError, shutil.Error):
        raise ProofFailure("runner_repository_copy_failed") from None

    destination_hashes = _repository_file_hashes(
        resolved_destination, temp_root=resolved_root
    )
    if source_hashes != destination_hashes:
        raise ProofFailure("runner_repository_copy_mismatch")
    return len(destination_hashes)


def _verify_release_archive_member(
    archive_path: Path,
    executable_path: Path,
    *,
    expected_archive_sha256: str,
) -> None:
    if _file_sha256(archive_path) != expected_archive_sha256:
        raise ProofFailure("runner_release_archive_digest_mismatch")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            matches = [
                name
                for name in archive.namelist()
                if PurePosixPath(name).name.casefold()
                == executable_path.name.casefold()
            ]
            if len(matches) != 1:
                raise ProofFailure("runner_release_member_ambiguous")
            digest = hashlib.sha256()
            size = 0
            with (
                archive.open(matches[0]) as expected,
                executable_path.open("rb") as actual,
            ):
                while True:
                    expected_chunk = expected.read(1024 * 1024)
                    actual_chunk = actual.read(1024 * 1024)
                    if expected_chunk != actual_chunk:
                        raise ProofFailure("runner_executable_not_from_release_archive")
                    if not expected_chunk:
                        break
                    digest.update(expected_chunk)
                    size += len(expected_chunk)
                if actual.read(1):
                    raise ProofFailure("runner_executable_not_from_release_archive")
    except ProofFailure:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ProofFailure("runner_release_archive_invalid") from exc
    if size == 0 or digest.hexdigest() != _file_sha256(executable_path):
        raise ProofFailure("runner_executable_not_from_release_archive")


def _expect_equal(label: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise ProofFailure(f"verification_mismatch:{label}")


def _expect_rejected(label: str, expected: Any, actual: Any) -> None:
    try:
        _expect_equal(label, expected, actual)
    except ProofFailure:
        return
    raise ProofFailure(f"negative_case_accepted:{label}")


def _normalized(value: Any) -> Any:
    if isinstance(value, memoryview):
        return {"bytes": value.tobytes().hex()}
    if isinstance(value, (bytes, bytearray)):
        return {"bytes": bytes(value).hex()}
    if isinstance(value, dict):
        return {
            str(key): _normalized(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    if isinstance(value, (datetime, date, datetime_time, Decimal, uuid.UUID)):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _rows_digest(rows: list[sa.engine.RowMapping]) -> str:
    encoded = sorted(
        json.dumps(_normalized(dict(row)), sort_keys=True, separators=(",", ":"))
        for row in rows
    )
    return _sha256("\n".join(encoded).encode("utf-8"))


def _data_inventory(engine: Engine, tenant_ids: list[uuid.UUID]) -> dict[str, Any]:
    inspector = sa.inspect(engine)
    inventory: dict[str, Any] = {}
    metadata = sa.MetaData()
    with engine.connect() as connection:
        for schema in inspector.get_schema_names():
            if schema in SYSTEM_SCHEMAS or schema.startswith(
                ("pg_", "information_schema")
            ):
                continue
            for name in inspector.get_table_names(schema=schema):
                table = sa.Table(
                    name, metadata, schema=schema, autoload_with=connection
                )
                all_rows = connection.execute(sa.select(table)).mappings().all()
                item: dict[str, Any] = {
                    "count": len(all_rows),
                    "sha256": _rows_digest(all_rows),
                }
                tenant_column = table.c.get("tenant_id")
                if tenant_column is not None:
                    item["tenants"] = {}
                    for tenant_id in tenant_ids:
                        scoped_rows = (
                            connection.execute(
                                sa.select(table).where(tenant_column == str(tenant_id))
                            )
                            .mappings()
                            .all()
                        )
                        item["tenants"][str(tenant_id)] = {
                            "count": len(scoped_rows),
                            "sha256": _rows_digest(scoped_rows),
                        }
                inventory[f"{schema}.{name}"] = item
    return inventory


def _materialized_view_inventory(
    engine: Engine, tenant_ids: list[uuid.UUID]
) -> dict[str, Any]:
    inspector = sa.inspect(engine)
    inventory: dict[str, Any] = {}
    metadata = sa.MetaData()
    with engine.connect() as connection:
        for schema in inspector.get_schema_names():
            if schema in SYSTEM_SCHEMAS or schema.startswith(
                ("pg_", "information_schema")
            ):
                continue
            for name in inspector.get_materialized_view_names(schema=schema):
                view = sa.Table(name, metadata, schema=schema, autoload_with=connection)
                all_rows = connection.execute(sa.select(view)).mappings().all()
                item: dict[str, Any] = {
                    "count": len(all_rows),
                    "sha256": _rows_digest(all_rows),
                }
                tenant_column = view.c.get("tenant_id")
                if tenant_column is not None:
                    item["tenants"] = {}
                    for tenant_id in tenant_ids:
                        scoped_rows = (
                            connection.execute(
                                sa.select(view).where(tenant_column == str(tenant_id))
                            )
                            .mappings()
                            .all()
                        )
                        item["tenants"][str(tenant_id)] = {
                            "count": len(scoped_rows),
                            "sha256": _rows_digest(scoped_rows),
                        }
                inventory[f"{schema}.{name}"] = item
    return inventory


def _row_inventory_difference_summary(
    expected: dict[str, Any], actual: dict[str, Any]
) -> str:
    differences = []
    for name in sorted(expected.keys() | actual.keys()):
        left = expected.get(name)
        right = actual.get(name)
        if left is None:
            differences.append(f"{name}:added")
        elif right is None:
            differences.append(f"{name}:missing")
        else:
            left_tenants = left.get("tenants", {})
            right_tenants = right.get("tenants", {})
            tenant_keys = left_tenants.keys() | right_tenants.keys()
            changed_tenants = sum(
                left_tenants.get(key) != right_tenants.get(key) for key in tenant_keys
            )
            if left != right:
                differences.append(
                    f"{name}:count={left['count']}->{right['count']}"
                    f",sha256_equal={left['sha256'] == right['sha256']}"
                    f",tenant_differences={changed_tenants}"
                )
    return "|".join(differences[:5]) or "unclassified"


def _large_object_inventory(engine: Engine) -> list[tuple[int, int, str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text("SELECT oid, lo_get(oid) FROM pg_largeobject_metadata ORDER BY oid")
        )
        return [(int(oid), len(data), _sha256(bytes(data))) for oid, data in rows]


def _relation_inventory(engine: Engine) -> list[tuple[Any, ...]]:
    statement = sa.text(
        """SELECT n.nspname, c.relname, c.relkind, c.relpersistence,
                  c.relispartition, pg_get_userbyid(c.relowner)
             FROM pg_class AS c
             JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname <> 'information_schema'
              AND n.nspname !~ '^pg_'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f', 'i', 'I')
            ORDER BY n.nspname, c.relname"""
    )
    with engine.connect() as connection:
        return [tuple(row) for row in connection.execute(statement)]


def _extension_inventory(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text("SELECT extname, extversion FROM pg_extension ORDER BY extname")
        )
        return [(str(name), str(version)) for name, version in rows]


def _role_inventory(engine: Engine, roles: tuple[str, str, str]) -> dict[str, Any]:
    owner, reader, member = roles
    params = {"owner": owner, "reader": reader, "member": member}
    with engine.connect() as connection:
        role_rows = connection.execute(
            sa.text(
                """SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb,
                          rolcanlogin, rolreplication, rolbypassrls, rolconnlimit
                     FROM pg_roles
                    WHERE rolname IN (:owner, :reader, :member)
                    ORDER BY rolname"""
            ),
            params,
        )
        membership_rows = connection.execute(
            sa.text(
                """SELECT granted.rolname, member.rolname, membership.admin_option
                     FROM pg_auth_members AS membership
                     JOIN pg_roles AS granted ON granted.oid = membership.roleid
                     JOIN pg_roles AS member ON member.oid = membership.member
                    WHERE granted.rolname = :reader AND member.rolname = :member"""
            ),
            params,
        )
        grants = connection.execute(
            sa.text(
                """SELECT table_schema, table_name, grantee, privilege_type, is_grantable
                     FROM information_schema.role_table_grants
                    WHERE table_schema = 'proof_fixture'
                      AND grantee IN (:owner, :reader, :member)
                    ORDER BY table_schema, table_name, grantee, privilege_type"""
            ),
            params,
        )
        defaults = connection.execute(
            sa.text(
                """SELECT namespace.nspname, defaults.defaclobjtype,
                          pg_get_userbyid(defaults.defaclrole),
                          CASE WHEN acl.grantee = 0 THEN 'PUBLIC'
                               ELSE pg_get_userbyid(acl.grantee) END,
                          acl.privilege_type, acl.is_grantable
                     FROM pg_default_acl AS defaults
                     LEFT JOIN pg_namespace AS namespace
                       ON namespace.oid = defaults.defaclnamespace
                     CROSS JOIN LATERAL aclexplode(defaults.defaclacl) AS acl
                    WHERE pg_get_userbyid(defaults.defaclrole) = :owner
                    ORDER BY namespace.nspname, defaults.defaclobjtype,
                             pg_get_userbyid(defaults.defaclrole), 4, acl.privilege_type"""
            ),
            params,
        )
        return {
            "roles": [tuple(row) for row in role_rows],
            "memberships": [tuple(row) for row in membership_rows],
            "grants": [tuple(row) for row in grants],
            "default_privileges": [tuple(row) for row in defaults],
        }


def _sequence_inventory(engine: Engine) -> list[tuple[Any, ...]]:
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                """SELECT schemaname, sequencename, start_value, min_value, max_value,
                          increment_by, cycle, cache_size, last_value
                     FROM pg_sequences
                    WHERE schemaname <> 'information_schema'
                      AND schemaname !~ '^pg_'
                    ORDER BY schemaname, sequencename"""
            )
        )
        return [tuple(row) for row in rows]


def _no_owner_profile_summary(
    source_relations: list[tuple[Any, ...]],
    restored_relations: list[tuple[Any, ...]],
) -> str:
    source_fixture = [row for row in source_relations if row[0] == "proof_fixture"]
    restored_fixture = [row for row in restored_relations if row[0] == "proof_fixture"]
    source_non_postgres = sum(row[5] != "postgres" for row in source_fixture)
    restored_postgres = sum(row[5] == "postgres" for row in restored_fixture)
    restored_other = sum(row[5] != "postgres" for row in restored_fixture)
    kinds = sorted({str(row[2]) for row in restored_fixture if row[5] != "postgres"})
    return (
        f"source_fixture={len(source_fixture)}"
        f",source_non_postgres={source_non_postgres}"
        f",restored_fixture={len(restored_fixture)}"
        f",restored_postgres={restored_postgres}"
        f",restored_other={restored_other}"
        f",restored_other_kinds={','.join(kinds) or 'none'}"
    )


def _schema_dump(container: str, database: str) -> bytes:
    result = _docker(
        "exec",
        container,
        "pg_dump",
        "-U",
        "postgres",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--no-comments",
        "--dbname",
        database,
    )
    lines = result.stdout.decode("utf-8", errors="strict").splitlines()
    stable = [
        line.rstrip()
        for line in lines
        if line.strip()
        and not line.startswith("--")
        and not line.startswith(("\\restrict ", "\\unrestrict "))
    ]
    statements: list[str] = []
    current: list[str] = []
    dollar_quote: str | None = None
    for line in stable:
        current.append(line.strip())
        for delimiter in re.findall(r"\$[A-Za-z0-9_]*\$", line):
            if dollar_quote is None:
                dollar_quote = delimiter
            elif delimiter == dollar_quote:
                dollar_quote = None
        if line.rstrip().endswith(";") and dollar_quote is None:
            statements.append(" ".join(current))
            current.clear()
    if current:
        statements.append(" ".join(current))
    canonical_statements = [
        _normalize_varchar_text_array_casts(statement)[0] for statement in statements
    ]
    return "\n".join(sorted(canonical_statements)).encode("utf-8")


_SQL_STRING_LITERAL = r"'(?:[^']|'')*'"
_ARRAY_VARCHAR_LITERAL = re.compile(
    rf"^\s*({_SQL_STRING_LITERAL})\s*::\s*character varying\s*$",
    re.IGNORECASE,
)
_ARRAY_VARCHAR_TO_TEXT_LITERAL = re.compile(
    rf"^\s*\(\s*({_SQL_STRING_LITERAL})\s*::\s*character varying\s*\)"
    r"\s*::\s*text\s*$",
    re.IGNORECASE,
)


def _sql_array_end(value: str, opening_bracket: int) -> int | None:
    depth = 0
    in_string = False
    position = opening_bracket
    while position < len(value):
        character = value[position]
        if in_string:
            if character == "'":
                if position + 1 < len(value) and value[position + 1] == "'":
                    position += 2
                    continue
                in_string = False
        elif character == "'":
            in_string = True
        elif character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return None


def _sql_array_elements(value: str) -> list[str]:
    elements = []
    start = 0
    bracket_depth = 0
    parenthesis_depth = 0
    in_string = False
    position = 0
    while position < len(value):
        character = value[position]
        if in_string:
            if character == "'":
                if position + 1 < len(value) and value[position + 1] == "'":
                    position += 2
                    continue
                in_string = False
        elif character == "'":
            in_string = True
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
        elif character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth -= 1
        elif character == "," and bracket_depth == 0 and parenthesis_depth == 0:
            elements.append(value[start:position].strip())
            start = position + 1
        position += 1
    elements.append(value[start:].strip())
    return elements


def _skip_sql_quoted_region(value: str, position: int, quote: str) -> int:
    escape_string = (
        quote == "'"
        and position > 0
        and value[position - 1] in "eE"
        and (
            position < 2
            or not (value[position - 2].isalnum() or value[position - 2] == "_")
        )
    )
    position += 1
    while position < len(value):
        if escape_string and value[position] == "\\":
            position += 2
            continue
        if value[position] == quote:
            if position + 1 < len(value) and value[position + 1] == quote:
                position += 2
                continue
            return position + 1
        position += 1
    return len(value)


def _next_unquoted_array(
    value: str, start: int, pattern: re.Pattern[str]
) -> re.Match[str] | None:
    position = start
    while position < len(value):
        if value.startswith("--", position):
            newline = value.find("\n", position + 2)
            position = len(value) if newline < 0 else newline + 1
            continue
        if value.startswith("/*", position):
            position += 2
            depth = 1
            while position < len(value) and depth:
                if value.startswith("/*", position):
                    depth += 1
                    position += 2
                elif value.startswith("*/", position):
                    depth -= 1
                    position += 2
                else:
                    position += 1
            continue
        if value[position] in "'\"":
            position = _skip_sql_quoted_region(value, position, value[position])
            continue
        if value[position] == "$":
            delimiter = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", value[position:])
            if delimiter:
                quote = delimiter.group(0)
                closing = value.find(quote, position + len(quote))
                position = len(value) if closing < 0 else closing + len(quote)
                continue
        match = pattern.match(value, position)
        if match:
            return match
        position += 1
    return None


def _normalize_varchar_text_array_casts(definition: str) -> tuple[str, int]:
    """Canonicalize only PostgreSQL's equivalent literal varchar[] -> text[] forms."""
    result = definition
    normalized_arrays = 0
    search_from = 0
    array_pattern = re.compile(r"\bARRAY\s*\[", re.IGNORECASE)
    while match := _next_unquoted_array(result, search_from, array_pattern):
        opening_bracket = result.find("[", match.start(), match.end())
        closing_bracket = _sql_array_end(result, opening_bracket)
        if closing_bracket is None:
            break
        elements = _sql_array_elements(result[opening_bracket + 1 : closing_bracket])
        tail = result[closing_bracket + 1 :]
        array_cast = re.match(r"\s*\)\s*::\s*text\s*\[\s*\]", tail, re.IGNORECASE)
        if array_cast:
            left_open = match.start() - 1
            while left_open >= 0 and result[left_open].isspace():
                left_open -= 1
            if left_open >= 0 and result[left_open] == "(":
                literal_matches = [
                    _ARRAY_VARCHAR_LITERAL.fullmatch(element) for element in elements
                ]
                if elements and all(literal_matches):
                    canonical = [f"{item.group(1)}::text" for item in literal_matches]
                    replacement = f"ARRAY[{', '.join(canonical)}]"
                    result = result[:left_open] + replacement + tail[array_cast.end() :]
                    normalized_arrays += 1
                    search_from = left_open + len(replacement)
                    continue
        else:
            literal_matches = [
                _ARRAY_VARCHAR_TO_TEXT_LITERAL.fullmatch(element)
                for element in elements
            ]
            if elements and all(literal_matches):
                canonical = [f"{item.group(1)}::text" for item in literal_matches]
                replacement = f"ARRAY[{', '.join(canonical)}]"
                result = (
                    result[: match.start()]
                    + replacement
                    + result[closing_bracket + 1 :]
                )
                normalized_arrays += 1
                search_from = match.start() + len(replacement)
                continue
        search_from = closing_bracket + 1
    return result, normalized_arrays


def _schema_definition_inventory(
    engine: Engine, normalized_objects: list[str]
) -> dict[str, list[tuple[Any, ...]]]:
    statements = {
        "columns": """
            SELECT table_schema, table_name,
                   row_number() OVER (
                       PARTITION BY table_schema, table_name
                       ORDER BY ordinal_position
                   ) AS logical_position,
                   column_name, data_type,
                   udt_schema, udt_name, is_nullable, column_default,
                   character_maximum_length, numeric_precision, numeric_scale,
                   datetime_precision, is_identity, identity_generation, is_generated,
                   generation_expression
              FROM information_schema.columns
             WHERE table_schema <> 'information_schema' AND table_schema !~ '^pg_'
             ORDER BY table_schema, table_name, ordinal_position
        """,
        "constraints": """
            SELECT namespace.nspname, relation.relname, constraint_row.conname,
                   constraint_row.contype, constraint_row.condeferrable,
                   constraint_row.condeferred, constraint_row.convalidated,
                   pg_get_constraintdef(constraint_row.oid, false)
              FROM pg_constraint AS constraint_row
              JOIN pg_class AS relation ON relation.oid = constraint_row.conrelid
              JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
             WHERE namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, relation.relname, constraint_row.conname
        """,
        "indexes": """
            SELECT namespace.nspname, table_row.relname, index_row.relname,
                   pg_get_indexdef(index_data.indexrelid, 0, false)
              FROM pg_index AS index_data
              JOIN pg_class AS table_row ON table_row.oid = index_data.indrelid
              JOIN pg_class AS index_row ON index_row.oid = index_data.indexrelid
              JOIN pg_namespace AS namespace ON namespace.oid = table_row.relnamespace
             WHERE namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, table_row.relname, index_row.relname
        """,
        "views": """
            SELECT namespace.nspname, relation.relname, relation.relkind,
                   relation.relispopulated, pg_get_viewdef(relation.oid, true)
              FROM pg_class AS relation
              JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
             WHERE relation.relkind IN ('v', 'm')
               AND namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, relation.relname
        """,
        "routines": """
            SELECT namespace.nspname, routine.proname,
                   pg_get_function_identity_arguments(routine.oid),
                   pg_get_function_result(routine.oid), routine.prokind,
                   routine.provolatile, routine.prosecdef, pg_get_functiondef(routine.oid)
              FROM pg_proc AS routine
              JOIN pg_namespace AS namespace ON namespace.oid = routine.pronamespace
             WHERE routine.prokind IN ('f', 'p')
               AND namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, routine.proname,
                      pg_get_function_identity_arguments(routine.oid)
        """,
        "triggers": """
            SELECT namespace.nspname, relation.relname, trigger_row.tgname,
                   pg_get_triggerdef(trigger_row.oid, true)
              FROM pg_trigger AS trigger_row
              JOIN pg_class AS relation ON relation.oid = trigger_row.tgrelid
              JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
             WHERE NOT trigger_row.tgisinternal
               AND namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, relation.relname, trigger_row.tgname
        """,
        "policies": """
            SELECT namespace.nspname, relation.relname, policy.polname,
                   policy.polcmd, policy.polpermissive,
                   pg_get_expr(policy.polqual, policy.polrelid, true),
                   pg_get_expr(policy.polwithcheck, policy.polrelid, true),
                   ARRAY(
                       SELECT CASE WHEN role_oid = 0 THEN 'PUBLIC'
                                   ELSE pg_get_userbyid(role_oid) END
                         FROM unnest(policy.polroles) AS role_row(role_oid)
                        ORDER BY 1
                   )
              FROM pg_policy AS policy
              JOIN pg_class AS relation ON relation.oid = policy.polrelid
              JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
             WHERE namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             ORDER BY namespace.nspname, relation.relname, policy.polname
        """,
        "types": """
            SELECT namespace.nspname, type_row.typname, type_row.typtype,
                   format_type(type_row.oid, NULL), type_row.typnotnull,
                   type_row.typdefault,
                   COALESCE(
                       array_agg(enum_row.enumlabel ORDER BY enum_row.enumsortorder)
                           FILTER (WHERE enum_row.enumlabel IS NOT NULL),
                       ARRAY[]::text[]
                   )
              FROM pg_type AS type_row
              JOIN pg_namespace AS namespace ON namespace.oid = type_row.typnamespace
              LEFT JOIN pg_enum AS enum_row ON enum_row.enumtypid = type_row.oid
             WHERE type_row.typtype IN ('e', 'd', 'r')
               AND namespace.nspname <> 'information_schema'
               AND namespace.nspname !~ '^pg_'
             GROUP BY namespace.nspname, type_row.typname, type_row.typtype,
                      type_row.oid, type_row.typnotnull, type_row.typdefault
             ORDER BY namespace.nspname, type_row.typname
        """,
    }
    with engine.connect() as connection:
        inventory = {
            name: [tuple(row) for row in connection.execute(sa.text(statement))]
            for name, statement in statements.items()
        }
    for category, definition_index in (("constraints", 7), ("indexes", 3)):
        normalized_rows = []
        for row in inventory[category]:
            values = list(row)
            original = str(values[definition_index])
            values[definition_index], count = _normalize_varchar_text_array_casts(
                original
            )
            if count:
                normalized_objects.append(f"{category}:{values[2]}")
            normalized_rows.append(tuple(values))
        inventory[category] = normalized_rows
    return inventory


def _schema_catalog_difference_summary(
    expected: dict[str, list[tuple[Any, ...]]],
    actual: dict[str, list[tuple[Any, ...]]],
) -> str:
    fields = {
        "columns": (
            "schema",
            "table",
            "position",
            "column",
            "data_type",
            "udt_schema",
            "udt_name",
            "nullable",
            "default",
            "char_length",
            "numeric_precision",
            "numeric_scale",
            "datetime_precision",
            "identity",
            "identity_generation",
            "generated",
            "generation_expression",
        ),
        "constraints": (
            "schema",
            "table",
            "constraint",
            "type",
            "deferrable",
            "deferred",
            "validated",
            "definition",
        ),
        "indexes": ("schema", "table", "index", "definition"),
        "views": ("schema", "relation", "kind", "populated", "definition"),
        "routines": (
            "schema",
            "routine",
            "arguments",
            "result",
            "kind",
            "volatility",
            "security_definer",
            "definition",
        ),
        "triggers": ("schema", "table", "trigger", "definition"),
        "policies": (
            "schema",
            "table",
            "policy",
            "command",
            "permissive",
            "using",
            "check",
            "roles",
        ),
        "types": (
            "schema",
            "type",
            "kind",
            "definition",
            "not_null",
            "default",
            "labels",
        ),
    }
    summaries = []
    for category, field_names in fields.items():

        def row_key(
            row: tuple[Any, ...], *, category_name: str = category
        ) -> tuple[Any, ...]:
            if category_name == "columns":
                return row[0], row[1], row[3]
            if category_name in {"views", "types"}:
                return tuple(row[:2])
            return tuple(row[:3])

        expected_rows = {row_key(row): row for row in expected[category]}
        actual_rows = {row_key(row): row for row in actual[category]}
        changed_keys = sorted(
            key
            for key in expected_rows.keys() | actual_rows.keys()
            if expected_rows.get(key) != actual_rows.get(key)
        )
        if changed_keys:
            details = []
            for key in changed_keys[:5]:
                expected_row = expected_rows.get(key)
                actual_row = actual_rows.get(key)
                name = ".".join(str(part) for part in key)
                if expected_row is None:
                    details.append(f"{name}:added")
                elif actual_row is None:
                    details.append(f"{name}:missing")
                else:
                    changed_fields = [
                        field_names[index]
                        for index, (left, right) in enumerate(
                            zip(expected_row, actual_row)
                        )
                        if left != right
                    ]
                    detail = f"{name}:fields={'/'.join(changed_fields) or 'none'}"
                    if category == "columns" and expected_row[2] != actual_row[2]:
                        detail += f":position={expected_row[2]}->{actual_row[2]}"
                    details.append(detail)
            summaries.append(f"{category}[{len(changed_keys)}:{'|'.join(details)}]")
    return ",".join(summaries) or "unclassified"


def _schema_definition_detail_summary(
    expected: dict[str, list[tuple[Any, ...]]],
    actual: dict[str, list[tuple[Any, ...]]],
) -> str:
    details = []
    for category, definition_index in (("constraints", 7), ("indexes", 3)):
        expected_rows = {tuple(row[:3]): row for row in expected[category]}
        actual_rows = {tuple(row[:3]): row for row in actual[category]}
        differing = sorted(
            key
            for key in expected_rows.keys() | actual_rows.keys()
            if expected_rows.get(key) != actual_rows.get(key)
        )
        for key in differing[:2]:
            left = expected_rows.get(key)
            right = actual_rows.get(key)
            label = ".".join(str(part) for part in key)
            if left is None or right is None:
                details.append(f"{category}:{label}:missing_or_added")
                continue
            left_definition = str(left[definition_index])
            right_definition = str(right[definition_index])
            left_safe = re.sub(r"'(?:[^']|'')*'", "'[literal]'", left_definition)[:180]
            right_safe = re.sub(r"'(?:[^']|'')*'", "'[literal]'", right_definition)[
                :180
            ]
            details.append(
                f"{category}:{label}:source={left_safe}:restored={right_safe}"
            )
    return "|".join(details) or "no_constraint_or_index_detail"


def _schema_difference_summary(expected: bytes, actual: bytes) -> str:
    changed = [
        line[2:].strip()
        for line in difflib.ndiff(
            expected.decode("utf-8").splitlines(), actual.decode("utf-8").splitlines()
        )
        if line.startswith(("+ ", "- "))
    ]
    objects: set[str] = set()
    pattern = re.compile(
        r"^(CREATE TABLE|ALTER TABLE(?: ONLY)?|CREATE (?:UNIQUE )?INDEX|"
        r"CREATE (?:MATERIALIZED )?VIEW|CREATE (?:OR REPLACE )?FUNCTION|"
        r"CREATE TYPE|CREATE SCHEMA|CREATE EXTENSION|ALTER SEQUENCE)\s+([^\s(]+)",
        re.IGNORECASE,
    )
    for line in changed:
        match = pattern.match(line)
        if match:
            objects.add(f"{match.group(1).upper()}:{match.group(2)}")
        else:
            objects.add(line.split(maxsplit=1)[0].upper() if line else "EMPTY")
    return ",".join(sorted(objects)[:16]) or "unclassified"


def _psql(
    container: str, database: str, statement: str, *, check: bool = True
) -> bytes:
    result = _docker(
        "exec",
        container,
        "psql",
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        "postgres",
        "-d",
        database,
        "-At",
        "-c",
        statement,
        check=check,
    )
    return result.stdout


def _create_roles(engine: Engine, roles: tuple[str, str, str]) -> None:
    _, reader, member = roles
    with engine.begin() as connection:
        for role in roles:
            connection.exec_driver_sql(f'CREATE ROLE "{role}" NOLOGIN INHERIT')
        connection.exec_driver_sql(f'GRANT "{reader}" TO "{member}"')


def _migration_environment(
    database_url: str, synthetic_totp_key: str
) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in (
            "COMSPEC",
            "HOMEDRIVE",
            "HOMEPATH",
            "PATHEXT",
            "PATH",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "WINDIR",
        )
        if key in os.environ
    }
    environment.update(
        {
            "APP_ENV": "development",
            "DATABASE_URL": database_url,
            "ADMIN_TOTP_SECRET_ENV": "development",
            "ADMIN_TOTP_ACTIVE_KEY_ID": "proof-only",
            "ADMIN_TOTP_KEYS": json.dumps(
                {"proof-only": synthetic_totp_key}, separators=(",", ":")
            ),
        }
    )
    return environment


def _upgrade_to(
    database_url: str,
    revision: str,
    synthetic_totp_key: str,
    secrets_to_redact: tuple[str, ...],
) -> None:
    try:
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=BACKEND,
            env=_migration_environment(database_url, synthetic_totp_key),
            capture_output=True,
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProofFailure("alembic_upgrade_unavailable_or_timed_out") from exc
    if migration.returncode:
        raise ProofFailure(
            f"alembic_upgrade_failed:{revision}\n"
            + _safe_error_tail(migration.stderr, secrets_to_redact)
        )


def _insert_synthetic_admin(
    connection: sa.engine.Connection, admin_id: uuid.UUID, proof_id: str
) -> None:
    connection.execute(
        sa.text(
            """INSERT INTO admin_user
                   (id, email, password_hash, email_verified,
                    totp_secret_envelope, totp_last_used_step)
                 VALUES (:id, :email, 'synthetic-no-login', true, NULL, NULL)"""
        ),
        {"id": admin_id, "email": f"proof-{proof_id}-{admin_id.hex[:8]}@example.test"},
    )


def _seed_persistent_owner(engine: Engine, proof_id: str) -> uuid.UUID:
    with engine.connect() as connection:
        tenants = list(connection.scalars(sa.text("SELECT id FROM tenant ORDER BY id")))
    _expect_equal("pre_wallet_tenant_count", 1, len(tenants))
    tenant_id = tenants[0]
    admin_id = uuid.uuid4()
    with engine.begin() as connection:
        _insert_synthetic_admin(connection, admin_id, proof_id)
        connection.execute(
            sa.text(
                """INSERT INTO tenant_admin (id, tenant_id, admin_user_id, active, created_at)
                     VALUES (:id, :tenant, :admin, true, now())"""
            ),
            {"id": uuid.uuid4(), "tenant": tenant_id, "admin": admin_id},
        )
        connection.execute(
            sa.text(
                """INSERT INTO platform_owner
                       (singleton, admin_user_id, authorization_reference, established_at)
                     VALUES (1, :admin, 'synthetic-global-backup-proof', now())"""
            ),
            {"admin": admin_id},
        )
    return tenant_id


def _seed_second_tenant(engine: Engine, proof_id: str) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO tenant (id, status, created_at) VALUES (:id, 'active', now())"
            ),
            {"id": tenant_id},
        )
        _insert_synthetic_admin(connection, admin_id, proof_id)
        connection.execute(
            sa.text(
                """INSERT INTO tenant_admin (id, tenant_id, admin_user_id, active, created_at)
                     VALUES (:id, :tenant, :admin, true, now())"""
            ),
            {"id": uuid.uuid4(), "tenant": tenant_id, "admin": admin_id},
        )
        connection.execute(
            sa.text("INSERT INTO tenant_credit_wallet (tenant_id) VALUES (:tenant)"),
            {"tenant": tenant_id},
        )
    return tenant_id


def _wait_for_server(container: str, database: str) -> None:
    for _ in range(90):
        result = _docker(
            "exec",
            container,
            "pg_isready",
            "-q",
            "-U",
            "postgres",
            "-d",
            database,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise ProofFailure("synthetic_postgresql_not_ready")


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _start_postgres(
    *,
    name: str,
    network: str,
    database: str,
    port: int,
    password: str,
    proof_id: str,
) -> str:
    process_env = {**os.environ, "POSTGRES_PASSWORD": password}
    result = _docker(
        "run",
        "--detach",
        "--pull=never",
        "--name",
        name,
        "--label",
        f"{PROOF_LABEL}={proof_id}",
        "--network",
        network,
        "--publish",
        f"127.0.0.1:{port}:5432",
        "--tmpfs",
        "/var/lib/postgresql/data:rw,noexec,nosuid,size=2g",
        "--memory=768m",
        "--cpus=1",
        "--shm-size=64m",
        "--env",
        "POSTGRES_USER=postgres",
        "--env",
        "POSTGRES_PASSWORD",
        "--env",
        f"POSTGRES_DB={database}",
        IMAGE,
        env=process_env,
    )
    return _lines(result)[0]


def _assert_ephemeral_storage(container_id: str) -> None:
    result = _docker(
        "inspect",
        "--format",
        "{{json .HostConfig.Tmpfs}}|{{json .Mounts}}",
        container_id,
    )
    try:
        tmpfs_json, mounts_json = _lines(result)[0].split("|", maxsplit=1)
        tmpfs = json.loads(tmpfs_json)
        mounts = json.loads(mounts_json)
    except (IndexError, json.JSONDecodeError) as exc:
        raise ProofFailure("synthetic_storage_inspection_failed") from exc
    if tmpfs != {"/var/lib/postgresql/data": "rw,noexec,nosuid,size=2g"} or mounts:
        raise ProofFailure("synthetic_storage_not_ephemeral")


def _seed_source(
    engine: Engine,
    tenant_ids: list[uuid.UUID],
    roles: tuple[str, str, str],
) -> str:
    owner, reader, _member = roles
    with engine.begin() as connection:
        available = connection.execute(
            sa.text(
                "SELECT default_version FROM pg_available_extensions WHERE name = 'pgcrypto'"
            )
        ).scalar_one_or_none()
        if not available:
            raise ProofFailure("synthetic_extension_unavailable")
        existing_tenants = list(
            connection.scalars(sa.text("SELECT id FROM tenant ORDER BY id"))
        )
        _expect_equal("synthetic_tenants", sorted(tenant_ids), sorted(existing_tenants))
        connection.exec_driver_sql("CREATE EXTENSION pgcrypto")
        connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{owner}"')
        connection.exec_driver_sql(
            f'GRANT REFERENCES ON TABLE public.tenant TO "{owner}"'
        )
        connection.exec_driver_sql(
            f'CREATE SCHEMA proof_fixture AUTHORIZATION "{owner}"'
        )
        connection.exec_driver_sql(f'SET ROLE "{owner}"')
        connection.exec_driver_sql(
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA proof_fixture GRANT SELECT ON TABLES TO "{reader}"'
        )
        connection.exec_driver_sql(
            "CREATE TYPE proof_fixture.proof_state AS ENUM ('queued', 'verified')"
        )
        connection.exec_driver_sql(
            """CREATE TABLE proof_fixture.tenant_record (
                   id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                   tenant_id uuid NOT NULL REFERENCES public.tenant(id),
                   state proof_fixture.proof_state NOT NULL,
                   payload jsonb NOT NULL,
                   payload_sha256 bytea NOT NULL,
                   updated_at timestamptz NOT NULL DEFAULT now()
               )"""
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_proof_record_tenant_state ON proof_fixture.tenant_record (tenant_id, state)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE proof_fixture.tenant_record ENABLE ROW LEVEL SECURITY"
        )
        connection.exec_driver_sql(
            """CREATE POLICY proof_tenant_policy ON proof_fixture.tenant_record
                 USING (tenant_id = NULLIF(current_setting('pyp.proof_tenant_id', true), '')::uuid)"""
        )
        connection.exec_driver_sql(
            """CREATE VIEW proof_fixture.tenant_counts AS
                 SELECT tenant_id, count(*) AS record_count
                   FROM proof_fixture.tenant_record GROUP BY tenant_id"""
        )
        connection.exec_driver_sql(
            """CREATE MATERIALIZED VIEW proof_fixture.tenant_snapshot AS
                 SELECT tenant_id, count(*) AS record_count
                   FROM proof_fixture.tenant_record GROUP BY tenant_id"""
        )
        connection.exec_driver_sql(
            """CREATE FUNCTION proof_fixture.count_for_tenant(p_tenant uuid)
                 RETURNS bigint LANGUAGE sql STABLE AS $$
                 SELECT count(*) FROM proof_fixture.tenant_record WHERE tenant_id = p_tenant
                 $$"""
        )
        connection.exec_driver_sql(
            """CREATE FUNCTION proof_fixture.touch_record() RETURNS trigger
                 LANGUAGE plpgsql AS $$
                 BEGIN NEW.updated_at := now(); RETURN NEW; END $$"""
        )
        connection.exec_driver_sql(
            """CREATE TRIGGER proof_touch_record BEFORE UPDATE
                 ON proof_fixture.tenant_record FOR EACH ROW
                 EXECUTE FUNCTION proof_fixture.touch_record()"""
        )
        for tenant_index, tenant_id in enumerate(tenant_ids, start=1):
            for row_index in range(2):
                payload = json.dumps(
                    {"proof": f"tenant-{tenant_index}", "record": row_index + 1},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                connection.execute(
                    sa.text(
                        """INSERT INTO proof_fixture.tenant_record
                               (tenant_id, state, payload, payload_sha256)
                           VALUES (
                               :tenant_id, 'verified', CAST(:payload AS jsonb),
                               digest(convert_to(CAST(:payload AS jsonb)::text, 'UTF8'), 'sha256')
                           )"""
                    ),
                    {"tenant_id": tenant_id, "payload": payload},
                )
        connection.exec_driver_sql(
            "REFRESH MATERIALIZED VIEW proof_fixture.tenant_snapshot"
        )
        connection.exec_driver_sql("RESET ROLE")
        connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA proof_fixture TO "{reader}"')
        connection.exec_driver_sql(
            f'GRANT SELECT ON ALL TABLES IN SCHEMA proof_fixture TO "{reader}"'
        )
    return str(available)


def _seed_runner_canary(engine: Engine, tenant_id: uuid.UUID, proof_id: str) -> str:
    marker = f"PYP-RESTIC-SYNTHETIC-CANARY-{proof_id}"
    payload = json.dumps({"canary": marker}, separators=(",", ":"))
    with engine.begin() as connection:
        inserted = connection.execute(
            sa.text(
                """INSERT INTO proof_fixture.tenant_record
                       (tenant_id, state, payload, payload_sha256)
                   VALUES (
                       :tenant_id, 'verified', CAST(:payload AS jsonb),
                       digest(convert_to(CAST(:payload AS jsonb)::text, 'UTF8'), 'sha256')
                   )"""
            ),
            {"tenant_id": tenant_id, "payload": payload},
        )
        connection.exec_driver_sql(
            "REFRESH MATERIALIZED VIEW proof_fixture.tenant_snapshot"
        )
    if inserted.rowcount != 1:
        raise ProofFailure("runner_canary_seed_failed")
    return marker


def _seed_large_object(engine: Engine) -> None:
    payload = b"synthetic global PostgreSQL large object proof"
    with engine.begin() as connection:
        oid = int(connection.execute(sa.text("SELECT lo_create(0)")).scalar_one())
        connection.execute(
            sa.text("SELECT lo_put(:oid, 0, :payload)"),
            {"oid": oid, "payload": payload},
        )


def _fixture_uuid(proof_id: str, tenant_id: uuid.UUID, label: str) -> uuid.UUID:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"pyp-synthetic-proof:{proof_id}")
    return uuid.uuid5(namespace, f"{tenant_id}:{label}")


def _global_backup_receipt_fixture(
    proof_id: str, tenant_id: uuid.UUID, observed_at: datetime
) -> tuple[dict[str, Any], ...]:
    return (
        {
            "id": _fixture_uuid(proof_id, tenant_id, "backup-receipt-validated"),
            "scheduled_day": observed_at.date(),
            "status": "validated",
            "started_at": observed_at - timedelta(minutes=2),
            "finished_at": observed_at - timedelta(minutes=1),
            "snapshot_id": "a" * 32,
            "dump_size_bytes": 4096,
            "duration_ms": 60_000,
            "verified": True,
            "error_code": None,
        },
        {
            "id": _fixture_uuid(proof_id, tenant_id, "backup-receipt-unknown"),
            "scheduled_day": observed_at.date() - timedelta(days=1),
            "status": "unknown",
            "started_at": observed_at - timedelta(days=1, minutes=2),
            "finished_at": None,
            "snapshot_id": None,
            "dump_size_bytes": None,
            "duration_ms": None,
            "verified": False,
            "error_code": "synthetic_readback_uncertain",
        },
    )


def _legacy_payment_without_provider_issue_fixture(
    proof_id: str,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    observed_at: datetime,
    *,
    total_cents: int,
) -> dict[str, Any]:
    """Representa somente uma tentativa sintética encerrada antes do provider."""
    return {
        "id": _fixture_uuid(proof_id, tenant_id, "payment-failed-before-issue"),
        "tenant_id": tenant_id,
        "client_id": client_id,
        "provider": "infinitepay",
        "checkout_key": f"synthetic-before-issue-{proof_id[:32]}-{tenant_id.hex[:8]}",
        "cart_revision": _sha256(f"synthetic-cart:{proof_id}:{tenant_id}".encode()),
        "total_cents": total_cents,
        "handle_snapshot": "synthetic-disabled-provider",
        "checkout_methods_snapshot": ["credit_card"],
        "capture_method": None,
        "cart_dismissed_at": None,
        "configuration_version": 1,
        "verification_profile": "synthetic-before-issue",
        "state": "failed_before_issue",
        "revision_number": 0,
        "provider_transaction_nsu": None,
        "confirmed_at": None,
        "created_at": observed_at,
        "updated_at": observed_at,
    }


def _completed_asset_file_cleanup_fixture(
    proof_id: str,
    tenant_id: uuid.UUID,
    observed_at: datetime,
) -> dict[str, Any]:
    """Preserva um recibo terminal com caminho sintético confinado ao tenant."""
    return {
        "id": _fixture_uuid(proof_id, tenant_id, "completed-asset-file-cleanup"),
        "tenant_id": tenant_id,
        "paths": [
            {
                "root": "source",
                "path": f"tenants/{tenant_id}/synthetic-proof/{proof_id}/removed.jpg",
            }
        ],
        "status": "completed",
        "attempts": 1,
        "last_error": None,
        "created_at": observed_at,
        "completed_at": observed_at,
    }


def _fixture_row_summary(
    populated: dict[str, dict[str, int]],
) -> dict[str, dict[str, Any]]:
    return {
        table_name: {
            "tenants_with_rows": len(tenant_counts),
            "rows_per_tenant": sorted(tenant_counts.values()),
            "total_rows": sum(tenant_counts.values()),
        }
        for table_name, tenant_counts in populated.items()
    }


def _seed_application_fixture(
    engine: Engine, tenant_ids: list[uuid.UUID], proof_id: str
) -> dict[str, Any]:
    """Popula relações de produto com dados artificiais, sem iniciar workers."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=1)
    folder_expires_at = now + timedelta(days=30)
    domains = APPLICATION_FIXTURE_DOMAINS
    metadata = sa.MetaData()
    populated: dict[str, dict[str, int]] = {
        name: {} for tables in domains.values() for name in tables
    }

    def insert(
        connection: sa.engine.Connection, table_name: str, values: dict[str, Any]
    ) -> None:
        table = sa.Table(table_name, metadata, autoload_with=connection)
        if set(values) - set(table.c.keys()):
            raise ProofFailure("synthetic_fixture_mapping_invalid")
        missing_required = [
            column.name
            for column in table.columns
            if not column.nullable
            and column.name not in values
            and column.server_default is None
            and column.identity is None
        ]
        if missing_required:
            raise ProofFailure(
                f"synthetic_fixture_missing_required_column:{table_name}:"
                + ",".join(missing_required)
            )
        try:
            connection.execute(sa.insert(table).values(**values))
        except sa.exc.SQLAlchemyError as exc:
            original = getattr(exc, "orig", None)
            sqlstate = getattr(original, "sqlstate", None)
            if not isinstance(sqlstate, str) or not re.fullmatch(
                r"[0-9A-Z]{5}", sqlstate
            ):
                sqlstate = "unknown"
            diagnostic = getattr(original, "diag", None)
            constraint = getattr(diagnostic, "constraint_name", None)
            if not isinstance(constraint, str) or not re.fullmatch(
                r"[a-z][a-z0-9_]{0,62}", constraint
            ):
                constraint = "unknown"
            raise ProofFailure(
                f"synthetic_fixture_insert_failed:{table_name}:{sqlstate}:{constraint}"
            ) from None

    with engine.begin() as connection:
        owner_admin_id = uuid.UUID(
            str(
                connection.execute(
                    sa.text(
                        "SELECT admin_user_id FROM platform_owner WHERE singleton = 1"
                    )
                ).scalar_one()
            )
        )
        insert(
            connection,
            "photographer_credit_package",
            {
                "id": _fixture_uuid(proof_id, tenant_ids[0], "credit-package"),
                "name": "Synthetic backup proof package",
                "description": "Inactive package used only by the local proof.",
                "credit_quantity": 10,
                "price_cents": None,
                "currency_code": None,
                "active": False,
                "created_by_admin_id": owner_admin_id,
                "updated_by_admin_id": owner_admin_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        for receipt in _global_backup_receipt_fixture(proof_id, tenant_ids[0], now):
            insert(connection, "global_postgresql_backup_run", receipt)

        for tenant_index, tenant_id in enumerate(tenant_ids, start=1):
            admin_id = uuid.UUID(
                str(
                    connection.execute(
                        sa.text(
                            "SELECT admin_user_id FROM tenant_admin WHERE tenant_id = :tenant "
                            "AND active ORDER BY created_at LIMIT 1"
                        ),
                        {"tenant": tenant_id},
                    ).scalar_one()
                )
            )
            wallet_table = sa.Table(
                "tenant_credit_wallet", metadata, autoload_with=connection
            )
            wallet_mode = connection.execute(
                sa.select(wallet_table.c.mode).where(
                    wallet_table.c.tenant_id == tenant_id
                )
            ).scalar_one_or_none()
            expected_wallet_mode = (
                "unmetered" if tenant_id == tenant_ids[0] else "finite"
            )
            if wallet_mode is None:
                insert(
                    connection,
                    "tenant_credit_wallet",
                    {
                        "tenant_id": tenant_id,
                        "mode": expected_wallet_mode,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            elif wallet_mode != expected_wallet_mode:
                raise ProofFailure("synthetic_fixture_wallet_mode_unexpected")
            insert(
                connection,
                "photographer_business_profile",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "business-profile"),
                    "admin_user_id": admin_id,
                    "tenant_id": tenant_id,
                    "full_name": f"Synthetic Photographer {tenant_index}",
                    "cpf_envelope": None,
                    "cpf_fingerprint": None,
                    "cpf_fingerprint_key_version": None,
                    "address_envelope": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            ids = {
                name: _fixture_uuid(proof_id, tenant_id, name)
                for name in (
                    "client",
                    "gallery",
                    "folder",
                    "photo",
                    "revoked-gallery-capability",
                    "disabled-payment-preferences",
                    "branding-settings",
                    "progressive-pricing-preset",
                    "progressive-pricing-tier-1",
                    "progressive-pricing-tier-2",
                    "derived-gallery",
                    "derived-gallery-membership",
                    "derived-gallery-photo",
                    "derived-gallery-photo-origin",
                    "private-upload-batch",
                    "private-gallery-notification",
                    "gallery-lifecycle-operation",
                    "payment-group",
                    "order",
                    "archive-cycle",
                    "archive-operation",
                    "archive-recovery-operation",
                    "archive-recovery-request",
                    "archive-recovery-credit-reservation",
                    "archive-object",
                    "facial-policy",
                    "facial-request",
                    "credit-entry",
                    "notification-event",
                    "notification-delivery",
                )
            }
            phone = f"+155555501{tenant_index:02d}"
            photo_bytes = b"synthetic archived jpeg fixture"
            photo_sha256 = _sha256(photo_bytes)
            storage_key = f"synthetic-proof/{proof_id}/tenant-{tenant_index}/photo.jpg"

            insert(
                connection,
                "client",
                {
                    "id": ids["client"],
                    "tenant_id": tenant_id,
                    "full_name": f"Synthetic Client {tenant_index}",
                    "phone_e164": phone,
                },
            )
            insert(
                connection,
                "client_phone",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "client-phone"),
                    "tenant_id": tenant_id,
                    "client_id": ids["client"],
                    "phone_e164": phone,
                    "active": True,
                    "verified_at": now,
                    "created_at": now,
                    "retired_at": None,
                },
            )
            insert(
                connection,
                "provider_payment",
                _legacy_payment_without_provider_issue_fixture(
                    proof_id,
                    tenant_id,
                    ids["client"],
                    now,
                    total_cents=500,
                ),
            )
            insert(
                connection,
                "asset_file_cleanup",
                _completed_asset_file_cleanup_fixture(proof_id, tenant_id, now),
            )
            gallery_name = f"Synthetic Gallery {tenant_index}"
            insert(
                connection,
                "parent_gallery",
                {
                    "id": ids["gallery"],
                    "tenant_id": tenant_id,
                    "name": gallery_name,
                    "event_name": "Local backup proof",
                    "description": "Synthetic fixture.",
                    "selection_duration_days": 1,
                    "payment_required": True,
                    "favorites_enabled": True,
                    "comments_enabled": True,
                    "pricing_mode": "fixed",
                    "fixed_unit_price_cents": 500,
                    "pricing_snapshot": {"currency": "BRL"},
                    "pricing_review_required": False,
                    "active": True,
                    "lifecycle_status": "active",
                    "access_mode": "standard",
                    "created_at": now,
                },
            )
            folder_name = f"Synthetic folder {tenant_index}"
            insert(
                connection,
                "photo_folder",
                {
                    "id": ids["folder"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": None,
                    "name": folder_name,
                    "status": "released",
                    "purpose": "content",
                    "audience_scope": "selected",
                    "position": 1,
                    "released_at": now,
                    "access_duration_days": 30,
                    "access_expires_at": folder_expires_at,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "gallery_preview_settings",
                {
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "enabled": False,
                    "generation": 1,
                    "strength": 50 + tenant_index,
                    "exposure_tenths": 0,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "folder_processing_settings",
                {
                    "tenant_id": tenant_id,
                    "folder_id": ids["folder"],
                    "preview_mode": "off",
                    "facial_mode": "off",
                    "preview_strength": 50 + tenant_index,
                    "preview_exposure_tenths": 0,
                    "revision": 1,
                    "updated_at": now,
                },
            )
            legacy_preview_settings = sa.Table(
                "preview_adjustment_settings", metadata, autoload_with=connection
            )
            existing_preview_settings = (
                connection.execute(
                    sa.select(
                        legacy_preview_settings.c.id,
                        legacy_preview_settings.c.enabled,
                        legacy_preview_settings.c.generation,
                        legacy_preview_settings.c.strength,
                    ).where(legacy_preview_settings.c.tenant_id == tenant_id)
                )
                .mappings()
                .one_or_none()
            )
            if existing_preview_settings is None:
                insert(
                    connection,
                    "preview_adjustment_settings",
                    {
                        "tenant_id": tenant_id,
                        "id": 1,
                        "enabled": False,
                        "generation": 1,
                        "strength": 50,
                        "updated_at": now,
                    },
                )
            elif (
                existing_preview_settings["id"] != 1
                or existing_preview_settings["enabled"] is not False
                or type(existing_preview_settings["generation"]) is not int
                or existing_preview_settings["generation"] < 1
                or type(existing_preview_settings["strength"]) is not int
                or not 10 <= existing_preview_settings["strength"] <= 100
            ):
                raise ProofFailure(
                    "synthetic_fixture_legacy_preview_settings_not_inert"
                )
            filename = f"proof-{tenant_index}.jpg"
            insert(
                connection,
                "photo_asset",
                {
                    "id": ids["photo"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": None,
                    "folder_id": ids["folder"],
                    "filename": filename,
                    "display_name": f"Synthetic photo {tenant_index}",
                    "storage_key": storage_key,
                    "available": True,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "derived_gallery",
                {
                    "id": ids["derived-gallery"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "name": f"Synthetic private gallery {tenant_index}",
                    "custom_message": None,
                    "selection_expires_at": expires_at,
                    "access_enabled": True,
                    "favorites_enabled": True,
                    "comments_enabled": False,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "gallery_access_capability",
                {
                    "id": ids["revoked-gallery-capability"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": ids["derived-gallery"],
                    "client_id": None,
                    "scope": "private_gallery_link",
                    "token_hash": _sha256(
                        f"synthetic-revoked-gallery-link:{proof_id}:{tenant_index}".encode()
                    ),
                    "token_mode": "legacy_random",
                    "token_version": 1,
                    "status": "revoked",
                    "expires_at": None,
                    "last_used_at": None,
                    "consumed_at": None,
                    "revoked_at": now,
                    "rotated_from_id": None,
                    "actor_admin_id": admin_id,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "payment_preferences",
                {
                    "id": ids["disabled-payment-preferences"],
                    "tenant_id": tenant_id,
                    "account_id": None,
                    "version": 0,
                    "pix_enabled": False,
                    "mercadopago_enabled": False,
                },
            )
            insert(
                connection,
                "branding_settings",
                {
                    "id": ids["branding-settings"],
                    "tenant_id": tenant_id,
                    "login_title": "Galeria sintética",
                    "login_intro": "Acesso de prova sem dados reais.",
                    "login_helper": "Fixture isolada.",
                    "logo_key": None,
                    "app_icon_key": None,
                    "favicon_key": None,
                    "watermark_text": "Prévia sintética",
                    "watermark_font": "sans-serif",
                    "watermark_color": "#FFFFFF",
                    "watermark_size": 24,
                    "watermark_direction": "diagonal",
                    "watermark_opacity": 42,
                    "watermark_position": "middle-center",
                    "watermark_shadow": True,
                    "watermark_security_lines": False,
                    "updated_at": now,
                },
            )
            preset_id = ids["progressive-pricing-preset"]
            insert(
                connection,
                "progressive_pricing_preset",
                {
                    "id": preset_id,
                    "tenant_id": tenant_id,
                    "code": f"synthetic-proof-v1-{tenant_index}",
                    "name": "Tarifa sintética inativa",
                    "version": 1,
                    "active": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            for tier_index, (minimum, maximum, unit_price_cents) in enumerate(
                ((1, 10, 125), (11, None, 100)), start=1
            ):
                insert(
                    connection,
                    "progressive_pricing_tier",
                    {
                        "id": ids[f"progressive-pricing-tier-{tier_index}"],
                        "tenant_id": tenant_id,
                        "preset_id": preset_id,
                        "minimum_quantity": minimum,
                        "maximum_quantity": maximum,
                        "unit_price_cents": unit_price_cents,
                        "created_at": now,
                    },
                )
            insert(
                connection,
                "derived_gallery_membership",
                {
                    "tenant_id": tenant_id,
                    "id": ids["derived-gallery-membership"],
                    "derived_gallery_id": ids["derived-gallery"],
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "status": "active",
                    "blocked_at": None,
                    "unlinked_at": None,
                    "actor_admin_id": admin_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "derived_gallery_photo",
                {
                    "tenant_id": tenant_id,
                    "id": ids["derived-gallery-photo"],
                    "derived_gallery_id": ids["derived-gallery"],
                    "photo_asset_id": ids["photo"],
                    "origin": "admin",
                    "created_at": now,
                },
            )
            insert(
                connection,
                "derived_gallery_photo_origin",
                {
                    "tenant_id": tenant_id,
                    "id": ids["derived-gallery-photo-origin"],
                    "derived_gallery_photo_id": ids["derived-gallery-photo"],
                    "origin": "admin",
                    "created_at": now,
                },
            )
            insert(
                connection,
                "private_upload_batch",
                {
                    "tenant_id": tenant_id,
                    "id": ids["private-upload-batch"],
                    "derived_gallery_id": ids["derived-gallery"],
                    "parent_gallery_id": None,
                    "folder_id": None,
                    "actor_admin_id": admin_id,
                    "status": "closed",
                    "recipient_ids": [str(ids["client"])],
                    "created_at": now,
                    "closed_at": now,
                    "announced_at": None,
                },
            )
            insert(
                connection,
                "private_upload_batch_asset",
                {
                    "tenant_id": tenant_id,
                    "batch_id": ids["private-upload-batch"],
                    "photo_asset_id": ids["photo"],
                },
            )
            insert(
                connection,
                "gallery_membership_notification_outbox",
                {
                    "tenant_id": tenant_id,
                    "id": ids["private-gallery-notification"],
                    "event_key": (
                        f"synthetic-private-gallery-created-{proof_id}-{tenant_index}"
                    ),
                    "event_type": "private_created",
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": ids["derived-gallery"],
                    "client_id": ids["client"],
                    "parent_name_snapshot": f"Synthetic gallery {tenant_index}",
                    "derived_name_snapshot": f"Synthetic private gallery {tenant_index}",
                    "client_name_snapshot": f"Synthetic Client {tenant_index}",
                    "admin_status": "read",
                    "external_status": "skipped",
                    "attempts": 0,
                    "last_error": None,
                    "next_attempt_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "parent_gallery_registration",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "gallery-registration"),
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "gallery_client_state",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "gallery-client-state"),
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "status": "active",
                    "selection_started_at": now,
                    "selection_expires_at": expires_at,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "notification_milestone",
                {
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "kind": "first_access",
                    "baseline": tenant_index == 0,
                    "created_at": now,
                },
            )
            reopening_request_id = _fixture_uuid(
                proof_id, tenant_id, "gallery-reopening-request"
            )
            insert(
                connection,
                "gallery_reopening_request",
                {
                    "id": reopening_request_id,
                    "tenant_id": tenant_id,
                    "derived_gallery_id": None,
                    "parent_gallery_id": ids["gallery"],
                    "photo_folder_id": None,
                    "requested_by_client_id": ids["client"],
                    "idempotency_key": f"synthetic-reopen-{proof_id}-{tenant_index}",
                    "status": "refused",
                    "decided_by_admin_id": admin_id,
                    "decided_at": now,
                    "approved_until": None,
                    "approved_duration_days": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "gallery_reopening_notification_outbox",
                {
                    "id": _fixture_uuid(
                        proof_id, tenant_id, "gallery-reopening-notification"
                    ),
                    "tenant_id": tenant_id,
                    "gallery_reopening_request_id": reopening_request_id,
                    "recipient_phone": None,
                    "status": "skipped",
                    "attempts": 0,
                    "last_error": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "gallery_access",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "gallery-access"),
                    "tenant_id": tenant_id,
                    "client_id": ids["client"],
                    "gallery_id": ids["gallery"],
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": None,
                    "active": True,
                },
            )
            insert(
                connection,
                "folder_client_grant",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "folder-client-grant"),
                    "tenant_id": tenant_id,
                    "folder_id": ids["folder"],
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "created_at": now,
                },
            )
            insert(
                connection,
                "gallery_lifecycle_operation",
                {
                    "id": ids["gallery-lifecycle-operation"],
                    "tenant_id": tenant_id,
                    "operation_type": "delete_parent_gallery",
                    "target_parent_gallery_id": ids["gallery"],
                    "target_client_id": None,
                    "actor_admin_id": admin_id,
                    "idempotency_key": (
                        f"synthetic-proof:{proof_id}:{tenant_index}:cancelled-lifecycle"
                    ),
                    "status": "cancelled",
                    "manifest": {
                        "fixture": "synthetic-only",
                        "external_actions": False,
                    },
                    "last_error": None,
                    "attempts": 0,
                    "lease_token": None,
                    "lease_expires_at": None,
                    "destructive_started_at": None,
                    "completed_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            for table_name in ("photo_selection", "photo_favorite", "photo_view"):
                values: dict[str, Any] = {
                    "id": _fixture_uuid(proof_id, tenant_id, table_name),
                    "tenant_id": tenant_id,
                    "derived_gallery_id": None,
                    "parent_gallery_id": ids["gallery"],
                    "photo_asset_id": ids["photo"],
                    "client_id": ids["client"],
                }
                values.update(
                    {"first_viewed_at": now, "last_viewed_at": now}
                    if table_name == "photo_view"
                    else {"created_at": now}
                )
                insert(connection, table_name, values)
            insert(
                connection,
                "photo_comment",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "photo-comment"),
                    "tenant_id": tenant_id,
                    "derived_gallery_id": None,
                    "parent_gallery_id": ids["gallery"],
                    "photo_asset_id": ids["photo"],
                    "client_id": ids["client"],
                    "body": "Synthetic comment.",
                    "created_at": now,
                    "removed_at": None,
                },
            )
            insert(
                connection,
                "price_rule",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "price-rule"),
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "minimum_quantity": 1,
                    "maximum_quantity": None,
                    "unit_price_cents": 500,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "payment_group",
                {
                    "id": ids["payment-group"],
                    "tenant_id": tenant_id,
                    "client_id": ids["client"],
                    "state": "reported",
                    "revision": f"synthetic-{proof_id}-{tenant_index}",
                    "total_cents": 500,
                    "pix_copy_paste_snapshot": "synthetic-pix-payload-not-payable",
                    "pix_instructions_snapshot": "Local fixture only; no payment was made.",
                    "pix_configuration_snapshot": {"proof": "synthetic-only"},
                    "created_at": now,
                    "reported_at": now,
                },
            )
            insert(
                connection,
                "sale_order",
                {
                    "id": ids["order"],
                    "tenant_id": tenant_id,
                    "derived_gallery_id": None,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "derived_gallery_id_snapshot": None,
                    "derived_gallery_name_snapshot": "",
                    "parent_gallery_id_snapshot": ids["gallery"],
                    "parent_gallery_name_snapshot": gallery_name,
                    "payment_status": "pending",
                    "total_cents": 500,
                    "frozen_at": now,
                    "confirmed_at": None,
                    "client_name_snapshot": f"Synthetic Client {tenant_index}",
                    "client_phone_snapshot": phone,
                    "price_rule_snapshot": {
                        "minimum_quantity": 1,
                        "unit_price_cents": 500,
                    },
                    "payment_required_snapshot": True,
                    "sales_message_snapshot": "Synthetic order only.",
                    "payment_message_snapshot": "No payment was made.",
                    "delivery_album_url": None,
                    "delivery_updated_at": None,
                    "delivery_revision": 0,
                    "pix_copy_paste_snapshot": "synthetic-pix-payload-not-payable",
                    "pix_qr_code_snapshot": None,
                    "pix_instructions_snapshot": "No payment was made.",
                    "pix_configuration_snapshot": {"proof": "synthetic-only"},
                    "pii_minimized_at": None,
                    "checkout_key": None,
                    "assets_removed_at": None,
                    "payment_group_id": ids["payment-group"],
                    "provider_payment_id": None,
                    "mercadopago_payment_id": None,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "sale_order_item",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "sale-order-item"),
                    "tenant_id": tenant_id,
                    "sale_order_id": ids["order"],
                    "photo_asset_id": ids["photo"],
                    "photo_asset_id_snapshot": ids["photo"],
                    "filename_snapshot": filename,
                    "folder_id_snapshot": ids["folder"],
                    "folder_name_snapshot": folder_name,
                    "checksum_sha256_snapshot": photo_sha256,
                    "unit_price_cents": 500,
                },
            )
            insert(
                connection,
                "photo_analysis",
                {
                    "photo_asset_id": ids["photo"],
                    "tenant_id": tenant_id,
                    "source_fingerprint": photo_sha256,
                    "source_bytes": len(photo_bytes),
                    "width": 1200,
                    "height": 800,
                    "pipeline_version": "synthetic-proof-v1",
                    "state": "pending",
                    "expires_at": expires_at,
                    "deleted_at": None,
                    "metrics": {"fixture": "synthetic"},
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_derivative",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "media-derivative"),
                    "tenant_id": tenant_id,
                    "photo_asset_id": ids["photo"],
                    "variant": "thumbnail",
                    "relative_path": None,
                    "status": "queued",
                    "width": None,
                    "height": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_job",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "media-job"),
                    "tenant_id": tenant_id,
                    "photo_asset_id": ids["photo"],
                    "kind": "generate_derivatives",
                    "status": "queued",
                    "attempts": 0,
                    "last_error": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            cycle_id, operation_id, object_id = (
                ids["archive-cycle"],
                ids["archive-operation"],
                ids["archive-object"],
            )
            remote_id = f"synthetic-{proof_id}-{tenant_index}"
            source_ref = f"photo:{ids['photo']}:original"
            manifest = {
                "schema_version": 1,
                "tenant_id": str(tenant_id),
                "parent_gallery_id": str(ids["gallery"]),
                "folder_id": str(ids["folder"]),
                "cycle_id": str(cycle_id),
                "operation_id": str(operation_id),
                "created_at": now.isoformat(timespec="microseconds").replace(
                    "+00:00", "Z"
                ),
                "object_count": 1,
                "total_bytes": len(photo_bytes),
                "objects": [
                    {
                        "object_id": str(object_id),
                        "source_ref": source_ref,
                        "object_type": "source",
                        "mime_type": "image/jpeg",
                        "size_bytes": len(photo_bytes),
                        "sha256": photo_sha256,
                        "remote_object_id": remote_id,
                    }
                ],
            }
            manifest_bytes = json.dumps(
                manifest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            insert(
                connection,
                "media_archive_cycle",
                {
                    "id": cycle_id,
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "folder_id": ids["folder"],
                    "cycle_number": 1,
                    "state": "reconciliation_required",
                    "manifest_version": 1,
                    "manifest": manifest,
                    "manifest_sha256": _sha256(manifest_bytes),
                    "object_count": 1,
                    "total_bytes": len(photo_bytes),
                    "archived_at": now,
                    "next_archive_check_at": None,
                    "last_window_notice_for_expiry": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_archive_notice",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "media-archive-notice"),
                    "tenant_id": tenant_id,
                    "cycle_id": cycle_id,
                    "notice_type": "archive_reconciliation_required",
                    "idempotency_key": f"synthetic-media-notice-{proof_id}-{tenant_index}",
                    "title": "Synthetic archive state",
                    "body": "Synthetic fixture notice; no remote action was sent.",
                    "deadline_at": None,
                    "created_at": now,
                    "read_at": None,
                    "superseded_at": None,
                },
            )
            insert(
                connection,
                "media_archive_operation",
                {
                    "id": operation_id,
                    "tenant_id": tenant_id,
                    "cycle_id": cycle_id,
                    "operation_type": "archive",
                    "status": "completed",
                    "stage": "completed",
                    "idempotency_key": f"synthetic-archive-{proof_id}-{tenant_index}",
                    "actor_type": "system",
                    "actor_admin_id": None,
                    "details": {"fixture": "synthetic-only"},
                    "last_error_code": None,
                    "last_error": None,
                    "attempts": 1,
                    "lease_token": None,
                    "lease_expires_at": None,
                    "started_at": now,
                    "completed_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_archive_space_reservation",
                {
                    "id": _fixture_uuid(
                        proof_id, tenant_id, "released-media-space-reservation"
                    ),
                    "tenant_id": tenant_id,
                    "operation_id": operation_id,
                    "volume_key": _sha256(
                        f"synthetic-volume:{proof_id}:{tenant_index}".encode()
                    ),
                    "reserved_bytes": len(photo_bytes),
                    "status": "released",
                    "created_at": now,
                    "released_at": now,
                },
            )
            insert(
                connection,
                "media_archive_object",
                {
                    "id": object_id,
                    "tenant_id": tenant_id,
                    "cycle_id": cycle_id,
                    "source_ref": source_ref,
                    "object_type": "source",
                    "mime_type": "image/jpeg",
                    "size_bytes": len(photo_bytes),
                    "sha256": photo_sha256,
                    "remote_object_id": remote_id,
                    "remote_deleted_at": None,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "media_archive_event",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "media-archive-event"),
                    "tenant_id": tenant_id,
                    "cycle_id": cycle_id,
                    "operation_id": operation_id,
                    "actor_type": "system",
                    "actor_admin_id": None,
                    "event_type": "archive_completed",
                    "cycle_state_before": "archiving",
                    "cycle_state_after": "archived",
                    "operation_status_before": "processing",
                    "operation_status_after": "completed",
                    "details": {"fixture": "synthetic-only"},
                    "created_at": now,
                },
            )
            insert(
                connection,
                "gallery_facial_policy",
                {
                    "id": ids["facial-policy"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "status": "disabled",
                    "legal_notice_version": "synthetic-notice-v1",
                    "legal_basis_reference": "synthetic-proof-only",
                    "retention_policy_version": "synthetic-retention-v1",
                    "minor_policy_version": "synthetic-minor-policy-v1",
                    "model_version": "synthetic-model-v1",
                    "quality_version": "synthetic-quality-v1",
                    "calibration_version": None,
                    "similarity_threshold_milli": 750,
                    "index_generation": 0,
                    "actor_admin_id": admin_id,
                    "activated_at": None,
                    "suspended_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "facial_search_request",
                {
                    "id": ids["facial-request"],
                    "tenant_id": tenant_id,
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "policy_id": ids["facial-policy"],
                    "status": "cancelled",
                    "reference_region_id": None,
                    "reference_source": "upload",
                    "authorization_method": "explicit_consent",
                    "consent_version": "synthetic-consent-v1",
                    "legal_notice_version": "synthetic-notice-v1",
                    "subject_declaration": "adult",
                    "representation_reference": None,
                    "model_version": "synthetic-model-v1",
                    "search_engine": "opencv-yunet-sface",
                    "quality_version": "synthetic-quality-v1",
                    "index_generation": 0,
                    "snapshot_total": 0,
                    "snapshot_ready": 0,
                    "compare_total": 0,
                    "compare_done": 0,
                    "reference_locator_ciphertext": None,
                    "reference_locator_nonce": None,
                    "reference_key_id": None,
                    "reference_deleted_at": None,
                    "completed_at": now,
                    "expires_at": expires_at,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "facial_search_consent_proof",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "facial-consent-proof"),
                    "tenant_id": tenant_id,
                    "source_search_request_id": ids["facial-request"],
                    "parent_gallery_id": ids["gallery"],
                    "client_id": ids["client"],
                    "authorization_method": "explicit_consent",
                    "consent_version": "synthetic-consent-v1",
                    "legal_notice_version": "synthetic-notice-v1",
                    "subject_declaration": "adult",
                    "recorded_at": now,
                    "created_at": now,
                },
            )
            settings = sa.Table(
                "notification_setting", metadata, autoload_with=connection
            )
            setting_exists = connection.execute(
                sa.select(settings.c.event_type).where(
                    settings.c.tenant_id == tenant_id,
                    settings.c.event_type == "payment_reported",
                )
            ).first()
            if setting_exists is None:
                insert(
                    connection,
                    "notification_setting",
                    {
                        "tenant_id": tenant_id,
                        "event_type": "payment_reported",
                        "whatsapp_enabled": False,
                        "push_enabled": False,
                        "whatsapp_disabled_at": now,
                        "push_disabled_at": now,
                        "whatsapp_body": "Synthetic fixture; delivery disabled.",
                        "push_title": "Synthetic proof",
                        "push_body": "No notification is sent.",
                        "version": 1,
                        "updated_at": now,
                    },
                )
            insert(
                connection,
                "notification_event",
                {
                    "id": ids["notification-event"],
                    "tenant_id": tenant_id,
                    "event_key": f"synthetic-proof:{proof_id}:{tenant_index}",
                    "event_type": "payment_reported",
                    "parent_gallery_id": ids["gallery"],
                    "derived_gallery_id": None,
                    "client_id": ids["client"],
                    "sale_order_id": ids["order"],
                    "template_version": 1,
                    "push_title": "Synthetic proof",
                    "push_body": "No notification is sent.",
                    "whatsapp_body": "Synthetic fixture only.",
                    "target_path": "/synthetic-proof",
                    "created_at": now,
                    "expires_at": expires_at,
                },
            )
            insert(
                connection,
                "notification_delivery",
                {
                    "id": ids["notification-delivery"],
                    "tenant_id": tenant_id,
                    "event_id": ids["notification-event"],
                    "channel": "push",
                    "recipient_role": "client",
                    "recipient_id": ids["client"],
                    "client_recipient_id": ids["client"],
                    "admin_recipient_id": None,
                    "device_key": "push",
                    "subscription_id": None,
                    "subscription_generation": None,
                    "status": "cancelled",
                    "attempts": 0,
                    "next_attempt_at": now,
                    "lease_until": None,
                    "lease_token": None,
                    "last_error": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            credit_entry_id = ids["credit-entry"]
            insert(
                connection,
                "photographer_credit_entry",
                {
                    "id": credit_entry_id,
                    "tenant_id": tenant_id,
                    "entry_type": "owner_grant",
                    "delta": 7,
                    "idempotency_key": f"synthetic-owner-grant-{proof_id}-{tenant_index}",
                    "operation_id": None,
                    "archive_operation_id": None,
                    "source_entry_id": None,
                    "package_id": None,
                    "actor_admin_id": None,
                    "global_owner_admin_id": owner_admin_id,
                    "source_reference": "synthetic-global-backup-proof",
                    "description": "Synthetic fixture grant; no purchase or billing.",
                    "created_at": now,
                },
            )
            recovery_operation_id = ids["archive-recovery-operation"]
            insert(
                connection,
                "media_archive_operation",
                {
                    "id": recovery_operation_id,
                    "tenant_id": tenant_id,
                    "cycle_id": cycle_id,
                    "operation_type": "restore",
                    "status": "reconciliation_required",
                    "stage": "readback",
                    "idempotency_key": (
                        f"synthetic-recovery-{proof_id}-{tenant_index}"
                    ),
                    "actor_type": "tenant",
                    "actor_admin_id": admin_id,
                    "details": {"fixture": "synthetic-uncertain-recovery"},
                    "last_error_code": "provider_uncertain",
                    "last_error": "Resultado externo incerto; reconciliação necessária.",
                    "attempts": 1,
                    "lease_token": None,
                    "lease_expires_at": None,
                    "started_at": now,
                    "completed_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_archive_recovery_request",
                {
                    "id": ids["archive-recovery-request"],
                    "tenant_id": tenant_id,
                    "operation_id": recovery_operation_id,
                    "cycle_id": cycle_id,
                    "requester_type": "tenant",
                    "requested_by_admin_id": admin_id,
                    "requested_by_tenant_admin_id": admin_id,
                    "requested_by_owner_admin_id": None,
                    "retry_of_operation_id": None,
                    "duration_days": 7 if tenant_index == 1 else 30,
                    "fee_credits_snapshot": 2,
                    "owner_exempt": False,
                    "technical_cover_exempt": False,
                    "closure_batch_id": None,
                    "created_at": now,
                },
            )
            insert(
                connection,
                "media_archive_recovery_credit_reservation",
                {
                    "id": ids["archive-recovery-credit-reservation"],
                    "tenant_id": tenant_id,
                    "operation_id": recovery_operation_id,
                    "reserved_credits": 2,
                    "status": "reconciliation_required",
                    "created_at": now,
                    "updated_at": now,
                },
            )
            insert(
                connection,
                "media_archive_recovery_credit_allocation_event",
                {
                    "id": _fixture_uuid(
                        proof_id, tenant_id, "archive-recovery-credit-reserved"
                    ),
                    "tenant_id": tenant_id,
                    "operation_id": recovery_operation_id,
                    "source_entry_id": credit_entry_id,
                    "credit_entry_id": None,
                    "event_type": "reserved",
                    "quantity": 2,
                    "idempotency_key": (
                        f"synthetic-recovery-reserved-{proof_id}-{tenant_index}"
                    ),
                    "occurred_at": now,
                },
            )
            insert(
                connection,
                "audit_event",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "audit-event"),
                    "tenant_id": tenant_id,
                    "event": "synthetic_backup_fixture_seeded",
                    "subject": f"synthetic-gallery:{ids['gallery']}",
                    "created_at": now,
                },
            )
            insert(
                connection,
                "platform_admin_event",
                {
                    "id": _fixture_uuid(proof_id, tenant_id, "platform-admin-event"),
                    "request_id": None,
                    "actor_admin_id": owner_admin_id,
                    "object_id": credit_entry_id,
                    "tenant_id": tenant_id,
                    "action": "credit.granted",
                    "reason_code": None,
                    "target_version": None,
                    "evidence_sha256": None,
                    "previous_status": None,
                    "next_status": None,
                    "result": "success",
                    "origin": "web_console",
                    "created_at": now,
                },
            )

            for table_name in (
                table for tables in domains.values() for table in tables
            ):
                table = sa.Table(table_name, metadata, autoload_with=connection)
                count = int(
                    connection.execute(
                        sa.select(sa.func.count())
                        .select_from(table)
                        .where(table.c.tenant_id == tenant_id)
                    ).scalar_one()
                )
                expected_count = {
                    "media_archive_operation": 2,
                    "progressive_pricing_tier": 2,
                }.get(table_name, 1)
                if count < 1 or (
                    table_name != "notification_setting" and count != expected_count
                ):
                    raise ProofFailure("synthetic_fixture_tenant_rows_unexpected")
                populated[table_name][str(tenant_id)] = count

    return {
        "tenant_rows_per_table": _fixture_row_summary(populated),
        "tenant_count": len(tenant_ids),
        "domains": {name: list(tables) for name, tables in domains.items()},
        "representative_tables_with_rows": len(populated),
        "global_backup_receipt_rows": {"validated": 1, "unknown": 1},
        "inactive_global_credit_package": 1,
        "remote_services_or_workers_used": False,
        "biometric_payloads_seeded": False,
    }


def _restore(
    container: str,
    database: str,
    archive: bytes,
    *,
    case: str,
    expected_roles: tuple[str, ...] = (),
    restore_options: tuple[str, ...] = (),
    check: bool = True,
) -> int:
    try:
        result = _docker(
            "exec",
            "-i",
            container,
            "pg_restore",
            "-U",
            "postgres",
            "--exit-on-error",
            *restore_options,
            "--dbname",
            database,
            input_bytes=archive,
            check=check,
            known_synthetic_roles=expected_roles,
        )
    except ProofFailure as exc:
        raise ProofFailure(f"{case}:{exc}") from None
    return result.returncode


def _role_present(engine: Engine, role: str) -> bool:
    with engine.connect() as connection:
        return bool(
            connection.execute(
                sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
            ).first()
        )


def _run_global_backup_runner_proof(
    *,
    proof_id: str,
    network: str,
    source_name: str,
    source_db: str,
    source_engine: Engine,
    tenant_ids: list[uuid.UUID],
    roles: tuple[str, str, str],
    canary: str,
    reserved_ports: list[int],
    temp_root: Path,
    restic_executable: Path,
    rclone_executable: Path,
    restic_archive: Path,
    rclone_archive: Path,
    owned_containers: list[str],
) -> dict[str, Any]:
    """Exercise the real runner against this proof's isolated PostgreSQL fixture."""

    try:
        resolved_temp_root = temp_root.expanduser().resolve()
        resolved_temp_base = Path(tempfile.gettempdir()).resolve()
        if not resolved_temp_root.is_relative_to(
            resolved_temp_base
        ) or resolved_temp_root.is_relative_to(ROOT.resolve()):
            raise ProofFailure("runner_temp_root_outside_temp")
        resolved_temp_root.mkdir(parents=True, exist_ok=True)
        restic_path = restic_executable.expanduser().resolve(strict=True)
        rclone_path = rclone_executable.expanduser().resolve(strict=True)
        restic_archive_path = restic_archive.expanduser().resolve(strict=True)
        rclone_archive_path = rclone_archive.expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProofFailure("runner_temp_or_binary_path_invalid") from exc
    if any(
        not path.is_file()
        for path in (restic_path, rclone_path, restic_archive_path, rclone_archive_path)
    ):
        raise ProofFailure("runner_binary_unavailable")
    _verify_release_archive_member(
        restic_archive_path,
        restic_path,
        expected_archive_sha256=RUNNER_RESTIC_WINDOWS_ARCHIVE_SHA256,
    )
    _verify_release_archive_member(
        rclone_archive_path,
        rclone_path,
        expected_archive_sha256=RUNNER_RCLONE_WINDOWS_ARCHIVE_SHA256,
    )

    runner_target_name = f"pyp-global-pg-proof-runner-target-{proof_id}"
    runner_target_db = f"pyp_global_runner_{proof_id}"
    runner_target_port = _free_loopback_port()
    while runner_target_port in reserved_ports:
        runner_target_port = _free_loopback_port()
    reserved_ports.append(runner_target_port)
    runner_target_password = secrets.token_hex(24)
    runner_target_id = _start_postgres(
        name=runner_target_name,
        network=network,
        database=runner_target_db,
        port=runner_target_port,
        password=runner_target_password,
        proof_id=proof_id,
    )
    owned_containers.append(runner_target_id)
    _assert_ephemeral_storage(runner_target_id)
    _wait_for_server(runner_target_name, runner_target_db)
    runner_target_url = (
        f"postgresql+psycopg://postgres:{runner_target_password}"
        f"@127.0.0.1:{runner_target_port}/{runner_target_db}"
    )
    runner_target_engine = sa.create_engine(runner_target_url, pool_pre_ping=True)
    _create_roles(runner_target_engine, roles)

    runner_work = resolved_temp_root / f"pyp-global-backup-runner-{proof_id}"
    try:
        runner_work.mkdir(mode=0o700, exist_ok=False)
    except OSError as exc:
        runner_target_engine.dispose()
        raise ProofFailure("runner_temp_directory_create_failed") from exc
    rclone_config = runner_work / "rclone.conf"
    restic_password_file = runner_work / "restic-password"
    wrong_password_file = runner_work / "wrong-restic-password"
    synthetic_password = secrets.token_urlsafe(36)
    wrong_synthetic_password = secrets.token_urlsafe(36)
    try:
        rclone_config.write_text("[local]\ntype = local\n", encoding="utf-8")
        restic_password_file.write_text(synthetic_password, encoding="utf-8")
        wrong_password_file.write_text(wrong_synthetic_password, encoding="utf-8")
    except OSError as exc:
        runner_target_engine.dispose()
        raise ProofFailure("runner_temp_configuration_write_failed") from exc

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    try:
        from app import global_postgresql_backup as global_backup
    except ImportError as exc:
        runner_target_engine.dispose()
        raise ProofFailure("runner_module_unavailable") from exc

    pg_dump_marker = "__pyp_synthetic_docker_pg_dump__"
    pg_restore_marker = "__pyp_synthetic_docker_pg_restore__"
    repository = "rclone:local:runner-repository"
    repository_path = runner_work / "runner-repository"
    relocated_repository = "rclone:local:runner-repository-relocated"
    relocated_repository_path = runner_work / "runner-repository-relocated"
    config = global_backup.GlobalPostgreSQLBackupConfig(
        repository=repository,
        restic_password_file=restic_password_file,
        rclone_config_file=rclone_config,
        repository_root=ROOT,
        pg_dump_executable=pg_dump_marker,
        pg_restore_executable=pg_restore_marker,
        restic_executable=str(restic_path),
        rclone_executable=str(rclone_path),
    )
    source_connection_url = f"postgresql://postgres@/{source_db}"
    restic_env = {
        **global_backup._base_environment(),
        "RESTIC_PASSWORD_FILE": str(restic_password_file),
        "RCLONE_CONFIG": str(rclone_config),
    }
    original_cwd = Path.cwd()
    original_path = os.environ.get("PATH", "")
    local_tools_path = str(rclone_path.parent)
    merged_path = local_tools_path + os.pathsep + original_path
    init_args = [str(restic_path), "-r", repository, "init"]
    try:
        os.chdir(runner_work)
        with patch.dict(os.environ, {"PATH": merged_path}):
            restic_env = {
                **global_backup._base_environment(),
                "RESTIC_PASSWORD_FILE": str(restic_password_file),
                "RCLONE_CONFIG": str(rclone_config),
            }
            try:
                initialized = subprocess.run(
                    init_args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=restic_env,
                    timeout=60,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ProofFailure("runner_repository_init_failed") from exc
            if initialized.returncode != 0 or not repository_path.is_dir():
                raise ProofFailure("runner_repository_init_failed")

            invalid_dump = False
            original_start = global_backup._start
            original_version_text = global_backup._version_text

            def docker_tool_version(executable: str, args: tuple[str, ...]) -> str:
                if executable == pg_dump_marker:
                    tool = "pg_dump"
                elif executable == pg_restore_marker:
                    tool = "pg_restore"
                else:
                    return original_version_text(executable, args)
                try:
                    checked = subprocess.run(
                        [
                            "docker",
                            "exec",
                            "--user",
                            "postgres",
                            source_name,
                            tool,
                            *args,
                        ],
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        timeout=10,
                        env=global_backup._base_environment(),
                        check=False,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise global_backup.GlobalPostgreSQLBackupError(
                        "tool_version_unverified"
                    ) from exc
                if checked.returncode != 0:
                    raise global_backup.GlobalPostgreSQLBackupError(
                        "tool_version_unverified"
                    )
                try:
                    return checked.stdout.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise global_backup.GlobalPostgreSQLBackupError(
                        "tool_version_unverified"
                    ) from exc

            def docker_aware_start(
                args: list[str],
                *,
                stdin: int | object = subprocess.DEVNULL,
                stdout: int | object = subprocess.DEVNULL,
                env: dict[str, str],
            ) -> subprocess.Popen[bytes]:
                if args and args[0] == pg_dump_marker and invalid_dump:
                    return original_start(
                        [
                            sys.executable,
                            "-c",
                            "import sys; sys.stdout.buffer.write(b'not-a-postgresql-custom-archive')",
                        ],
                        stdin=stdin,
                        stdout=stdout,
                        env=env,
                    )
                if args and args[0] in {pg_dump_marker, pg_restore_marker}:
                    tool = "pg_dump" if args[0] == pg_dump_marker else "pg_restore"
                    return subprocess.Popen(
                        [
                            "docker",
                            "exec",
                            "-i",
                            "--user",
                            "postgres",
                            source_name,
                            tool,
                            *args[1:],
                        ],
                        stdin=stdin,
                        stdout=stdout,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        shell=False,
                    )
                return original_start(args, stdin=stdin, stdout=stdout, env=env)

            with (
                patch.object(global_backup, "_start", side_effect=docker_aware_start),
                patch.object(
                    global_backup, "_version_text", side_effect=docker_tool_version
                ),
            ):
                try:
                    receipt = global_backup.create_global_postgresql_backup(
                        source_connection_url, config
                    )
                except global_backup.GlobalPostgreSQLBackupError as exc:
                    raise ProofFailure(f"runner_backup_failed:{exc.code}") from None
                if not receipt.verified:
                    raise ProofFailure("runner_snapshot_not_verified")

                relocated_repository_file_count = _copy_synthetic_repository(
                    repository_path,
                    relocated_repository_path,
                    temp_root=runner_work,
                )

                try:
                    restored_dump = subprocess.run(
                        [
                            str(restic_path),
                            "-r",
                            relocated_repository,
                            "dump",
                            receipt.snapshot_id,
                            global_backup.ARCHIVE_FILENAME,
                        ],
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        timeout=180,
                        env=restic_env,
                        check=False,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise ProofFailure("runner_snapshot_readback_failed") from exc
                if (
                    restored_dump.returncode != 0
                    or len(restored_dump.stdout) != receipt.dump_size_bytes
                    or not restored_dump.stdout.startswith(b"PGDMP")
                ):
                    raise ProofFailure("runner_snapshot_readback_failed")

                restored = _docker(
                    "exec",
                    "-i",
                    "--user",
                    "postgres",
                    runner_target_name,
                    "pg_restore",
                    "--exit-on-error",
                    "--dbname",
                    runner_target_db,
                    input_bytes=restored_dump.stdout,
                    check=False,
                )
                if restored.returncode != 0:
                    raise ProofFailure("runner_restore_failed")

                _expect_equal(
                    "runner_relations",
                    _relation_inventory(source_engine),
                    _relation_inventory(runner_target_engine),
                )
                source_data = _data_inventory(source_engine, tenant_ids)
                runner_data = _data_inventory(runner_target_engine, tenant_ids)
                _expect_equal("runner_tenant_data", source_data, runner_data)
                source_extensions = _extension_inventory(source_engine)
                _expect_equal(
                    "runner_extensions",
                    source_extensions,
                    _extension_inventory(runner_target_engine),
                )
                _expect_equal(
                    "runner_sequences",
                    _sequence_inventory(source_engine),
                    _sequence_inventory(runner_target_engine),
                )
                _expect_equal(
                    "runner_large_objects",
                    _large_object_inventory(source_engine),
                    _large_object_inventory(runner_target_engine),
                )
                source_materialized_views = _materialized_view_inventory(
                    source_engine, tenant_ids
                )
                runner_materialized_views = _materialized_view_inventory(
                    runner_target_engine, tenant_ids
                )
                if source_materialized_views != runner_materialized_views:
                    raise ProofFailure(
                        "runner_materialized_views_mismatch:"
                        + _row_inventory_difference_summary(
                            source_materialized_views, runner_materialized_views
                        )
                    )
                _expect_equal(
                    "runner_roles_acl",
                    _role_inventory(source_engine, roles),
                    _role_inventory(runner_target_engine, roles),
                )
                normalized_objects: list[str] = []
                source_schema = _schema_definition_inventory(
                    source_engine, normalized_objects
                )
                runner_schema = _schema_definition_inventory(
                    runner_target_engine, normalized_objects
                )
                _expect_equal("runner_schema_catalog", source_schema, runner_schema)

                marker_bytes = canary.encode("utf-8")
                if not any(
                    marker_bytes in path.read_bytes()
                    for repository_root in (
                        repository_path,
                        relocated_repository_path,
                    )
                    for path in repository_root.rglob("*")
                    if path.is_file()
                ):
                    plaintext_canary_absent = True
                else:
                    raise ProofFailure("runner_plaintext_detected")

                wrong_synthetic_password = secrets.token_urlsafe(36)
                wrong_password_file.write_text(
                    wrong_synthetic_password, encoding="utf-8"
                )
                wrong_config = replace(config, restic_password_file=wrong_password_file)
                try:
                    global_backup.create_global_postgresql_backup(
                        source_connection_url, wrong_config
                    )
                except global_backup.GlobalPostgreSQLBackupError as exc:
                    wrong_password_error = exc.code
                    if wrong_password_error not in {
                        "backup_execution_failed",
                        "snapshot_create_failed",
                    } or wrong_synthetic_password in str(exc):
                        raise ProofFailure(
                            "runner_wrong_password_not_sanitized"
                        ) from None
                else:
                    raise ProofFailure("runner_wrong_password_accepted")

                invalid_dump = True
                try:
                    global_backup.create_global_postgresql_backup(
                        source_connection_url, config
                    )
                except global_backup.GlobalPostgreSQLBackupError as exc:
                    invalid_archive_error = exc.code
                    if (
                        invalid_archive_error != "snapshot_readback_failed"
                        or "not-a-postgresql-custom-archive" in str(exc)
                    ):
                        raise ProofFailure(
                            "runner_invalid_archive_not_sanitized"
                        ) from None
                else:
                    raise ProofFailure("runner_invalid_archive_accepted")
                finally:
                    invalid_dump = False

                if any(
                    marker_bytes in path.read_bytes()
                    for repository_root in (
                        repository_path,
                        relocated_repository_path,
                    )
                    for path in repository_root.rglob("*")
                    if path.is_file()
                ):
                    raise ProofFailure("runner_plaintext_detected_after_negative_cases")

        return {
            "status": "verified",
            "snapshot_id": receipt.snapshot_id,
            "archive_bytes": receipt.dump_size_bytes,
            "relocated_repository_file_count": relocated_repository_file_count,
            "tenant_count": len(tenant_ids),
            "table_count": len(source_data),
            "relation_count": len(_relation_inventory(source_engine)),
            "sequence_count": len(_sequence_inventory(source_engine)),
            "extension_count": len(source_extensions),
            "plaintext_canary_absent": plaintext_canary_absent,
            "wrong_password_error": wrong_password_error,
            "invalid_archive_error": invalid_archive_error,
        }
    finally:
        runner_target_engine.dispose()
        os.chdir(original_cwd)


def _safe_error_tail(data: bytes, secrets_to_redact: tuple[str, ...]) -> str:
    decoded = data.decode("utf-8", errors="replace")
    for secret in secrets_to_redact:
        if secret:
            decoded = decoded.replace(secret, "[redacted]")
    return "\n".join(decoded.splitlines()[-20:])


def run_proof(*, runner_options: RunnerProofOptions | None = None) -> dict[str, Any]:
    proof_id = uuid.uuid4().hex[:12]
    image_inspect = _lines(
        _docker("image", "inspect", IMAGE, "--format", "{{.Id}}|{{json .RepoDigests}}")
    )[0]
    baseline = _inventory()
    if baseline["context"] != EXPECTED_CONTEXT:
        raise ProofFailure("docker_context_not_local_desktop")

    image_id, image_digests_json = image_inspect.split("|", maxsplit=1)
    try:
        image_digests = json.loads(image_digests_json)
    except json.JSONDecodeError as exc:
        raise ProofFailure("synthetic_postgres_image_inspection_failed") from exc
    if EXPECTED_IMAGE_DIGEST not in image_digests:
        raise ProofFailure("synthetic_postgres_image_digest_mismatch")
    network = f"pyp-global-pg-proof-net-{proof_id}"
    source_name = f"pyp-global-pg-proof-source-{proof_id}"
    target_name = f"pyp-global-pg-proof-target-{proof_id}"
    source_db = f"pyp_global_src_{proof_id}"
    target_db = f"pyp_global_tgt_{proof_id}"
    roles = tuple(
        f"pyp_proof_{kind}_{proof_id}" for kind in ("owner", "reader", "member")
    )
    tenant_ids: list[uuid.UUID] = []
    ports = [_free_loopback_port(), _free_loopback_port()]
    while ports[0] == ports[1]:
        ports[1] = _free_loopback_port()
    passwords = [secrets.token_hex(24), secrets.token_hex(24)]
    owned_containers: list[str] = []
    owned_network: str | None = None
    started = time.monotonic()
    result: dict[str, Any] = {}
    runner_integration: dict[str, Any] | None = None

    try:
        net_id = _lines(
            _docker(
                "network",
                "create",
                "--driver",
                "bridge",
                "--label",
                f"{PROOF_LABEL}={proof_id}",
                network,
            )
        )[0]
        owned_network = net_id
        source_id = _start_postgres(
            name=source_name,
            network=network,
            database=source_db,
            port=ports[0],
            password=passwords[0],
            proof_id=proof_id,
        )
        owned_containers.append(source_id)
        _assert_ephemeral_storage(source_id)
        target_id = _start_postgres(
            name=target_name,
            network=network,
            database=target_db,
            port=ports[1],
            password=passwords[1],
            proof_id=proof_id,
        )
        owned_containers.append(target_id)
        _assert_ephemeral_storage(target_id)
        _wait_for_server(source_name, source_db)
        _wait_for_server(target_name, target_db)

        source_url = f"postgresql+psycopg://postgres:{passwords[0]}@127.0.0.1:{ports[0]}/{source_db}"
        synthetic_totp_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        source_engine = sa.create_engine(source_url, pool_pre_ping=True)
        target_url = f"postgresql+psycopg://postgres:{passwords[1]}@127.0.0.1:{ports[1]}/{target_db}"
        target_engine = sa.create_engine(target_url, pool_pre_ping=True)
        try:
            redactions = (passwords[0], source_url, synthetic_totp_key)
            _upgrade_to(source_url, "20261031_0093", synthetic_totp_key, redactions)
            owner_tenant_id = _seed_persistent_owner(source_engine, proof_id)
            _upgrade_to(source_url, "20261031_0094", synthetic_totp_key, redactions)
            second_tenant_id = _seed_second_tenant(source_engine, proof_id)
            tenant_ids.extend((owner_tenant_id, second_tenant_id))
            _upgrade_to(source_url, "head", synthetic_totp_key, redactions)

            with source_engine.connect() as connection:
                version = str(
                    connection.execute(sa.text("SHOW server_version")).scalar_one()
                )
                migration_head = str(
                    connection.execute(
                        sa.text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                )
            _expect_equal("postgres_major", "17", version.split(".")[0])
            _create_roles(source_engine, roles)
            extension_version = _seed_source(source_engine, tenant_ids, roles)
            _seed_large_object(source_engine)
            application_fixture = _seed_application_fixture(
                source_engine, tenant_ids, proof_id
            )
            if runner_options is not None:
                runner_canary = _seed_runner_canary(
                    source_engine, tenant_ids[0], proof_id
                )
                runner_integration = _run_global_backup_runner_proof(
                    proof_id=proof_id,
                    network=network,
                    source_name=source_name,
                    source_db=source_db,
                    source_engine=source_engine,
                    tenant_ids=tenant_ids,
                    roles=roles,
                    canary=runner_canary,
                    reserved_ports=ports,
                    temp_root=runner_options.temp_root,
                    restic_executable=runner_options.restic_executable,
                    rclone_executable=runner_options.rclone_executable,
                    restic_archive=runner_options.restic_archive,
                    rclone_archive=runner_options.rclone_archive,
                    owned_containers=owned_containers,
                )
            with source_engine.connect() as connection:
                tenant_count = int(
                    connection.execute(
                        sa.text("SELECT count(*) FROM tenant")
                    ).scalar_one()
                )
            _expect_equal("synthetic_tenant_count", 2, tenant_count)

            full_dump = _docker(
                "exec",
                source_name,
                "pg_dump",
                "-U",
                "postgres",
                "--format=custom",
                "--dbname",
                source_db,
            ).stdout
            full_sha256 = _sha256(full_dump)
            _expect_equal("archive_sha256", full_sha256, _sha256(full_dump))
            listed = _docker(
                "exec", "-i", source_name, "pg_restore", "--list", input_bytes=full_dump
            )
            if listed.returncode:
                raise ProofFailure("archive_list_failed")

            truncated = full_dump[: max(1, len(full_dump) // 2)]
            if (
                _docker(
                    "exec",
                    "-i",
                    source_name,
                    "pg_restore",
                    "--list",
                    input_bytes=truncated,
                    check=False,
                ).returncode
                == 0
            ):
                raise ProofFailure("truncated_archive_accepted")
            _expect_rejected("archive_sha256", full_sha256, "0" * 64)

            missing_role_code = _restore(
                target_name, target_db, full_dump, case="missing_role", check=False
            )
            if missing_role_code == 0 or _role_present(target_engine, roles[0]):
                raise ProofFailure(
                    "archive_restored_without_required_role_provisioning"
                )

            # Banco de destino da primeira tentativa ficou isolado e incompleto; criar outro vazio.
            _create_roles(target_engine, roles)
            _expect_equal(
                "target_role_provisioning",
                [True] * len(roles),
                [_role_present(target_engine, role) for role in roles],
            )
            truncated_db = f"pyp_global_truncated_{proof_id}"
            _docker("exec", target_name, "createdb", "-U", "postgres", truncated_db)
            truncated_restore = _restore(
                target_name,
                truncated_db,
                full_dump[: max(1, len(full_dump) // 2)],
                case="truncated_archive",
                check=False,
            )
            if truncated_restore == 0:
                raise ProofFailure("truncated_archive_restore_accepted")
            full_target_db = f"pyp_global_full_{proof_id}"
            _docker("exec", target_name, "createdb", "-U", "postgres", full_target_db)
            _restore(
                target_name,
                full_target_db,
                full_dump,
                case="full_restore",
                expected_roles=roles,
            )
            full_target_url = f"postgresql+psycopg://postgres:{passwords[1]}@127.0.0.1:{ports[1]}/{full_target_db}"
            full_target_engine = sa.create_engine(full_target_url, pool_pre_ping=True)

            no_owner_target_db = f"pyp_global_noacl_{proof_id}"
            _docker(
                "exec", target_name, "createdb", "-U", "postgres", no_owner_target_db
            )
            _restore(
                target_name,
                no_owner_target_db,
                full_dump,
                case="no_owner_restore",
                expected_roles=roles,
                restore_options=("--no-owner", "--no-privileges"),
            )
            no_owner_target_url = f"postgresql+psycopg://postgres:{passwords[1]}@127.0.0.1:{ports[1]}/{no_owner_target_db}"
            no_owner_engine = sa.create_engine(no_owner_target_url, pool_pre_ping=True)
            try:
                source_relations = _relation_inventory(source_engine)
                full_relations = _relation_inventory(full_target_engine)
                _expect_equal("relations", source_relations, full_relations)
                source_extensions = _extension_inventory(source_engine)
                full_extensions = _extension_inventory(full_target_engine)
                _expect_equal("extensions", source_extensions, full_extensions)
                _expect_rejected(
                    "extension_missing_negative",
                    source_extensions,
                    [item for item in full_extensions if item[0] != "pgcrypto"],
                )
                wrong_extension_version = [
                    (name, "0.0-invalid") if name == "pgcrypto" else (name, version)
                    for name, version in full_extensions
                ]
                _expect_rejected(
                    "extension_version", source_extensions, wrong_extension_version
                )

                source_data = _data_inventory(source_engine, tenant_ids)
                full_data = _data_inventory(full_target_engine, tenant_ids)
                _expect_equal("table_data", source_data, full_data)
                source_materialized_views = _materialized_view_inventory(
                    source_engine, tenant_ids
                )
                full_materialized_views = _materialized_view_inventory(
                    full_target_engine, tenant_ids
                )
                if source_materialized_views != full_materialized_views:
                    raise ProofFailure(
                        "materialized_views_mismatch:"
                        + _row_inventory_difference_summary(
                            source_materialized_views, full_materialized_views
                        )
                    )
                source_large_objects = _large_object_inventory(source_engine)
                full_large_objects = _large_object_inventory(full_target_engine)
                _expect_equal("large_objects", source_large_objects, full_large_objects)
                source_sequences = _sequence_inventory(source_engine)
                full_sequences = _sequence_inventory(full_target_engine)
                _expect_equal("sequences", source_sequences, full_sequences)
                source_roles = _role_inventory(source_engine, roles)
                full_roles = _role_inventory(full_target_engine, roles)
                _expect_equal("roles_acl", source_roles, full_roles)
                schema_normalized_objects: list[str] = []
                source_schema_catalog = _schema_definition_inventory(
                    source_engine, schema_normalized_objects
                )
                full_schema_catalog = _schema_definition_inventory(
                    full_target_engine, schema_normalized_objects
                )
                catalog_differences = [
                    name
                    for name in source_schema_catalog
                    if source_schema_catalog[name] != full_schema_catalog[name]
                ]
                if catalog_differences:
                    raise ProofFailure(
                        "schema_catalog_mismatch:"
                        + _schema_catalog_difference_summary(
                            source_schema_catalog, full_schema_catalog
                        )
                        + ":"
                        + _schema_definition_detail_summary(
                            source_schema_catalog, full_schema_catalog
                        )
                    )
                source_schema = _schema_dump(source_name, source_db)
                full_schema = _schema_dump(target_name, full_target_db)
                schema_dump_canonical_match = source_schema == full_schema

                altered_data = dict(full_data)
                first_table = next(iter(altered_data))
                altered_data[first_table] = {**altered_data[first_table], "count": -1}
                _expect_rejected("table_data_hash", source_data, altered_data)
                if source_large_objects:
                    altered_large_objects = list(full_large_objects)
                    first_large_object = altered_large_objects[0]
                    altered_large_objects[0] = (
                        first_large_object[0],
                        first_large_object[1],
                        "0" * 64,
                    )
                    _expect_rejected(
                        "large_object_content",
                        source_large_objects,
                        altered_large_objects,
                    )

                no_owner_relations = _relation_inventory(no_owner_engine)
                proof_owner_rows = [
                    row for row in no_owner_relations if row[0] == "proof_fixture"
                ]
                if not proof_owner_rows or any(
                    row[5] != "postgres" for row in proof_owner_rows
                ):
                    raise ProofFailure(
                        "no_owner_profile_not_observed:"
                        + _no_owner_profile_summary(
                            source_relations, no_owner_relations
                        )
                    )
                no_owner_data = _data_inventory(no_owner_engine, tenant_ids)
                _expect_equal("no_owner_data", source_data, no_owner_data)
                _expect_equal(
                    "no_owner_materialized_views",
                    source_materialized_views,
                    _materialized_view_inventory(no_owner_engine, tenant_ids),
                )
                _expect_equal(
                    "no_owner_large_objects",
                    source_large_objects,
                    _large_object_inventory(no_owner_engine),
                )
                no_owner_roles = _role_inventory(no_owner_engine, roles)
                if no_owner_roles["grants"] or no_owner_roles["default_privileges"]:
                    raise ProofFailure("no_privileges_profile_not_observed")
                no_owner_schema = _schema_dump(target_name, no_owner_target_db)
                if source_schema != no_owner_schema:
                    raise ProofFailure(
                        "no_owner_schema_definitions:"
                        + _schema_difference_summary(source_schema, no_owner_schema)
                    )

                partial_db = f"pyp_global_partial_{proof_id}"
                _docker("exec", target_name, "createdb", "-U", "postgres", partial_db)
                _psql(target_name, partial_db, "CREATE SCHEMA proof_fixture")
                if (
                    _restore(
                        target_name,
                        partial_db,
                        full_dump,
                        case="partial_conflict",
                        check=False,
                    )
                    == 0
                ):
                    raise ProofFailure("partial_restore_conflict_accepted")
            finally:
                full_target_engine.dispose()
                no_owner_engine.dispose()
        finally:
            source_engine.dispose()
            target_engine.dispose()

        result = {
            "postgres_version": version,
            "alembic_head": migration_head,
            "extension": "pgcrypto",
            "extension_version": extension_version,
            "relations": len(source_relations),
            "tables": len(source_data),
            "foreign_tables": sum(row[2] == "f" for row in source_relations),
            "partitioned_tables": sum(row[2] == "p" for row in source_relations),
            "partitions": sum(bool(row[4]) for row in source_relations),
            "sequences": len(source_sequences),
            "materialized_views": len(source_materialized_views),
            "large_objects": len(source_large_objects),
            "tenant_count": 2,
            "application_fixture": application_fixture,
            "synthetic_roles": len(source_roles["roles"]),
            "role_memberships": len(source_roles["memberships"]),
            "role_grants": len(source_roles["grants"]),
            "default_privileges": len(source_roles["default_privileges"]),
            "schema_catalog_categories": list(source_schema_catalog),
            "schema_text_array_cast_normalizations": len(
                set(schema_normalized_objects)
            ),
            "schema_dump_canonical_match": schema_dump_canonical_match,
            "schema_dump_difference_summary": (
                _schema_difference_summary(source_schema, full_schema)
                if not schema_dump_canonical_match
                else "identical"
            ),
            "archive_bytes": len(full_dump),
            "archive_sha256": full_sha256,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "image_id": image_id,
            "image_digest": EXPECTED_IMAGE_DIGEST,
            "negative_cases": [
                "truncated_archive",
                "wrong_archive_sha256",
                "missing_synthetic_role",
                "missing_extension_metadata",
                "wrong_extension_version",
                "table_content_mismatch",
                "large_object_content_mismatch",
                "partial_restore_conflict",
            ],
            "role_acl_profiles": [
                "full_after_synthetic_role_provisioning",
                "no-owner-no-privileges_gap",
            ],
        }
        if runner_integration is not None:
            result["restic_rclone_runner_integration"] = runner_integration
        return result
    finally:
        for container_id in reversed(owned_containers):
            label = _lines(
                _docker(
                    "inspect",
                    "--format",
                    f'{{{{ index .Config.Labels "{PROOF_LABEL}" }}}}',
                    container_id,
                )
            )[0]
            if label == proof_id:
                # --volumes remove only anonymous volumes attached to this owned container.
                _docker("rm", "--force", "--volumes", container_id)
        if owned_network:
            label = _lines(
                _docker(
                    "network",
                    "inspect",
                    "--format",
                    f'{{{{ index .Labels "{PROOF_LABEL}" }}}}',
                    owned_network,
                )
            )[0]
            if label == proof_id:
                _docker("network", "rm", owned_network)
        remaining_containers, remaining_networks = _proof_resources(proof_id)
        if remaining_containers or remaining_networks:
            raise ProofFailure("synthetic_resources_not_cleaned")
        after = _inventory()
        result["docker_inventory_unchanged"] = after == baseline
        result["docker_inventory_delta"] = _inventory_delta_summary(baseline, after)
        if after != baseline:
            raise ProofFailure("docker_inventory_not_unchanged")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-local-synthetic-proof",
        action="store_true",
        help="cria PostgreSQL sintéticos descartáveis no Docker local desktop-linux",
    )
    parser.add_argument(
        "--with-global-backup-runner",
        action="store_true",
        help="exercita o runner real com Restic/Rclone locais e PostgreSQL sintético",
    )
    parser.add_argument("--runner-temp-root", type=Path)
    parser.add_argument("--runner-restic-executable", type=Path)
    parser.add_argument("--runner-rclone-executable", type=Path)
    parser.add_argument("--runner-restic-archive", type=Path)
    parser.add_argument("--runner-rclone-archive", type=Path)
    args = parser.parse_args()
    if not args.run_local_synthetic_proof:
        parser.error(
            "use --run-local-synthetic-proof para executar a prova local isolada"
        )
    runner_values = (
        args.runner_temp_root,
        args.runner_restic_executable,
        args.runner_rclone_executable,
        args.runner_restic_archive,
        args.runner_rclone_archive,
    )
    if args.with_global_backup_runner and any(value is None for value in runner_values):
        parser.error(
            "--with-global-backup-runner exige --runner-temp-root, "
            "--runner-restic-executable, --runner-rclone-executable, "
            "--runner-restic-archive e --runner-rclone-archive"
        )
    if not args.with_global_backup_runner and any(
        value is not None for value in runner_values
    ):
        parser.error("parâmetros runner exigem --with-global-backup-runner")
    runner_options = (
        RunnerProofOptions(
            temp_root=args.runner_temp_root,
            restic_executable=args.runner_restic_executable,
            rclone_executable=args.runner_rclone_executable,
            restic_archive=args.runner_restic_archive,
            rclone_archive=args.runner_rclone_archive,
        )
        if args.with_global_backup_runner
        else None
    )
    try:
        result = run_proof(runner_options=runner_options)
    except ProofFailure as exc:
        print(f"proof_failed: {exc}", file=sys.stderr)
        return 1
    print("synthetic_global_postgresql_proof=passed")
    for key, value in result.items():
        print(f"{key}={value}")
    print("docker_resources_after_cleanup=proof_labeled_resources_absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
