"""Test-only oracle for the proposed per-object provider binding contract.

This module deliberately does not import the application worker, database, or
storage adapters. It characterizes fail-closed routing with synthetic records;
it does not prove production composition or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

TENANT_A = "00000000-0000-4000-8000-000000000001"
TENANT_B = "00000000-0000-4000-8000-000000000002"
CYCLE_DRIVE_A = "00000000-0000-4000-8000-000000000006"
CYCLE_RCLONE_A = "00000000-0000-4000-8000-000000000007"
DRIVE_A = "00000000-0000-4000-8000-000000000003"
RCLONE_A = "00000000-0000-4000-8000-000000000004"
RCLONE_B = "00000000-0000-4000-8000-000000000005"


@dataclass(frozen=True)
class SyntheticBinding:
    tenant_id: str
    provider_id: str
    provider_kind: str


@dataclass(frozen=True)
class SyntheticObject:
    tenant_id: str
    cycle_id: str
    object_provider_id: str | None
    cycle_provider_id: str | None
    manifest_version: int
    manifest_provider_id: str | None


class BindingContractError(ValueError):
    """Static contract error with no tenant or provider values in its message."""


SYNTHETIC_BINDINGS = (
    SyntheticBinding(TENANT_A, DRIVE_A, "google_drive"),
    SyntheticBinding(TENANT_A, RCLONE_A, "rclone_crypt"),
    SyntheticBinding(TENANT_B, RCLONE_B, "rclone_crypt"),
)


def _resolve_object_binding(
    obj: SyntheticObject,
    *,
    bindings: tuple[SyntheticBinding, ...],
    proven_legacy_provider_id: str | None = None,
) -> SyntheticBinding:
    """Resolve from object identity or caller-verified authoritative V1 proof.

    The proof argument is only a test input; this oracle has no way to discover
    or validate real historical account/root evidence.
    """
    if obj.manifest_version == 1:
        if proven_legacy_provider_id is None:
            raise BindingContractError("legacy_binding_unavailable")
        if (
            (obj.object_provider_id is not None and obj.object_provider_id != proven_legacy_provider_id)
            or (
                obj.cycle_provider_id is not None
                and obj.cycle_provider_id != proven_legacy_provider_id
            )
            or obj.manifest_provider_id is not None
        ):
            raise BindingContractError("legacy_binding_mismatch")
        provider_id = proven_legacy_provider_id
    elif obj.manifest_version == 2:
        provider_id = obj.object_provider_id
        if (
            provider_id is None
            or provider_id != obj.cycle_provider_id
            or provider_id != obj.manifest_provider_id
        ):
            raise BindingContractError("provider_identity_mismatch")
    else:
        raise BindingContractError("manifest_version_unsupported")

    matches = [
        binding
        for binding in bindings
        if binding.tenant_id == obj.tenant_id and binding.provider_id == provider_id
    ]
    if len(matches) != 1:
        raise BindingContractError("binding_unavailable")
    binding = matches[0]
    if obj.manifest_version == 1 and binding.provider_kind != "google_drive":
        raise BindingContractError("legacy_provider_must_be_drive")
    return binding


def _dispatch_synthetic(
    obj: SyntheticObject,
    *,
    bindings: tuple[SyntheticBinding, ...] = SYNTHETIC_BINDINGS,
    proven_legacy_provider_id: str | None = None,
    transport_calls: list[str],
) -> str:
    """Model the required pre-transport gate without an actual transport."""
    binding = _resolve_object_binding(
        obj,
        bindings=bindings,
        proven_legacy_provider_id=proven_legacy_provider_id,
    )
    transport_calls.append(binding.provider_id)
    return binding.provider_kind


def _v2_object(
    *,
    tenant_id: str = TENANT_A,
    cycle_id: str = CYCLE_DRIVE_A,
    provider_id: str = DRIVE_A,
    cycle_provider_id: str | None = None,
    manifest_provider_id: str | None = None,
) -> SyntheticObject:
    return SyntheticObject(
        tenant_id=tenant_id,
        cycle_id=cycle_id,
        object_provider_id=provider_id,
        cycle_provider_id=cycle_provider_id or provider_id,
        manifest_version=2,
        manifest_provider_id=manifest_provider_id or provider_id,
    )


def test_objects_in_distinct_cycles_route_by_their_own_provider_id() -> None:
    transport_calls: list[str] = []
    drive_object = _v2_object(cycle_id=CYCLE_DRIVE_A, provider_id=DRIVE_A)
    rclone_object = _v2_object(cycle_id=CYCLE_RCLONE_A, provider_id=RCLONE_A)

    assert _dispatch_synthetic(drive_object, transport_calls=transport_calls) == "google_drive"
    assert _dispatch_synthetic(rclone_object, transport_calls=transport_calls) == "rclone_crypt"
    assert transport_calls == [DRIVE_A, RCLONE_A]


def test_cross_tenant_binding_is_rejected_before_transport() -> None:
    transport_calls: list[str] = []
    obj = _v2_object(tenant_id=TENANT_A, provider_id=RCLONE_B)

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(obj, transport_calls=transport_calls)

    assert transport_calls == []


@pytest.mark.parametrize(
    "obj",
    (
        _v2_object(cycle_provider_id=RCLONE_A),
        _v2_object(manifest_provider_id=RCLONE_A),
        SyntheticObject(
            tenant_id=TENANT_A,
            cycle_id=CYCLE_RCLONE_A,
            object_provider_id=None,
            cycle_provider_id=RCLONE_A,
            manifest_version=2,
            manifest_provider_id=RCLONE_A,
        ),
    ),
)
def test_catalog_cycle_and_manifest_provider_must_match_before_transport(
    obj: SyntheticObject,
) -> None:
    transport_calls: list[str] = []

    with pytest.raises(BindingContractError, match="^provider_identity_mismatch$"):
        _dispatch_synthetic(obj, transport_calls=transport_calls)

    assert transport_calls == []


def test_retry_does_not_fall_back_to_another_current_binding() -> None:
    transport_calls: list[str] = []
    stored_object = _v2_object(provider_id=DRIVE_A)
    only_current_binding = (SyntheticBinding(TENANT_A, RCLONE_A, "rclone_crypt"),)

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(
            stored_object,
            bindings=only_current_binding,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_ambiguous_duplicate_binding_fails_before_transport() -> None:
    transport_calls: list[str] = []
    obj = _v2_object()
    duplicate_bindings = (
        SyntheticBinding(TENANT_A, DRIVE_A, "google_drive"),
        SyntheticBinding(TENANT_A, DRIVE_A, "google_drive"),
    )

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(
            obj,
            bindings=duplicate_bindings,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_v1_requires_proven_drive_binding_and_never_falls_back() -> None:
    transport_calls: list[str] = []
    legacy_object = SyntheticObject(TENANT_A, CYCLE_DRIVE_A, None, None, 1, None)

    with pytest.raises(BindingContractError, match="^legacy_binding_unavailable$"):
        _dispatch_synthetic(legacy_object, transport_calls=transport_calls)
    assert transport_calls == []

    assert (
        _dispatch_synthetic(
            legacy_object,
            proven_legacy_provider_id=DRIVE_A,
            transport_calls=transport_calls,
        )
        == "google_drive"
    )
    assert transport_calls == [DRIVE_A]


def test_v1_proof_cannot_resolve_to_rclone() -> None:
    transport_calls: list[str] = []
    legacy_object = SyntheticObject(TENANT_A, CYCLE_DRIVE_A, None, None, 1, None)

    with pytest.raises(BindingContractError, match="^legacy_provider_must_be_drive$"):
        _dispatch_synthetic(
            legacy_object,
            proven_legacy_provider_id=RCLONE_A,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_v1_backfilled_catalog_provider_still_requires_matching_proof() -> None:
    transport_calls: list[str] = []
    legacy_object = SyntheticObject(
        tenant_id=TENANT_A,
        cycle_id=CYCLE_DRIVE_A,
        object_provider_id=DRIVE_A,
        cycle_provider_id=DRIVE_A,
        manifest_version=1,
        manifest_provider_id=None,
    )

    with pytest.raises(BindingContractError, match="^legacy_binding_unavailable$"):
        _dispatch_synthetic(legacy_object, transport_calls=transport_calls)
    assert transport_calls == []

    assert (
        _dispatch_synthetic(
            legacy_object,
            proven_legacy_provider_id=DRIVE_A,
            transport_calls=transport_calls,
        )
        == "google_drive"
    )
    assert transport_calls == [DRIVE_A]


def test_v1_backfill_proof_must_match_persisted_catalog_provider() -> None:
    transport_calls: list[str] = []
    legacy_object = SyntheticObject(
        tenant_id=TENANT_A,
        cycle_id=CYCLE_DRIVE_A,
        object_provider_id=DRIVE_A,
        cycle_provider_id=DRIVE_A,
        manifest_version=1,
        manifest_provider_id=None,
    )

    with pytest.raises(BindingContractError, match="^legacy_binding_mismatch$"):
        _dispatch_synthetic(
            legacy_object,
            proven_legacy_provider_id=RCLONE_A,
            transport_calls=transport_calls,
        )

    assert transport_calls == []
