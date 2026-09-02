from app.pix import PixCodeError, normalize_pix_copy_paste, pix_qr_data_url


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
