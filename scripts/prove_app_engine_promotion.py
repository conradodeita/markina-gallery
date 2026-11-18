"""Exercise the root-only Docker Engine promotion boundary on a disposable CI runner."""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import production_app_compose_bridge as bridge

BASE_IMAGE = "docker.io/library/python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
OLD_REVISION = "1" * 40
RECEIPT_HASH = hashlib.sha256(b"synthetic-engine-receipt").hexdigest()
SERVER_PROGRAM = (
    "import os; from http.server import BaseHTTPRequestHandler,HTTPServer; "
    f"body=(os.environ['PROOF_SERVICE']+('-old' if os.environ['APP_VERSION']=='{OLD_REVISION}' "
    "else '-target')+'\\n').encode(); "
    "H=type('H',(BaseHTTPRequestHandler,),{'do_GET':lambda self:(self.send_response(200),"
    "self.end_headers(),self.wfile.write(body))}); "
    "HTTPServer(('0.0.0.0',8000),H).serve_forever()"
)


def require_ci_runner():
    if (os.name != "posix" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.geteuid() != 0 or not Path("/var/run/docker.sock").is_socket()):
        raise SystemExit("Somente runner GitHub-hosted descartável com Docker root é permitido")


def configure_runner_context():
    runner_root = Path(__file__).resolve().parent.parent
    if not runner_root.is_dir():
        raise SystemExit("Checkout do runner não está disponível para a prova Engine")

    original_run = bridge._run

    def run_in_runner_workspace(argv, *, cwd=None, app_version="", input_text=None,
                                timeout=120, max_output=bridge.MAX_COMMAND_OUTPUT_BYTES):
        effective_cwd = runner_root if cwd is None else cwd
        return original_run(argv, cwd=effective_cwd, app_version=app_version, input_text=input_text,
                            timeout=timeout, max_output=max_output)

    bridge.PROJECT_ROOT = runner_root
    bridge._run = run_in_runner_workspace

    fixed = Path("/usr/bin/docker")
    if fixed.is_file() and os.access(fixed, os.X_OK):
        return

    executable = shutil.which("docker")
    if (not isinstance(executable, str) or not executable.startswith("/")
            or not Path(executable).is_file() or not os.access(executable, os.X_OK)):
        raise SystemExit("CLI Docker absoluto não está disponível no runner")

    def run_bridge_docker(args, *, input_text=None, timeout=120,
                          max_output=bridge.MAX_COMMAND_OUTPUT_BYTES):
        return bridge._run([executable, *args], input_text=input_text, timeout=timeout, max_output=max_output)

    bridge._docker = run_bridge_docker


def run(stage, *args, timeout=240):
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("prova Engine falhou em " + stage) from None
    if result.returncode:
        raise RuntimeError("prova Engine falhou em " + stage)
    return result.stdout.strip()


def inspect(identity):
    result = json.loads(run("inspect", "docker", "inspect", identity))
    if len(result) != 1 or not isinstance(result[0], dict):
        raise RuntimeError("inspect Engine não retornou identidade única")
    return result[0]


def require_unused_image_tag(tag):
    result = subprocess.run(["docker", "image", "inspect", tag], check=False,
                            capture_output=True, text=True)
    if result.returncode == 0:
        raise RuntimeError("prova recusou uma tag de imagem preexistente")


def wait_healthy(identity):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        item = inspect(identity)
        state = item.get("State", {})
        health = state.get("Health") or {}
        if state.get("Status") == "running" and health.get("Status") == "healthy":
            return item
        if state.get("Status") not in {"created", "running"}:
            break
        time.sleep(1)
    raise RuntimeError("prova Engine falhou no healthcheck sintético")


def write_manifest(mode, target_sha, fingerprint, containers, engine):
    directory = bridge._operation_directory(mode, target_sha, fingerprint)
    directory.mkdir(mode=0o700)
    os.chmod(directory, 0o700)
    value = {
        "version": 1,
        "mode": mode,
        "target_sha": target_sha,
        "fingerprint": fingerprint,
        "source_fingerprint": "e" * 64,
        "services": {},
        "files": [],
        "models": {service: {} for service in bridge.SERVICES},
        "containers": containers,
        "engine": engine,
    }
    bridge._write_private_file(directory / "manifest.json", json.dumps(value, sort_keys=True).encode())
    return value


