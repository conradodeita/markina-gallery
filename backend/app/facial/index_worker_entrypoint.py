"""Entrypoint dedicado aos jobs de indexação do acervo."""

from __future__ import annotations

from app.facial.face_worker import main

if __name__ == "__main__":
    main("index")
