from __future__ import annotations

from copy import deepcopy

import pytest

from app.environment_transition_inventory import (
    BIOMETRIC_COUNTERS,
    CONFIG_DIGEST_NAMES,
    CREDENTIAL_COUNTERS,
    EXPECTED_SERVICES,
    RETIRED_SERVICES,
    EnvironmentInventoryError,
    build_environment_inventory,
    classify_external_integrations,
    render_environment_inventory,
)


def _input_values(**overrides):
    services = []
    for name in sorted(EXPECTED_SERVICES):
        retired = name in RETIRED_SERVICES
        services.append({
            "name": name,
            "status": "missing" if retired else "running",
            "health": "unknown" if retired else "healthy",
            "image_digest": None if retired else "sha256:" + "1" * 64,
            "revision": None if retired else "a" * 40,
            "ports": ([{"host_ip": "127.0.0.1", "host_port": 8080}] if name == "nginx" else []),
        })
    values = {
        "source_environment": "staging",
        "target_environment": "production",
        "code_revision": "a" * 40,
        "schema_revision": "20261024_0088",
        "services": services,
        "configuration_digests": {name: "b" * 64 for name in CONFIG_DIGEST_NAMES},
        "credential_counts": {name: 1 for name in CREDENTIAL_COUNTERS},
        "biometric_counts": {name: 0 for name in BIOMETRIC_COUNTERS},
        "whatsapp_binding_counts": [],
        "integration_evidence": {
            name: {
                "enabled": False,
                "credential_matches_target": None,
                "provider_validated_for_target": None,
            }
            for name in ("facial", "smtp", "whatsapp")
        },
        "live_payment_gate": False,
        "unknown_consumer_count": 0,
    }
    values.update(overrides)
    return values


def _inventory(**overrides):
    values = _input_values(**overrides)
    return build_environment_inventory(**values)


def test_approved_fingerprint_is_stable_and_contains_only_sanitized_metadata() -> None:
    first = _inventory()
    second_input = _input_values()
    second_input["source_environment"] = "STAGING"
    second_input["services"] = list(reversed(second_input["services"]))
    second_input["configuration_digests"] = dict(reversed(list(second_input["configuration_digests"].items())))
    second_input["credential_counts"] = dict(reversed(list(second_input["credential_counts"].items())))
    second_input["biometric_counts"] = dict(reversed(list(second_input["biometric_counts"].items())))
    second_input["integration_evidence"] = dict(
        reversed(list(second_input["integration_evidence"].items())))
    second = build_environment_inventory(**second_input)

    assert first["blockers"] == []
    assert first["approval_fingerprint"] == second["approval_fingerprint"]
    rendered = render_environment_inventory(first)
    assert "staging" not in rendered
    assert "token-secret-sentinel" not in rendered
    assert "/opt/" not in rendered


@pytest.mark.parametrize(
    ("overrides", "expected_blocker"),
    [
        ({"source_environment": "private-environment-sentinel"}, "ambiente_origem_invalido"),
        ({"live_payment_gate": True}, "gate_pagamentos_nao_fechado"),
        ({"live_payment_gate": None}, "gate_pagamentos_nao_fechado"),
        ({"unknown_consumer_count": 1}, "consumidor_nao_classificado"),
        ({"integration_evidence": {
            name: {
                "enabled": name == "facial",
                "credential_matches_target": None,
                "provider_validated_for_target": None,
            }
            for name in ("facial", "smtp", "whatsapp")
        }}, "integracao_nao_classificada"),
        ({"biometric_counts": {**{name: 0 for name in BIOMETRIC_COUNTERS},
                                "photo_embeddings": 1}}, "dados_biometricos_vinculados_a_origem"),
        ({"services": []}, "inventario_servicos_incompleto"),
    ],
)
def test_blocked_inventory_never_issues_approval_fingerprint(overrides, expected_blocker) -> None:
    inventory = _inventory(**overrides)
    rendered = render_environment_inventory(inventory)

    assert expected_blocker in inventory["blockers"]
    assert inventory["approval_fingerprint"] is None
    assert "private-environment-sentinel" not in rendered
    assert "tenant-id-sentinel" not in rendered
    assert "ciphertext-sentinel" not in rendered


def test_unrecognized_port_binding_blocks_fingerprint_without_echo() -> None:
    values = _input_values()
    services = deepcopy(values["services"])
    nginx = next(service for service in services if service["name"] == "nginx")
    nginx["ports"] = [{"host_ip": "sensitive-host-sentinel", "host_port": 8080}]
    values["services"] = services

    inventory = build_environment_inventory(**values)
    rendered = render_environment_inventory(inventory)

    assert "portas_divergentes" in inventory["blockers"]
    assert inventory["approval_fingerprint"] is None
    assert "sensitive-host-sentinel" not in rendered


def test_whatsapp_bindings_are_aggregated_by_safe_environment_category() -> None:
    bindings = [
        {"environment_category": "outro_ambiente_conhecido", "status": "ready", "count": 2},
        {"environment_category": "production", "status": "sandbox", "count": 1},
    ]
    values = _input_values(whatsapp_binding_counts=bindings)
    inventory = build_environment_inventory(**values)
    rendered = render_environment_inventory(inventory)

    assert inventory["whatsapp_binding_counts"] == sorted(
        bindings, key=lambda item: (item["environment_category"], item["status"]),
    )
    assert inventory["approval_fingerprint"]
    assert "tenant-id-sentinel" not in rendered
    assert "phone-sentinel" not in rendered


def test_whatsapp_binding_rejects_raw_environment_label_without_echo() -> None:
    values = _input_values(whatsapp_binding_counts=[
        {"environment_category": "private-environment-sentinel", "status": "ready", "count": 1},
    ])
    with pytest.raises(EnvironmentInventoryError) as caught:
        build_environment_inventory(**values)

    assert str(caught.value) == "contagens_whatsapp_invalidas"
    assert "private-environment-sentinel" not in str(caught.value)


def test_render_rejects_unreviewed_extra_fields() -> None:
    inventory = _inventory()
    inventory["secret_sentinel"] = "must-not-render"

    with pytest.raises(EnvironmentInventoryError) as caught:
        render_environment_inventory(inventory)

    assert str(caught.value) == "inventario_invalido"
    assert "must-not-render" not in str(caught.value)


@pytest.mark.parametrize(
    ("enabled", "credential_matches", "provider_validated", "expected"),
    [
        (False, None, None, "desativado"),
        (True, True, True, "validado_destino"),
        (True, True, False, "nao_classificado"),
        (True, False, True, "nao_classificado"),
        (True, None, None, "nao_classificado"),
        (None, True, True, "nao_classificado"),
    ],
)
def test_external_integration_classification_is_fail_closed(
    enabled, credential_matches, provider_validated, expected,
) -> None:
    evidence = {
        name: {
            "enabled": enabled,
            "credential_matches_target": credential_matches,
            "provider_validated_for_target": provider_validated,
        }
        for name in ("facial", "smtp", "whatsapp")
    }

    assert set(classify_external_integrations(evidence).values()) == {expected}


@pytest.mark.parametrize("counter", sorted(BIOMETRIC_COUNTERS))
def test_any_environment_bound_biometric_ciphertext_blocks_transition(counter) -> None:
    inventory = _inventory(biometric_counts={
        **{name: 0 for name in BIOMETRIC_COUNTERS}, counter: 1,
    })

    assert "dados_biometricos_vinculados_a_origem" in inventory["blockers"]
    assert inventory["approval_fingerprint"] is None
