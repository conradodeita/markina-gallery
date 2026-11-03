"""Adaptador POSIX da restauração facial, nunca invocado implicitamente."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from facial_runtime_restoration import (
    FACIAL,
    GATES,
    GENERAL_RESTORE_MODE,
    HEX,
    IMAGE,
    MODULE_CHANGES_BY_SERVICE,
    OPERATION,
    PROJECT,
    SCHEMA,
    SERVICES,
    SHA,
    Approval,
    RestorationError,
    digest,
    require,
)

ROOT = Path("/opt/markina-gallery")
CODE = Path(__file__).resolve().parents[1]
DEPLOY_STATE = Path("/var/lib/markina-gallery/deploy-state")
STATE = DEPLOY_STATE / "facial-runtime-restoration"
CANDIDATE_MANIFEST = "facial-runtime-candidates.json"
ORIGIN = "https://markina.pickyourpic.com.br"
KNOWN = set(SERVICES) | {"web", "nginx", "db", "redis", "evolution-api", "evolution-db", "evolution-redis", "preview-adjustment-worker"}
PENDING = ("app-in-flight.sha", "app-rollback-in-flight.sha", "web-in-flight.sha", "web-pending.identity", "orders-in-flight.json", "pillow-in-flight.json", "environment-cutover-in-flight.json", "preview-adjustment-migration-in-flight.json", "preview-worker-security-in-flight.json")
COHERENT = frozenset({
    "FACIAL_CREDENTIAL_ENV", "FACIAL_MODEL_ROOT", "FACIAL_MODEL_MANIFEST_PATH", "FACIAL_MODEL_VERSION",
    "FACIAL_QUALITY_VERSION", "FACIAL_CALIBRATION_VERSION", "FACIAL_SIMILARITY_THRESHOLD_MILLI",
    "FACIAL_AMBIGUOUS_THRESHOLD_MILLI", "FACIAL_REFERENCE_AMBIGUOUS_THRESHOLD_MILLI",
    "FACIAL_REGION_AMBIGUOUS_THRESHOLD_MILLI", "FACIAL_AEAD_KEYS_JSON", "FACIAL_AEAD_ACTIVE_KEY_ID",
    "FACIAL_LEGAL_NOTICE_VERSION", "FACIAL_CONSENT_VERSION", "FACIAL_LEGAL_BASIS_REFERENCE",
    "FACIAL_RETENTION_POLICY_VERSION", "FACIAL_MINOR_POLICY_VERSION", "FACIAL_MINOR_SEARCH_ENABLED",
    "FACIAL_REFERENCE_RETENTION_SECONDS", "FACIAL_CANDIDATE_RETENTION_SECONDS",
})
COMMAND_ENV = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "COMPOSE_REMOVE_ORPHANS": "false", "COMPOSE_IGNORE_ORPHANS": "true"}
CANDIDATE_TMPFS = {
    "/tmp": "rw,nosuid,nodev,noexec,size=128m",
    "/run": "rw,nosuid,nodev,noexec,size=16m",
}

IMAGE_PROBE = r'''
import hashlib,importlib.util,json,platform,sys
from importlib.metadata import distributions
from pathlib import Path
root=Path('/app/app')
mods={'app/'+p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))}
packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in distributions()}
manifest=Path('/app/facial-assets/model-manifest.json')
result={'architecture':{'aarch64':'arm64','arm64':'arm64','x86_64':'amd64'}.get(platform.machine(),platform.machine()),'python':platform.python_version(),'modules':mods,'packages':packages,'models_verified':False,'opencv':None,'numpy':None,'model_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None}
for name in ('cv2','numpy'):
 if importlib.util.find_spec(name):
  m=__import__(name); result['opencv' if name=='cv2' else name]=m.__version__
try:
 from app.facial.model_assets import verify_models
 verify_models(Path('/app/facial-assets/model-manifest.json'),Path('/opt/markina-face-models'))
 result['models_verified']=True
except (RuntimeError,OSError,ValueError): pass
print(json.dumps(result,sort_keys=True))
'''

# Runs against the loaded runtime without importing its auth ORM or reading images.
# Values remain inside the container; only aggregate eligibility and its digest leave.
ACTIVATION_PROBE = r'''
import hashlib,json,os,sys
from uuid import UUID
import psycopg
request=json.load(sys.stdin)
scope=sorted(str(UUID(x)) for x in request['allowlist'])
url=os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)
params={key:os.environ.get('FACIAL_'+key.upper(),'') for key in ('model_version','quality_version','calibration_version','legal_notice_version','consent_version','legal_basis_reference','retention_policy_version')}
params['threshold']=int(os.environ.get('FACIAL_SIMILARITY_THRESHOLD_MILLI','750'))
query=''' + '"""' + r'''
SELECT r.parent_gallery_id::text,r.stage FROM facial_rollout r
JOIN tenant t ON t.id=r.tenant_id AND t.status='active'
JOIN parent_gallery p ON p.id=r.parent_gallery_id AND p.tenant_id=r.tenant_id
JOIN gallery_facial_policy g ON g.parent_gallery_id=r.parent_gallery_id AND g.tenant_id=r.tenant_id
WHERE r.environment='production' AND r.status='active' AND r.stage IN ('canary','limited','general')
AND p.active AND p.lifecycle_status='active' AND g.status='active'
AND r.approved_by_admin_id IS NOT NULL AND r.approved_at IS NOT NULL
AND r.approval_reference IS NOT NULL
AND r.model_version=%(model_version)s AND r.quality_version=%(quality_version)s
AND r.calibration_version=%(calibration_version)s
AND r.legal_notice_version=%(legal_notice_version)s AND r.consent_version=%(consent_version)s
AND r.legal_basis_reference=%(legal_basis_reference)s AND r.retention_policy_version=%(retention_policy_version)s
AND g.model_version=r.model_version AND g.quality_version=r.quality_version
AND g.calibration_version=r.calibration_version AND g.similarity_threshold_milli=%(threshold)s
AND EXISTS(SELECT 1 FROM facial_calibration_approval c WHERE c.tenant_id=r.tenant_id
AND c.environment='production' AND c.status='approved' AND c.model_version=r.model_version
AND c.quality_version=r.quality_version AND c.calibration_version=r.calibration_version
AND c.similarity_threshold_milli=%(threshold)s AND c.relevant_group_count>0
AND c.approved_group_count=c.relevant_group_count)
''' + '"""' + r'''
with psycopg.connect(url) as db:
 db.execute('SET TRANSACTION READ ONLY')
 db.execute("SET LOCAL statement_timeout='15s'")
 rows=db.execute(query,params).fetchall()
 actual=sorted(x[0] for x in rows)
 result={'scope_digest':hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'scope_count':len(actual),'calibration_verified':actual==scope and bool(actual),'stage':request['stage'] if all(x[1]==request['stage'] for x in rows) else None}
 db.rollback()
