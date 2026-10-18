"""CSV financeiro: uma linha por pedido, sem ativos ou dados bancários."""

import csv
from datetime import UTC, datetime
from io import StringIO
from zoneinfo import ZoneInfo

HEADERS = ["Nome do cliente", "Item/descrição", "Total dos itens/pedido", "Data e hora"]


def safe_text(value: str) -> str:
    # Excel pode interpretar fórmulas mesmo depois de espaço/control character.
    normalized = value.lstrip()
    if normalized.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def payment_orders_csv(groups: list[dict]) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADERS)
    for group in groups:
        for order in group["orders"]:
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
            writer.writerow([
                safe_text(group["client"]["name"]),
                safe_text(f'{quantity} fotografias — {order["parent_gallery"]["name"]}'),
                f"{cents // 100},{cents % 100:02d}", confirmed_at,
            ])
    return output.getvalue().encode("utf-8-sig")
