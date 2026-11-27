"""Fixtures and a test-only oracle for the proposed Rclone sidecar contract.

This file deliberately does not import an application parser or storage adapter.
It checks the contract corpus before those components are authorized and wired.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path
from uuid import UUID

import pytest

MAX_SIDECAR_BYTES = 1024
MAX_OBJECT_BYTES = 5 * 1024**4
SIDECAR_KEYS = frozenset({
    "schema_version",
    "tenant_id",
    "provider_id",
    "object_id",
    "remote_object_id",
    "mime_type",
    "size_bytes",
    "sha256",
})
UUID_FIELDS = ("tenant_id", "provider_id", "object_id")
REMOTE_ID = re.compile(r"[A-Za-z0-9_-]{1,256}")
SHA256 = re.compile(r"[0-9a-f]{64}")
REMOTE_ID_PREFIX = "r1_"
LOGICAL_KEY_UUIDS = (
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000006",
    "00000000-0000-4000-8000-000000000007",
    "00000000-0000-4000-8000-000000000002",
    "00000000-0000-4000-8000-000000000004",
)
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "media_archive_rclone_sidecar"
VALID_FIXTURE = FIXTURE_DIR / "valid_v1.json"
EXPECTED_CATALOG_ROW = {
    "schema_version": 1,
    "tenant_id": "00000000-0000-4000-8000-000000000001",
    "provider_id": "00000000-0000-4000-8000-000000000003",
    "object_id": "00000000-0000-4000-8000-000000000004",
    "remote_object_id": (
        "r1_MDAwMDAwMDAtMDAwMC00MDAwLTgwMDAtMDAwMDAwMDAwMDAxOjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwNjowMDAwMDAwMC0wMDAwLTQwMDAtODAwMC0wMDAwMDAwMDAwMDc6"
        "MDAwMDAwMDAtMDAwMC00MDAwLTgwMDAtMDAwMDAwMDAwMDAyOjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwNA"
    ),
    "mime_type": "image/jpeg",
    "size_bytes": 12345,
    "sha256": "a" * 64,
}


class SidecarContractError(ValueError):
    """Static test-oracle error; never includes sidecar values or raw bytes."""


def _canonical_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise SidecarContractError("invalid_remote_id")
    try:
        canonical = str(UUID(value))
    except ValueError as exc:
        raise SidecarContractError("invalid_remote_id") from exc
    if canonical != value:
        raise SidecarContractError("invalid_remote_id")
    return canonical


def _encode_remote_object_id(logical_key: tuple[str, ...]) -> str:
    """Test-only oracle for the proposed versioned UUID tuple token."""
    if not isinstance(logical_key, tuple) or len(logical_key) != 5:
        raise SidecarContractError("invalid_remote_id")
    canonical_parts = tuple(_canonical_uuid(part) for part in logical_key)
    payload = ":".join(canonical_parts).encode("ascii")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    remote_id = f"{REMOTE_ID_PREFIX}{encoded}"
    if not REMOTE_ID.fullmatch(remote_id):
        raise SidecarContractError("invalid_remote_id")
    return remote_id


def _decode_remote_object_id(remote_id: object) -> tuple[str, ...]:
    """Decode the proposed logical key; provider selection stays separate."""
    if (
        not isinstance(remote_id, str)
        or not REMOTE_ID.fullmatch(remote_id)
        or not remote_id.startswith(REMOTE_ID_PREFIX)
    ):
        raise SidecarContractError("invalid_remote_id")
    encoded = remote_id[len(REMOTE_ID_PREFIX) :]
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = base64.b64decode(encoded + padding, altchars=b"-_", validate=True)
        canonical_encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        decoded = payload.decode("ascii")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise SidecarContractError("invalid_remote_id") from exc
    if canonical_encoded != encoded:
        raise SidecarContractError("invalid_remote_id")
    parts = tuple(decoded.split(":"))
    if len(parts) != 5:
        raise SidecarContractError("invalid_remote_id")
    return tuple(_canonical_uuid(part) for part in parts)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SidecarContractError("duplicate_key")
        result[key] = value
    return result


def _reject_nonfinite(_value: str) -> None:
    raise SidecarContractError("nonfinite_number")


def _parse_contract_fixture(
    raw: bytes,
    *,
    expected: dict[str, object],
) -> dict[str, object]:
    """Test-only contract oracle, intentionally independent from app behavior."""
    if not isinstance(raw, bytes):
        raise SidecarContractError("bytes_required")
    if len(raw) > MAX_SIDECAR_BYTES:
        raise SidecarContractError("payload_too_large")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except SidecarContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SidecarContractError("invalid_json") from exc

    if not isinstance(value, dict) or set(value) != SIDECAR_KEYS:
        raise SidecarContractError("invalid_shape")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise SidecarContractError("unsupported_version")
    for field in UUID_FIELDS:
        raw_uuid = value[field]
        if not isinstance(raw_uuid, str):
            raise SidecarContractError("invalid_uuid")
        try:
            if str(UUID(raw_uuid)) != raw_uuid:
                raise SidecarContractError("invalid_uuid")
        except ValueError as exc:
            raise SidecarContractError("invalid_uuid") from exc
    remote_id = value["remote_object_id"]
    if not isinstance(remote_id, str) or not REMOTE_ID.fullmatch(remote_id):
        raise SidecarContractError("invalid_remote_id")
    logical_key = _decode_remote_object_id(remote_id)
    if logical_key[0] != value["tenant_id"] or logical_key[4] != value["object_id"]:
        raise SidecarContractError("remote_id_identity_mismatch")
    mime_type = value["mime_type"]
    if not isinstance(mime_type, str) or not 1 <= len(mime_type) <= 127:
        raise SidecarContractError("invalid_mime_type")
    size_bytes = value["size_bytes"]
    if type(size_bytes) is not int or not 0 < size_bytes <= MAX_OBJECT_BYTES:
        raise SidecarContractError("invalid_size")
    digest = value["sha256"]
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise SidecarContractError("invalid_sha256")
    if value != expected:
        raise SidecarContractError("catalog_mismatch")
    return value


def _valid_fixture_bytes() -> bytes:
    return VALID_FIXTURE.read_bytes()


def _payload_with_changes(**changes: object) -> bytes:
    payload = json.loads(_valid_fixture_bytes())
    payload.update(changes)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def test_valid_fixture_is_within_limit_and_matches_synthetic_catalog() -> None:
    raw = _valid_fixture_bytes()

    assert len(raw) < MAX_SIDECAR_BYTES
    assert _parse_contract_fixture(raw, expected=EXPECTED_CATALOG_ROW) == EXPECTED_CATALOG_ROW


def test_remote_object_id_round_trips_the_canonical_logical_key() -> None:
    remote_id = _encode_remote_object_id(LOGICAL_KEY_UUIDS)

    assert remote_id == EXPECTED_CATALOG_ROW["remote_object_id"]
    assert _decode_remote_object_id(remote_id) == LOGICAL_KEY_UUIDS
    assert "00000000-0000-4000-8000-000000000003" not in remote_id


def test_remote_object_id_five_uuid_tuple_stays_within_catalog_limit() -> None:
    remote_id = _encode_remote_object_id(LOGICAL_KEY_UUIDS)

    assert len(remote_id) == 249
    assert len(remote_id) <= 256
    assert REMOTE_ID.fullmatch(remote_id)


@pytest.mark.parametrize(
    "logical_key",
    (
        ("00000000-0000-4000-8000-000000000009", *LOGICAL_KEY_UUIDS[1:]),
        (*LOGICAL_KEY_UUIDS[:4], "00000000-0000-4000-8000-000000000009"),
    ),
)
def test_sidecar_identity_must_match_tenant_and_object_in_remote_id(
    logical_key: tuple[str, ...],
) -> None:
    raw = _payload_with_changes(remote_object_id=_encode_remote_object_id(logical_key))

    with pytest.raises(SidecarContractError, match="^remote_id_identity_mismatch$"):
        _parse_contract_fixture(raw, expected=EXPECTED_CATALOG_ROW)


@pytest.mark.parametrize(
    "remote_id",
    [
        "v2_" + base64.urlsafe_b64encode(":".join(LOGICAL_KEY_UUIDS).encode()).decode().rstrip("="),
        "r1_!",
        "r1_" + base64.urlsafe_b64encode(":".join(LOGICAL_KEY_UUIDS[:4]).encode()).decode().rstrip("="),
        "r1_"
        + base64.urlsafe_b64encode(
            ":".join(("not-a-uuid", *LOGICAL_KEY_UUIDS[1:])).encode()
        ).decode().rstrip("="),
        "r1_"
        + base64.urlsafe_b64encode(
            ":".join(("ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF", *LOGICAL_KEY_UUIDS[1:])).encode()
        ).decode().rstrip("="),
        EXPECTED_CATALOG_ROW["remote_object_id"] + "=",
        EXPECTED_CATALOG_ROW["remote_object_id"] + "A",
        "r1_" + "A" * 254,
    ],
)
def test_malformed_or_noncanonical_remote_object_id_fails_closed(remote_id: str) -> None:
    with pytest.raises(SidecarContractError, match="^invalid_remote_id$"):
        _decode_remote_object_id(remote_id)


def test_exact_size_limit_is_allowed_but_next_byte_is_rejected_before_decode(monkeypatch) -> None:
    padded = _valid_fixture_bytes() + b" " * (MAX_SIDECAR_BYTES - len(_valid_fixture_bytes()))
    assert len(padded) == MAX_SIDECAR_BYTES
    assert _parse_contract_fixture(padded, expected=EXPECTED_CATALOG_ROW) == EXPECTED_CATALOG_ROW

    def fail_if_decoded(*_args, **_kwargs):
        pytest.fail("payload acima do limite chegou ao parser JSON")

    monkeypatch.setattr(json, "loads", fail_if_decoded)
    with pytest.raises(SidecarContractError, match="payload_too_large"):
        _parse_contract_fixture(padded + b" ", expected=EXPECTED_CATALOG_ROW)


@pytest.mark.parametrize(
    ("fixture_name", "error_code"),
    (("duplicate_key.json", "duplicate_key"), ("truncated.json", "invalid_json")),
)
def test_malformed_raw_fixtures_fail_closed(fixture_name: str, error_code: str) -> None:
    raw = (FIXTURE_DIR / fixture_name).read_bytes()

    with pytest.raises(SidecarContractError, match=error_code):
        _parse_contract_fixture(raw, expected=EXPECTED_CATALOG_ROW)


@pytest.mark.parametrize(
    ("changes", "error_code"),
    (
        ({"provider_id": None}, "invalid_uuid"),
        ({"remote_object_id": "../outside"}, "invalid_remote_id"),
        ({"mime_type": "m" * 128}, "invalid_mime_type"),
        ({"size_bytes": True}, "invalid_size"),
        ({"size_bytes": 0}, "invalid_size"),
        ({"size_bytes": MAX_OBJECT_BYTES + 1}, "invalid_size"),
        ({"sha256": "A" * 64}, "invalid_sha256"),
        ({"schema_version": True}, "unsupported_version"),
        ({"schema_version": 2}, "unsupported_version"),
    ),
)
def test_invalid_field_types_and_bounds_fail_closed(changes: dict[str, object], error_code: str) -> None:
    with pytest.raises(SidecarContractError, match=error_code):
        _parse_contract_fixture(_payload_with_changes(**changes), expected=EXPECTED_CATALOG_ROW)


@pytest.mark.parametrize(
    ("field", "other_value"),
    (
        ("tenant_id", "00000000-0000-4000-8000-000000000002"),
        ("provider_id", "00000000-0000-4000-8000-000000000005"),
        ("object_id", "00000000-0000-4000-8000-000000000006"),
        ("remote_object_id", "r1_different_object"),
        ("mime_type", "image/png"),
        ("size_bytes", 12346),
        ("sha256", "b" * 64),
    ),
)
def test_catalog_binding_mismatch_fails_closed(field: str, other_value: object) -> None:
    expected = dict(EXPECTED_CATALOG_ROW)
    expected[field] = other_value

    with pytest.raises(SidecarContractError, match="catalog_mismatch"):
        _parse_contract_fixture(_valid_fixture_bytes(), expected=expected)


@pytest.mark.parametrize("changes", ({"extra": "unexpected"}, {"object_id": None}))
def test_missing_or_extra_fields_fail_closed(changes: dict[str, object]) -> None:
    payload = json.loads(_valid_fixture_bytes())
    if "extra" in changes:
        payload.update(changes)
    else:
        payload.pop("object_id")

    with pytest.raises(SidecarContractError, match="invalid_shape"):
        _parse_contract_fixture(json.dumps(payload).encode("utf-8"), expected=EXPECTED_CATALOG_ROW)


def test_parser_errors_do_not_include_sidecar_values() -> None:
    raw = _payload_with_changes(tenant_id="not-a-uuid")

    with pytest.raises(SidecarContractError) as error:
        _parse_contract_fixture(raw, expected=EXPECTED_CATALOG_ROW)

    assert str(error.value) == "invalid_uuid"
    assert b"not-a-uuid" in raw
