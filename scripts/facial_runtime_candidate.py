"""Prepara um contexto facial offline sem reconstruir o código SaaS da worktree.

O inventário recebido deve vir de coleta revisada. Este módulo não autentica uma
origem de inventário e não acessa produção, baixa modelos ou executa Docker.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from email.parser import Parser
from pathlib import Path

try:
    from .facial_runtime_image_import import ImageBinding
except ImportError:
    from facial_runtime_image_import import ImageBinding

COMMON_OVERLAYS = frozenset({"app/facial/config.py", "app/facial/rollout.py"})
FACIAL_WORKERS = frozenset({"face-search-worker", "face-index-worker", "face-maintenance-worker"})
SERVICE_OVERLAYS = {
    "api": COMMON_OVERLAYS,
    "worker": COMMON_OVERLAYS,
    **{service: COMMON_OVERLAYS | {"app/facial/face_worker.py"} for service in FACIAL_WORKERS},
}
# Compatibility name for callers inspecting the common, non-worker overlay set.
OVERLAYS = COMMON_OVERLAYS
VERSIONS = {"numpy": "2.2.6", "opencv-python-headless": "4.12.0.88"}
IMAGE = re.compile(r"sha256:[0-9a-f]{64}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MODEL_VERSION = "yunet-2023mar+sface-2021dec"
MANIFEST_SHA256 = "c8322285b6103a50008ce1082a2ba8a99422cfe1731e160837cba11ebdecf075"


class CandidateError(RuntimeError):
    """Preparação recusada; mensagens não incluem conteúdo de arquivos."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CandidateError(message)


def _file_bytes(path: Path, *, limit: int = 160_000_000) -> bytes:
    meta = path.lstat()
    _require(stat.S_ISREG(meta.st_mode) and meta.st_nlink == 1 and meta.st_size <= limit,
             "Arquivo de preparação não é regular/exclusivo ou excede o limite.")
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as handle:
        opened = os.fstat(handle.fileno())
        _require((meta.st_dev, meta.st_ino) == (opened.st_dev, opened.st_ino),
                 "Arquivo foi substituído durante a abertura.")
        data = handle.read(limit + 1)
    after = path.lstat()
    _require((meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns)
             == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
             "Arquivo mudou durante a leitura.")
    return data


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _python_source_bytes(path: Path) -> bytes:
    data = _file_bytes(path, limit=1_000_000)
    normalized = data.replace(bytes((13, 10)), bytes((10,)))
    _require(bytes((13,)) not in normalized,
             "Overlay Python contém retorno de carro isolado.")
    return normalized


def _packages(values: Mapping[str, str]) -> dict[str, str]:
    result = {re.sub(r"[-_.]+", "-", k).lower(): v for k, v in values.items()}
    _require(len(result) == len(values) and all(isinstance(v, str) for v in result.values()),
             "Inventário de pacotes inválido.")
    return result