def build_synthetic_image(root, tag, image_role, images):
    context = root / ("image-" + image_role)
    context.mkdir(mode=0o700)
    require_unused_image_tag(tag)
    images["tags"].append(tag)
    dockerfile = "\n".join((
        f"FROM {BASE_IMAGE}",
        "ARG PROOF_MARKER",
        "RUN mkdir -p /seed /image-proof && printf 'image-owned\\n' > /seed/image-marker "
        + "&& printf '%s' \"$PROOF_MARKER\" > /image-proof/role",
        "ENTRYPOINT []",
        "EXPOSE 8000",
        "HEALTHCHECK --interval=1s --timeout=2s --retries=30 --start-period=1s "
        + "CMD [\"python3\",\"-B\",\"-c\",\"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=1).read()\"]",
        "CMD " + json.dumps(["python3", "-B", "-u", "-c", SERVER_PROGRAM]),
        "",
    ))
    (context / "Dockerfile").write_text(dockerfile, encoding="ascii")
    run("build synthetic image", "docker", "build", "--network=none", "--quiet", "--build-arg",
        f"PROOF_MARKER={image_role}", "-t", tag, str(context), timeout=420)


def http_body(network, service):
    code = "import sys,urllib.request; print(urllib.request.urlopen('http://'+sys.argv[1]+':8000/',timeout=5).read().decode())"
    return run("route check", "docker", "run", "--rm", "--network", network,
               "--entrypoint", "python3", BASE_IMAGE, "-B", "-c", code, service, timeout=30)


def require_empty_volume(volume, image):
    code = "import os; assert os.listdir('/seed') == []"
    run("NoCopy volume check", "docker", "run", "--rm", "--network", "none", "--mount",
        f"type=volume,source={volume},target=/seed,readonly", "--entrypoint", "python3",
        image, "-B", "-c", code)


def peer_projection(identity):
    item = inspect(identity)
    return {key: item[key] for key in ("Id", "Image", "Config", "HostConfig", "Mounts", "NetworkSettings")}


def make_service_container(project, network, service, image_tag, legacy_alias, bind_source, volume, scenario):
    name = f"{project}-{service}-original"
    command = [
        "docker", "create", "--name", name,
        "--label", f"com.docker.compose.project={project}",
        "--label", f"com.docker.compose.service={service}",
        "--label", f"io.pickyourpic.release={OLD_REVISION}",
        "--hostname", legacy_alias,
        "--network", network,
        "--network-alias", service,
        "--restart=no", "--read-only", "--expose", "8000",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--tmpfs", "/run:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "--env", f"APP_VERSION={OLD_REVISION}",
        "--env", f"PROOF_SERVICE={service}",
    ]
    if service == "api":
        command.extend(("--env", "APP_ENV=production", "--env", "FACIAL_PROCESSING_ENABLED=true",
                        "--volume", f"{bind_source}:/run/proof:ro",
                        "--volume", f"{volume}:/seed:rw,nocopy"))
    command.append(image_tag)
    identity = run("create synthetic original", *command)
    scenario["container_ids"].append(identity)
    run("start synthetic original", "docker", "start", identity)
    return identity


