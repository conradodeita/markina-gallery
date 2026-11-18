"""Constantes e transporte HTTP compartilhados pelos adaptadores Google Drive."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

import httpx

SCOPE = "https://www.googleapis.com/auth/drive.file"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"


class DriveTransport(Protocol):
    """Fronteira HTTP substituível por transporte sintético nos testes."""

    def post(self, url: str, **kwargs: Any) -> httpx.Response: ...

    def get(self, url: str, **kwargs: Any) -> httpx.Response: ...

    def put(self, url: str, **kwargs: Any) -> httpx.Response: ...

    def patch(self, url: str, **kwargs: Any) -> httpx.Response: ...


class HttpxDriveTransport:
    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=httpx.Timeout(8.0, connect=3.0), follow_redirects=False) as client:
            return client.request(method, url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self._request("POST", url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(2):
            response = self._request("GET", url, **kwargs)
            if response.status_code not in {429, 500, 502, 503, 504} or attempt == 1:
                return response
            time.sleep(0.1)
        raise AssertionError("tentativa HTTP GET esgotada sem resposta")

    @contextmanager
    def stream_get(self, url: str, **kwargs: Any) -> Iterator[httpx.Response]:
        """Lê conteúdo binário em streaming, mantendo o cliente aberto durante o consumo."""
        kwargs.setdefault("timeout", httpx.Timeout(120.0, connect=3.0))
        with httpx.Client(follow_redirects=False) as client, client.stream(
            "GET", url, **kwargs
        ) as response:
            yield response

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        # Upload é uma operação de escrita; não repete chunks automaticamente.
        kwargs.setdefault("timeout", httpx.Timeout(120.0, connect=3.0))
        return self._request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        kwargs.setdefault("timeout", httpx.Timeout(30.0, connect=3.0))
        return self._request("PATCH", url, **kwargs)
