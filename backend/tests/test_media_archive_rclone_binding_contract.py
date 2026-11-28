"""Test-only oracle for the proposed per-object provider binding contract.

This module deliberately does not import the application worker, database, or
storage adapters. It characterizes fail-closed routing with synthetic records;
it does not prove production composition or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

TENANT_A = "00000000-0000-4000-8000-000000000001"
TENANT_B = "00000000-0000-4000-8000-000000000002"
CYCLE_DRIVE_A = "00000000-0000-4000-8000-000000000006"
CYCLE_RCLONE_A = "00000000-0000-4000-8000-000000000007"
DRIVE_A = "00000000-0000-4000-8000-000000000003"
RCLONE_A = "00000000-0000-4000-8000-000000000004"
RCLONE_B = "00000000-0000-4000-8000-000000000005"
_UNSET = object()


@dataclass(frozen=True)
class SyntheticBinding:
    tenant_id: str
    provider_id: str
    provider_kind: str


@dataclass(frozen=True)
class SyntheticBindingIdentity:
    tenant_id: str
    verified_account_subject: str
    destination_root_id: str
    provider_id: str
    credential_version: int


@dataclass(frozen=True)
class SyntheticCycle:
    tenant_id: str
    cycle_id: str
    provider_id: str | None


@dataclass(frozen=True)
class SyntheticObject:
    tenant_id: str
    cycle_id: str
    object_provider_id: str | None
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
    cycles: tuple[SyntheticCycle, ...],
    bindings: tuple[SyntheticBinding, ...],
    proven_legacy_provider_id: str | None = None,
) -> SyntheticBinding:
    """Resolve by tenant-scoped cycle and object identity.

    The V1 proof argument is only a test input; this oracle cannot discover or
    validate real historical account/root evidence.
    """
    cycle_matches = [
        cycle
        for cycle in cycles
        if cycle.tenant_id == obj.tenant_id and cycle.cycle_id == obj.cycle_id
    ]
    if len(cycle_matches) != 1:
        raise BindingContractError("cycle_unavailable")
    cycle = cycle_matches[0]

    if obj.manifest_version == 1:
        if proven_legacy_provider_id is None:
            raise BindingContractError("legacy_binding_unavailable")
        if (
            (cycle.provider_id is not None and cycle.provider_id != proven_legacy_provider_id)
            or (
                obj.object_provider_id is not None
                and obj.object_provider_id != proven_legacy_provider_id
            )
            or obj.manifest_provider_id is not None
        ):
            raise BindingContractError("legacy_binding_mismatch")
        provider_id = proven_legacy_provider_id
    elif obj.manifest_version == 2:
        provider_id = obj.object_provider_id
        if (
            provider_id is None
            or provider_id != cycle.provider_id
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
    cycles: tuple[SyntheticCycle, ...],
    bindings: tuple[SyntheticBinding, ...] = SYNTHETIC_BINDINGS,
    proven_legacy_provider_id: str | None = None,
    transport_calls: list[str],
) -> str:
    """Model the required pre-transport gate without an actual transport."""
    binding = _resolve_object_binding(
        obj,
        cycles=cycles,
        bindings=bindings,
        proven_legacy_provider_id=proven_legacy_provider_id,
    )
    transport_calls.append(binding.provider_id)
    return binding.provider_kind


def _reconnect_binding_identity(
    previous: SyntheticBindingIdentity,
    *,
    tenant_id: str,
    verified_account_subject: str,
    destination_root_id: str,
    rotated_credential_version: int,
    candidate_provider_id: str,
) -> SyntheticBindingIdentity:
    """Apply only the approved same-account-and-root binding rule."""
    same_identity_and_root = (
        previous.tenant_id == tenant_id
        and previous.verified_account_subject == verified_account_subject
        and previous.destination_root_id == destination_root_id
    )
    if same_identity_and_root:
        return SyntheticBindingIdentity(
            tenant_id=tenant_id,
            verified_account_subject=verified_account_subject,
            destination_root_id=destination_root_id,
            provider_id=previous.provider_id,
            credential_version=rotated_credential_version,
        )
    if candidate_provider_id == previous.provider_id:
        raise BindingContractError("provider_id_must_change")
    return SyntheticBindingIdentity(
        tenant_id=tenant_id,
        verified_account_subject=verified_account_subject,
        destination_root_id=destination_root_id,
        provider_id=candidate_provider_id,
        credential_version=rotated_credential_version,
    )


def _v2_records(
    *,
    tenant_id: str = TENANT_A,
    cycle_id: str = CYCLE_DRIVE_A,
    cycle_provider_id: str = DRIVE_A,
    object_provider_id: str | None | object = _UNSET,
    manifest_provider_id: str | None | object = _UNSET,
) -> tuple[SyntheticCycle, SyntheticObject]:
    object_provider = (
        cycle_provider_id if object_provider_id is _UNSET else object_provider_id
    )
    manifest_provider = (
        cycle_provider_id if manifest_provider_id is _UNSET else manifest_provider_id
    )
    return (
        SyntheticCycle(tenant_id, cycle_id, cycle_provider_id),
        SyntheticObject(
            tenant_id=tenant_id,
            cycle_id=cycle_id,
            object_provider_id=cast(str | None, object_provider),
            manifest_version=2,
            manifest_provider_id=cast(str | None, manifest_provider),
        ),
    )


def test_objects_in_distinct_cycles_route_by_each_cycle_provider() -> None:
    transport_calls: list[str] = []
    drive_cycle, drive_object = _v2_records(
        cycle_id=CYCLE_DRIVE_A,
        cycle_provider_id=DRIVE_A,
    )
    rclone_cycle, rclone_object = _v2_records(
        cycle_id=CYCLE_RCLONE_A,
        cycle_provider_id=RCLONE_A,
    )

    assert (
        _dispatch_synthetic(
            drive_object,
            cycles=(drive_cycle, rclone_cycle),
            transport_calls=transport_calls,
        )
        == "google_drive"
    )
    assert (
        _dispatch_synthetic(
            rclone_object,
            cycles=(drive_cycle, rclone_cycle),
            transport_calls=transport_calls,
        )
        == "rclone_crypt"
    )
    assert transport_calls == [DRIVE_A, RCLONE_A]


def test_object_cannot_use_a_different_provider_inside_the_same_cycle() -> None:
    transport_calls: list[str] = []
    cycle, object_row = _v2_records(
        cycle_id=CYCLE_DRIVE_A,
        cycle_provider_id=DRIVE_A,
        object_provider_id=RCLONE_A,
        manifest_provider_id=RCLONE_A,
    )

    with pytest.raises(BindingContractError, match="^provider_identity_mismatch$"):
        _dispatch_synthetic(
            object_row,
            cycles=(cycle,),
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_cross_tenant_binding_is_rejected_before_transport() -> None:
    transport_calls: list[str] = []
    cycle, obj = _v2_records(
        tenant_id=TENANT_A,
        cycle_id=CYCLE_RCLONE_A,
        cycle_provider_id=RCLONE_B,
    )

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(obj, cycles=(cycle,), transport_calls=transport_calls)

    assert transport_calls == []


@pytest.mark.parametrize(
    "cycle_provider_id,object_provider_id,manifest_provider_id",
    (
        (DRIVE_A, RCLONE_A, RCLONE_A),
        (DRIVE_A, DRIVE_A, RCLONE_A),
        (None, DRIVE_A, DRIVE_A),
        (DRIVE_A, None, DRIVE_A),
    ),
)
def test_cycle_object_and_manifest_provider_must_match(
    cycle_provider_id: str | None,
    object_provider_id: str | None,
    manifest_provider_id: str | None,
) -> None:
    transport_calls: list[str] = []
    cycle, obj = _v2_records(
        cycle_provider_id=cycle_provider_id,
        object_provider_id=object_provider_id,
        manifest_provider_id=manifest_provider_id,
    )

    with pytest.raises(BindingContractError, match="^provider_identity_mismatch$"):
        _dispatch_synthetic(obj, cycles=(cycle,), transport_calls=transport_calls)

    assert transport_calls == []


def test_missing_or_ambiguous_tenant_scoped_cycle_fails_before_transport() -> None:
    transport_calls: list[str] = []
    cycle, obj = _v2_records()

    with pytest.raises(BindingContractError, match="^cycle_unavailable$"):
        _dispatch_synthetic(obj, cycles=(), transport_calls=transport_calls)
    assert transport_calls == []

    foreign_tenant_cycle = SyntheticCycle(TENANT_B, cycle.cycle_id, cycle.provider_id)
    with pytest.raises(BindingContractError, match="^cycle_unavailable$"):
        _dispatch_synthetic(
            obj,
            cycles=(foreign_tenant_cycle,),
            transport_calls=transport_calls,
        )
    assert transport_calls == []

    duplicate_cycle = SyntheticCycle(cycle.tenant_id, cycle.cycle_id, cycle.provider_id)
    with pytest.raises(BindingContractError, match="^cycle_unavailable$"):
        _dispatch_synthetic(
            obj,
            cycles=(cycle, duplicate_cycle),
            transport_calls=transport_calls,
        )
    assert transport_calls == []


def test_retry_does_not_fall_back_to_another_current_binding() -> None:
    transport_calls: list[str] = []
    cycle, stored_object = _v2_records(cycle_provider_id=DRIVE_A)
    only_current_binding = (SyntheticBinding(TENANT_A, RCLONE_A, "rclone_crypt"),)

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(
            stored_object,
            cycles=(cycle,),
            bindings=only_current_binding,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_ambiguous_duplicate_binding_fails_before_transport() -> None:
    transport_calls: list[str] = []
    cycle, obj = _v2_records()
    duplicate_bindings = (
        SyntheticBinding(TENANT_A, DRIVE_A, "google_drive"),
        SyntheticBinding(TENANT_A, DRIVE_A, "google_drive"),
    )

    with pytest.raises(BindingContractError, match="^binding_unavailable$"):
        _dispatch_synthetic(
            obj,
            cycles=(cycle,),
            bindings=duplicate_bindings,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_v1_requires_proven_drive_binding_and_never_falls_back() -> None:
    transport_calls: list[str] = []
    legacy_cycle = SyntheticCycle(TENANT_A, CYCLE_DRIVE_A, None)
    legacy_object = SyntheticObject(TENANT_A, CYCLE_DRIVE_A, None, 1, None)

    with pytest.raises(BindingContractError, match="^legacy_binding_unavailable$"):
        _dispatch_synthetic(
            legacy_object,
            cycles=(legacy_cycle,),
            transport_calls=transport_calls,
        )
    assert transport_calls == []

    assert (
        _dispatch_synthetic(
            legacy_object,
            cycles=(legacy_cycle,),
            proven_legacy_provider_id=DRIVE_A,
            transport_calls=transport_calls,
        )
        == "google_drive"
    )
    assert transport_calls == [DRIVE_A]


def test_v1_proof_cannot_resolve_to_rclone() -> None:
    transport_calls: list[str] = []
    legacy_cycle = SyntheticCycle(TENANT_A, CYCLE_DRIVE_A, None)
    legacy_object = SyntheticObject(TENANT_A, CYCLE_DRIVE_A, None, 1, None)

    with pytest.raises(BindingContractError, match="^legacy_provider_must_be_drive$"):
        _dispatch_synthetic(
            legacy_object,
            cycles=(legacy_cycle,),
            proven_legacy_provider_id=RCLONE_A,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_v1_backfilled_catalog_provider_still_requires_matching_proof() -> None:
    transport_calls: list[str] = []
    backfilled_cycle = SyntheticCycle(TENANT_A, CYCLE_DRIVE_A, DRIVE_A)
    backfilled_object = SyntheticObject(
        TENANT_A,
        CYCLE_DRIVE_A,
        DRIVE_A,
        1,
        None,
    )

    with pytest.raises(BindingContractError, match="^legacy_binding_unavailable$"):
        _dispatch_synthetic(
            backfilled_object,
            cycles=(backfilled_cycle,),
            transport_calls=transport_calls,
        )
    assert transport_calls == []

    assert (
        _dispatch_synthetic(
            backfilled_object,
            cycles=(backfilled_cycle,),
            proven_legacy_provider_id=DRIVE_A,
            transport_calls=transport_calls,
        )
        == "google_drive"
    )
    assert transport_calls == [DRIVE_A]


def test_v1_backfill_proof_must_match_persisted_catalog_and_cycle() -> None:
    transport_calls: list[str] = []
    backfilled_cycle = SyntheticCycle(TENANT_A, CYCLE_DRIVE_A, DRIVE_A)
    backfilled_object = SyntheticObject(
        TENANT_A,
        CYCLE_DRIVE_A,
        RCLONE_A,
        1,
        None,
    )

    with pytest.raises(BindingContractError, match="^legacy_binding_mismatch$"):
        _dispatch_synthetic(
            backfilled_object,
            cycles=(backfilled_cycle,),
            proven_legacy_provider_id=DRIVE_A,
            transport_calls=transport_calls,
        )

    assert transport_calls == []


def test_reconnect_same_verified_account_and_root_preserves_provider_id() -> None:
    previous = SyntheticBindingIdentity(
        tenant_id=TENANT_A,
        verified_account_subject="synthetic-subject-account-a",
        destination_root_id="synthetic-root-a",
        provider_id=RCLONE_A,
        credential_version=1,
    )

    reconnected = _reconnect_binding_identity(
        previous,
        tenant_id=TENANT_A,
        verified_account_subject="synthetic-subject-account-a",
        destination_root_id="synthetic-root-a",
        rotated_credential_version=2,
        candidate_provider_id=RCLONE_B,
    )

    assert reconnected.provider_id == previous.provider_id
    assert reconnected.credential_version == 2


@pytest.mark.parametrize(
    "tenant_id,verified_account_subject,destination_root_id",
    (
        (TENANT_A, "synthetic-subject-account-b", "synthetic-root-a"),
        (TENANT_A, "synthetic-subject-account-a", "synthetic-root-b"),
        (TENANT_B, "synthetic-subject-account-a", "synthetic-root-a"),
    ),
)
def test_reconnect_account_or_root_change_requires_new_provider_id(
    tenant_id: str,
    verified_account_subject: str,
    destination_root_id: str,
) -> None:
    previous = SyntheticBindingIdentity(
        tenant_id=TENANT_A,
        verified_account_subject="synthetic-subject-account-a",
        destination_root_id="synthetic-root-a",
        provider_id=RCLONE_A,
        credential_version=1,
    )

    changed = _reconnect_binding_identity(
        previous,
        tenant_id=tenant_id,
        verified_account_subject=verified_account_subject,
        destination_root_id=destination_root_id,
        rotated_credential_version=1,
        candidate_provider_id=RCLONE_B,
    )

    assert changed.provider_id == RCLONE_B
    assert changed.provider_id != previous.provider_id


def test_existing_object_keeps_old_binding_after_new_binding_is_created() -> None:
    transport_calls: list[str] = []
    old_cycle, old_object = _v2_records(
        cycle_id=CYCLE_DRIVE_A,
        cycle_provider_id=RCLONE_A,
    )
    new_cycle, new_object = _v2_records(
        cycle_id=CYCLE_RCLONE_A,
        cycle_provider_id=RCLONE_B,
    )
    both_bindings = (
        SyntheticBinding(TENANT_A, RCLONE_A, "rclone_crypt"),
        SyntheticBinding(TENANT_A, RCLONE_B, "rclone_crypt"),
    )

    assert (
        _dispatch_synthetic(
            old_object,
            cycles=(old_cycle, new_cycle),
            bindings=both_bindings,
            transport_calls=transport_calls,
        )
        == "rclone_crypt"
    )
    assert (
        _dispatch_synthetic(
            new_object,
            cycles=(old_cycle, new_cycle),
            bindings=both_bindings,
            transport_calls=transport_calls,
        )
        == "rclone_crypt"
    )
    assert transport_calls == [RCLONE_A, RCLONE_B]


def test_changed_identity_cannot_reuse_previous_provider_id() -> None:
    previous = SyntheticBindingIdentity(
        tenant_id=TENANT_A,
        verified_account_subject="synthetic-subject-account-a",
        destination_root_id="synthetic-root-a",
        provider_id=RCLONE_A,
        credential_version=1,
    )

    with pytest.raises(BindingContractError, match="^provider_id_must_change$"):
        _reconnect_binding_identity(
            previous,
            tenant_id=TENANT_A,
            verified_account_subject="synthetic-subject-account-a",
            destination_root_id="synthetic-root-b",
            rotated_credential_version=2,
            candidate_provider_id=RCLONE_A,
        )
