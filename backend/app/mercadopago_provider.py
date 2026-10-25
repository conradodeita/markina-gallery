"""Adaptador do SDK oficial; somente endpoints Orders e conta recebedora."""

import json
import re

import httpx
import mercadopago
from mercadopago.config import RequestOptions
from mercadopago.errors.exceptions import MercadoPagoError as SDKError
from mercadopago.http import HttpClient


class MercadoPagoError(RuntimeError):
    def __init__(self, category="unavailable", status=None):
        self.category = category
        self.status = status
        super().__init__("Não foi possível consultar o Mercado Pago com segurança.")


class BoundedTransport(HttpClient):
    """Mantém o SDK e limita rede, redirects, retries e corpo sem logar payload."""

    def request(self, method, url, maxretries=None, **kwargs):
        if not url.startswith("https://api.mercadopago.com/"):
            raise MercadoPagoError("invalid_endpoint")
        try:
            with (
                httpx.Client(timeout=15, follow_redirects=False) as client,
                client.stream(method, url, headers=kwargs.get("headers"),
                              params=kwargs.get("params"), content=kwargs.get("data")) as response,
            ):
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 131072:
                        raise MercadoPagoError("invalid_response")
                data = json.loads(body) if body else {}
                return {"status": response.status_code, "response": data}
        except (httpx.HTTPError, ValueError):
            raise MercadoPagoError() from None


class OrdersProvider:
    def __init__(self, token):
        self.sdk = mercadopago.SDK(
            token, http_client=BoundedTransport(),
            request_options=RequestOptions(connection_timeout=15.0, max_retries=0),
        )

    def _call(self, operation, *args, **kwargs):
        try:
            result = operation(*args, **kwargs)
        except MercadoPagoError:
            raise
        except SDKError as exc:
            category = "unauthorized" if exc.status_code in (401, 403) else "unavailable"
            raise MercadoPagoError(category, exc.status_code) from None
        except (ValueError, TypeError, KeyError):
            # SDK exceptions may carry a complete financial request or secret.
            raise MercadoPagoError() from None
        status = result.get("status")
        if not isinstance(status, int) or not 200 <= status < 300:
            category = "unauthorized" if status in (401, 403) else "unavailable"
            raise MercadoPagoError(category, status)
        data = result.get("response")
        if not isinstance(data, dict):
            raise MercadoPagoError("invalid_response")
        return data

    def identity(self):
        return self._call(self.sdk.user().get)

    def create(self, body, key):
        options = RequestOptions(custom_headers={"x-idempotency-key": str(key)}, max_retries=0)
        return self._call(self.sdk.order().create, body, request_options=options)

    def get(self, order_id):
        if not re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", order_id):
            raise MercadoPagoError("invalid_order_id")
        return self._call(self.sdk.order().get, order_id)

    def search(self, *, reference, begin_date, end_date):
        return self._call(self.sdk.order().search, {
            "external_reference": reference, "type": "online",
            "begin_date": begin_date, "end_date": end_date, "page": 1, "page_size": 20,
        })

    def cancel(self, order_id, key):
        if not re.fullmatch(r"ORD[A-Za-z0-9]{1,61}", order_id):
            raise MercadoPagoError("invalid_order_id")
        return self._call(self.sdk.order().cancel, order_id, request_options=RequestOptions(
            custom_headers={"x-idempotency-key": str(key)}, max_retries=0))
