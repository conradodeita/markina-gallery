from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import environment_transition_channels as channels
from app import environment_transition_runtime as runtime
from app.email_delivery import SmtpEmailProvider


def test_runtime_blocks_open_flags_and_unpaused_writer_before_engine(monkeypatch):
    creator = Mock(side_effect=AssertionError("Must not open database"))
    monkeypatch.setattr(runtime, "create_engine", creator)
    monkeypatch.setenv("FACIAL_PROCESSING_ENABLED", "true")
    monkeypatch.setenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS", "false")
    with pytest.raises(ValueError):
        runtime.run_runtime("apply", "synthetic", inventory=None, plan=None, paused=True, network_checks=False)
    monkeypatch.setenv("FACIAL_PROCESSING_ENABLED", "false")
    monkeypatch.setenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS", "true")
    with pytest.raises(ValueError):
        runtime.run_runtime("prepare", "synthetic", inventory=None, plan=None, paused=False, network_checks=False)
    monkeypatch.setenv("MERCADOPAGO_ALLOW_LIVE_PAYMENTS", "false")
    with pytest.raises(ValueError):
        runtime.run_runtime("apply", "synthetic", inventory=None, plan=None, paused=False, network_checks=False)
    creator.assert_not_called()


def test_reference_directory_is_never_cleared_to_make_preflight_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("FACIAL_REFERENCE_ROOT", str(tmp_path))
    entry = tmp_path / "synthetic.reference"
    entry.write_bytes(b"synthetic ciphertext")
    with pytest.raises(ValueError):
        runtime.require_reference_store_empty()
    assert entry.read_bytes() == b"synthetic ciphertext"
    entry.unlink()
    runtime.require_reference_store_empty()


@pytest.mark.parametrize('busy', [False, True])
def test_idle_proof_is_read_only_has_no_backup_or_payload_and_refuses_active_jobs(monkeypatch, busy):
    from app import environment_transition_bundle as bundle
    events = []
    connection = SimpleNamespace(
        exec_driver_sql=lambda sql: events.append(sql),
        execute=lambda _: SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: ['20261026_0090'])))
    engine = SimpleNamespace(begin=lambda: nullcontext(connection), dispose=Mock())
    monkeypatch.setattr(runtime, 'create_engine', lambda *a, **kw: engine)
    monkeypatch.setattr(runtime, 'require_reference_store_empty', lambda: None)
    monkeypatch.setattr(runtime, 'preservation_metadata_verified', lambda _: None)
    monkeypatch.setattr(runtime, 'contexts_for', lambda _: (None, None, None))
    loader = Mock(side_effect=AssertionError('Must not read backup or payload'))
    monkeypatch.setattr(runtime, 'load_bundle', loader)
    def idle(_):
        assert events[0] == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
        if busy:
            raise bundle.CutoverBundleError('Jobs ativos.')
    monkeypatch.setattr(bundle, 'assert_sql_only_idle', idle)
    for key, value in {'FACIAL_PROCESSING_ENABLED': 'false', 'MERCADOPAGO_ALLOW_LIVE_PAYMENTS': 'false',
                       'APP_ENV': 'staging', 'DATABASE_URL': 'synthetic'}.items():
        monkeypatch.setenv(key, value)
    if busy:
        with pytest.raises(bundle.CutoverBundleError):
            runtime.run_runtime('idle', 'synthetic', inventory=None, plan=None, paused=False, network_checks=False)
    else:
        result = runtime.run_runtime('idle', 'synthetic', inventory=None, plan=None, paused=False, network_checks=False)
        assert result['consumers_idle'] is True
    loader.assert_not_called()
    engine.dispose.assert_called_once()


def test_channel_check_authenticates_without_send_or_pairing(monkeypatch):
    email = SmtpEmailProvider(host="synthetic.invalid", port=587, username="synthetic-user",
        password="synthetic-secret", from_address="synthetic@sample.invalid")
    monkeypatch.setattr(channels, "email_provider_from_environment", lambda: email)
    operations = []

    class SMTP:
        def __init__(self, **kwargs):
            operations.append("connect")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def ehlo(self):
            operations.append("ehlo")
        def starttls(self, **kwargs):
            operations.append("tls")
        def login(self, username, password):
            assert password == "synthetic-secret"
            operations.append("auth")
        def noop(self):
            operations.append("noop")
            return 250, b"ok"

    monkeypatch.setattr(channels.smtplib, "SMTP", SMTP)
    channel = SimpleNamespace(environment="staging", tenant_id="synthetic-tenant", status="ready",
        expected_phone_e164="+5511999999999", connected_phone_e164="+5511999999999")
    session = SimpleNamespace(begin=lambda: nullcontext(), scalars=lambda _: [channel])
    monkeypatch.setattr(channels, "Session", lambda **kwargs: nullcontext(session))
    provider = SimpleNamespace(api_url="http://synthetic.invalid", api_key="synthetic-key",
        instance="synthetic-instance", webhook_url="https://synthetic.invalid/webhook",
        webhook_secret="synthetic-hook", connection_status=lambda: SimpleNamespace(
            state="open", connected_phone_e164=channel.expected_phone_e164))
    monkeypatch.setattr(channels, "resolve_binding", lambda *args: SimpleNamespace(
        name="evolution", provider=provider))
    monkeypatch.setenv("APP_ENV", "staging")
    result = channels.inspect_channel_continuity(None, network_checks=True)
    assert result["network_checked"] is True
    assert operations == ["connect", "ehlo", "tls", "ehlo", "auth", "noop"]
    assert "synthetic-secret" not in repr(result)
    provider.connection_status = lambda: SimpleNamespace(state="open", connected_phone_e164="+5511888888888")
    with pytest.raises(channels.ChannelTransitionError):
        channels.inspect_channel_continuity(None, network_checks=True)
