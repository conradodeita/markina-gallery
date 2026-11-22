"""Read-only dependency impact and web build provenance gates (Python 3.8+)."""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import posixpath
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MANIFESTS = {"frontend/package.json", "frontend/package-lock.json"}
PYTHON_MANIFESTS = {
    "backend/requirements.txt", "backend/requirements-push.txt",
    "backend/face-requirements.txt",
}
DEPENDENCY_MANIFESTS = FRONTEND_MANIFESTS | PYTHON_MANIFESTS
COMPOSE_FILES = (
    "docker/docker-compose.yml", "docker/docker-compose.preview-adjustment.yml",
    "docker/docker-compose.system-monitor.yml",
)
WEB_BUILD_BLOBS = {
    "frontend/Dockerfile": "33c362d3d51c01b4c4504446736ca2682e59ce68",
    "frontend/.dockerignore": "ba2800b368ee6b58da6cf05286c12d5012802997",
}


def is_dependency_manifest(path):
    name = posixpath.basename(path)
    return path in DEPENDENCY_MANIFESTS or (path.startswith("backend/") and ("requirements" in name or "constraints" in name)
                                           and name.endswith((".txt", ".in", ".lock")))


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError("git_evidence_unavailable")
    return result.stdout.decode("utf-8").strip()


def paths(root, base, target):
    git(root, "merge-base", "--is-ancestor", base, target)
    return set(filter(None, git(root, "diff", "--name-only", base, target).splitlines()))


def source(root, revision, path):
    return git(root, "show", "{}:{}".format(revision, path)).replace("\r\n", "\n")


def parse_compose(text):
    """Only the versioned service/build/image/profile subset; no env is read."""
    result, service, in_services, in_build = {}, None, False, False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            in_services = line == "services:"
            service = None
            continue
        if not in_services:
            continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line)
        if match:
            service = match.group(1)
            result[service] = {}
            in_build = False
            continue
        if service is None:
            raise ValueError("unrecognized_compose_services")
        match = re.match(r"    ([\w-]+):\s*(.*?)\s*$", line)
        if match:
            key, value = match.groups()
            in_build = key == "build"
            if key in {"extends", "include"}:
                raise ValueError("unrecognized_compose_inheritance")
            if key == "build":
                result[service]["build"] = {"context": value} if value else {}
            if key == "image":
                result[service]["image"] = value
            continue
        if in_build and line.startswith("      ") and not line.startswith("        "):
            if line.strip() == "args:":
                result[service]["build"]["args"] = {}
                continue
            match = re.fullmatch(r"      (context|dockerfile):\s*(\S+)\s*", line)
            if not match:
                raise ValueError("unsupported_compose_build_option")
            result[service]["build"][match.group(1)] = match.group(2)
    return result


def catalogue(root, revision):
    files = set(git(root, "ls-tree", "-r", "--name-only", revision, "docker/").splitlines())
    services = {}
    for file in COMPOSE_FILES:
        if file not in files:
            continue
        for name, config in parse_compose(source(root, revision, file)).items():
            services.setdefault(name, {}).update(config)
    for config in services.values():
        if "build" in config:
            build = config["build"]
            context = posixpath.normpath(posixpath.join("docker", build.get("context", "")))
            if context not in {"frontend", "backend"}:
                raise ValueError("unrecognized_build_context")
            config["context"] = context
            config["dockerfile"] = context + "/" + build.get("dockerfile", "Dockerfile")
    return services


def copied_inputs(dockerfile):
    inputs = []
    for line in dockerfile.replace("\\\n", " ").splitlines():
        match = re.match(r"\s*COPY\s+(.+)", line, re.I)
        if not match:
            continue
        body = match.group(1)
        if body.startswith("--from="):
            continue
        if body.startswith("--"):
            raise ValueError("unsupported_copy_option")
        tokens = json.loads(body) if body.startswith("[") else shlex.split(body)
        if len(tokens) < 2 or any("$" in token or token.startswith("/") or ".." in token.split("/") for token in tokens[:-1]):
            raise ValueError("unsupported_copy_source")
        inputs.extend(tokens[:-1])
    return inputs


