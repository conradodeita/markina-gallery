"""Protocolo Unix local do instalador; não cria socket, serviço ou subprocesso."""

from __future__ import annotations

import json
import socket
import struct

MAX_REQUEST = 98304


class ProtocolError(RuntimeError):
    pass


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("request_invalid")
        result[key] = value
    return result


def _receive(connection, size):
    value = bytearray()
    while len(value) < size:
        chunk = connection.recv(min(size - len(value), 4096))
        if not chunk:
            raise ProtocolError("request_invalid")
        value.extend(chunk)
    return bytes(value)


def parse_request(payload: bytes):
    if not 1 <= len(payload) <= MAX_REQUEST:
        raise ProtocolError("request_invalid")
    request = json.loads(payload, object_pairs_hook=_unique_pairs)
    if (
        not isinstance(request, dict)
        or set(request) != {"v", "fullchain", "private_key"}
        or type(request["v"]) is not int
        or request["v"] != 1
        or not isinstance(request["fullchain"], str)
        or not isinstance(request["private_key"], str)
    ):
        raise ProtocolError("request_invalid")
    chain, key = (
        request["fullchain"].encode("ascii"),
        request["private_key"].encode("ascii"),
    )
    if not 1 <= len(chain) <= 65536 or not 1 <= len(key) <= 16384:
        raise ProtocolError("request_invalid")
    return chain, key


def handle_connection(connection: socket.socket, expected_uid: int, install):
    """Uma solicitação limitada; `install(chain,key)` é ligado pelo operador.

    A identidade vem do kernel Linux, nunca de campos do pedido. O construtor
    confiável do serviço futuro fixa UID e instalador; não há shell, Docker,
    destino ou comando selecionável pelo peer. Resposta nunca inclui PEM.
    """
    connection.settimeout(5)
    try:
        if not hasattr(socket, "SO_PEERCRED"):
            raise ProtocolError("peer_denied")
        _, uid, _ = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if not isinstance(expected_uid, int) or uid != expected_uid:
            raise ProtocolError("peer_denied")
        size = struct.unpack("!I", _receive(connection, 4))[0]
        if not 1 <= size <= MAX_REQUEST:
            raise ProtocolError("request_invalid")
        chain, key = parse_request(_receive(connection, size))
        # Instalação/validação não pode expor exceções ou retornar campos livres.
        try:
            receipt = install(chain, key)
            fingerprint, replayed = receipt["fingerprint"], receipt["replayed"]
            if (
                not isinstance(fingerprint, str)
                or len(fingerprint) != 64
                or any(c not in "0123456789abcdef" for c in fingerprint)
                or type(replayed) is not bool
            ):
                raise ValueError()
        except Exception:  # noqa: BLE001 — fronteira do instalador privilegiado, sem exceção original.
            raise ProtocolError("installation_failed") from None
        response = {"ok": True, "fingerprint": fingerprint, "replayed": replayed}
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RecursionError,
        ProtocolError,
    ) as error:
        # ProtocolError só é construído com os códigos fixos acima.
        code = str(error) if isinstance(error, ProtocolError) else "request_invalid"
        response = {"ok": False, "error": code}
    try:
        connection.sendall(json.dumps(response, separators=(",", ":")).encode() + b"\n")
    except OSError:
        pass
