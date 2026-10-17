import csv
from io import StringIO

from app.statistics_report import CSV_HEADERS, report_csv, report_html


def test_csv_keeps_item_rows_exact_and_escapes_delimiter_and_quotes():
    row = {header: "" for header in CSV_HEADERS}
    row.update({
        "pedido_id": "pedido-1", "cliente_nome": 'Ana; "Fotógrafa"',
        "fotografia_nome": "foto;final.jpg", "quantidade": 1,
        "valor_unitario": 123456, "total_item": 123456,
        "forma_pagamento": "pix", "conta_destino": "Nubank", "categoria": "Fotografia",
    })
    content = report_csv([row])
    parsed = list(csv.DictReader(StringIO(content), delimiter=";"))
    assert content.startswith("pedido_id;cliente_nome;cliente_telefone;")
    assert len(parsed) == 1
    assert parsed[0]["cliente_nome"] == 'Ana; "Fotógrafa"'
    assert parsed[0]["fotografia_nome"] == "foto;final.jpg"
    assert parsed[0]["valor_unitario"] == "1234.56"
    assert parsed[0]["total_item"] == "1234.56"
    assert "total_pedido" not in parsed[0]


def test_html_is_self_contained_and_escapes_customer_content():
    report = {
        "orders": [{"confirmed_at": "", "client_name": "<script>alert(1)</script>",
            "gallery_name": "Galeria", "status": "pending", "total_cents": 0}],
        "items": [], "by_gallery": [], "by_folder": [], "abandoned": [], "selected_not_purchased": [],
        "reconciliations": [{"order_id": "order-1", "order_total_cents": 0, "items_total_cents": 50, "difference_cents": -50}],
        "revenue_cents": 0, "confirmed_order_count": 0, "sold_photo_count": 0,
        "conversion_rate_percent": None, "converted_selection_count": 0, "eligible_selection_count": 0,
        "selection_metrics_available": True,
    }
    html = report_html(report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "R$ -0.50" in html
    assert "<style>" in html and "https://" not in html and "<script" not in html