def required_inputs(root, revision, context, dockerfile):
    body = source(root, revision, dockerfile)
    copied = copied_inputs(body)
    pip_commands = "\n".join(re.findall(r"\bpip3?\s+install\b([^&;\n]*)", body.replace("\\\n", " ")))
    required, pending = set(), re.findall(r"(?:-r|--requirement|-c|--constraint)(?:=|\s+)([^\s\\]+)", pip_commands)
    while pending:
        name = pending.pop()
        if not re.fullmatch(r"[\w./-]+", name):
            raise ValueError("unrecognized_requirement_input")
        file = posixpath.normpath(posixpath.join(context, name))
        if not file.startswith(context + "/"):
            raise ValueError("requirement_include_outside_context")
        relative = file[len(context) + 1:]
        if not any(item == "." or relative == item.rstrip("/") or relative.startswith(item.rstrip("/") + "/")
                   or fnmatch.fnmatch(relative, item) for item in copied):
            raise ValueError("requirement_not_copied_to_image")
        if file in required:
            continue
        required.add(file)
        content = source(root, revision, file)
        for include in re.findall(r"^\s*(?:-r|--requirement|-c|--constraint)(?:=|\s+)([^\s#]+)", content, re.M):
            if not re.fullmatch(r"[\w./-]+", include):
                raise ValueError("unrecognized_requirement_include")
            pending.append(posixpath.relpath(posixpath.join(posixpath.dirname(file), include), context))
    return required


def impact(root, base, target):
    changed = paths(root, base, target)
    before, after = catalogue(root, base), catalogue(root, target)
    images = {}
    protected = sorted(p for p in changed if p.startswith("docker/") or "/Dockerfile" in p or p.endswith(".dockerignore")
                       or p.startswith("backend/app/") or p.startswith("backend/migrations/")
                       or p.startswith("backend/facial-assets/"))
    for service, config in after.items():
        if "context" not in config:
            if config != before.get(service):
                images.setdefault(config.get("image", service), {"services": [], "changed_inputs": [], "specialized": True})["services"].append(service)
            continue
        context, dockerfile = config["context"], config["dockerfile"]
        copies = copied_inputs(source(root, target, dockerfile))
        required = required_inputs(root, target, context, dockerfile)
        affected = []
        for file in changed:
            relative = file[len(context) + 1:] if file.startswith(context + "/") else None
            if file in {dockerfile, context + "/.dockerignore"} or file in required or (relative is not None and any(
                    item == "." or relative == item.rstrip("/") or relative.startswith(item.rstrip("/") + "/")
                    or fnmatch.fnmatch(relative, item) for item in copies)):
                affected.append(file)
        if affected or config != before.get(service):
            entry = images.setdefault(dockerfile, {"services": [], "changed_inputs": sorted(affected),
                "context": context, "dockerfile": dockerfile, "requirements": sorted(required),
                "specialized": dockerfile not in {"frontend/Dockerfile", "backend/Dockerfile"}})
            entry["services"].append(service)
    return {"base_sha": git(root, "rev-parse", base), "target_sha": git(root, "rev-parse", target),
            "changed_manifests": sorted(p for p in changed if is_dependency_manifest(p)), "protected_changes": protected,
            "images": images, "automatic_deploy": False}


def api_provenance(root, base, target):
    changed = paths(root, base, target)
    if any(p.startswith("backend/") and p not in PYTHON_MANIFESTS for p in changed):
        raise ValueError("backend_runtime_diverges_from_api_source")
    return {"api_source_sha": git(root, "rev-parse", base), "pending_python_manifests": sorted(changed & PYTHON_MANIFESTS)}


def web_scope(root, base, target):
    changed = paths(root, base, target)
    if any(p.startswith("docker/") or p in WEB_BUILD_BLOBS or
           (p.startswith("backend/") and p not in PYTHON_MANIFESTS) for p in changed):
        raise ValueError("protected_change_outside_web_release")
    for path, blob in WEB_BUILD_BLOBS.items():
        if git(root, "rev-parse", target + ":" + path) != blob:
            raise ValueError("web_build_definition_not_approved")
    for line in git(root, "ls-tree", "-r", target, "frontend/").splitlines():
        if line.startswith(("120000", "160000")) or re.search(r"\tfrontend/(?:.*/)?\.env(?:\.|$)", line):
            raise ValueError("unsafe_web_context_entry")
    # ls-files includes ignored paths; only exclusions in the pinned .dockerignore are admitted.
    for file in git(root, "ls-files", "--others", "--", "frontend/").splitlines():
        relative = file[len("frontend/"):]
        if not (relative.startswith(("node_modules/", ".next/", ".git/")) or relative.endswith(".log")):
            raise ValueError("unversioned_web_context_entry")
    return {"context": "frontend", "source_tree_oid": git(root, "rev-parse", target + ":frontend"),
            "build_blobs": WEB_BUILD_BLOBS, "pending_python_manifests": sorted(changed & PYTHON_MANIFESTS)}