def _wheel(path: Path, expected_hash: str) -> tuple[str, bytes]:
    _require(bool(DIGEST.fullmatch(expected_hash)), "Checksum de wheel inválido.")
    data = _file_bytes(path)
    _require(_hash(data) == expected_hash, "Checksum de wheel divergente.")
    match = re.fullmatch(
        r"(numpy|opencv_python_headless)-(2\.2\.6|4\.12\.0\.88)-"
        r"(cp313|cp37)-(cp313|abi3)-([a-z0-9_.]+)\.whl", path.name,
    )
    _require(match is not None, "Wheel fora das versões/tags permitidas.")
    name, version, python_tag, abi_tag, platform_tag = match.groups()
    name = name.replace("_", "-")
    platforms = platform_tag.split(".")
    _require(version == VERSIONS[name]
             and all(p.startswith("manylinux") and p.endswith("_aarch64") for p in platforms)
             and ((name == "numpy" and (python_tag, abi_tag) == ("cp313", "cp313"))
                  or (name == "opencv-python-headless" and (python_tag, abi_tag) == ("cp37", "abi3"))),
             "Wheel incompatível com CPython 3.13/Linux ARM64.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = [m for m in archive.infolist() if m.filename.endswith(".dist-info/METADATA")]
            _require(len(members) == 1 and members[0].file_size < 1_000_000,
                     "Metadata de wheel inválida.")
            metadata = Parser().parsestr(archive.read(members[0]).decode("utf-8"))
    except (zipfile.BadZipFile, UnicodeError, OSError) as exc:
        raise CandidateError("Wheel ilegível.") from exc
    _require(isinstance(metadata["Name"], str)
             and metadata["Name"].replace("_", "-").lower() == name
             and metadata["Version"] == version, "Metadata de wheel diverge do nome.")
    return name, data


@dataclass(frozen=True)
class CandidatePlan:
    context: Path
    baseline_image: str
    donor_image: str
    baseline_alias: str
    donor_alias: str
    file_sha256: tuple[tuple[str, str], ...]
    baseline_binding: ImageBinding | None = field(default=None, repr=False)
    donor_binding: ImageBinding | None = field(default=None, repr=False)

    @property
    def baseline_local_image(self) -> str:
        return self.baseline_binding.local_image if self.baseline_binding else self.baseline_image

    @property
    def donor_local_image(self) -> str:
        return self.donor_binding.local_image if self.donor_binding else self.donor_image

    def commands(self, candidate_tag: str, docker_context: str, builder: str) -> list[list[str]]:
        """Comandos locais; o executor deve conferir os aliases antes do build."""
        _require(bool(re.fullmatch(r"pyp-facial-restore:[a-z0-9][a-z0-9._-]{0,100}", candidate_tag)),
                 "Tag candidata fora do namespace local.")
        _require(bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}", docker_context))
                 and bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,100}", builder)),
                 "Contexto/builder Docker inválido.")
        docker = ["docker", "--context", docker_context]
        return [
            docker + ["tag", self.baseline_local_image, self.baseline_alias],
            docker + ["tag", self.donor_local_image, self.donor_alias],
            docker + ["image", "inspect", self.baseline_alias, self.donor_alias,
             "--format", "{{.Id}} {{.Os}}/{{.Architecture}}"],
            docker + ["buildx", "build", "--builder", builder, "--load", "--pull=false",
             "--network=none", "--platform=linux/arm64",
             "--tag", candidate_tag, str(self.context)],
            docker + ["run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
             "--security-opt=no-new-privileges", "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
             "--entrypoint", "python", candidate_tag, "/opt/facial-restore/verify.py", "candidate"],
        ]


def build_local(plan: CandidatePlan, candidate_tag: str, runner: Callable[[list[str]], str],
                *, docker_context: str, builder: str) -> str:
    """Executa exclusivamente Docker local; falhas do runner MUST interromper.

    O runner retorna stdout e lança exceção para exit code não zero. Não há
    fallback que busque imagens ou dependências remotas. O retorno é o ID da
    imagem candidata, após prova dentro de container sem rede/mounts de dados.
    """
    commands = plan.commands(candidate_tag, docker_context, builder)
    docker = ["docker", "--context", docker_context]

    def verify_context() -> None:
        entries = list(plan.context.rglob("*"))
        _require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in entries),
                 "Contexto contém link/junction.")
        observed = {str(p.relative_to(plan.context)).replace("\\", "/"): _hash(_file_bytes(p))
                    for p in entries if not p.is_dir()}
        _require(bool(plan.file_sha256) and observed == dict(plan.file_sha256),
                 "Contexto mudou depois da preparação.")

    verify_context()
    # O driver docker usa as imagens conferidas no daemon local. Um builder
    # docker-container poderia consultar um registry para os aliases locais.
    builder_info = runner(docker + ["buildx", "inspect", builder])
    match = re.search(r"(?im)^Driver:\s*(\S+)\s*$", builder_info)
    _require(match is not None and match.group(1) == "docker",
             "O build offline exige o driver docker local.")

    def inspect(reference: str, expected: str | None = None,
                binding: ImageBinding | None = None) -> Mapping:
        items = json.loads(runner(docker + ["image", "inspect", reference]))
        _require(isinstance(items, list) and len(items) == 1, "Imagem local não é única.")
        info = items[0]
        if binding is not None:
            binding.verify_inspect(info)
        _require(bool(IMAGE.fullmatch(info.get("Id", "")))
                 and (expected is None or info["Id"] == expected)
                 and info.get("Os") == "linux" and info.get("Architecture") == "arm64"
                 and not info.get("Config", {}).get("OnBuild")
                 and not info.get("Config", {}).get("Volumes"),
                 "Imagem local/alias/plataforma/configuração divergente.")
        return info

    def tag_exists(reference: str) -> bool:
        listed = runner(docker + ["image", "ls", "--format", "{{.Repository}}:{{.Tag}}", reference])
        return reference in {line.strip() for line in listed.splitlines()}

    _require(not tag_exists(candidate_tag),
             "Tag candidata já existe; recusando sobrescrever uma imagem local.")
    inspect(plan.baseline_local_image, plan.baseline_local_image, plan.baseline_binding)
    inspect(plan.donor_local_image, plan.donor_local_image, plan.donor_binding)
    for command, alias, expected, binding in [
        (commands[0], plan.baseline_alias, plan.baseline_local_image, plan.baseline_binding),
        (commands[1], plan.donor_alias, plan.donor_local_image, plan.donor_binding),
    ]:
        if tag_exists(alias):
            inspect(alias, expected, binding)
        else:
            runner(command)
            inspect(alias, expected, binding)
    verify_context()
    runner(commands[3])
    candidate = inspect(candidate_tag)["Id"]
    # Execute por ID, pois uma tag não é identidade imutável.
    verify = commands[4]
    verify[verify.index(candidate_tag)] = candidate
    runner(verify)
    return candidate


