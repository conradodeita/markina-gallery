"""Contratos isolados; Docker CLI real só acessa API sintética em loopback, nunca daemon/SSH."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SHA_OLD = "a" * 40
SHA_MAIN = "b" * 40
IMAGE_OLD = "sha256:" + "1" * 64
IMAGE_NEW = "sha256:" + "2" * 64
API_OLD = "sha256:" + "3" * 64
API_NEW = "sha256:" + "4" * 64
HASH_WEB = "5" * 64
HASH_API = "6" * 64
BASH = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")

# A fronteira de comandos externos é simulada. Os contratos de estado/ordem,
# filesystem, fingerprint e scripts sob teste são reais.
STUB = r'''
import sys,json,os,hashlib
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(newline="\n")
p=Path(os.environ["FIXTURE"])
s=json.loads(p.read_text())
a=sys.argv[2:]; kind=sys.argv[1]
compose_version=""
if kind=="docker" and a and a[0].startswith("__APP_VERSION="):
    compose_version=a.pop(0).split("=",1)[1]
with Path(os.environ["CALLS"]).open("a") as log: log.write(kind+" "+" ".join(a)+"\n")
def save(): p.write_text(json.dumps(s))
def die(message="stub refused",code=1): print(message,file=sys.stderr);sys.exit(code)
def image(ref):
    if ref in s["images"]: return s["images"][ref]
    if ref in s["images"].values(): return ref
    die("image absent")
if kind=="git":
    if a[0]=="rev-parse":
        v=a[-1]
        if ":scripts/" in v:
            data=(Path(os.environ["SOURCE_ROOT"])/v.split(":",1)[1]).read_bytes().replace(b"\r\n",b"\n")
            print(hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest())
        else: print(s["root"] if v=="--show-toplevel" else s["checkout"] if v=="HEAD" else s["main"])
    elif a[:2]==["remote","get-url"]: print("https://github.com/example/project")
    elif a[0]=="ls-remote": print(s["remote"]+"\trefs/heads/main")
    elif a[0]=="status":
        if s.get("dirty"): print(" M unexpected")
    elif a[0]=="check-ignore": pass
    elif a[0]=="cat-file":
        if s.get("missing_target"): die("missing commit")
    elif a[0]=="merge-base":
        if s.get("ancestry_fail"): die("bad ancestry")
    elif a[0]=="diff":
        if s.get("scope_fail"): die("backend mismatch")
    elif a[0]=="switch": s["checkout"]=a[-1];save()
    elif a[0]=="show":
        path=a[-1].split(":",1)[1]
        if path.endswith("check_prod_app_release_scope.py"): print("raise SystemExit(0)")
        elif path.endswith("runtime-gates.json"): print("{}")
        else: print((Path(os.environ["SOURCE_ROOT"])/path).read_text())
    else: die("unexpected git "+repr(a))
elif kind=="dependency-policy":
    # Pure policy boundary: real Git/build-context behavior is covered by
    # test_dependency_release.py, including its actual shell invocation.
    if s.get("scope_fail"): die("dependency scope refused")
    print('{"fixture_policy_contract":true}')
elif kind=="docker":
    if a[0]=="ps": print("\n".join(s["services"]))
    elif a[:2]==["image","inspect"]: print(image(a[-1]))
    elif a[:2]==["image","tag"]:
        val=image(a[2]);s["images"][a[3]]=val;save()
    elif a[0]=="inspect":
        fmt=a[a.index("--format")+1];target=a[-1]
        service=next((k for k,v in s["services"].items() if target in (k,v["id"])),None)
        if service is None: die("container absent")
        c=s["services"][service]
        if fmt=="{{.Image}}": print(c["image"])
        elif fmt=="{{.Config.Image}}": print("markina-gallery-"+service)
        elif "Config.Env" in fmt:
            print(s["api_version"] if "{{range" in fmt else json.dumps(["APP_VERSION="+s["api_version"]]))
        elif "NetworkSettings.Ports" in fmt: print('{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}')
        elif "|" in fmt: print("|".join([c["id"],c["image"],c["started"],"running",c["health"],c["hash"]]))
        elif "State.Health" in fmt: print(c["health"])
        elif "project.working_dir" in fmt: print(s["root"]+"/docker")
        elif "project.config_files" in fmt: print(s["files"])
        elif "config-hash" in fmt: print(c["hash"])
        elif "compose.service" in fmt: print(service)
        elif "compose.project" in fmt: print("markina-gallery")
        else: die("unknown inspect "+fmt)
    elif a[0]=="compose":
        index=next(i for i,x in enumerate(a) if x in ("ps","config","build","up","exec"));cmd=a[index:]
        if cmd[0]=="config":
            if "--hash" in cmd:
                if cmd[-1]=="web": print("web "+s["web_hash"])
                else: print("api "+s["services"]["api"]["hash"]+"\nweb "+s["web_hash"])
            elif "json" in cmd: print("{}")
        elif cmd[0]=="ps":
            service=cmd[-1]
            if service in s["services"]: print(s["services"][service]["id"])
        elif cmd[0]=="build":
            if s.get("build_fail"): die("synthetic build failure")
            for service in cmd[1:]: s["images"]["markina-gallery-"+service]=s["built"][service]
            if s.get("drift_build"): s["services"]["worker"]["started"]="changed"
            if s.get("health_drift_build"): s["services"]["web"]["health"]="unhealthy"
            if s.get("config_drift_build"): Path(s["overlay_native"]).write_text("changed overlay")
            save()
        elif cmd[0]=="up":
            if s.get("up_fail"): die("synthetic recreate failure")
            for service in ("api","web"):
                if service in cmd:
                    c=s["services"].setdefault(service,{"hash":s["web_hash"],"started":"new"})
                    c["image"]=image("markina-gallery-"+service);c["id"]="new-"+service;c["health"]="unhealthy" if s.get("health_fail") else "healthy"
                    if service=="web" and s.get("wrong_image_up"): c["image"]=s["wrong_image"]
                    if service=="api": s["api_version"]=compose_version or s["main"]
            save()
        elif cmd[0]=="exec":
            if "alembic" in cmd: print("20261022_0087 (head)")
        else: die("unexpected compose "+repr(cmd))
    else: die("unexpected docker "+repr(a))
elif kind=="curl":
    if s.get("http_fail"): die("synthetic HTTPS failure")
    if "--write-out" in a: print("404" if not s.get("statistics_back") else "200",end="")
else: die("unknown kind")
'''

RPC_SERVER = r'''
import contextlib,io,sys
sys.stdout.reconfigure(newline="\n")
code=compile(open(sys.argv[1]).read(),sys.argv[1],"exec")
reader=sys.stdin.buffer
def field():
    value=bytearray()
    while True:
        c=reader.read(1)
        if not c: raise EOFError
        if c==b"\0": return value.decode()
        value.extend(c)
while True:
    try:
        args=[]
        while (value:=field())!="__END__": args.append(value)
    except EOFError: break
    out,err=io.StringIO(),io.StringIO(); status=0
    sys.argv=["stub.py",*args]
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        try: exec(code,{"__name__":"__main__"})
        except SystemExit as e: status=e.code or 0
        except Exception as e: status=99; print(repr(e),file=sys.stderr)
    sys.stdout.write(out.getvalue()+"\0"+err.getvalue()+"\0"+str(status)+"\n")
    sys.stdout.flush()
'''


class ReleaseContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release-contract-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.state = self.base / "state"
        self.project.mkdir()
        self.state.mkdir()
        self.fixture = self.base / "model.json"
        self.calls = self.base / "calls.log"
        self.stub = self.base / "stub.py"
        self.stub.write_text(STUB, encoding="utf-8")
        self.server = self.base / "rpc.py"
        self.server.write_text(RPC_SERVER, encoding="utf-8")
        def shell_path(path):
            if os.name != "nt":
                return path.as_posix()
            return subprocess.check_output([BASH, "-c", 'cygpath -u "$1"', "--", path.as_posix()], text=True).strip()
        project_shell, state_shell = shell_path(self.project), shell_path(self.state)
        self.scripts = {}
        for name in ("web", "app-services"):
            text = (ROOT / f"scripts/deploy-prod-{name}.sh").read_text(encoding="utf-8")
            text = text.replace("/opt/markina-gallery", project_shell).replace("/var/lib/markina-gallery/deploy-state", state_shell)
            path = self.base / f"{name}.sh"
            path.write_text(text, encoding="utf-8", newline="\n")
            self.scripts[name] = path
        files = re.search(r'COMPOSE_FILE_LABEL="([^"]+)"', self.scripts["web"].read_text()).group(1)
        for path in files.split(","):
            if os.name == "nt":
                path = subprocess.check_output([BASH, "-c", 'cygpath -w "$1"', "--", path], text=True).strip()
            f = Path(path)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("fixture")
        (self.project / "docker/.env.homolog").write_text("fixture; no credentials")
        self.model = {
            "root": project_shell, "main": SHA_MAIN, "remote": SHA_MAIN,
            "checkout": SHA_OLD, "api_version": SHA_OLD, "files": files, "web_hash": HASH_WEB,
            "overlay_native": str(self.state / "branding.compose.yml"),
            "images": {"markina-gallery-web": IMAGE_OLD, "markina-gallery-api": API_OLD},
            "built": {"web": IMAGE_NEW, "api": API_NEW},
            "services": {k: {"id": k, "image": i, "hash": h, "started": "unchanged", "health": "healthy"}
                         for k, i, h in [("web", IMAGE_OLD, HASH_WEB), ("api", API_OLD, HASH_API),
                                         ("nginx", "sha256:" + "7" * 64, "8" * 64),
                                         ("worker", "sha256:" + "9" * 64, "0" * 64)]},
        }
        self.save()
        self.current = f"{SHA_OLD} {IMAGE_OLD} {HASH_WEB} {SHA_OLD}"
        (self.state / "web-current.identity").write_text(self.current + "\n")
        (self.state / "production-release.lock").write_text("existing-lock-content\n")

    def save(self):
        self.fixture.write_text(json.dumps(self.model))

    def reload(self):
        self.model = json.loads(self.fixture.read_text())
        return self.model

    def mutate(self, **changes):
        self.model.update(changes)
        self.save()

    def log(self):
        return self.calls.read_text() if self.calls.exists() else ""

    def run_shell(self, code, flow="web", extra="", ok=True):
        quote = lambda p: "'" + str(p).replace("'", "'\\''") + "'"
        env = os.environ.copy()
        env.update(FIXTURE=str(self.fixture), CALLS=str(self.calls), SOURCE_ROOT=str(ROOT))
        python = quote(Path(os.sys.executable).as_posix())
        script = f'''source {quote(self.scripts[flow].as_posix())}
source {quote((ROOT/'scripts/deploy-prod-state.sh').as_posix())}
source {quote((ROOT/'scripts/deploy-prod-lock.sh').as_posix())}
cd {quote(self.project.as_posix())}
EXPECTED_REPOSITORY=example/project
EXPECTED_URL="$PUBLIC_URL"
coproc RPC {{ {python} -u {quote(self.server.as_posix())} {quote(self.stub.as_posix())}; }}
rpc_pid=$RPC_PID
exec 7<&${{RPC[0]}} 8>&${{RPC[1]}}
trap 'kill "$rpc_pid" 2>/dev/null || true' EXIT
stub_call() {{
  local output error status
  while ! mkdir {quote((self.base/'rpc.lock').as_posix())} 2>/dev/null; do command sleep 0.01; done
  printf '%s\\0' "$@" '__END__' >&8
  IFS= read -r -d '' output <&7
  IFS= read -r -d '' error <&7
  IFS= read -r status <&7
  rmdir {quote((self.base/'rpc.lock').as_posix())}
  printf '%s' "$output"
  printf '%s' "$error" >&2
  return "$status"
}}
python3() {{ {python} "$@"; }}
git() {{ stub_call git "$@"; }}
dependency_policy() {{
  if [[ "$1" == web-build ]]; then cat >/dev/null; fi
  stub_call dependency-policy "$@"
}}
docker() {{
  if [[ "$*" == "compose "* && " $* " == *" -f - "* ]]; then cat >/dev/null; fi
  stub_call docker "__APP_VERSION=${{APP_VERSION:-}}" "$@"
}}
curl() {{ stub_call curl "$@"; }}
hostname() {{ echo clearbudget-vnic; }}
sleep() {{ :; }}
flock() {{ return 0; }}
{extra}
{code}
'''
        result = subprocess.run([BASH, "-c", script], env=env, capture_output=True, text=True, timeout=120, check=False)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr + "\n" + self.log()[-3000:])
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def mode(self, mode, flow="web", approval=None, extra="", ok=True, args=""):
        flag = "--approval-code" if flow == "web" else "--approval-fingerprint"
        return self.run_shell(f'main --mode {mode} --sha {self.model["main"]} {flag+" "+approval if approval else ""} {args}', flow, extra, ok)

    def fingerprint(self, mode="inventory", flow="web", args=""):
        result = self.mode(mode, flow, args=args)
        return re.search(r'approval_(?:code|fingerprint)=([0-9a-f]{64})', result.stdout).group(1)

    def snapshot(self):
        return {p.relative_to(self.base).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for folder in (self.state, self.project) for p in folder.rglob("*") if p.is_file()}

    def release(self):
        self.mode("release", approval=self.fingerprint())

    def test_inventory_no_writes_or_lock_even_missing(self):
        (self.state / "production-release.lock").unlink()
        before = self.snapshot()
        self.mode("inventory", extra="flock() { exit 79; }; mktemp() { exit 78; }")
        self.assertEqual(before, self.snapshot())
        self.assertNotRegex(self.log(), r'git (fetch|switch)|image tag|compose .* (up|build)')

    def test_app_inventory_no_temporary_fetch_or_writes(self):
        before = self.snapshot()
        self.mode("inventory", flow="app-services", extra="flock() { exit 79; }; mktemp() { exit 78; }")
        self.assertEqual(before, self.snapshot())
        self.assertNotIn("git fetch", self.log())

    def test_missing_or_conflicting_identity_fails_before_mutation(self):
        for value in (None, self.current.replace(IMAGE_OLD, IMAGE_NEW), "malformed"):
            p = self.state / "web-current.identity"
            if value is None:
                p.unlink(missing_ok=True)
            else:
                p.write_text(value + "\n")
            before = self.snapshot()
            self.mode("inventory", ok=False)
            self.assertEqual(before, self.snapshot())

    def test_legacy_markers_do_not_override_identity(self):
        for name in ("web-last-healthy.sha", "app-last-healthy.sha", "last-healthy.sha"):
            (self.state / name).write_text("c" * 40 + "\n")
        self.fingerprint()

    def test_explicit_reconciliation_preserves_id_not_markers(self):
        (self.state / "web-current.identity").unlink()
        args = f"--active-sha {SHA_OLD} --active-image {IMAGE_OLD}"
        before = self.snapshot()
        fp = self.fingerprint("reconcile-inventory", args=args)
        self.assertEqual(before, self.snapshot())
        self.mode("reconcile", approval=fp, args=args)
        self.assertEqual((self.state / "web-current.identity").read_text().strip(), self.current)
        self.assertEqual(self.reload()["services"]["web"]["id"], "web")
        self.mode("reconcile-inventory", args=args, ok=False)

    def test_wrong_reconciliation_image_fails(self):
        (self.state / "web-current.identity").unlink()
        self.mode("reconcile-inventory", args=f"--active-sha {SHA_OLD} --active-image {IMAGE_NEW}", ok=False)

    def test_wrong_sha_missing_object_and_scope_fail_closed(self):
        for change in ({"remote": "c" * 40}, {"missing_target": True}, {"scope_fail": True}, {"dirty": True}):
            original = dict(self.model)
            self.mutate(**change)
            before = self.snapshot()
            self.mode("inventory", ok=False)
            self.assertEqual(before, self.snapshot())
            self.model = original
            self.save()

    def test_wrong_fingerprint_does_not_mutate(self):
        before = self.snapshot()
        self.mode("release", approval="0" * 64, ok=False)
        self.assertEqual(before, self.snapshot())
        self.assertNotIn("image tag", self.log())

    def test_release_preserves_image_and_other_services(self):
        nonweb = {k: dict(v) for k, v in self.model["services"].items() if k != "web"}
        self.release()
        self.reload()
        self.assertEqual(self.model["services"]["web"]["image"], IMAGE_NEW)
        self.assertEqual({k: v for k, v in self.model["services"].items() if k != "web"}, nonweb)
        self.assertEqual((self.state / "web-previous.identity").read_text().strip(), self.current)
        self.assertFalse((self.state / "web-pending.identity").exists())
        self.assertIn("up -d --no-deps --no-build --force-recreate web", self.log())
        self.assertNotRegex(self.log(), r'(nginx -s|alembic upgrade|docker .*prune)')

    def test_build_failure_recovery_does_not_recreate_old_container(self):
        fp = self.fingerprint()
        self.mutate(build_fail=True)
        self.mode("release", approval=fp, ok=False)
        self.assertTrue((self.state / "web-pending.identity").exists())
        self.assertNotIn("up -d", self.log())
        self.reload()
        self.assertEqual(self.model["services"]["web"]["image"], IMAGE_OLD)
        self.mutate(build_fail=False)
        fp = self.fingerprint("recover-inventory")
        self.mode("recover", approval=fp)
        self.assertEqual(self.reload()["checkout"], SHA_OLD)
        self.assertNotIn("up -d", self.log())

    def test_failed_health_or_https_recovery_restores_exact_id(self):
        for failure in ("health_fail", "http_fail", "statistics_back"):
            fp = self.fingerprint()
            self.mutate(**{failure: True})
            self.mode("release", approval=fp, ok=False)
            self.assertTrue((self.state / "web-pending.identity").exists())
            self.reload()
            self.mutate(**{failure: False})
            fp = self.fingerprint("recover-inventory")
            self.mode("recover", approval=fp)
            self.assertEqual(self.reload()["services"]["web"]["image"], IMAGE_OLD)

    def test_recovery_with_absent_web(self):
        fp = self.fingerprint()
        self.mutate(up_fail=True)
        self.mode("release", approval=fp, ok=False)
        self.reload()
        del self.model["services"]["web"]
        self.model["up_fail"] = False
        self.save()
        fp = self.fingerprint("recover-inventory")
        self.mode("recover", approval=fp)
        self.assertEqual(self.reload()["services"]["web"]["image"], IMAGE_OLD)

    def test_runtime_drift_build_prevents_recreation(self):
        fp = self.fingerprint()
        self.mutate(drift_build=True)
        self.mode("release", approval=fp, ok=False)
        self.assertNotIn("up -d", self.log())
        self.mode("recover-inventory", ok=False)

    def test_rollback_checks_id_and_image_availability(self):
        self.release()
        fp = self.fingerprint("rollback-inventory")
        self.mode("rollback", approval=fp)
        self.assertEqual(self.reload()["services"]["web"]["image"], IMAGE_OLD)
        self.assertEqual(self.model["checkout"], SHA_OLD)

    def test_missing_or_retagged_rollback_image_blocks_before_checkout(self):
        self.release()
        self.reload()
        saved = "markina-gallery-web:rollback-" + IMAGE_OLD.split(":")[1]
        for value in (None, IMAGE_NEW):
            if value is None:
                self.model["images"].pop(saved, None)
                self.model["images"] = {k: v for k, v in self.model["images"].items() if v != IMAGE_OLD}
            else:
                self.model["images"][saved] = value
            self.save()
            before = self.snapshot()
            self.mode("rollback-inventory", ok=False)
            self.assertEqual(before, self.snapshot())

    def test_lock_busy_missing_and_cross_flow_pending(self):
        fp = self.fingerprint()
        before = self.snapshot()
        self.mode("release", approval=fp, extra="flock() { return 1; }", ok=False)
        self.assertEqual(before, self.snapshot())
        (self.state / "production-release.lock").unlink()
        self.mode("release", approval=fp, ok=False)
        (self.state / "production-release.lock").write_text("lock")
        (self.state / "app-rollback-in-flight.sha").write_text(SHA_OLD)
        self.mode("release", approval=fp, ok=False)

    def test_lock_not_truncated(self):
        p = self.state / "production-release.lock"
        before = (p.read_bytes(), p.stat().st_mtime_ns)
        self.release()
        self.assertEqual(before, (p.read_bytes(), p.stat().st_mtime_ns))

    def test_app_then_web_and_web_then_app(self):
        fp = self.fingerprint(flow="app-services")
        self.mode("release", flow="app-services", approval=fp)
        receipt = (self.state / "web-current.identity").read_text().split()
        self.assertEqual(receipt[:2], [SHA_MAIN, IMAGE_NEW])
        self.reload()
        next_sha, next_image = "c" * 40, "sha256:" + "f" * 64
        self.model["built"]["web"] = next_image
        self.mutate(main=next_sha, remote=next_sha)
        api_before = dict(self.model["services"]["api"])
        self.release()
        self.assertEqual(self.reload()["services"]["api"], api_before)
        self.assertEqual(self.model["api_version"], SHA_MAIN)
        self.assertEqual((self.state / "web-current.identity").read_text().split()[:2], [next_sha, next_image])

    def test_web_then_app_inventory_preserves_api_version(self):
        self.release()
        self.reload()
        self.assertEqual(self.model["api_version"], SHA_OLD)
        self.fingerprint(flow="app-services")

    def test_web_then_app_release_and_rollback_preserve_independent_versions(self):
        self.release()
        self.reload()
        self.mutate(main="c" * 40, remote="c" * 40)
        fp = self.fingerprint(flow="app-services")
        self.mode("release", flow="app-services", approval=fp)
        self.assertEqual((self.state / "app-api-rollback.version").read_text().strip(), SHA_OLD)
        self.assertEqual((self.state / "app-web-rollback.identity").read_text().split()[:2], [SHA_MAIN, IMAGE_NEW])
        fp = self.fingerprint("rollback-inventory", flow="app-services")
        self.mode("rollback", flow="app-services", approval=fp)
        self.assertEqual(self.reload()["api_version"], SHA_OLD)
        self.assertEqual(self.model["services"]["api"]["image"], API_OLD)
        self.assertEqual(self.model["services"]["web"]["image"], IMAGE_NEW)
        self.fingerprint()

    def test_app_failed_build_or_health_preserves_recovery_identity(self):
        for failure in ("build_fail", "health_fail"):
            fp = self.fingerprint(flow="app-services")
            self.mutate(**{failure: True})
            self.mode("release", flow="app-services", approval=fp, ok=False)
            self.assertTrue((self.state / "app-in-flight.sha").exists())
            self.reload()
            self.mutate(**{failure: False})
            fp = self.fingerprint("rollback-inventory", flow="app-services")
            self.mode("rollback", flow="app-services", approval=fp)
            self.assertEqual(self.reload()["services"]["web"]["image"], IMAGE_OLD)
            self.assertEqual(self.model["services"]["api"]["image"], API_OLD)

    def test_recovery_failure_keeps_pending_evidence(self):
        fp = self.fingerprint()
        self.mutate(health_fail=True)
        self.mode("release", approval=fp, ok=False)
        fp = self.fingerprint("recover-inventory")
        self.mode("recover", approval=fp, ok=False)
        self.assertTrue((self.state / "web-pending.identity").exists())
        self.mode("inventory", ok=False)

    def test_health_drift_during_build_blocks_recreation(self):
        fp = self.fingerprint()
        self.mutate(health_drift_build=True)
        self.mode("release", approval=fp, ok=False)
        self.assertNotIn("up -d", self.log())

    def test_compose_drift_during_build_blocks_recreation_and_recovery(self):
        fp = self.fingerprint()
        self.mutate(config_drift_build=True)
        self.mode("release", approval=fp, ok=False)
        self.assertNotIn("up -d", self.log())
        self.mode("recover-inventory", ok=False)

    def test_unexpected_runtime_image_is_not_declared_healthy(self):
        fp = self.fingerprint()
        self.mutate(wrong_image_up=True, wrong_image=IMAGE_OLD)
        self.mode("release", approval=fp, ok=False)
        self.assertTrue((self.state / "web-pending.identity").exists())
        self.assertEqual((self.state / "web-current.identity").read_text().strip(), self.current)

    def test_recovery_rejects_image_outside_the_failed_attempt(self):
        fp = self.fingerprint()
        self.mutate(health_fail=True)
        self.mode("release", approval=fp, ok=False)
        self.reload()
        unexpected = "sha256:" + "e" * 64
        self.model["services"]["web"].update(image=unexpected, health="healthy")
        self.model["images"]["unrelated-release"] = unexpected
        self.mutate(health_fail=False)
        before = self.snapshot()
        self.mode("recover-inventory", ok=False)
        self.assertEqual(before, self.snapshot())

    def test_rollback_accepts_unhealthy_current_image_with_valid_identity(self):
        self.release()
        self.reload()
        self.model["services"]["web"]["health"] = "unhealthy"
        self.save()
        fp = self.fingerprint("rollback-inventory")
        self.mode("rollback", approval=fp)
        self.assertEqual(self.reload()["services"]["web"]["image"], IMAGE_OLD)

    def test_wrapper_validates_body_in_memory_and_rejects_tampering(self):
        # Fronteiras curl/bash são stubs; a lógica de regex e blob do wrapper é real.
        source = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(encoding="utf-8")
        source = source.replace('/opt/markina-gallery', self.model['root'])
        path = self.base / 'wrapper.sh'
        path.write_text(source, encoding='utf-8', newline='\n')
        # GitHub raw serves Git LF bytes; a Windows checkout may use CRLF.
        payload = self.base / 'app-payload.sh'
        payload.write_text((ROOT / 'scripts/deploy-prod-app-services.sh').read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
        quote = lambda p: "'" + str(p).replace("'", "'\\''") + "'"
        python = quote(Path(os.sys.executable).as_posix())
        for tamper in (False, True):
            command = f'''
export SSH_ORIGINAL_COMMAND=MARKINA_APP_TARGET_SHA={SHA_MAIN}
curl() {{ cat {quote(payload.as_posix())}; {'echo tampered' if tamper else ':'}; }}
git() {{ {python} -c 'import sys,hashlib; sys.stdout.reconfigure(newline="\\n"); b=sys.stdin.buffer.read(); print(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\\0"+b).hexdigest())'; }}
bash() {{ cat >/dev/null; echo verified-body; }}
mktemp() {{ exit 79; }}
source {quote(path.as_posix())}
'''
            before = self.snapshot()
            result = subprocess.run([BASH, '-c', command], capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(result.returncode == 0, not tamper, result.stderr)
            self.assertEqual('verified-body' in result.stdout, not tamper)
            self.assertEqual(before, self.snapshot())

    def test_orders_wrapper_runs_only_pinned_python_inventory_with_exact_sha(self):
        source = (ROOT / "scripts/production-preflight-ssh-wrapper.sh").read_text(encoding="utf-8")
        source = source.replace('/opt/markina-gallery', self.model['root'])
        path = self.base / 'orders-wrapper.sh'
        path.write_text(source, encoding='utf-8', newline='\n')
        payload = self.base / 'orders-payload.py'
        payload.write_text((ROOT / 'scripts/orders_pilot_release.py').read_text(encoding='utf-8'),
                           encoding='utf-8', newline='\n')
        args = self.base / 'orders-args.txt'
        quote = lambda p: "'" + str(p).replace("'", "'\\''") + "'"
        python = quote(Path(os.sys.executable).as_posix())
        command = f'''
export SSH_ORIGINAL_COMMAND=MARKINA_ORDERS_TARGET_SHA={SHA_MAIN}
curl() {{ cat {quote(payload.as_posix())}; }}
git() {{ {python} -c 'import sys; sys.stdout.reconfigure(newline="\\n"); b=sys.stdin.buffer.read(); import hashlib; print(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\\0"+b).hexdigest())'; }}
python3() {{ printf '%s\\n' "$@" > {quote(args.as_posix())}; cat >/dev/null; echo verified-orders-body; }}
source {quote(path.as_posix())}
'''
        before = self.snapshot()
        result = subprocess.run([BASH, '-c', command], capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('verified-orders-body', result.stdout)
        python_args = args.read_text().splitlines()
        self.assertEqual(python_args[:2], ['-B', '-'])
        import orders_pilot_release as release

        output = io.StringIO()
        with (patch('sys.argv', ['orders_pilot_release.py', *python_args[2:]]),
              patch.object(release.Host, 'main_sha', return_value=SHA_MAIN),
              patch.object(release.Host, 'inventory', return_value={'checkout_sha': SHA_OLD}) as inventory,
              patch.object(release, 'validate_inventory', return_value='f' * 64),
              contextlib.redirect_stdout(output)):
            release.main()
        inventory.assert_called_once_with()
        self.assertEqual(json.loads(output.getvalue().splitlines()[0])['target_sha'], SHA_MAIN)
        self.assertEqual(before, self.snapshot())

    def test_malformed_sha_is_rejected_without_queries(self):
        self.run_shell('main --mode inventory --sha invalid', ok=False)
        self.assertEqual(self.log(), '')

    def test_recovery_remains_possible_if_remote_main_advances(self):
        fp = self.fingerprint()
        self.mutate(build_fail=True)
        self.mode("release", approval=fp, ok=False)
        self.reload()
        self.mutate(build_fail=False, remote="c" * 40)
        fp = self.fingerprint("recover-inventory")
        self.mode("recover", approval=fp)
        self.assertEqual(self.reload()["checkout"], SHA_OLD)

    @unittest.skipIf(os.name == "nt", "flock real é validado no Linux isolado e CI")
    def test_real_flock_excludes_app_and_web_without_truncation(self):
        self.assertIsNotNone(shutil.which("flock"))
        marker = self.base / "acquired"
        command = f'source "{ROOT}/scripts/deploy-prod-lock.sh"; acquire_production_deploy_lock "{self.state}" web; touch "{marker}"; sleep 2'
        process = subprocess.Popen([BASH, "-c", command])
        self.addCleanup(lambda: process.wait(timeout=5))
        import time
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(marker.exists())
        before = (self.state / "production-release.lock").read_bytes()
        result = subprocess.run([BASH, "-c", f'source "{ROOT}/scripts/deploy-prod-lock.sh"; acquire_production_deploy_lock "{self.state}" app'], capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.state / "production-release.lock").read_bytes(), before)

    def test_fingerprint_cannot_hide_runtime_failure(self):
        self.model["services"]["web"]["health"] = "unhealthy"
        self.save()
        self.mode("inventory", flow="app-services", ok=False)


class DockerSnapshotContracts(unittest.TestCase):
    """Exercita o template Go real, sem criar/inspecionar containers reais."""

    def setUp(self):
        docker = shutil.which("docker")
        if not docker:
            if os.environ.get("CI"):
                self.fail("CI precisa do Docker CLI para testar o template real")
            self.skipTest("Docker CLI ausente; executar esta classe no host/CI")
        temp = tempfile.TemporaryDirectory(prefix="snapshot-docker-api-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.helper = self.base / "state.sh"
        self.helper.write_text((ROOT / "scripts/deploy-prod-state.sh").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        self.containers = {}
        cases = [
            ("migrate", "exited", {}),
            ("worker", "running", {}),
            ("empty-health", "exited", {"Health": {}}),
            ("null-health", "running", {"Health": None}),
            ("missing-health-status", "running", {"Health": {"FailingStreak": 0}}),
            ("null-health-status", "running", {"Health": {"Status": None}}),
            ("empty-health-status", "running", {"Health": {"Status": ""}}),
            ("api", "running", {"Health": {"Status": "healthy"}}),
            ("unhealthy-worker", "running", {"Health": {"Status": "unhealthy"}}),
            ("starting-worker", "running", {"Health": {"Status": "starting"}}),
            ("web", "running", {"Health": {"Status": "healthy"}}),
        ]
        for number, (service, status, optional) in enumerate(cases, 1):
            cid = f"{number:x}" * 64
            self.containers[cid] = {
                "Id": cid, "Image": IMAGE_OLD,
                "State": {"StartedAt": "2026-09-29T19:12:34.023453014Z", "Status": status, **optional},
                "Config": {"Labels": {"com.docker.compose.project": "snapshot-fixture",
                                      "com.docker.compose.service": service,
                                      "com.docker.compose.config-hash": HASH_API}},
            }
        self.failed_id = None
        self.requests = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                fixture.requests.append((self.command, self.path))
                path = urlparse(self.path).path
                if path.endswith("/containers/json"):
                    data = [{"Id": cid, "Names": ["/" + c["Config"]["Labels"]["com.docker.compose.service"]],
                             "Image": "fixture-image", "ImageID": c["Image"], "Command": "fixture", "Created": 1,
                             "State": c["State"]["Status"], "Status": c["State"]["Status"],
                             "Labels": c["Config"]["Labels"], "Ports": []} for cid, c in fixture.containers.items()]
                elif "/containers/" in path and path.endswith("/json"):
                    prefix = path.split("/")[-2]
                    matches = [c for cid, c in fixture.containers.items() if cid.startswith(prefix)]
                    if not matches or matches[0]["Id"] == fixture.failed_id:
                        self.send_error(500, "synthetic inspect failure")
                        return
                    data = matches[0]
                else:
                    self.send_error(404, "unexpected synthetic API request")
                    return
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close_server():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(close_server)
        self.env = os.environ.copy()
        for name in ("DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
            self.env.pop(name, None)
        self.env.update(DOCKER_HOST=f"tcp://127.0.0.1:{server.server_port}", DOCKER_API_VERSION="1.45",
                        DOCKER_CONFIG=str(self.base), DOCKER_CLI_HINTS="false")
        # Apenas um cliente real: nenhuma chamada pode alcançar o daemon do host.
        self.env["PATH"] = str(Path(docker).parent) + os.pathsep + self.env["PATH"]

    def snapshot(self):
        return subprocess.run([BASH, "-c", 'source "$1"; PROJECT_NAME=snapshot-fixture; release_non_web_snapshot',
                               "--", self.helper.as_posix()], env=self.env, capture_output=True, text=True,
                              timeout=30, check=False)

    def test_real_formatter_preserves_exited_and_optional_health(self):
        result = self.snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = []
        for cid, c in self.containers.items():
            if c["Config"]["Labels"]["com.docker.compose.service"] == "web":
                continue
            health = (c["State"].get("Health") or {}).get("Status") or ""
            expected.append(f'{cid}|{IMAGE_OLD}|2026-09-29T19:12:34.023453014Z|{c["State"]["Status"]}|{health}|{HASH_API}')
        self.assertCountEqual(result.stdout.splitlines(), expected)
        self.assertTrue(any("all=1" in path for _, path in self.requests))
        self.assertTrue(all(method == "GET" for method, _ in self.requests))

    def test_real_formatter_propagates_inspect_failure(self):
        self.failed_id = "1" * 64  # O migrate continua enumerado; não pode ser omitido em erro.
        result = self.snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("synthetic inspect failure", result.stderr)

    def test_real_formatter_still_rejects_missing_required_field(self):
        del self.containers["1" * 64]["State"]["StartedAt"]
        result = self.snapshot()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("StartedAt", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