def setup_scenario(root, label, scenario, synthetic_images):
    token = uuid.uuid4().hex[:12]
    project = f"markina-gallery-engine-proof-{token}"
    network = project + "_internal"
    volume = project + "_media-source"
    receipt = RECEIPT_HASH
    bind_root = root / ("bind-" + label)
    bind_root.mkdir(mode=0o700)
    (bind_root / "custody.marker").write_text("synthetic read-only bind", encoding="ascii")
    scenario.update({
        "project": project, "network": network, "volume": volume, "bind_root": bind_root,
        "candidate_names": [], "container_ids": [], "image_tags": [],
        "network_created": False, "volume_created": False,
    })
    candidate_names = scenario["candidate_names"]
    image_tags = scenario["image_tags"]

    existing_network = run("check network name", "docker", "network", "ls", "--quiet", "--filter", f"name=^/{network}$")
    if existing_network:
        raise RuntimeError("prova recusou uma rede preexistente")
    existing_volume = subprocess.run(["docker", "volume", "inspect", volume], capture_output=True,
                                     text=True, check=False)
    if existing_volume.returncode == 0:
        raise RuntimeError("prova recusou um volume preexistente")
    run("create isolated network", "docker", "network", "create", "--driver", "bridge", "--internal",
        "--label", f"com.docker.compose.project={project}", network)
    scenario["network_created"] = True
    run("create empty named volume", "docker", "volume", "create", "--label",
        f"com.docker.compose.project={project}", volume)
    scenario["volume_created"] = True

    bridge.PROJECT = project
    bridge.ENGINE_NETWORK = network
    bridge._ENGINE_BIND_ROOTS = (str(bind_root),)
    bridge.STATE_DIR = root / ("deploy-state-" + label)
    bridge.STATE_DIR.mkdir(mode=0o700)
    bridge.MARKINA_STATE_ROOT = root / ("protected-" + label)
    bridge.MARKINA_STATE_ROOT.mkdir(mode=0o700)
    bridge.BRIDGE_STATE = bridge.MARKINA_STATE_ROOT / "app-compose-bridge"
    bridge._ensure_root_bridge_directory()
    scenario["engine_create_original"] = bridge._engine_create

    def track_created_candidate(name, payload):
        identity = scenario["engine_create_original"](name, payload)
        scenario["container_ids"].append(identity)
        return identity

    bridge._engine_create = track_created_candidate
    bridge._engine_bootstrap_receipt = lambda: receipt

    def assert_synthetic_sources_unchanged(context):
        if bridge._engine_bootstrap_receipt() != context["engine"].get("receipt"):
            raise bridge.BridgeError("engine_bootstrap_receipt_changed")

    bridge._assert_sources_unchanged = assert_synthetic_sources_unchanged

    originals = {}
    target_ids = {}
    for service in bridge.SERVICES:
        service_tag = f"{project}-{service}"
        old_tag = f"{service_tag}-old"
        target_tag = f"{service_tag}-target"
        for tag in (service_tag, old_tag, target_tag):
            require_unused_image_tag(tag)
        image_tags.extend((service_tag, old_tag, target_tag))
        run("tag shared baseline image", "docker", "image", "tag", synthetic_images["old"], old_tag)
        run("tag baseline image", "docker", "image", "tag", old_tag, service_tag)
        alias = f"pyp-drive-owner-{token}-{service}"
        identity = make_service_container(project, network, service, service_tag, alias, bind_root, volume, scenario)
        wait_healthy(identity)
        originals[service] = inspect(identity)
        run("tag shared target image", "docker", "image", "tag", synthetic_images["target"], target_tag)
        run("tag approved target image", "docker", "image", "tag", target_tag, service_tag)
        target_ids[service] = run("read target image id", "docker", "image", "inspect", "--format", "{{.Id}}", service_tag)

    bridge.ENGINE_BOOTSTRAP = {
        service: (originals[service]["Id"], originals[service]["Image"]) for service in bridge.SERVICES
    }
    bridge.ENGINE_BOOTSTRAP_HOSTNAMES = {
        service: originals[service]["Config"]["Hostname"] for service in bridge.SERVICES
    }
    for service, identity in target_ids.items():
        bridge._write_private_file(bridge.STATE_DIR / f"app-{service}-target-id", identity.encode("ascii"))

    target_sha = hashlib.sha256((project + label).encode()).hexdigest()[:40]
    fingerprint = hashlib.sha256((project + label).encode()).hexdigest()
    engine = {"type": "engine-bootstrap", "receipt": receipt}
    engine["containers"] = bridge._engine_records(originals)
    context = {"engine": engine, "containers": originals}
    manifest = write_manifest("release", target_sha, fingerprint, originals, engine)

    peer_name = project + "-peer"
    peer_id = run("create unrelated peer", "docker", "run", "--detach", "--name", peer_name,
                  "--network", "none", "--entrypoint", "sleep", BASE_IMAGE, "600")
    scenario["container_ids"].append(peer_id)
    peer_before = peer_projection(peer_id)
    candidate_names.extend(
        f"{project}-{service}-app-{target_sha[:12]}-{fingerprint[:12]}" for service in bridge.SERVICES)

    scenario.update({
        "receipt": receipt, "originals": originals, "target_ids": target_ids,
        "context": context, "manifest": manifest, "target_sha": target_sha,
        "fingerprint": fingerprint, "peer_id": peer_id, "peer_before": peer_before,
        "seed_image": synthetic_images["target"],
    })
    return scenario