def prepare_context(
    destination: Path, *, baseline: Mapping, donor: Mapping, manifest_path: Path,
    overlays: Mapping[str, Path], wheels: Mapping[Path, str],
    service: str = "api",
    baseline_binding: ImageBinding | None = None, donor_binding: ImageBinding | None = None,
) -> CandidatePlan:
    """Escreve somente um diretório novo após validar todos os inputs.

    baseline segue o inventário {image, runtime:{architecture,python,packages,
    module_sha256}}. donor exige image, architecture, os, manifest_sha256,
    installed_versions e assets, incluindo marcador e pesos verificados.
    Os valores de checksum de wheels devem ter sido obtidos por fonte confiável.
    """
    base_id, donor_id = baseline.get("image", ""), donor.get("image", "")
    _require(bool(IMAGE.fullmatch(base_id) and IMAGE.fullmatch(donor_id)),
             "Imagens precisam ser identificadas por digest integral.")
    for source_id, binding in [(base_id, baseline_binding), (donor_id, donor_binding)]:
        if binding is not None:
            binding.validate()
            _require(binding.source_image == source_id, "Prova de importação pertence a outro config original.")
    runtime = baseline.get("runtime", {})
    _require(runtime.get("architecture") in {"aarch64", "arm64"}
             and re.match(r"3\.13\.\d+\b", runtime.get("python", "")) is not None
             and donor.get("architecture") in {"aarch64", "arm64"}
             and donor.get("os") == "linux", "Runtime/doadora incompatíveis com Linux ARM64/CPython 3.13.")
    package_versions = _packages(runtime.get("packages", {}))
    _require(bool(package_versions), "Inventário de pacotes ausente.")
    for name, version in VERSIONS.items():
        _require(package_versions.get(name, version) == version
                 and donor.get("installed_versions", {}).get(name) == version,
                 "Versão facial diverge do runtime/doadora revisados.")
    modules = runtime.get("module_sha256", {})
    allowed_overlays = SERVICE_OVERLAYS.get(service)
    _require(allowed_overlays is not None, "Serviço fora da allowlist de candidatos.")
    _require(allowed_overlays <= modules.keys() and bool(modules)
             and all(isinstance(k, str) and k.startswith("app/") and ".." not in k.split("/")
                     and isinstance(v, str) and DIGEST.fullmatch(v) for k, v in modules.items()),
             "Inventário de módulos inválido.")
    _require(set(overlays) == allowed_overlays, "Overlays fora da allowlist exata do serviço.")
    # O checkout Windows pode ter CRLF, enquanto blobs Git e o operador usam
    # bytes LF. Normalize antes de embutir a imagem para tornar hashes Git-bound.
    overlay_data = {name: _python_source_bytes(path) for name, path in overlays.items()}
    manifest_bytes = _file_bytes(manifest_path, limit=32_768).replace(b"\r\n", b"\n")
    manifest_hash = _hash(manifest_bytes)
    manifest = json.loads(manifest_bytes)
    _require(manifest_hash == MANIFEST_SHA256 and manifest.get("model_version") == MODEL_VERSION
             and manifest.get("schema_version") == 1
             and set(manifest.get("models", {})) == {"yunet", "sface"}
             and donor.get("manifest_sha256") == manifest_hash,
             "Manifesto doador diverge do manifesto fixado.")
    assets = donor.get("assets", {})
    required_assets = {"markina-face-models/.markina-face-models.json"}
    for entry in manifest["models"].values():
        filename = entry.get("filename", "")
        _require(bool(re.fullmatch(r"[a-zA-Z0-9._-]+\.onnx", filename)), "Nome de modelo inválido.")
        key = "markina-face-models/" + filename
        required_assets.add(key)
        _require(assets.get(key) == {"bytes": entry["bytes"], "sha256": entry["sha256"]},
                 "Bytes do modelo doador não foram comprovados.")
    _require(set(assets) == required_assets
             and assets["markina-face-models/.markina-face-models.json"].get("bytes", 0) > 0
             and bool(DIGEST.fullmatch(assets["markina-face-models/.markina-face-models.json"].get("sha256", ""))),
             "Conjunto de assets ou marcador não comprovado.")
    wheel_data, wheel_names, requirement_lines = {}, set(), []
    for path, checksum in wheels.items():
        name, data = _wheel(path, checksum)
        _require(name not in wheel_names, "Wheel facial duplicada.")
        wheel_names.add(name)
        wheel_data[path.name] = data
        requirement_lines.append(f"file:///wheelhouse/{path.name} --hash=sha256:{checksum}")
    required_wheels = {name for name in VERSIONS if name not in package_versions}
    _require(wheel_names == required_wheels,
             "Wheels devem corresponder somente às dependências faciais ausentes no baseline.")
    expected_modules = dict(modules)
    expected_modules.update({name: _hash(data) for name, data in overlay_data.items()})
    expected_packages = dict(package_versions)
    expected_packages.update(VERSIONS)
    recipe = {
        "schema_version": 1, "service": service, "baseline_image": base_id, "donor_image": donor_id,
        "manifest_sha256": manifest_hash, "model_version": MODEL_VERSION,
        "baseline_modules": dict(modules), "candidate_modules": expected_modules,
        "baseline_packages": package_versions, "candidate_packages": expected_packages,
        "python": runtime["python"], "model_assets": assets,
    }
    _require(not destination.exists() and not destination.is_symlink(), "Diretório de contexto já existe.")
    _require(all(not p.is_symlink() and not getattr(p, "is_junction", lambda: False)()
                 for p in destination.parents), "Diretório de contexto atravessa link/junction.")
    destination.mkdir(mode=0o700, parents=False)
    for name, data in overlay_data.items():
        target = destination / "overlays" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if wheel_data:
        (destination / "wheelhouse").mkdir()
    for name, data in wheel_data.items():
        (destination / "wheelhouse" / name).write_bytes(data)
    for name, data in {
        "recipe.json": json.dumps(recipe, sort_keys=True).encode(),
        "model-manifest.json": manifest_bytes,
        "verify.py": VERIFY_SOURCE.encode(),
    }.items():
        (destination / name).write_bytes(data)
    if requirement_lines:
        (destination / "requirements-restore.txt").write_text(
            "\n".join(sorted(requirement_lines)) + "\n", encoding="utf-8", newline="\n"
        )
    base_alias = "pyp-facial-restore-base:" + base_id.removeprefix("sha256:")
    donor_alias = "pyp-facial-restore-donor:" + donor_id.removeprefix("sha256:")
    model_copies = "\n".join(
        f"COPY --from=model_donor /opt/{name} /opt/{name}"
        for name in sorted(required_assets)
    )
    dependency_instructions = ""
    if wheel_data:
        dependency_instructions = """COPY wheelhouse /wheelhouse
COPY requirements-restore.txt /opt/facial-restore/
RUN python -m pip install --no-cache-dir --no-index --no-deps --require-hashes -r /opt/facial-restore/requirements-restore.txt
"""
    overlay_instructions = "\n".join(
        f"COPY overlays/{name} /app/{name}" for name in sorted(allowed_overlays)
    )
    dockerfile = f"""FROM {donor_alias} AS model_donor
FROM {base_alias}
COPY recipe.json verify.py /opt/facial-restore/
RUN python /opt/facial-restore/verify.py baseline
{dependency_instructions}{model_copies}
COPY model-manifest.json /app/facial-assets/model-manifest.json
{overlay_instructions}
RUN python /opt/facial-restore/verify.py candidate
"""
    (destination / "Dockerfile").write_text(dockerfile, encoding="utf-8", newline="\n")
    (destination / ".dockerignore").write_text("*.log\n.env*\n", encoding="utf-8")
    context_hashes = tuple(sorted(
        (str(p.relative_to(destination)).replace("\\", "/"), _hash(_file_bytes(p)))
        for p in destination.rglob("*") if p.is_file()
    ))
    return CandidatePlan(destination, base_id, donor_id, base_alias, donor_alias, context_hashes,
                         baseline_binding, donor_binding)


