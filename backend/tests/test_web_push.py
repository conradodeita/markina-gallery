import base64
import socket
from uuid import uuid4

import pytest

from app import web_push as transport
from tests.test_push_subscriptions import subscription


def payload():
    return {"id": str(uuid4()), "title": "Pagamento confirmado", "body": "Seu pedido foi confirmado.",
            "path": "/library"}


def test_encrypts_vapid_payload_without_network_or_logs(monkeypatch, caplog):
    monkeypatch.setenv("WEB_PUSH_VAPID_PRIVATE_KEY", base64.urlsafe_b64encode(b"a" * 32).decode())
    monkeypatch.setenv("WEB_PUSH_VAPID_SUBJECT", "mailto:synthetic@example.invalid")
    captured = {}
    def post(_self, url, data, headers, **kwargs):
        captured.update(url=url, data=data, headers=headers, kwargs=kwargs)
        response = transport.Response()
        response.status_code = 201
        response._content = b""
        return response
    monkeypatch.setattr(transport.PushHTTPS, "post", post)
    content = payload()
    transport.send_push(subscription(), content)
    assert content["body"].encode() not in captured["data"]
    assert captured["headers"]["content-encoding"] == "aes128gcm"
    assert captured["headers"]["ttl"] == "3600"
    assert "authorization" in captured["headers"]
    assert not caplog.text


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fd00::1", "224.0.0.1", "ff02::1"])
def test_rejects_internal_dns_answers(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))])
    with pytest.raises(transport.PushFailure, match="destination_blocked"):
        transport.resolve_public("fcm.googleapis.com")


def test_socket_connects_only_to_validated_address_without_second_dns(monkeypatch):
    connected = []
    class FakeSocket:
        def settimeout(self, _timeout): pass
        def connect(self, address): connected.append(address)
        def close(self): pass
    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: FakeSocket())
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: pytest.fail("Segundo DNS permitiria rebinding"))
    connection = transport.PinnedHTTPS("fcm.googleapis.com", (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)))
    connection._pinned_socket(("fcm.googleapis.com", 443), 8)
    assert connected == [("8.8.8.8", 443)]
    assert connection.host == "fcm.googleapis.com"  # TLS/SNI e certificado permanecem hostname


def test_redirect_never_followed_and_remote_body_not_read(monkeypatch):
    monkeypatch.setattr(transport, "resolve_public", lambda _host: "resolved")
    calls = []
    class FakeConnection:
        def __init__(self, *args): pass
        def request(self, *args, **kwargs): calls.append(args)
        def getresponse(self):
            class Remote:
                status = 302
                def read(self): pytest.fail("Corpo remoto não deve ser lido")
            return Remote()
        def close(self): pass
    monkeypatch.setattr(transport, "PinnedHTTPS", FakeConnection)
    response = transport.PushHTTPS().post("https://fcm.googleapis.com/fcm/send/opaque", b"encrypted", {})
    assert response.status_code == 302 and response.text == ""
    assert len(calls) == 1


@pytest.mark.parametrize("path", ["https://evil.invalid", "//evil.invalid", "/api/admin", "/library?token=secret", "/gallery/../admin"])
def test_payload_navigation_is_constrained(path):
    with pytest.raises(transport.PushFailure):
        transport.validate_payload({**payload(), "path": path})


def test_invalid_payload_and_missing_config_never_connect(monkeypatch):
    monkeypatch.setattr(transport.PushHTTPS, "post", lambda *_a, **_k: pytest.fail("Não enviar"))
    with pytest.raises(transport.PushFailure):
        transport.send_push(subscription(), {**payload(), "body": "a" * 141})
    monkeypatch.delenv("WEB_PUSH_VAPID_PRIVATE_KEY", raising=False)
    with pytest.raises(transport.PushFailure, match="configuration_required"):
        transport.send_push(subscription(), payload())
