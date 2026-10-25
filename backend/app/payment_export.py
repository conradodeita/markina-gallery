"""CSV financeiro: uma linha por pedido, sem ativos ou dados bancários."""

import csv
from datetime import UTC, datetime
from io import StringIO
from zoneinfo import ZoneInfo

HEADERS = ["Nome do cliente", "Item/descrição", "Total dos itens/pedido", "Data e hora"]
FINANCIAL_HEADERS = ["Pedido", "Compra", "Provedor", "Método", "Estado do pedido",
                     "Situação financeira", "Estado da order externa", "Estado da transação"]


def safe_text(value: str) -> str:
    # Excel pode interpretar fórmulas mesmo depois de espaço/control character.
    normalized = value.lstrip()
    if normalized.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def payment_orders_csv(groups: list[dict], *, include_financial_details: bool = False) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow([*HEADERS, *FINANCIAL_HEADERS] if include_financial_details else HEADERS)
    for group in groups:
        for order in group["orders"]:
            mp = order.get("mercadopago") or {}
            if mp.get("test_account") and not include_financial_details:
                continue
            quantity = sum(len(folder["items"]) for folder in order["folders"])
            cents = order["total_cents"]
            confirmed_at = ""
            if order.get("confirmed_at"):
                instant = datetime.fromisoformat(order["confirmed_at"])
                if instant.tzinfo is None:
                    instant = instant.replace(tzinfo=UTC)
                confirmed_at = instant.astimezone(ZoneInfo("America/Sao_Paulo")).strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            test_prefix = "TESTE — " if mp.get("test_account") else ""
            row = [
                safe_text(group["client"]["name"]),
                safe_text(f'{test_prefix}{quantity} fotografias — {order["parent_gallery"]["name"]}'),
                f"{cents // 100},{cents % 100:02d}", confirmed_at,
            ]
            if include_financial_details:
                row.extend(safe_text(str(value or "")) for value in (
                    order["id"], mp.get("id") or order.get("provider_payment_id")
                    or ((order.get("communication") or {}).get("payment_group") or {}).get("id"),
                    order.get("payment_provider"), order.get("payment_method"),
                    order.get("payment_status"), order.get("financial_status"),
                    "/".join(filter(None, [mp.get("order_status"), mp.get("order_detail")])),
                    "/".join(filter(None, [mp.get("transaction_status"), mp.get("transaction_detail")])),
                ))
            writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")
