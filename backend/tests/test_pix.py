from app.pix import (
    PixCodeError,
    normalize_pix_configuration,
    normalize_pix_copy_paste,
    pix_qr_data_url,
)


def _crc16(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def valid_pix_code(merchant: str = "MARKINA") -> str:
    payload = (
        "000201"
        "52040000"
        "5303986"
        "5802BR"
        f"59{len(merchant):02d}{merchant}"
        "6009SAO PAULO"
        "6304"
    )
    return payload + _crc16(payload)


def test_pix_copy_paste_is_validated_and_qr_is_generated_from_same_value() -> None:
    code = valid_pix_code()

    assert normalize_pix_copy_paste(f"  {code}  ") == code
    data_url = pix_qr_data_url(code)
    assert data_url.startswith("data:image/png;base64,")
    assert len(data_url) > 200


def test_pix_rejects_empty_structure_and_invalid_crc() -> None:
    assert normalize_pix_copy_paste("  ") is None
    for malformed in ("pix-copia-cola", valid_pix_code()[:-1] + "0"):
        try:
            normalize_pix_copy_paste(malformed)
        except PixCodeError:
            pass
        else:
            raise AssertionError("Código PIX malformado foi aceito")


def test_simple_pix_keys_generate_valid_static_br_code() -> None:
    cases = (
        ("529.982.247-25", "cpf", "52998224725"),
        ("(11) 99999-1234", "phone", "+5511999991234"),
        ("FOTOGRAFO@EXAMPLE.COM", "email", "fotografo@example.com"),
    )
    for raw_value, expected_type, expected_value in cases:
        configured = normalize_pix_configuration(
            raw_value,
            receiver_name="João Fotografia",
            receiver_city="São Paulo",
        )
        assert configured is not None
        assert configured.input_type == expected_type
        assert configured.input_value == expected_value
        assert configured.receiver_name == "JOAO FOTOGRAFIA"
        assert configured.receiver_city == "SAO PAULO"
        assert normalize_pix_copy_paste(configured.copy_paste) == configured.copy_paste
        assert pix_qr_data_url(configured.copy_paste).startswith("data:image/png;base64,")


def test_simple_pix_key_requires_valid_key_and_receiver_metadata() -> None:
    invalid = (
        ("123.456.789-00", "MARKINA", "SAO PAULO"),
        ("fotografo@example.com", "", "SAO PAULO"),
        ("11988887777", "MARKINA", ""),
        ("fotografo@example.com", "NOME DO RECEBEDOR QUE ULTRAPASSA VINTE E CINCO", "SAO PAULO"),
        ("fotografo@example.com", "MARKINA", "CIDADE QUE ULTRAPASSA QUINZE"),
        ("550e8400-e29b-41d4-a716-446655440000", "MARKINA", "SAO PAULO"),
    )
    for value, name, city in invalid:
        try:
            normalize_pix_configuration(value, receiver_name=name, receiver_city=city)
        except PixCodeError:
            pass
        else:
            raise AssertionError("Configuração PIX simples inválida foi aceita")
