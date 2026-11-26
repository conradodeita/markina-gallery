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
import socket
import subprocess
import sys
import time
import uuid
from datetime import date, datetime
from datetime import time as datetime_time
from decimal import Decimal
from pathlib import Path
from typing import Any

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


def _seed_large_object(engine: Engine) -> None:
    payload = b"synthetic global PostgreSQL large object proof"
    with engine.begin() as connection:
        oid = int(connection.execute(sa.text("SELECT lo_create(0)")).scalar_one())
        connection.execute(
            sa.text("SELECT lo_put(:oid, 0, :payload)"),
            {"oid": oid, "payload": payload},
        )


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


def _safe_error_tail(data: bytes, secrets_to_redact: tuple[str, ...]) -> str:
    decoded = data.decode("utf-8", errors="replace")
    for secret in secrets_to_redact:
        if secret:
            decoded = decoded.replace(secret, "[redacted]")
    return "\n".join(decoded.splitlines()[-20:])


def run_proof() -> dict[str, Any]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-local-synthetic-proof",
        action="store_true",
        help="cria apenas dois PostgreSQL sintéticos descartáveis no Docker local desktop-linux",
    )
    args = parser.parse_args()
    if not args.run_local_synthetic_proof:
        parser.error(
            "use --run-local-synthetic-proof para executar a prova local isolada"
        )
    try:
        result = run_proof()
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