VERIFY_SOURCE = '''"""Prova executada dentro da imagem; não acessa banco ou rede."""
import base64
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
from pathlib import Path

def require(value):
    if not value:
        raise SystemExit("facial-restore: runtime diverge do inventário revisado")

phase = sys.argv[1]
require(phase in {"baseline", "candidate"})
recipe = json.loads(Path("/opt/facial-restore/recipe.json").read_text())
require(platform.machine() in {"aarch64", "arm64"} and sys.version == recipe["python"])
root = Path("/app/app")
modules = {str(p.relative_to("/app")): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(root.rglob("*.py"))}
packages = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
            for d in importlib.metadata.distributions()}
require(modules == recipe[phase + "_modules"])
require(packages == recipe[phase + "_packages"])
manifest = Path("/app/facial-assets/model-manifest.json")
require(hashlib.sha256(manifest.read_bytes()).hexdigest() == recipe["manifest_sha256"])
if phase == "candidate":
    for relative, expected in recipe["model_assets"].items():
        p = Path("/opt") / relative
        require(p.is_file() and p.stat().st_size == expected["bytes"]
                and hashlib.sha256(p.read_bytes()).hexdigest() == expected["sha256"])
    import cv2
    import numpy
    require(cv2.__version__ == "4.12.0" and numpy.__version__ == "2.2.6")
    os.environ.update(APP_ENV="test", FACIAL_CREDENTIAL_ENV="test",
                      FACIAL_PROCESSING_ENABLED="true", FACIAL_REQUIRE_EXPLICIT_ROLLOUT="true",
                      FACIAL_MODEL_ROOT="/opt/markina-face-models",
                      FACIAL_MODEL_MANIFEST_PATH=str(manifest),
                      FACIAL_AEAD_ACTIVE_KEY_ID="restoration-test",
                      FACIAL_AEAD_KEYS_JSON=json.dumps({"restoration-test":base64.b64encode(b"s"*32).decode()}))
    for key in ["MODEL", "QUALITY", "CALIBRATION", "LEGAL_NOTICE", "CONSENT", "RETENTION_POLICY", "MINOR_POLICY"]:
        os.environ["FACIAL_" + key + "_VERSION"] = recipe["model_version"] if key == "MODEL" else "synthetic-v1"
    os.environ["FACIAL_LEGAL_BASIS_REFERENCE"] = "synthetic-test-only"
    sys.path.insert(0, "/app")
    from app.facial.config import facial_settings_from_environment
    settings = facial_settings_from_environment(verify_runtime_assets=True)
    require(settings.enabled and settings.require_explicit_rollout)
print("facial-restore: " + phase + " verified")
'''
