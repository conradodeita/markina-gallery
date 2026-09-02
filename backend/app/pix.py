"""Validação EMV/BR Code e renderização local de QR PIX."""

import base64
from io import BytesIO

import qrcode


class PixCodeError(ValueError):
    pass


def _crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def normalize_pix_copy_paste(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    if len(normalized) > 4_000 or any(ord(character) < 32 for character in normalized):
        raise PixCodeError("O código PIX copia e cola contém caracteres inválidos.")

    fields: dict[str, str] = {}
    position = 0
    try:
        while position < len(normalized):
            tag = normalized[position : position + 2]
            length_text = normalized[position + 2 : position + 4]
            if len(tag) != 2 or len(length_text) != 2 or not length_text.isdigit():
                raise PixCodeError("O código PIX copia e cola está malformado.")
            length = int(length_text)
            value_start = position + 4
            value_end = value_start + length
            if value_end > len(normalized):
                raise PixCodeError("O código PIX copia e cola está incompleto.")
            fields[tag] = normalized[value_start:value_end]
            position = value_end
    except UnicodeError as exc:
        raise PixCodeError("O código PIX copia e cola está malformado.") from exc

    required = {"00": "01", "52": None, "53": "986", "58": "BR", "59": None, "60": None}
    if any(tag not in fields for tag in required) or any(
        expected is not None and fields[tag] != expected for tag, expected in required.items()
    ):
        raise PixCodeError("O código não representa um PIX copia e cola brasileiro válido.")
    if len(normalized) < 8 or normalized[-8:-4] != "6304":
        raise PixCodeError("O código PIX não contém o verificador obrigatório.")
    expected_crc = _crc16_ccitt(normalized[:-4])
    if normalized[-4:].upper() != expected_crc:
        raise PixCodeError("O verificador do código PIX é inválido.")
    return normalized[:-4] + normalized[-4:].upper()


def pix_qr_data_url(copy_paste: str) -> str:
    normalized = normalize_pix_copy_paste(copy_paste)
    if not normalized:
        raise PixCodeError("Informe o código PIX antes de gerar o QR Code.")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(normalized)
    qr.make(fit=True)
    output = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
