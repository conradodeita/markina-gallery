"""Adaptador RFC Web Push: criptografia da biblioteca e transporte HTTPS fixado ao IP validado."""

import base64
import ipaddress
import json
import os
import re
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPSConnection
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from requests import Response

from app.push_subscriptions import validate_endpoint, validate_subscription

DNS_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="push-dns")
DNS_SLOTS = BoundedSemaphore(2)
SEND_TIMEOUT = 8


def push_configuration_ready() -> bool:
    """Somente valida; nunca gera chaves nem expõe configuração privada."""
    try:
        private = os.environ.get("WEB_PUSH_VAPID_PRIVATE_KEY", "")
        public = os.environ.get("WEB_PUSH_VAPID_PUBLIC_KEY", "")
        subject = os.environ.get("WEB_PUSH_VAPID_SUBJECT", "")
        if not re.fullmatch(r"[A-Za-z0-9_+/=-]{40,500}", private) or not re.fullmatch(r"mailto:[^\s@]+@[^\s@]+", subject):
            return False
        key = Vapid.from_string(private).public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(key).decode().rstrip("=") == public.rstrip("=")
    except (ValueError, TypeError):
        return False


class PushFailure(Exception):
    def __init__(self, category: str, *, status: int = 0, transient=False, ambiguous=False):
        super().__init__(category)
        self.category, self.status = category, status
        self.transient, self.ambiguous = transient, ambiguous


def safe_target(path: str) -> bool:
    return bool(isinstance(path, str) and re.fullmatch(
        r"/(?:admin(?:/payments|/galleries/[0-9a-f-]{36}|/galleries/sources/[0-9a-f-]{36}/edit/imagens)?"
        r"|library|gallery/[0-9a-f-]{36}|public-galleries/[0-9a-f-]{36})", path))


def validate_payload(payload: dict) -> str:
    if not isinstance(payload, dict) or set(payload) != {"id", "title", "body", "path"}:
        raise PushFailure("invalid_payload")
    if not isinstance(payload["id"], str) or not re.fullmatch(r"[0-9a-f-]{36}", payload["id"]):
        raise PushFailure("invalid_payload")
    for key, limit in (("title", 60), ("body", 140)):
        value = payload[key]
        if not isinstance(value, str) or not 1 <= len(value) <= limit or any(ord(c) < 32 for c in value):
            raise PushFailure("invalid_payload")
    if not safe_target(payload["path"]):
        raise PushFailure("invalid_destination")
    return json.dumps(payload, ensure_ascii=False)


def resolve_public(host: str):
    if not DNS_SLOTS.acquire(blocking=False):
        raise PushFailure("dns_busy", transient=True)
    future = DNS_POOL.submit(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
    future.add_done_callback(lambda _: DNS_SLOTS.release())
    try:
        addresses = future.result(timeout=3)
    except (TimeoutError, OSError):
        future.cancel()
        raise PushFailure("dns_unavailable", transient=True) from None
    parsed = [ipaddress.ip_address(row[4][0]) for row in addresses]
    if not parsed or any(not address.is_global or address.is_multicast for address in parsed):
        raise PushFailure("destination_blocked")
    return addresses[0]


class PinnedHTTPS(HTTPSConnection):
    def __init__(self, host, resolved):
        super().__init__(host, timeout=SEND_TIMEOUT, context=ssl.create_default_context())
        self.resolved = resolved
        # A conexão TCP usa o endereço numérico já validado. TLS continua validando o hostname.
        self._create_connection = self._pinned_socket

    def _pinned_socket(self, _address, timeout, _source_address=None):
        family, socktype, proto, _, address = self.resolved
        stream = socket.socket(family, socktype, proto)
        try:
            stream.settimeout(timeout)
            stream.connect(address)
            return stream
        except OSError:
            stream.close()
            raise


class PushHTTPS:
    """Interface mínima para requests_session; sem proxies, redirects ou corpo de resposta."""
    def post(self, url, data, headers, timeout=None, **_kwargs):
        del timeout
        parsed = urlsplit(validate_endpoint(url))
        resolved = resolve_public(parsed.hostname)
        connection = PinnedHTTPS(parsed.hostname, resolved)
        try:
            connection.request("POST", parsed.path + (f"?{parsed.query}" if parsed.query else ""),
                               body=data, headers=headers)
            remote = connection.getresponse()
            result = Response()
            result.status_code = remote.status
            result._content = b""  # jamais incorporar corpo do provedor em exceções/logs
            result.reason = "push_provider"
            return result
        except (OSError, TimeoutError):
            raise PushFailure("transport_interrupted", transient=True, ambiguous=True) from None
        finally:
            connection.close()


def send_push(subscription: dict, payload: dict, *, ttl: int = 3600):
    try:
        subscription = validate_subscription(subscription)
        data = validate_payload(payload)
        private_key = os.environ.get("WEB_PUSH_VAPID_PRIVATE_KEY", "")
        subject = os.environ.get("WEB_PUSH_VAPID_SUBJECT", "")
        if not re.fullmatch(r"[A-Za-z0-9_+/=-]{40,500}", private_key) or not re.fullmatch(
            r"mailto:[^\s@]+@[^\s@]+", subject):
            raise PushFailure("configuration_required")
        vapid = Vapid.from_string(private_key)
        response = webpush(subscription_info=subscription, data=data, vapid_private_key=vapid,
                           vapid_claims={"sub": subject}, requests_session=PushHTTPS(),
                           ttl=max(1, min(ttl, 3600)), timeout=SEND_TIMEOUT, verbose=False,
                           headers={"Topic": payload["id"].replace("-", "")})
        if response.status_code not in {200, 201, 202}:
            raise PushFailure("provider_rejected", status=response.status_code)
    except WebPushException as exc:
        code = exc.response.status_code if exc.response is not None else 0
        raise PushFailure("subscription_expired" if code in {404, 410} else "provider_rejected",
                          status=code, transient=code == 429 or code >= 500) from None
    except (ValueError, KeyError, TypeError):
        raise PushFailure("invalid_configuration_or_subscription") from None
