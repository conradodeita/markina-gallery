"""Validação do Turnstile com transporte HTTP sintético, sem chamada externa."""

import json

import httpx
import pytest

from app.photographer_turnstile import (
    EXPECTED_ACTION,
    SITEVERIFY_URL,
    TurnstileConfigurationError,
    TurnstileSettings,
    TurnstileUnavailable,
    TurnstileVerifier,
    settings_from_environment,
)


def test_turnstile_is_off_by_default_and_requires_exact_safe_configuration(monkeypatch):
    monkeypatch.delenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED", raising=False)
    assert settings_from_environment() is None

    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED", "true")
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SITE_KEY", "synthetic-public-site-key")
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY", "synthetic-secret-value")
    settings = settings_from_environment()
    assert settings is not None
    assert settings.expected_hostname == "pickyourpic.com.br"
    assert "synthetic-secret-value" not in repr(settings)

    monkeypatch.delenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY")
    with pytest.raises(TurnstileConfigurationError):
        settings_from_environment()

    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_SECRET_KEY", "synthetic-secret-value")
    monkeypatch.setenv("PHOTOGRAPHER_SIGNUP_TURNSTILE_HOSTNAME", "*.pickyourpic.com.br")
    with pytest.raises(TurnstileConfigurationError):
        settings_from_environment()


def test_turnstile_posts_only_secret_and_token_then_checks_exact_hostname_and_action():
    captured = []

    def siteverify(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"success": True, "hostname": "PICKYOURPIC.COM.BR.", "action": EXPECTED_ACTION},
        )

    settings = TurnstileSettings(
        site_key="synthetic-site-key",
        secret_key="synthetic-secret-key",
        expected_hostname="pickyourpic.com.br",
    )
    verifier = TurnstileVerifier(settings, transport=httpx.MockTransport(siteverify))

    assert verifier.verify("synthetic-one-use-token") is True
    request = captured[0]
    assert str(request.url) == SITEVERIFY_URL
    assert request.method == "POST"
    assert json.loads(request.read()) == {
        "secret": "synthetic-secret-key",
        "response": "synthetic-one-use-token",
    }
    assert b"remoteip" not in request.read()
    assert "synthetic-secret-key" not in repr(verifier)


@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "hostname": "pickyourpic.com.br", "action": EXPECTED_ACTION},
        {"success": True, "hostname": "another.example", "action": EXPECTED_ACTION},
        {"success": True, "hostname": "pickyourpic.com.br", "action": "login"},
    ],
)
def test_turnstile_rejects_invalid_success_hostname_or_action(payload):
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    verifier = TurnstileVerifier(
        TurnstileSettings("synthetic-site-key", "synthetic-secret-key"),
        transport=transport,
    )
    assert verifier.verify("synthetic-token") is False


@pytest.mark.parametrize("body", [b"not-json", b"[]"])
def test_turnstile_malformed_siteverify_response_fails_as_unavailable(body):
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=body, headers={"Content-Type": "application/json"})
    )
    verifier = TurnstileVerifier(
        TurnstileSettings("synthetic-site-key", "synthetic-secret-key"),
        transport=transport,
    )
    with pytest.raises(TurnstileUnavailable):
        verifier.verify("synthetic-token")


def test_turnstile_http_failure_and_invalid_token_fail_closed_without_retry():
    requests = []

    def fail(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503, json={"success": False})

    verifier = TurnstileVerifier(
        TurnstileSettings("synthetic-site-key", "synthetic-secret-key"),
        transport=httpx.MockTransport(fail),
    )
    assert verifier.verify("") is False
    assert verifier.verify("x" * 2049) is False
    assert requests == []
    with pytest.raises(TurnstileUnavailable):
        verifier.verify("synthetic-token")
    assert len(requests) == 1
