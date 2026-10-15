"""Contrato das guardas do wrapper; comandos Docker/SSH são fronteiras isoladas."""
import copy
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "reset-homolog-owner.sh").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "maintenance-homolog.yml").read_text(encoding="utf-8")


def topology_fixture():
    volumes = {"source": "media-source", "derivatives": "media-derivatives", "history": "media-history",
               "facial-references": "facial-references", "branding": "branding-assets", "raw-staging": "media-raw-staging"}
    environment = {"APP_ENV": "staging", "DATABASE_URL": "postgresql+psycopg://synthetic@db/markina_gallery",
                   "PUBLIC_APP_ORIGIN": "https://markina.pickyourpic.com.br", "REDIS_URL": "redis://redis:6379/0"}
    cfg = {"name": "markina-gallery", "volumes": {v: {"name": f"markina-gallery_{v}"} for v in volumes.values()},
           "services": {"api": {"environment": environment, "volumes": [
               {"target": f"/var/lib/markina/{k}", "source": v} for k, v in volumes.items()]},
               "db": {"environment": {"POSTGRES_DB": "markina_gallery"}}, "redis": {}, "evolution-db": {},
               "evolution-redis": {}, "nginx": {"ports": [{"published": "8080", "host_ip": "127.0.0.1"}]}}}
    actual = {"Image": "sha256:synthetic", "Config": {"Labels": {"com.docker.compose.project": "markina-gallery"},
              "Env": [f"{k}={v}" for k, v in environment.items()]}, "Mounts": [
                  {"Destination": f"/var/lib/markina/{k}", "Name": f"markina-gallery_{v}"} for k, v in volumes.items()]}
    return cfg, actual


def accepted(cfg, actual, image_id="sha256:synthetic"):
    policy = SCRIPT.split("compose --profile whatsapp-real config --format json | python3 -c '\n", 1)[1].split("\n' || fail", 1)[0]
    def docker_output(args):
        if args[:2] == ["docker", "inspect"]:
            return json.dumps([actual]).encode()
        assert args == ["docker", "image", "inspect", "markina-gallery-api"]
        return json.dumps([{"Id": image_id}]).encode()
    with patch.dict(os.environ, {"MARKINA_RESET_API_ID": "synthetic-api"}), \
            patch("sys.stdin", io.StringIO(json.dumps(cfg))), patch("subprocess.check_output", docker_output), \
            redirect_stdout(io.StringIO()):
        try:
            exec(compile(policy, "owner-reset-topology", "exec"), {})  # noqa: S102 - executa só a política versionada sob fronteiras mockadas
        except SystemExit:
            return False
    return True


def main():
    cfg, actual = topology_fixture()
    assert accepted(cfg, actual)
    assert not accepted(cfg, actual, image_id="sha256:unpublished")
    for mutate in (
        lambda c, a: c.update(name="another-project"),
        lambda c, a: c["services"]["api"]["environment"].update(APP_ENV="production"),
        lambda c, a: c["services"]["api"]["environment"].update(PUBLIC_APP_ORIGIN="https://other.test"),
        lambda c, a: a["Config"].update(Env=["DATABASE_URL=postgresql://synthetic@other-db/other"]),
        lambda c, a: c["services"]["nginx"]["ports"][0].update(host_ip="0.0.0.0"),
        lambda c, a: c["services"]["db"].update(ports=[{"published": "5432"}]),
        lambda c, a: a["Mounts"][0].update(Name="another-project_media-source"),
        lambda c, a: c["volumes"]["media-raw-staging"].update(name="other_raw"),
        lambda c, a: a["Config"]["Labels"].update({"com.docker.compose.project": "other"}),
    ):
        changed_cfg, changed_actual = copy.deepcopy(cfg), copy.deepcopy(actual)
        mutate(changed_cfg, changed_actual)
        assert not accepted(changed_cfg, changed_actual)
    workflow = yaml.safe_load(WORKFLOW)
    on = workflow.get("on", workflow.get(True))
    assert set(on) == {"workflow_dispatch"}
    assert on["workflow_dispatch"]["inputs"]["mode"]["options"] == ["inventory", "execute", "owner-inventory", "owner-execute"]
    job = workflow["jobs"]["homolog-data"]
    assert job["if"] == "github.ref == 'refs/heads/develop'"
    registration = workflow["jobs"]["registration"]
    assert registration["if"] == "github.ref != 'refs/heads/develop'"
    assert "environment" not in registration and "env" not in registration
    assert "ssh" not in str(registration["steps"])
    assert job["environment"] == "homolog"
    assert job["permissions"] == {"contents": "read"}
    for guard in ("refs/heads/develop", "RESET_HOMOLOG_TO_OWNER_AND_DELETE_164_DUMPS_WITHOUT_BACKUP", "EXPECTED_APP_SHA", "--owner-email", "--expected-sha"):
        assert guard in WORKFLOW
    for guard in ("verify_writer_id", "writer ainda ativo", "writer ativo fora da pausa conferida", "writers mantidos pausados",
                  "evolution_snapshot", "Evolution mudou durante a manutenção", "os.W_OK | os.X_OK", "github\\.com/conradodeita/markina-gallery", "--no-deps", "--pull never", "flock -n", "pending.json", "MARKINA_RESET_SCRIPT_SHA256"):
        assert guard in SCRIPT
    for forbidden in ("pg_dump", "docker system prune", "compose down", "rm -rf", "alembic", "git checkout", "git reset"):
        assert forbidden not in SCRIPT
    print("owner-reset policy: ok")


if __name__ == "__main__":
    main()
