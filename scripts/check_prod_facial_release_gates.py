#!/usr/bin/env python3
"""Emite elegibilidade fail-closed para release facial de produção."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "openspec/changes/improve-client-face-reference-capture/production-gates.json"
)
payload = json.loads(path.read_text(encoding="utf-8"))
gates = payload.get("gates")
ready = payload.get("release_ready") is True and isinstance(gates, dict) and bool(gates)
pending: list[str] = []
for name, gate in (gates.items() if isinstance(gates, dict) else []):
    if (
        not isinstance(gate, dict)
        or gate.get("status") != "aprovado"
        or not isinstance(gate.get("evidence"), str)
        or not gate["evidence"].strip()
    ):
        ready = False
        pending.append(str(name))

value = "true" if ready else "false"
print(f"release_ready={value}")
print(f"gates_pendentes={','.join(pending) if pending else 'nenhum'}")
output = os.environ.get("GITHUB_OUTPUT")
if output:
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"release_ready={value}\n")
if not ready:
    print("Release facial bloqueado: cada gate precisa de status aprovado e evidência verificável.")