def cleanup(scenario):
    if scenario.get("engine_create_original"):
        bridge._engine_create = scenario["engine_create_original"]
    for identity in reversed(scenario.get("container_ids", [])):
        subprocess.run(["docker", "container", "rm", "--force", identity], capture_output=True, check=False)
    if scenario.get("network_created"):
        subprocess.run(["docker", "network", "rm", scenario["network"]], capture_output=True, check=False)
    if scenario.get("volume_created"):
        subprocess.run(["docker", "volume", "rm", scenario["volume"]], capture_output=True, check=False)
    for tag in scenario.get("image_tags", []):
        subprocess.run(["docker", "image", "rm", "--force", tag], capture_output=True, check=False)


def cleanup_shared_images(images):
    for tag in images.get("tags", []):
        subprocess.run(["docker", "image", "rm", "--force", tag], capture_output=True, check=False)


def assert_active_responses(scenario, suffix):
    for service in bridge.SERVICES:
        expected = f"{service}-{suffix}"
        if http_body(scenario["network"], service) != expected:
            raise RuntimeError("prova Engine falhou na rota " + service + "/" + suffix)


def prove_success_and_rollback(root, synthetic_images):
    scenario = {}
    try:
        setup_scenario(root, "success", scenario, synthetic_images)
        _, bootstrap = bridge._engine_discover("inventory", scenario["target_sha"])
        if bootstrap is None or bootstrap.get("type") != "engine-bootstrap":
            raise RuntimeError("prova Engine não selecionou o recibo bootstrap exato")
        require_empty_volume(scenario["volume"], scenario["seed_image"])
        bridge._engine_release(scenario["context"], scenario["manifest"], scenario["target_sha"])
        active = bridge._inspect_api_web()
        for service in bridge.SERVICES:
            if (active[service]["Id"] == scenario["originals"][service]["Id"]
                    or active[service]["Image"] != scenario["target_ids"][service]
                    or bridge._engine_revision(active[service]) != scenario["target_sha"]
                    or not bridge._engine_healthy(active[service])):
                raise RuntimeError("prova Engine falhou na promoção " + service)
        assert_active_responses(scenario, "target")
        _, attestation = bridge._engine_discover("inventory", scenario["target_sha"])
        if attestation is None or attestation.get("type") != "engine-attested":
            raise RuntimeError("prova Engine não validou o recibo da promoção")
        require_empty_volume(scenario["volume"], scenario["seed_image"])
        if peer_projection(scenario["peer_id"]) != scenario["peer_before"]:
            raise RuntimeError("prova Engine alterou recurso vizinho")

        rollback_engine = {"type": "engine-attested", "receipt": scenario["receipt"]}
        rollback_engine["containers"] = bridge._engine_records(active)
        rollback_manifest = write_manifest("rollback", scenario["target_sha"], "f" * 64, active, rollback_engine)
        rollback_context = {"engine": rollback_engine, "containers": active}
        bridge._engine_rollback(rollback_context, rollback_manifest, scenario["manifest"])
        restored = bridge._inspect_api_web()
        if any(restored[service]["Id"] != scenario["originals"][service]["Id"] for service in bridge.SERVICES):
            raise RuntimeError("prova Engine não restaurou os containers originais")
        assert_active_responses(scenario, "old")
        _, rollback_attestation = bridge._engine_discover("inventory", scenario["target_sha"])
        if rollback_attestation is None or rollback_attestation.get("type") != "engine-attested":
            raise RuntimeError("prova Engine não validou o recibo do rollback")
        require_empty_volume(scenario["volume"], scenario["seed_image"])
        if peer_projection(scenario["peer_id"]) != scenario["peer_before"]:
            raise RuntimeError("rollback Engine alterou recurso vizinho")
    finally:
        cleanup(scenario)


