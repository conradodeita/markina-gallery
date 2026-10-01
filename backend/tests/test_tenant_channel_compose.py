"""Configuração Compose resolvida; nenhum container ou segredo real é utilizado."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONSUMERS = {"api", "worker", "face-search-worker"}


@pytest.mark.parametrize("present", [False, True])
def test_optional_bindings_reach_only_transport_consumers(tmp_path, present):
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Verificação exige CLI Docker Compose, sem daemon.")
    bindings = tmp_path / "synthetic-bindings.env"
    values = {
        "WHATSAPP_TENANT_BINDINGS": '{"11111111-1111-4111-8111-111111111111":"A"}',
        "WHATSAPP_BINDING_A_PROVIDER": "sandbox",
        "WHATSAPP_BINDING_A_API_KEY": "synthetic-$literal #hash=tail",
    }
    if present:
        bindings.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    baseline = tmp_path / "synthetic-legacy.env"
    baseline.write_text("WHATSAPP_PROVIDER=sandbox\nWHATSAPP_INSTANCE=synthetic-legacy\n", encoding="utf-8")
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("WHATSAPP_", "COMPOSE_"))}
    environment["WHATSAPP_BINDINGS_ENV_FILE"] = str(bindings)
    resolved = subprocess.run([
        docker, "compose", "--env-file", str(baseline), "-p", "pyp-bindings-test",
        "-f", str(ROOT / "docker/docker-compose.yml"), "--profile", "facial",
        "config", "--format", "json",
    ], env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
    assert resolved.returncode == 0, "Compose não resolveu a configuração sintética."
    services = json.loads(resolved.stdout)["services"]
    assert CONSUMERS <= services.keys()
    for name, service in services.items():
        delivered = service.get("environment", {})
        for key, expected in values.items():
            if present and name in CONSUMERS:
                # A saída canonical de `config` escapa dólares para poder
                # ser reutilizada como Compose sem interpolar o valor raw.
                assert delivered.get(key) == expected.replace("$", "$$"), (name, key)
            else:
                assert key not in delivered, (name, key)
        if name in CONSUMERS:
            assert delivered["WHATSAPP_PROVIDER"] == "sandbox"
            assert delivered["WHATSAPP_INSTANCE"] == "synthetic-legacy"