print(json.dumps(result,sort_keys=True))
'''

GENERAL_ACTIVATION_PROBE = r'''
import hashlib,json,os,sys
import psycopg
request=json.load(sys.stdin)
fields=('model_version','quality_version','calibration_version','legal_notice_version','legal_basis_reference','retention_policy_version','minor_policy_version')
params={key:os.environ.get('FACIAL_'+key.upper(),'') for key in fields}
params['threshold']=int(os.environ.get('FACIAL_SIMILARITY_THRESHOLD_MILLI','750'))
query="""SELECT p.id::text FROM parent_gallery p
JOIN tenant t ON t.id=p.tenant_id AND t.status='active'
JOIN gallery_facial_policy g ON g.parent_gallery_id=p.id AND g.tenant_id=p.tenant_id
WHERE p.active AND p.lifecycle_status='active' AND g.status='active'
AND g.model_version=%(model_version)s AND g.quality_version=%(quality_version)s
AND g.calibration_version=%(calibration_version)s
AND g.legal_notice_version=%(legal_notice_version)s AND g.legal_basis_reference=%(legal_basis_reference)s
AND g.retention_policy_version=%(retention_policy_version)s AND g.minor_policy_version=%(minor_policy_version)s
AND g.similarity_threshold_milli=%(threshold)s"""
with psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)) as db:
 db.execute('SET TRANSACTION READ ONLY'); db.execute("SET LOCAL statement_timeout='15s'")
 scope=sorted(row[0] for row in db.execute(query,params).fetchall()); db.rollback()
print(json.dumps({'scope_digest':hashlib.sha256(json.dumps(scope,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'scope_count':len(scope),'stage':request['stage'],'calibration_verified':False,'calibration_waived':True,'authorization_reference':request['authorization_reference']},sort_keys=True))
'''

FUNCTIONAL_PROBE = r'''
import json,os,sys
from uuid import UUID
import psycopg
p=json.load(sys.stdin)
parameters={'request':str(UUID(p['request_id'])),'scope':[str(UUID(x)) for x in p['allowlist']],'start':p['started_at'],'model':os.environ['FACIAL_MODEL_VERSION'],'quality':os.environ['FACIAL_QUALITY_VERSION']}
query="""SELECT json_build_object('request_ready',q.status='ready' AND q.completed_at IS NOT NULL,'reference_purged',q.reference_locator_ciphertext IS NULL AND q.reference_locator_nonce IS NULL AND (q.reference_source='indexed_region' OR q.reference_deleted_at IS NOT NULL))
FROM facial_search_request q WHERE q.id=%(request)s::uuid
AND q.parent_gallery_id=ANY(%(scope)s::uuid[]) AND q.created_at>=%(start)s::timestamptz
AND q.expires_at>now() AND q.model_version=%(model)s AND q.quality_version=%(quality)s
AND q.search_engine='opencv-yunet-sface'
AND ((q.reference_source='upload' AND q.authorization_method='explicit_consent' AND q.consent_version IS NOT NULL) OR (q.reference_source='indexed_region' AND q.authorization_method='direct_region'))
AND EXISTS(SELECT 1 FROM parent_gallery_registration a WHERE a.tenant_id=q.tenant_id AND a.parent_gallery_id=q.parent_gallery_id AND a.client_id=q.client_id AND a.status='active')"""
with psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)) as db:
 db.execute('SET TRANSACTION READ ONLY'); db.execute("SET LOCAL statement_timeout='15s'")
 row=db.execute(query,parameters).fetchone(); db.rollback()
 print(json.dumps(row[0] if row else {'request_ready':False,'reference_purged':False}))
