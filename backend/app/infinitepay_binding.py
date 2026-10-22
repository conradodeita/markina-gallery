"""Credenciais InfinitePay próprias do fotógrafo, fornecidas pelo servidor."""

from __future__ import annotations

import json
import os
import re
from uuid import UUID


class InfinitePayBindingError(RuntimeError):
    """Binding ausente, ambíguo ou incompatível com o ambiente atual."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InfinitePayBindingError("Binding InfinitePay indisponível.")
        result[key] = value
    return result


def _aliases(environ: dict[str, str]) -> dict[UUID, str]:
    try:
        value = json.loads(environ.get("INFINITEPAY_TENANT_BINDINGS", "{}"),
                           object_pairs_hook=_unique_pairs)
        if not isinstance(value, dict):
            raise InfinitePayBindingError("Binding InfinitePay indisponível.")
        result: dict[UUID, str] = {}
        for owner, alias in value.items():
            tenant_id = UUID(owner)
            if (str(tenant_id) != owner or not isinstance(alias, str)
                    or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", alias)
                    or alias in result.values()):
                raise InfinitePayBindingError("Binding InfinitePay indisponível.")
            result[tenant_id] = alias
        return result
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        raise InfinitePayBindingError("Binding InfinitePay indisponível.") from None


def api_key_for_tenant(tenant_id: UUID, *, environ: dict[str, str] | None = None, db=None) -> str | None:
    """Resolve apenas a chave do tenant pedido; nunca usa fallback de outra conta."""
    if db is not None:
        from app.infinitepay_credentials import current_key
        from app.integration_secrets import IntegrationSecretError

        try:
            return current_key(db, tenant_id=tenant_id)
        except IntegrationSecretError:
            raise InfinitePayBindingError("Binding InfinitePay indisponível.") from None
    values = os.environ if environ is None else environ
    alias = _aliases(values).get(tenant_id)
    if alias is None:
        return None
    prefix = f"INFINITEPAY_BINDING_{alias}_"
    current_environment = values.get("APP_ENV", "development").strip()
    credential_environment = values.get(prefix + "CREDENTIAL_ENV", "").strip()
    api_key = values.get(prefix + "API_KEY", "").strip()
    if (not current_environment or credential_environment != current_environment
            or not api_key or len(api_key) > 512
            or any(not 32 <= ord(character) <= 126 for character in api_key)):
        raise InfinitePayBindingError("Binding InfinitePay indisponível.")
    return api_key


def api_key_configured(tenant_id: UUID, *, db=None) -> bool:
    try:
        return api_key_for_tenant(tenant_id, db=db) is not None
    except InfinitePayBindingError:
        return False
