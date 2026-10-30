"""Verificação de continuidade de canais; não envia e-mail nem WhatsApp."""

import hashlib
import json
import os
import smtplib
import ssl

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import WhatsAppChannelSettings
from app.email_delivery import SmtpEmailProvider, email_provider_from_environment
from app.whatsapp_binding import resolve_binding


class ChannelTransitionError(RuntimeError):
    pass


def _private_digest(values):
    """Somente para o pacote cifrado; nunca emitir em recibos ou logs."""
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def inspect_channel_continuity(connection, *, network_checks: bool) -> dict:
    """Configuração/identidade iguais antes e depois; network_checks usa só leituras."""
    try:
        email = email_provider_from_environment()
        smtp_fingerprint = None
        if isinstance(email, SmtpEmailProvider):
            if network_checks:
                tls = ssl.create_default_context()
                client_type = smtplib.SMTP_SSL if email.implicit_tls else smtplib.SMTP
                kwargs = {"host": email.host, "port": email.port, "timeout": email.timeout_seconds}
                if email.implicit_tls:
                    kwargs["context"] = tls
                with client_type(**kwargs) as client:
                    client.ehlo()
                    if not email.implicit_tls:
                        client.starttls(context=tls)
                        client.ehlo()
                    client.login(email.username, email.password)
                    if client.noop()[0] != 250:
                        raise ValueError
            smtp_fingerprint = _private_digest([email.host, email.port, email.username,
                email.password, email.from_address, email.implicit_tls])
        whatsapp = []
        with (Session(bind=connection, join_transaction_mode="create_savepoint") as session,
              session.begin()):
            channels = list(session.scalars(select(WhatsAppChannelSettings).order_by(
                WhatsAppChannelSettings.id)))
            for channel in channels:
                if channel.environment != os.environ.get("APP_ENV"):
                    raise ValueError
                binding = resolve_binding(session, channel.tenant_id)
                provider = binding.provider
                if binding.name == "evolution":
                    if network_checks:
                        status = provider.connection_status()
                        if channel.status == "ready" and (
                            status.state != "open" or not status.connected_phone_e164
                            or status.connected_phone_e164 != channel.expected_phone_e164
                            or status.connected_phone_e164 != channel.connected_phone_e164
                        ):
                            raise ValueError
                    identity = [str(channel.tenant_id), provider.api_url, provider.api_key,
                        provider.instance, provider.webhook_url, provider.webhook_secret,
                        channel.expected_phone_e164, channel.connected_phone_e164]
                elif binding.name == "sandbox":
                    identity = [str(channel.tenant_id), "sandbox"]
                else:
                    raise ValueError
                whatsapp.append(_private_digest(identity))
        return {"smtp_identity": smtp_fingerprint, "whatsapp_identities": sorted(whatsapp),
                "network_checked": network_checks}
    except Exception:  # noqa: BLE001 - bibliotecas de rede/HTTP podem incluir credenciais nos erros
        raise ChannelTransitionError("Continuidade de canais não comprovada.") from None
