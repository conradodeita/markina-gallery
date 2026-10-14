"""Limites HTTP do upload de referência antes do processamento biométrico."""

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.main import read_bounded_body


def _request(chunks: list[bytes], *, content_length: str | None = None) -> Request:
    messages = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]

    async def receive():
        return messages.pop(0) if messages else {"type": "http.request", "body": b"", "more_body": False}

    headers = [] if content_length is None else [(b"content-length", content_length.encode())]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers}, receive)


def test_bounded_body_accepts_chunks_at_the_exact_limit() -> None:
    payload = asyncio.run(
        read_bounded_body(
            _request([b"jpeg", b"data"]),
            max_bytes=8,
            error_detail="limite",
        )
    )
    assert payload == b"jpegdata"


@pytest.mark.parametrize(
    "upload_request",
    (
        _request([b"12345", b"6789"]),
        _request([b"small"], content_length="999"),
        _request([b"small"], content_length="inválido"),
        _request([]),
    ),
)
def test_bounded_body_rejects_oversized_invalid_or_empty_upload(
    upload_request: Request,
) -> None:
    with pytest.raises(HTTPException) as captured:
        asyncio.run(
            read_bounded_body(upload_request, max_bytes=8, error_detail="limite")
        )
    assert captured.value.status_code == 413
    assert captured.value.detail == "limite"
