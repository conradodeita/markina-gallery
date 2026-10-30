import pytest

from app.facial.crypto import FacialCryptoContext, FacialCryptoContextPair
from app.facial.environment_migration_guard import (
    BiometricWritePermit,
    BiometricWritePreflight,
    FacialWriteGuardError,
    authorize_biometric_migration_write,
    run_guarded_biometric_write,
)

_SOURCE = FacialCryptoContext.from_keyring(
    environment="staging",
    active_key_id="source",
    keys={"source": b"s" * 32},
)
_TARGET = FacialCryptoContext.from_keyring(
    environment="production",
    active_key_id="target",
    keys={"target": b"t" * 32},
)
_CONTEXTS = FacialCryptoContextPair(source=_SOURCE, destination=_TARGET)
_INVENTORY = "a" * 64
_PLAN = "b" * 64
_CONSUMERS = frozenset(
    {"api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker"}
)


def _valid_preflight(**overrides) -> BiometricWritePreflight:
    values = {
        "contexts": _CONTEXTS,
        "current_inventory_fingerprint": _INVENTORY,
        "approved_inventory_fingerprint": _INVENTORY,
        "backup_inventory_fingerprint": _INVENTORY,
        "inventory_current": True,
        "backup_authenticated_and_reopened": True,
        "backup_record_count": 3,
        "expected_record_count": 3,
        "operation_plan_fingerprint": _PLAN,
        "approved_plan_fingerprint": _PLAN,
        "plan_reviewed": True,
        "approval_confirmation": f"APPLY_BIOMETRIC_CONTEXT:{_INVENTORY}:{_PLAN}",
        "paused_consumers": _CONSUMERS,
        "active_job_count": 0,
        "reference_file_count": 0,
        "reference_locator_count": 0,
        "unknown_reference_entry_count": 0,
        "nonempty_notification_count": 0,
        "facial_processing_enabled": False,
        "live_payments_allowed": False,
        "app_environment_before": "staging",
        "app_environment_after": "staging",
    }
    values.update(overrides)
    return BiometricWritePreflight(**values)


def test_valid_preflight_issues_redacted_in_memory_permit():
    permit = authorize_biometric_migration_write(_valid_preflight())

    assert isinstance(permit, BiometricWritePermit)
    assert permit.source_environment == "staging"
    assert permit.target_environment == "production"
    assert repr(permit) == "BiometricWritePermit(<redacted>)"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"inventory_current": False}, "inventory_unverified"),
        ({"approved_inventory_fingerprint": "c" * 64}, "fingerprint_mismatch"),
        ({"backup_inventory_fingerprint": "c" * 64}, "fingerprint_mismatch"),
        ({"backup_authenticated_and_reopened": False}, "backup_unverified"),
        ({"backup_record_count": 2}, "record_count_mismatch"),
        ({"plan_reviewed": False}, "plan_unverified"),
        ({"approved_plan_fingerprint": "c" * 64}, "plan_unverified"),
        ({"approval_confirmation": ""}, "approval_missing"),
        ({"paused_consumers": frozenset({"api"})}, "consumers_not_paused"),
        ({"active_job_count": 1}, "jobs_active"),
        ({"facial_processing_enabled": True}, "production_gates_open"),
        ({"live_payments_allowed": True}, "production_gates_open"),
        ({"app_environment_after": "production"}, "app_env_changed"),
    ],
)
def test_any_missing_or_divergent_gate_prevents_first_write(changes, reason):
    invoked = []

    def write(_permit):
        invoked.append(True)

    with pytest.raises(FacialWriteGuardError) as error:
        run_guarded_biometric_write(
            _valid_preflight(**changes),
            write=write,
        )

    assert error.value.reason_code == reason
    assert str(error.value) == "Preflight de transição biométrica bloqueado."
    assert invoked == []


def test_valid_gates_authorize_only_the_passed_write_callback():
    observed = []

    result = run_guarded_biometric_write(
        _valid_preflight(),
        write=lambda permit: observed.append(permit.inventory_fingerprint),
    )

    assert result is None
    assert observed == [_INVENTORY]


@pytest.mark.parametrize("field", [
    "reference_file_count", "reference_locator_count",
    "unknown_reference_entry_count", "nonempty_notification_count",
])
@pytest.mark.parametrize("value", [None, 1, -1, False])
def test_sql_only_guard_rejects_unverified_or_unsupported_storage(field, value):
    called = []
    with pytest.raises(FacialWriteGuardError) as error:
        run_guarded_biometric_write(
            _valid_preflight(**{field: value}), write=lambda _: called.append(True),
        )
    assert error.value.reason_code == "unsupported_storage_present"
    assert not called


def test_invalid_fingerprint_shape_and_non_boolean_attestations_fail_closed():
    with pytest.raises(FacialWriteGuardError) as fingerprint_error:
        authorize_biometric_migration_write(
            _valid_preflight(current_inventory_fingerprint="private-inventory-value")
        )
    with pytest.raises(FacialWriteGuardError) as attestation_error:
        authorize_biometric_migration_write(_valid_preflight(inventory_current="yes"))

    assert fingerprint_error.value.reason_code == "invalid_preflight"
    assert attestation_error.value.reason_code == "inventory_unverified"


def test_guard_accepts_only_known_nonproduction_to_production_contexts():
    wrong_target = FacialCryptoContextPair(
        source=_SOURCE,
        destination=FacialCryptoContext.from_keyring(
            environment="development",
            active_key_id="target",
            keys={"target": b"t" * 32},
        ),
    )

    with pytest.raises(FacialWriteGuardError) as error:
        authorize_biometric_migration_write(
            _valid_preflight(contexts=wrong_target)
        )

    assert error.value.reason_code == "environment_context_invalid"
