"""Oracle metadata collector. Pipe over an already authorized SSH connection.

Reads only the named Compose project's metadata and selected package metadata.
Does not inspect environment maps, credentials, application data or logs.
"""
import datetime
import json
import pathlib
import platform
import subprocess


def run(args):
    return subprocess.check_output(args, universal_newlines=True, stderr=subprocess.DEVNULL).strip()


def collect():
    result = {
        "schema_version": 1,
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project": "markina-gallery",
        "host_architecture": platform.machine(),
        "checkout_sha": run(["git", "-C", "/opt/markina-gallery", "rev-parse", "HEAD"]),
        "services": {}, "state": {},
    }
    ids = run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=markina-gallery"]).splitlines()
    fmt = (
        '{"container_id":"{{.Id}}","image_id":"{{.Image}}","reference":{{json .Config.Image}},'
        '"status":{{json .State.Status}},"started_at":{{json .State.StartedAt}},'
        '"health":{{if index .State "Health"}}{{json (index (index .State "Health") "Status")}}{{else}}null{{end}},'
        '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
        '"config_hash":{{json (index .Config.Labels "com.docker.compose.config-hash")}},'
        '"ports":{{json .NetworkSettings.Ports}}}'
    )
    imagefmt = '{"id":"{{.Id}}","repo_digests":{{json .RepoDigests}},"architecture":{{json .Architecture}},"os":{{json .Os}}}'
    pycode = (
        "import importlib.metadata as m,json; names=['aiohttp','multidict','urllib3','yarl']; result={};\n"
        "for n in names:\n try: result[n]=m.version(n)\n except m.PackageNotFoundError: result[n]=None\n"
        "print(json.dumps(result))"
    )
    nodecode = (
        "const fs=require('fs'); const names=['next','react','react-dom'];"
        "console.log(JSON.stringify(Object.fromEntries(names.map(n=>{let p='/app/node_modules/'+n+'/package.json';"
        "return [n,fs.existsSync(p)?JSON.parse(fs.readFileSync(p,'utf8')).version:null]}))))"
    )
    python_services = {
        "api", "worker", "face-search-worker", "face-index-worker", "face-maintenance-worker",
        "face-gemma-index-worker", "preview-adjustment-worker", "raw-development-worker",
    }
    for cid in ids:
        item = json.loads(run(["docker", "inspect", "--format", fmt, cid]))
        item["image"] = json.loads(run(["docker", "image", "inspect", "--format", imagefmt, item["image_id"]]))
        service = item["service"]
        if service in result["services"]:
            raise ValueError("duplicate_service_requires_review")
        if item["status"] == "running" and service in python_services:
            item["packages"] = json.loads(run(["docker", "exec", "-e", "PYTHONDONTWRITEBYTECODE=1", cid, "python", "-B", "-c", pycode]))
        if item["status"] == "running" and service == "web":
            item["packages"] = json.loads(run(["docker", "exec", cid, "node", "-e", nodecode]))
        if item["status"] == "running" and service == "api":
            # Only this non-secret revision field, never the environment map.
            item["source_sha"] = run(["docker", "exec", cid, "printenv", "APP_VERSION"])
        result["services"][service] = item
    for name in ("web-current.identity", "web-previous.identity", "app-last-healthy.sha", "app-previous.sha"):
        path = pathlib.Path("/var/lib/markina-gallery/deploy-state") / name
        if path.is_file() and not path.is_symlink():
            result["state"][name] = path.read_text().strip()
    return result


if __name__ == "__main__":
    print(json.dumps(collect(), sort_keys=True))