def web_build(config):
    service = config.get("services", {}).get("web", {})
    build = service.get("build")
    if not isinstance(build, dict) or set(build) - {"context", "dockerfile"}:
        raise ValueError("additional_or_unrecognized_web_build_inputs")
    if build.get("context") != "/opt/markina-gallery/frontend" or build.get("dockerfile", "Dockerfile") != "Dockerfile":
        raise ValueError("web_build_context_not_isolated")
    if service.get("volumes") or service.get("env_file") or service.get("environment"):
        raise ValueError("web_runtime_inputs_not_approved")
    return {"resolved_context": build["context"], "isolated": True}


def plan(root, base, target, inventory, group):
    report = impact(root, base, target)
    blockers, selected, excluded = [], {}, []
    if inventory.get("project") != "markina-gallery" or inventory.get("schema_version") != 1:
        raise ValueError("inventory_identity_invalid")
    collected = dt.datetime.fromisoformat(inventory["collected_at"])
    now = dt.datetime.now(dt.timezone.utc)
    if collected.tzinfo is None or not 0 <= (now - collected).total_seconds() <= 3600:
        raise ValueError("inventory_expired_or_future")
    if inventory.get("checkout_sha") != report["base_sha"]:
        raise ValueError("inventory_checkout_mismatch")
    arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(inventory.get("host_architecture"))
    if arch is None:
        raise ValueError("unvalidated_host_architecture")
    if group == "web":
        lock = json.loads(source(root, target, "frontend/package-lock.json"))["packages"]
        desired = {name: lock["node_modules/" + name]["version"] for name in ("next", "react", "react-dom")}
    else:
        pins = dict(re.findall(r"^([a-zA-Z0-9-]+)==([^\s;]+)$", source(root, target, "backend/requirements-push.txt"), re.M))
        desired = {name: pins[name] for name in ("aiohttp", "multidict", "urllib3", "yarl")}
    if report["protected_changes"]:
        blockers.append("protected_changes_require_homologation")
    for image, data in report["images"].items():
        if (group == "web" and image != "frontend/Dockerfile") or (group == "python" and data.get("context") != "backend"):
            continue
        for service in data["services"]:
            current = inventory.get("services", {}).get(service)
            if not current or current.get("status") != "running":
                excluded.append(service)
                continue
            image_id = current.get("image_id", "")
            metadata = current.get("image", {})
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) or metadata.get("id") != image_id:
                raise ValueError("inventory_image_identity_invalid")
            if metadata.get("architecture") != arch or current.get("health") != "healthy":
                raise ValueError("inventory_architecture_or_health_invalid")
            if any(not isinstance(current.get("packages", {}).get(name), str) for name in desired):
                raise ValueError("installed_package_versions_missing")
            selected[service] = {"previous_image_id": image_id, "repo_digests": metadata.get("repo_digests", []),
                                 "architecture": arch, "installed_packages": current.get("packages", {})}
            if group == "python":
                # The existing app executor only updates api/web. Do not silently omit worker consumers.
                blockers.append("{}:{}".format(service, "specialized_homologation_and_rollback_required" if data["specialized"] else "dependency_executor_and_rollback_required"))
    if group == "web":
        receipt = inventory.get("state", {}).get("web-current.identity", "").split()
        if len(receipt) != 4 or not re.fullmatch(r"[0-9a-f]{40}", receipt[0]) or receipt[1] != selected.get("web", {}).get("previous_image_id"):
            raise ValueError("web_inventory_provenance_missing")
        report["web_provenance"] = web_scope(root, receipt[0], target)
        api_source = inventory.get("services", {}).get("api", {}).get("source_sha", "")
        if not re.fullmatch(r"[0-9a-f]{40}", api_source):
            raise ValueError("api_inventory_provenance_missing")
        report["api_provenance"] = api_provenance(root, api_source, target)
    if not selected:
        blockers.append("no_active_affected_services")
    report.update(group=group, target_packages=desired, selected_services=selected, excluded_inactive_services=sorted(excluded),
                  blockers=sorted(set(blockers)), ready_for_operational_inventory=not blockers,
                  release_authorized=False, migrations="none")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["impact", "plan", "web-scope", "api-provenance", "web-build"])
    parser.add_argument("--base")
    parser.add_argument("--target")
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--group", choices=["web", "python"])
    args = parser.parse_args()
    try:
        if args.operation == "web-build":
            result = web_build(json.load(sys.stdin))
        else:
            if not args.base or not args.target:
                raise ValueError("base_and_target_required")
            if args.operation == "plan":
                if not args.inventory or not args.group:
                    raise ValueError("inventory_and_group_required")
                result = plan(ROOT, args.base, args.target, json.loads(args.inventory.read_text(encoding="utf-8-sig")), args.group)
            else:
                result = {"impact": impact, "web-scope": web_scope, "api-provenance": api_provenance}[args.operation](ROOT, args.base, args.target)
        print(json.dumps(result, sort_keys=True))
        return 1 if result.get("blockers") else 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({"ready": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