'''


def environment(item: dict) -> dict[str, str]:
    result = {}
    for value in item["Config"].get("Env", []):
        key, separator, content = value.partition("=")
        require(separator and key not in result, "ambiente_duplicado_ou_invalido")
        result[key] = content
    return result


def configuration(item: dict) -> dict:
    mounts = item.get("Mounts", [])
    destinations = [m.get("Destination") for m in mounts]
    require(all(isinstance(d, str) and d.startswith("/") for d in destinations) and len(set(destinations)) == len(destinations), "mounts_ambiguos")
    config = item["Config"]
    host = item["HostConfig"]
    host_keys = ("RestartPolicy", "Memory", "NanoCpus", "ReadonlyRootfs", "CapDrop", "CapAdd", "SecurityOpt", "Privileged", "Devices", "DeviceRequests", "Runtime", "PidMode", "IpcMode", "NetworkMode", "PortBindings", "Dns", "ExtraHosts", "Ulimits", "Tmpfs", "LogConfig")
    return {"environment": environment(item), "command": config.get("Cmd"), "entrypoint": config.get("Entrypoint"), "user": config.get("User"), "working_dir": config.get("WorkingDir"), "healthcheck": config.get("Healthcheck"), "labels": {k:v for k,v in (config.get("Labels") or {}).items() if not k.startswith("com.docker.compose.")}, "mounts": sorted(mounts, key=lambda x:x["Destination"]), "host": {k:host.get(k) for k in host_keys}, "networks": sorted(item.get("NetworkSettings", {}).get("Networks", {}))}


def configuration_without_restart(item: dict) -> dict:
    result = configuration(item)
    result["host"].pop("RestartPolicy", None)
    return result


def _escape(value):
    if isinstance(value, str):
        return value.replace("$", "$$")
    if isinstance(value, list):
        return [_escape(x) for x in value]
    if isinstance(value, dict):
        return {k:_escape(v) for k,v in value.items()}
    return value


class RestorationHost:
    def __init__(self, *, support_sha: str, root: Path = ROOT, state: Path = STATE,
                 shared_state: Path | None = None, code_root: Path = CODE,
                 command: Callable[[Sequence[str], bytes | None, int], bytes] | None = None,
                 sleeper=time.sleep, monotonic=time.monotonic):
        require(SHA.fullmatch(support_sha), "sha_invalido")
        if shared_state is None:
            shared_state = DEPLOY_STATE if state == STATE else state
        self.support_sha, self.root, self.state = support_sha, root, state
        self.shared_state, self.code_root = shared_state, code_root
        if command is None:
            require(os.geteuid() == 0 and os.getegid() == 0 and root == ROOT and state == STATE and shared_state == DEPLOY_STATE
                    and socket.gethostname() == "clearbudget-vnic", "destino_nao_autorizado")
        self.command = command or self._command
        self.sleeper, self.monotonic = sleeper, monotonic
        self._raw = {}

    def _command(self, args, data, timeout):
        try:
            command = list(args)
            if command and command[0] == "git":
                command = ["git", "-c", "safe.directory=" + str(self.root),
                           "-c", "safe.directory=" + str(self.code_root), *command[1:]]
            return subprocess.run(command, cwd=self.root, input=data, capture_output=True,
                timeout=timeout, check=True, env=COMMAND_ENV).stdout
        except (OSError, subprocess.SubprocessError):
            raise RestorationError("comando_operacional_falhou") from None

    def run(self, *args, data=None, timeout=60):
        try:
            value = self.command(args, data, timeout)
            require(isinstance(value, bytes), "resposta_invalida")
            return value.decode("utf-8").strip()
        except RestorationError:
            raise
        except (OSError, UnicodeError, subprocess.SubprocessError):
            raise RestorationError("comando_operacional_falhou") from None

    def obj(self, *args, **kwargs):
        try:
            return json.loads(self.run(*args, **kwargs))
        except (ValueError, TypeError):
            raise RestorationError("resposta_json_invalida") from None

    def _assert_preserved_layer(self, item, *, reason="camada_gravavel_nao_preservada"):
        changes = sorted(self.run("docker", "diff", item["Id"]).splitlines())
        if not changes:
            return
        mounts = sorted(m["Destination"] for m in item.get("Mounts", []))
        allowed = set()
        for destination in mounts:
            path = destination.rstrip("/")
            while path:
                allowed.add(path)
                path = path.rsplit("/", 1)[0]
        require(all(line[:2] in {"A ", "C "} and line[2:] in allowed for line in changes), reason)
        expected = {"id": item["Id"], "image": item["Image"], "mounts": mounts, "changes": changes}
        proof = self.obj(sys.executable, str(Path(__file__).with_name("facial_runtime_layer_probe.py")),
                         item["Id"], data=json.dumps({"mounts": mounts, "changes": changes}).encode(),
                         timeout=120)
        require(proof == {"safe": True, "proof_sha256": digest(expected)}, reason)

    def _safe_directory(self, path: Path, *, private=False, owner_uid=None, owner_gid=None):
        require(path.is_absolute(), "diretorio_relativo")
        for parent in reversed((path, *path.parents[:-1])):
            info = parent.lstat()
            require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode), "diretorio_inseguro")
        info = path.lstat()
        expected_owner = os.geteuid() if owner_uid is None else owner_uid
        expected_group = os.getegid() if owner_gid is None else owner_gid
        require(info.st_uid == expected_owner and info.st_gid == expected_group
                and not (stat.S_IMODE(info.st_mode) & 0o022), "diretorio_owner_ou_modo_invalido")
        if private:
            require(stat.S_IMODE(info.st_mode) == 0o700, "diretorio_privado_invalido")

    def _shared_state_owner_ids(self):
        if self.shared_state != DEPLOY_STATE:
            return os.geteuid(), os.getegid()
        try:
            import pwd
            owner = pwd.getpwnam("ubuntu")
            return owner.pw_uid, owner.pw_gid
        except (ImportError, KeyError):
            raise RestorationError("proprietario_estado_compartilhado_indisponivel") from None

    def _shared_state_owner_uid(self):
        return self._shared_state_owner_ids()[0]

    def _safe_shared_state(self):
        owner_uid, owner_gid = self._shared_state_owner_ids()
        self._safe_directory(self.shared_state, private=True, owner_uid=owner_uid, owner_gid=owner_gid)

    def _ensure_private_state(self, *, create=False):
        self._safe_shared_state()
        require(self.state == self.shared_state or self.state.parent == self.shared_state, "estado_fora_do_diretorio")
        if self.state == self.shared_state:
            self._safe_directory(self.state, private=True)
            return True
        if self.state.exists() or self.state.is_symlink():
            owner_gid = 0 if self.state == STATE else os.getegid()
            self._safe_directory(self.state, private=True, owner_gid=owner_gid)
            return True
        if not create:
            return False
        try:
            self.state.mkdir(mode=0o700)
        except FileExistsError:
            pass
        owner_gid = 0 if self.state == STATE else os.getegid()
        self._safe_directory(self.state, private=True, owner_gid=owner_gid)
        return True

    def _assert_no_pending_operations(self):
        self._safe_shared_state()
        require(not any((self.shared_state / name).exists() or (self.shared_state / name).is_symlink()
                        for name in PENDING), "operacao_concorrente_pendente")
        locations = [self.shared_state]
        if self.state != self.shared_state and self._ensure_private_state():
            locations.append(self.state)
        for location in locations:
            for work in location.glob("facial-restore-*"):
                require(not work.is_symlink(), "estado_restauracao_inseguro")
                if not work.is_dir():
                    continue
                journal = work / "in-flight.json"
                require(not journal.is_symlink(), "estado_restauracao_inseguro")
                require(not journal.exists(), "restauracao_pendente")

    def _read(self, path: Path, *, limit=8_000_000):
        return self._read_file(path, limit=limit)

    def _read_file(self, path: Path, *, limit=8_000_000, parent_owner_uid=None, parent_owner_gid=None):
        self._safe_directory(path.parent, private=True, owner_uid=parent_owner_uid, owner_gid=parent_owner_gid)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= limit, "arquivo_privado_inseguro")
            data = stream.read(limit + 1)
            require(len(data) <= limit, "arquivo_excessivo")
            return data

    def _write(self, path: Path, value: bytes, *, create=True):
        self._safe_directory(path.parent, private=True)
        if not create:
            self._read(path)
        else:
            require(not path.exists() and not path.is_symlink(), "arquivo_existente")
        temp = path.with_suffix(path.suffix + ".tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temp, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _work(self, operation):
        require(OPERATION.fullmatch(operation), "operacao_invalida")
        return self.state / ("facial-restore-" + operation)

    @contextmanager
    def lock(self):
        try:
            import fcntl
            owner_uid, owner_gid = self._shared_state_owner_ids()
            self._safe_directory(self.shared_state, private=True, owner_uid=owner_uid, owner_gid=owner_gid)
            path = self.shared_state / "production-release.lock"
            fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
            with os.fdopen(fd, "r+") as stream:
                info = os.fstat(stream.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == owner_uid and info.st_gid == owner_gid
                        and stat.S_IMODE(info.st_mode) == 0o600, "lock_inseguro")
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield
        except (ImportError, OSError):
            raise RestorationError("lock_posix_indisponivel_ou_ocupado") from None

    def inspect(self, identity):
        require(HEX.fullmatch(identity) or IMAGE.fullmatch(identity), "identidade_invalida")
        values = self.obj("docker", "inspect", identity)
        require(isinstance(values, list) and len(values) == 1, "inspect_ambiguo")
        return values[0]

    def _compose_files(self, item):
        raw = item["Config"].get("Labels", {}).get("com.docker.compose.project.config_files", "")
        paths = raw.split(",")
        require(raw and len(paths) <= 16 and len(set(paths)) == len(paths), "proveniencia_ambigua")
        result = []
        for text in paths:
            path = Path(text)
            require(path.is_absolute() and not path.is_symlink(), "manifesto_inseguro")
            resolved = path.resolve(strict=True)
            require(self.root in resolved.parents or self.shared_state in resolved.parents, "manifesto_fora_das_raizes")
            info = path.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not stat.S_IMODE(info.st_mode) & 0o022, "manifesto_inseguro")
            result.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return result

    def _sql(self, sql):
        # SQL is selected exclusively by this module, not a CLI argument.
        text = "BEGIN READ ONLY; SET LOCAL statement_timeout='15s'; " + sql + "; ROLLBACK;"
        command = 'exec psql -X -q -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
        return self.obj("docker", "exec", "-i", "markina-gallery-db-1", "sh", "-c", command, data=text.encode())

    def inventory(self):
        checkout_sha = self.run("git", "rev-parse", "HEAD")
        require(SHA.fullmatch(checkout_sha) and not self.run("git", "status", "--porcelain"), "checkout_ativo_sujo_ou_desconhecido")
        require(self.run("git", "-C", str(self.code_root), "rev-parse", "HEAD") == self.support_sha
            and not self.run("git", "-C", str(self.code_root), "status", "--porcelain"), "suporte_sujo_ou_divergente")
        self._assert_no_pending_operations()
        ids = self.run("docker", "ps", "-aq", "--no-trunc", "--filter", "label=com.docker.compose.project=" + PROJECT).split()
        require(1 <= len(ids) <= 100 and all(HEX.fullmatch(x) for x in ids), "inventario_containers_invalido")
        values = self.obj("docker", "inspect", *ids)
        selected, extras = {}, []
        for item in values:
            labels = item["Config"].get("Labels", {})
            name = labels.get("com.docker.compose.service")
            require(labels.get("com.docker.compose.project") == PROJECT, "projeto_divergente")
            running = item["State"]["Status"] == "running"
            require(name in KNOWN or not running, "servico_ativo_desconhecido")
            if name not in KNOWN:
                extras.append({"id": item["Id"], "image": item["Image"], "status": item["State"]["Status"]})
            elif name not in selected or (running and selected[name]["State"]["Status"] != "running"):
                if name in selected:
                    old = selected[name]
                    extras.append({"id": old["Id"], "image": old["Image"], "status": old["State"]["Status"]})
                selected[name] = item
            else:
                require(not running, "servico_ativo_duplicado")
                extras.append({"id": item["Id"], "image": item["Image"], "status": item["State"]["Status"]})
        self._raw = selected
        services = {}
        for name, item in selected.items():
            config = configuration(item)
            services[name] = {"container_id": item["Id"], "image_id": item["Image"], "status": item["State"]["Status"], "health": item["State"].get("Health", {}).get("Status"), "configuration_digest": digest(config), "ports": {k:v for k,v in (item["HostConfig"].get("PortBindings") or {}).items() if v}, "compose_files": self._compose_files(item) if name in SERVICES else [], "environment": environment(item).get("APP_ENV"), "facial_enabled": environment(item).get("FACIAL_PROCESSING_ENABLED"), "started_at": item["State"].get("StartedAt")}
        revisions = self._sql("SELECT json_agg(version_num) FROM alembic_version")
        require(revisions == [SCHEMA], "schema_divergente")
        architecture = self.run("uname", "-m")
        return {"format": 1, "project": PROJECT, "schema": SCHEMA, "support_sha": self.support_sha, "checkout_sha": checkout_sha, "architecture": {"aarch64":"arm64", "arm64":"arm64"}.get(architecture, architecture), "collected_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "services": services, "other_containers": sorted(extras, key=lambda x:x["id"])}

    def prove_images(self, manifest):
        require(set(manifest.get("services", {})) == set(SERVICES), "escopo_candidato_invalido")
        result = {}
        for service in SERVICES:
            item = manifest["services"][service]
            for field in ("image_id", "baseline_image_id"):
                require(IMAGE.fullmatch(item.get(field, "")), "imagem_invalida")
            before = self._probe_image(item["baseline_image_id"])
            require(before == item.get("baseline_runtime"), "baseline_runtime_nao_comprovado")
            result[service] = self._probe_image(item["image_id"])
            for module, value in item.get("module_changes", {}).items():
                require(module in MODULE_CHANGES_BY_SERVICE[service], "modulo_fora_do_escopo")
                # The hash includes file newline, read raw to avoid normalization.
                raw = self.command(("git", "-C", str(self.code_root), "show", self.support_sha + ":backend/" + module), None, 30)
                require(raw and hashlib.sha256(raw).hexdigest() == value, "modulo_nao_corresponde_ao_suporte")
        return result

    def _probe_image(self, image):
        info = self.obj("docker", "image", "inspect", image)
        require(len(info) == 1 and info[0].get("Id") == image and info[0].get("Architecture") == "arm64" and info[0].get("Os") == "linux", "imagem_arm64_nao_comprovada")
        return self.obj("docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m", "--entrypoint", "python", image, "-B", "-c", IMAGE_PROBE, timeout=120)

    def prepare(self, operation, receipt):
        work = self._work(operation)
        self._ensure_private_state(create=True)
        require(not work.exists() and not work.is_symlink(), "preparacao_existente")
        work.mkdir(mode=0o700)
        models = {}
        for service in SERVICES:
            files = receipt["inventory"]["services"][service]["compose_files"]
            args = ["docker", "compose", "--project-directory", str(self.root / "docker"), "-p", PROJECT]
            for f in files:
                args += ["-f", f["path"]]
            models[service] = self.obj(*args, "--profile", "facial", "config", "--format", "json")
            hash_result = self.run(*args, "config", "--hash", service)
            expected = self._raw[service]["Config"].get("Labels", {}).get("com.docker.compose.config-hash")
            require(hash_result.split() == [service, expected], "compose_nao_reproduz_baseline")
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        raw = json.dumps({"containers": self._raw, "models": models,
                          "activation_policy": receipt["manifest"].get("activation_policy", "strict"),
                          "authorization_reference": receipt["manifest"].get("authorization_reference")},
                         sort_keys=True).encode()
        encrypted = AESGCM(key).encrypt(nonce, raw, (operation + ":" + receipt["fingerprint"]).encode())
        self._write(work / "config.key", key)
        self._write(work / "config.sealed", nonce + encrypted)
        self._write(work / "prepared.json", json.dumps(receipt, sort_keys=True).encode())
        require(self._private(operation, receipt)["containers"] == self._raw, "preparacao_nao_reaberta")

    def load(self, operation):
        try:
            return json.loads(self._read(self._work(operation) / "prepared.json"))
        except (ValueError, UnicodeError):
            raise RestorationError("recibo_invalido") from None

    def candidate_manifest(self):
        owner_uid, owner_gid = self._shared_state_owner_ids()
        try:
            value = json.loads(self._read_file(self.shared_state / CANDIDATE_MANIFEST,
                                               limit=2_000_000,
                                               parent_owner_uid=owner_uid,
                                               parent_owner_gid=owner_gid))
        except (ValueError, UnicodeError):
            raise RestorationError("manifesto_candidato_invalido") from None
        require(isinstance(value, dict) and value.get("format") == 1, "manifesto_candidato_invalido")
        return value

    def _private(self, operation, receipt):
        work = self._work(operation)
        key = self._read(work / "config.key", limit=32)
        raw = self._read(work / "config.sealed")
        try:
            require(len(key) == 32 and len(raw) > 28, "configuracao_cifrada_invalida")
            return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], (operation + ":" + receipt["fingerprint"]).encode()))
        except RestorationError:
            raise
        except (InvalidTag, ValueError, TypeError, UnicodeError):
            raise RestorationError("configuracao_nao_autenticada") from None

    def journal(self, operation, value, *, create=False):
        self._write(self._work(operation) / "in-flight.json", json.dumps(value, sort_keys=True).encode(), create=create)

    def read_journal(self, operation):
        try:
            return json.loads(self._read(self._work(operation) / "in-flight.json", limit=65536))
        except (ValueError, UnicodeError):
            raise RestorationError("journal_invalido") from None

    def _current(self, service):
        require(service in SERVICES, "servico_fora_do_escopo")
        ids = self.run("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + PROJECT, "--filter", "label=com.docker.compose.service=" + service).split()
        values = [self.inspect(x) for x in ids]
        active = [x for x in values if x["State"]["Status"] == "running"]
        require(len(active) <= 1, "consumidor_ambiguo")
        if active:
            return active[0]
        require(len(values) == 1, "consumidor_parado_ambiguo_ou_ausente")
        return values[0]

    @staticmethod
    def _restart_option(item):
        policy = item.get("HostConfig", {}).get("RestartPolicy") or {}
        name = policy.get("Name")
        require(name in {"no", "always", "unless-stopped", "on-failure"}, "politica_de_reinicio_desconhecida")
        retries = policy.get("MaximumRetryCount", 0)
        require(isinstance(retries, int) and retries >= 0, "politica_de_reinicio_invalida")
        return f"on-failure:{retries}" if name == "on-failure" and retries else name

    def _assert_known_process(self, service, item):
        commands = {
            "api": ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            "worker": ["python", "-m", "app.worker"],
            "face-search-worker": ["python", "-m", "app.facial.search_worker_entrypoint"],
            "face-index-worker": ["python", "-m", "app.facial.index_worker_entrypoint"],
            "face-maintenance-worker": ["python", "-m", "app.facial.maintenance_worker_entrypoint"],
        }
        require(item.get("Config", {}).get("Cmd") == commands[service], "comando_de_consumidor_desconhecido")
        require(isinstance(item.get("State", {}).get("Pid"), int) and item["State"]["Pid"] > 0,
                "pid_de_consumidor_invalido")

    def _restore_stopped(self, operation, record):
        errors = []
        resumed = []
        for entry in reversed(record.get("stop_restore", [])):
            try:
                item = self.inspect(entry["id"])
                require(item["Id"] == entry["id"] and item["Image"] == entry["image_id"], "identidade_de_retomada_divergente")
                require(digest(configuration_without_restart(item)) == entry["preserved_configuration_digest"],
                        "configuracao_de_retomada_divergente")
                state = item["State"]["Status"]
                self.run("docker", "update", "--restart=" + entry["restart"], entry["id"])
                if state == "exited":
                    self.run("docker", "start", entry["id"])
                elif state != "running":
                    raise RestorationError("estado_de_retomada_desconhecido")
                deadline = self.monotonic() + 120
                while True:
                    item = self.inspect(entry["id"])
                    state = item["State"]["Status"]
                    health = item["State"].get("Health", {}).get("Status")
                    if state == "running" and health in {None, "healthy"}:
                        break
                    require(state in {"running", "starting"} and self.monotonic() < deadline,
                            "retomada_de_consumidor_nao_confirmada")
                    self.sleeper(0.5)
                resumed.append({"service": entry["service"], "id": entry["id"]})
            except (RestorationError, KeyError, TypeError):
                errors.append(entry.get("service", "unknown"))
        record["resumed_after_stop_failure"] = resumed
        record["stop_restore_errors"] = errors
        record["stop_restore"] = []
        self.journal(operation, record)
        return errors

    def quiesce(self, operation, receipt, record):
        saved = self._private(operation, receipt)
        # Verifica todos os consumidores antes do primeiro sinal/restart-policy change.
        current = {name:self._current(name) for name in SERVICES}
        for name, item in current.items():
            allowed = {receipt["inventory"]["services"][name]["image_id"], receipt["manifest"]["services"][name]["image_id"]}
            require(item["Image"] in allowed, "imagem_atual_desconhecida")
            baseline = saved["containers"][name]
            expected_id = record.get("active_ids", {}).get(name)
            if item["Image"] == baseline["Image"]:
                expected_id = record.get("previous_ids", {}).get(name) if record.get("phase") == "recovering" else None
                if not expected_id and not (record.get("phase") == "recovering" and record.get("intent") == name):
                    expected_id = receipt["inventory"]["services"][name]["container_id"]
            require(expected_id is None or item["Id"] == expected_id, "id_de_consumidor_divergente")
            if item["Image"] == baseline["Image"]:
                require(configuration(item) == configuration(baseline), "configuracao_baseline_divergente")
            else:
                expected = configuration(baseline)
                expected["environment"] = self._target_environment(saved, name, environment(item).get("FACIAL_PROCESSING_ENABLED") == "true")
                expected["host"]["ReadonlyRootfs"] = True
                expected["host"]["Tmpfs"] = CANDIDATE_TMPFS
                require(configuration(item) == expected, "configuracao_candidata_divergente")
            if item["State"]["Status"] == "running":
                self._assert_known_process(name, item)
        for item in current.values():
            self._assert_preserved_layer(item)

        affected = set(SERVICES)
        if record.get("phase") == "recovering":
            affected = set(record.get("replaced", [])) | {record.get("intent")}
            affected.discard(None)
        record.setdefault("drain_receipts", [])
        record["stop_restore"] = []
        try:
            for name in SERVICES:
                if name not in affected:
                    continue
                item = current[name]
                if item["State"]["Status"] != "running":
                    require(item["State"]["Status"] in {"exited", "created"}, "estado_de_parada_desconhecido")
                    continue
                receipt_entry = {
                    "service": name,
                    "id": item["Id"],
                    "image_id": item["Image"],
                    "configuration_digest": digest(configuration(item)),
                    "preserved_configuration_digest": digest(configuration_without_restart(item)),
                    "started_at": item["State"].get("StartedAt"),
                    "restart": self._restart_option(item),
                }
                require(receipt_entry["started_at"], "inicio_de_consumidor_ausente")
                record["stop_restore"].append(receipt_entry)
                record["stop_intent"] = name
                self.journal(operation, record)
                self.run("docker", "update", "--restart=no", item["Id"])
                self.run("docker", "kill", "--signal=SIGTERM", item["Id"])
                deadline = self.monotonic() + 120
                while True:
                    state = self.inspect(item["Id"])["State"]
                    if state["Status"] == "exited":
                        require(state.get("ExitCode") == 0, "saida_graciosa_nao_confirmada")
                        break
                    require(
                        state["Status"] == "running" and self.monotonic() < deadline,
                        "timeout_sem_sigkill",
                    )
                    self.sleeper(0.25)
                stopped = self.inspect(item["Id"])
                require(
                    stopped["Id"] == receipt_entry["id"]
                    and stopped["Image"] == receipt_entry["image_id"]
                    and stopped["State"].get("StartedAt") == receipt_entry["started_at"]
                    and digest(configuration_without_restart(stopped))
                    == receipt_entry["preserved_configuration_digest"],
                    "identidade_de_parada_divergente",
                )
                record.setdefault("stopped", []).append(name)
                record["drain_receipts"].append(
                    {**receipt_entry, "exit_code": 0, "phase": record["phase"]}
                )
                record.pop("stop_intent", None)
                self.journal(operation, record)
            for expected in current.values():
                item = self.inspect(expected["Id"])
                require(
                    item["Id"] == expected["Id"] and item["Image"] == expected["Image"],
                    "identidade_de_parada_divergente",
                )
                self._assert_preserved_layer(item)
            busy = self._sql(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND state IN "
                "('active','idle in transaction','idle in transaction (aborted)')"
            )
            require(busy == 0, "sessao_ativa_impede_troca")
            for entry in record["stop_restore"]:
                self.run("docker", "update", "--restart=" + entry["restart"], entry["id"])
        except RestorationError as error:
            record["last_stop_failure"] = str(error)
            resume_errors = self._restore_stopped(operation, record)
            if resume_errors:
                raise RestorationError("parada_falhou_retomada_incompleta") from None
            raise
        record["stop_restore"] = []
        record.pop("stop_intent", None)
        record.pop("last_stop_failure", None)
        self.journal(operation, record)

    def _target_environment(self, saved, service, enabled):
        result = environment(saved["containers"][service])
        api = environment(saved["containers"]["api"])
        for key in COHERENT:
            if key in api:
                result[key] = api[key]
            else:
                result.pop(key, None)
        general = saved.get("activation_policy", "strict") == GENERAL_RESTORE_MODE
        result.update(APP_ENV="production", FACIAL_CREDENTIAL_ENV="production",
                      PYTHONDONTWRITEBYTECODE="1",
                      FACIAL_PROCESSING_ENABLED="true" if enabled else "false",
                      FACIAL_REQUIRE_EXPLICIT_ROLLOUT="false" if general else "true",
                      FACIAL_REQUIRE_PRODUCTION_CALIBRATION="false" if general else "true")
        return result

    def replace(self, operation, receipt, service, *, enabled, previous=False):
        require(service in SERVICES, "servico_fora_do_escopo")
        saved = self._private(operation, receipt)
        baseline = saved["containers"][service]
        if previous:
            current = self._current(service)
            require(current["State"]["Status"] != "running", "consumidor_nao_pausado")
            if current["Image"] == baseline["Image"] and configuration_without_restart(current) == configuration_without_restart(baseline):
                policy = self._restart_option(baseline)
                self.run("docker", "update", "--restart=" + policy, current["Id"])
                if baseline["State"]["Status"] == "running":
                    self.run("docker", "start", current["Id"])
                    deadline = self.monotonic() + 120
                    while True:
                        current = self.inspect(current["Id"])
                        health = current["State"].get("Health", {}).get("Status")
                        if current["State"]["Status"] == "running" and health in {None, "healthy"}:
                            return current["Id"]
                        require(current["State"]["Status"] in {"running", "starting"}
                                and self.monotonic() < deadline, "retomada_de_consumidor_nao_confirmada")
                        self.sleeper(0.5)
                return current["Id"]
            require(current["State"]["Status"] in {"exited", "created"}, "consumidor_nao_pausado")
        model = copy.deepcopy(saved["models"][service])
        require(service in model.get("services", {}), "modelo_incompleto")
        target = model["services"][service]
        target["image"] = baseline["Image"] if previous else receipt["manifest"]["services"][service]["image_id"]
        target["environment"] = environment(baseline) if previous else self._target_environment(saved, service, enabled)
        target["command"] = baseline["Config"].get("Cmd")
        target["entrypoint"] = baseline["Config"].get("Entrypoint")
        target.pop("build", None)
        if not previous:
            target["read_only"] = True
            target["tmpfs"] = [f"{path}:{options}" for path, options in sorted(CANDIDATE_TMPFS.items())]
        data = json.dumps(_escape(model), sort_keys=True).encode()
        path = self._work(operation) / (service + ("-previous" if previous else "-enabled" if enabled else "-dark") + ".compose.json")
        if path.exists():
            require(self._read(path) == data, "modelo_persistido_divergente")
        else:
            self._write(path, data)
        args = ("docker", "compose", "--project-directory", str(self.root / "docker"), "-p", PROJECT, "-f", str(path), "--profile", "facial")
        self.run(*args, "config", "--quiet")
        # Recovery returns originally stopped facial services to a stopped state.
        action = "create" if previous and baseline["State"]["Status"] != "running" else "up"
        if previous:
            current = self._current(service)
            require(current.get("HostConfig", {}).get("ReadonlyRootfs") is True
                    and current.get("HostConfig", {}).get("Tmpfs") == CANDIDATE_TMPFS,
                    "candidato_nao_preservavel")
            self._assert_preserved_layer(current, reason="candidato_nao_preservavel")
        if action == "create":
            self.run(*args, action, "--no-deps", "--no-build", "--pull", "never", "--force-recreate", service)
        else:
            self.run(*args, action, "-d", "--no-deps", "--no-build", "--pull", "never", "--force-recreate", service)
        return self._current(service)["Id"]

    def verify(self, operation, receipt, *, enabled, previous=False):
        saved = self._private(operation, receipt)
        for service, baseline in saved["containers"].items():
            if service not in SERVICES:
                actual = self.inspect(baseline["Id"])
                require(actual["Id"] == baseline["Id"] and actual["Image"] == baseline["Image"] and configuration(actual) == configuration(baseline) and actual["State"]["Status"] == baseline["State"]["Status"] and actual["State"].get("StartedAt") == baseline["State"].get("StartedAt"), "peer_alterado")
                continue
            untouched = service in FACIAL and not enabled and not previous
            if untouched:
                actual = self.inspect(baseline["Id"])
            else:
                actual = self._current(service)
            expected_image = baseline["Image"] if previous or untouched else receipt["manifest"]["services"][service]["image_id"]
            require(actual["Image"] == expected_image, "imagem_carregada_divergente")
            expected = configuration(baseline)
            if not previous and not untouched:
                expected["environment"] = self._target_environment(saved, service, enabled)
                expected["host"]["ReadonlyRootfs"] = True
                expected["host"]["Tmpfs"] = CANDIDATE_TMPFS
            require(configuration(actual) == expected, "configuracao_carregada_divergente")
            running = baseline["State"]["Status"] == "running" if previous or untouched else True
            if running:
                deadline = self.monotonic() + 120
                while actual["State"].get("Health", {}).get("Status") != "healthy":
                    require(actual["State"]["Status"] == "running" and self.monotonic() < deadline, "healthcheck_nao_confirmado")
                    self.sleeper(0.5)
                    actual = self.inspect(actual["Id"])
            else:
                require(actual["State"]["Status"] in {"exited", "created"}, "facial_deveria_estar_parado")
            if not previous and not untouched:
                self._assert_preserved_layer(actual, reason="camada_candidata_nao_vazia")
        require(self._sql("SELECT json_agg(version_num) FROM alembic_version") == [SCHEMA], "schema_alterado")
        codes = [self.run("curl", "--proto", "=https", "--tlsv1.2", "--max-time", "10", "-sS", "-o", "/dev/null", "-w", "%{http_code}", ORIGIN + path) for path in ("/api/health", "/healthz")]
        require(codes == ["200", "200"], "https_nao_saudavel")
        return {"schema": SCHEMA, "peers_unchanged": True, "https": codes}

    def activation_proof(self, operation, approval: Approval):
        work = self._work(operation)
        evidence = json.loads(self._read(work / "gates.json"))
        require(evidence.get("fingerprint") == approval.fingerprint and evidence.get("scope_digest") == approval.scope_digest() and evidence.get("stage") == approval.stage, "evidencia_de_ativacao_divergente")
        require(set(evidence.get("gates", {})) == GATES, "conjunto_de_gates_incompleto")
        for gate in GATES:
            entry = evidence["gates"][gate]
            require(isinstance(entry, dict) and HEX.fullmatch(entry.get("sha256", "")), "evidencia_de_gate_invalida")
            name = entry.get("file", "")
            require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}\.json", name), "arquivo_de_gate_invalido")
            raw = self._read(work / name)
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"], "hash_de_evidencia_divergente")
            value = json.loads(raw)
            require(value.get("gate") == gate and value.get("fingerprint") == approval.fingerprint and value.get("scope_digest") == approval.scope_digest(), "vinculo_de_evidencia_divergente")
        api = self._current("api")
        saved = self._private(operation, self.load(operation))
        general = saved.get("activation_policy", "strict") == GENERAL_RESTORE_MODE
        if general:
            require(approval.stage == "general" and saved.get("authorization_reference"), "dispensa_nao_autorizada")
            decision = json.loads(self._read(work / evidence["gates"]["calibration"]["file"]))
            require(decision.get("decision") == "waived-by-owner"
                    and decision.get("authorization_reference") == saved["authorization_reference"],
                    "dispensa_sem_decisao_do_proprietario")
            require(environment(api).get("FACIAL_REQUIRE_EXPLICIT_ROLLOUT") == "false"
                    and environment(api).get("FACIAL_REQUIRE_PRODUCTION_CALIBRATION") == "false",
                    "modo_geral_nao_carregado")
        else:
            require(environment(api).get("FACIAL_REQUIRE_EXPLICIT_ROLLOUT") == "true"
                    and environment(api).get("FACIAL_REQUIRE_PRODUCTION_CALIBRATION") == "true",
                    "modo_estrito_nao_carregado")
        proof = self.obj("docker", "exec", "-i", api["Id"], "python", "-B", "-c",
                         GENERAL_ACTIVATION_PROBE if general else ACTIVATION_PROBE,
                         data=json.dumps({"allowlist": approval.allowlist, "stage": approval.stage,
                                          "authorization_reference": saved.get("authorization_reference")}).encode())
        proof["gates"] = sorted(GATES)
        return proof

    def recovery_proof(self, operation, receipt):
        """Consume a protected, separately produced restore receipt; never run restore."""
        value = json.loads(self._read(self._work(operation) / "recovery-proof.json"))
        require(value.get("format") == 1 and value.get("kind") == "logical-restore-proof-v1"
            and value.get("fingerprint") == receipt["fingerprint"]
            and value.get("schema") == SCHEMA
            and value.get("support_sha") == self.support_sha
            and value.get("restore_exit_code") == 0
            and HEX.fullmatch(value.get("backup_sha256", ""))
            and re.fullmatch(r"pyp-facial-restore-rehearsal-[0-9a-f]{10}", value.get("destination", "")),
            "prova_de_recuperacao_incompleta")
        evidence = value.get("evidence_file", "")
        require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}\.json", evidence)
            and HEX.fullmatch(value.get("evidence_sha256", "")), "recibo_de_restore_invalido")
        raw = self._read(self._work(operation) / evidence)
        require(hashlib.sha256(raw).hexdigest() == value["evidence_sha256"], "evidencia_de_restore_divergente")
        proof = json.loads(raw)
        require(proof.get("backup_sha256") == value["backup_sha256"]
            and proof.get("destination") == value["destination"]
            and proof.get("schema") == SCHEMA
            and proof.get("restore_exit_code") == 0, "restore_nao_comprovado")

    def functional_proof(self, operation, approval):
        work = self._work(operation)
        value = json.loads(self._read(work / "functional-proof.json"))
        require(value.get("fingerprint") == approval.fingerprint and value.get("scope_digest") == approval.scope_digest(), "prova_funcional_divergente")
        try:
            request_id = str(UUID(value["request_id"]))
        except (ValueError, TypeError, KeyError):
            raise RestorationError("consulta_de_prova_invalida") from None
        artifact = value.get("ui_artifact", "")
        require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}\.png", artifact)
            and HEX.fullmatch(value.get("ui_artifact_sha256", "")), "artefato_de_ui_invalido")
        raw = self._read(work / artifact)
        require(raw.startswith(b"\x89PNG\r\n\x1a\n") and hashlib.sha256(raw).hexdigest() == value["ui_artifact_sha256"], "artefato_de_ui_divergente")
        record = self.read_journal(operation)
        api = self._current("api")
        proof = self.obj("docker", "exec", "-i", api["Id"], "python", "-B", "-c", FUNCTIONAL_PROBE,
            data=json.dumps({"request_id":request_id, "allowlist":approval.allowlist, "started_at":record["activation_started_at"]}).encode())
        require(proof.get("request_ready") is True and proof.get("reference_purged") is True, "consulta_real_nao_confirmada")
        proof.update(fingerprint=approval.fingerprint, scope_digest=approval.scope_digest(), ui_artifact_sha256=value["ui_artifact_sha256"])
        return proof

    def complete(self, operation, result):
        record = self.read_journal(operation)
        require(record.get("phase") == "complete" and record.get("fingerprint") == result.get("fingerprint"), "journal_nao_concluido")
        require(record.get("enabled") == result.get("enabled"), "estado_final_divergente")
        path = self._work(operation) / ("activated.json" if result["enabled"] else "recovered.json")
        raw = json.dumps(result, sort_keys=True).encode()
        if path.exists():
            require(self._read(path) == raw, "recibo_final_divergente")
        else:
            self._write(path, raw)
        journal = self._work(operation) / "in-flight.json"
        self._read(journal)
        journal.unlink()
        directory = os.open(journal.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
