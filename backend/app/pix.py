"""Validação/geração EMV BR Code e renderização local de QR PIX."""

import base64
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

import qrcode


class PixCodeError(ValueError):
    pass


@dataclass(frozen=True)
class PixConfiguration:
    input_type: str
    input_value: str
    copy_paste: str
    receiver_name: str | None = None
    receiver_city: str | None = None


def _crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _emv_field(tag: str, value: str) -> str:
    encoded_length = len(value.encode("utf-8"))
    if encoded_length > 99:
        raise PixCodeError("Um campo necessário ao PIX excede o tamanho permitido.")
    return f"{tag}{encoded_length:02d}{value}"


def _ascii_pix_text(value: str | None, *, label: str, maximum: int) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip().upper())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = re.sub(r"[^A-Z0-9 ]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        raise PixCodeError(f"Informe {label} para gerar o QR a partir da chave PIX.")
    if len(normalized) > maximum:
        raise PixCodeError(f"{label.capitalize()} excede o tamanho permitido de {maximum} caracteres.")
    return normalized


def _valid_cpf(value: str) -> bool:
    if len(value) != 11 or value == value[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(digit) * weight for digit, weight in zip(value[:size], range(size + 1, 1, -1)))
        check = (total * 10 % 11) % 10
        if int(value[size]) != check:
            return False
    return True


def _normalize_simple_key(value: str) -> tuple[str, str]:
    candidate = value.strip()
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", candidate):
        if len(candidate) > 77:
            raise PixCodeError("O e-mail informado excede o tamanho aceito para chave PIX.")
        return "email", candidate.lower()

    digits = re.sub(r"\D", "", candidate)
    looks_like_cpf = bool(re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", candidate))
    if len(digits) == 11 and (looks_like_cpf or _valid_cpf(digits)):
        if not _valid_cpf(digits):
            raise PixCodeError("Informe um CPF válido como chave PIX.")
        return "cpf", digits

    if digits.startswith("55") and len(digits) in {12, 13}:
        national = digits[2:]
    elif len(digits) in {10, 11}:
        national = digits
    else:
        national = ""
    if national and 10 <= int(national[:2]) <= 99:
        if len(national) == 11 and national[2] != "9":
            raise PixCodeError("Celular brasileiro deve incluir o dígito 9 após o DDD.")
        return "phone", f"+55{national}"

    raise PixCodeError(
        "Informe um CPF, telefone brasileiro, e-mail ou código PIX copia e cola válido."
    )


def build_static_pix_code(
    key: str,
    *,
    receiver_name: str,
    receiver_city: str,
) -> str:
    """Monta BR Code estático sem valor; o banco confirma o recebedor ao pagar."""

    name = _ascii_pix_text(receiver_name, label="o nome do recebedor", maximum=25)
    city = _ascii_pix_text(receiver_city, label="a cidade do recebedor", maximum=15)
    merchant_account = _emv_field("00", "BR.GOV.BCB.PIX") + _emv_field("01", key)
    additional_data = _emv_field("05", "***")
    payload = "".join(
        (
            _emv_field("00", "01"),
            _emv_field("26", merchant_account),
            _emv_field("52", "0000"),
            _emv_field("53", "986"),
            _emv_field("58", "BR"),
            _emv_field("59", name),
            _emv_field("60", city),
            _emv_field("62", additional_data),
            "6304",
        )
    )
    return payload + _crc16_ccitt(payload)


def normalize_pix_configuration(
    value: str | None,
    *,
    receiver_name: str | None = None,
    receiver_city: str | None = None,
) -> PixConfiguration | None:
    if value is None or not value.strip():
        return None
    candidate = value.strip()
    if candidate.startswith("000201"):
        copy_paste = normalize_pix_copy_paste(candidate)
        if not copy_paste:
            return None
        return PixConfiguration("br_code", copy_paste, copy_paste)
    input_type, key = _normalize_simple_key(candidate)
    name = _ascii_pix_text(receiver_name, label="o nome do recebedor", maximum=25)
    city = _ascii_pix_text(receiver_city, label="a cidade do recebedor", maximum=15)
    copy_paste = build_static_pix_code(key, receiver_name=name, receiver_city=city)
    return PixConfiguration(input_type, key, copy_paste, name, city)


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
