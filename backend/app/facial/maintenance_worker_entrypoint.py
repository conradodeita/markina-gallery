"""Entrypoint dedicado a purge e retenção facial."""

from __future__ import annotations

from app.facial.face_worker import main

if __name__ == "__main__":
    main("maintenance")