def prove_partial_recovery(root, synthetic_images):
    scenario = {}
    original_docker = bridge._docker
    detached_web = {"id": ""}
    try:
        setup_scenario(root, "recovery", scenario, synthetic_images)
        _, bootstrap = bridge._engine_discover("inventory", scenario["target_sha"])
        if bootstrap is None or bootstrap.get("type") != "engine-bootstrap":
            raise RuntimeError("prova Engine não selecionou o recibo bootstrap exato")
        web_candidate_name = scenario["candidate_names"][1]

        def fail_between_network_operations(args, **kwargs):
            if args[:2] == ["network", "disconnect"]:
                result = original_docker(args, **kwargs)
                candidate = bridge._engine_inspect(args[-1])
                if candidate.get("Name") == "/" + web_candidate_name:
                    detached_web["id"] = candidate["Id"]
                return result
            if args[:2] == ["network", "connect"] and args[-1] == detached_web["id"]:
                raise bridge.BridgeError("proof_injected_connect_failure")
            return original_docker(args, **kwargs)

        bridge._docker = fail_between_network_operations
        try:
            bridge._engine_release(scenario["context"], scenario["manifest"], scenario["target_sha"])
        except bridge.BridgeError as error:
            if error.code != "proof_injected_connect_failure":
                raise
        else:
            raise RuntimeError("prova Engine não acionou a falha parcial prevista")
        finally:
            bridge._docker = original_docker

        if not detached_web["id"]:
            raise RuntimeError("prova Engine não isolou a candidata web")
        pending, journal_hash = bridge._engine_private_object(bridge.BRIDGE_STATE / bridge.ENGINE_PENDING)
        if pending["candidates"]["web"]["id"] != detached_web["id"]:
            raise RuntimeError("journal Engine não registrou a candidata web")
        require_empty_volume(scenario["volume"], scenario["seed_image"])
        if http_body(scenario["network"], "web") != "web-recovery-old":
            raise RuntimeError("a rota web original não sobreviveu à falha parcial")
        if http_body(scenario["network"], "api") != "api-recovery-target":
            raise RuntimeError("a rota api promovida não permaneceu saudável")

        recovery_engine = {"type": "engine-recovery", "receipt": scenario["receipt"], "journal": journal_hash}
        rollback_manifest = write_manifest("rollback", scenario["target_sha"], "a" * 64,
                                           scenario["originals"], recovery_engine)
        recovery_context = {"engine": recovery_engine, "containers": scenario["originals"]}
        bridge._engine_rollback(recovery_context, rollback_manifest, scenario["manifest"])
        restored = bridge._inspect_api_web()
        if any(restored[service]["Id"] != scenario["originals"][service]["Id"] for service in bridge.SERVICES):
            raise RuntimeError("recuperação Engine não restaurou o par original")
        assert_active_responses(scenario, "old")
        _, attestation = bridge._engine_discover("inventory", scenario["target_sha"])
        if attestation is None or attestation.get("type") != "engine-attested":
            raise RuntimeError("recuperação Engine não validou o recibo de conclusão")
        require_empty_volume(scenario["volume"], scenario["seed_image"])
        if peer_projection(scenario["peer_id"]) != scenario["peer_before"]:
            raise RuntimeError("recuperação Engine alterou recurso vizinho")
    finally:
        bridge._docker = original_docker
        cleanup(scenario)


def main():
    require_ci_runner()
    configure_runner_context()
    run("pull isolated base image", "docker", "pull", BASE_IMAGE, timeout=420)
    with tempfile.TemporaryDirectory(prefix="markina-engine-proof-") as temporary:
        root = Path(temporary)
        os.chmod(root, stat.S_IRWXU)
        token = uuid.uuid4().hex[:12]
        images = {"tags": []}
        try:
            for image_role in ("old", "target"):
                tag = f"markina-gallery-engine-proof-{token}-{image_role}"
                build_synthetic_image(root, tag, image_role, images)
                images[image_role] = tag
            prove_success_and_rollback(root, images)
            prove_partial_recovery(root, images)
        finally:
            cleanup_shared_images(images)
    print("Docker Engine isolado: promoção, aliases, rollback, falha parcial, NoCopy e serviço vizinho verificados")


if __name__ == "__main__":
    main()
