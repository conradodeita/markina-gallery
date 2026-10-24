"""Exercise the real retirement release with local filesystem and external fixtures."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGET = "a" * 40
PREVIOUS = "b" * 40
INVENTORY = {"checkout_sha": PREVIOUS, "active_sha": PREVIOUS, "fixture": "approved"}
FINGERPRINT = hashlib.sha256(json.dumps(INVENTORY, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
ARCHIVE = b"fixture-custom-archive\n"

HARNESS = r'''#!/usr/bin/env bash
set -Eeuo pipefail
source "$FLOW_SOURCE"
TARGET_SHA="$FLOW_TARGET"
APPROVAL_FINGERPRINT="$FLOW_FINGERPRINT"
event() { printf '%s\n' "$*" >> "$FLOW_ROOT/events"; }
inventory() {
  CHECKOUT_SHA="$FLOW_PREVIOUS"
  ACTIVE_SHA="$FLOW_PREVIOUS"
  printf 'retirement_inventory_json=%s\n' "$FLOW_INVENTORY"
}
acquire_retirement_lock() { event lock; }
verify_restore_receipt() { event receipt; }
curl() { event https; }
remove_binding_after_health() {
  [[ "$1" == "$FLOW_INVENTORY" ]] || return 90
  event remove_binding
}
git() {
  case "$1" in
    fetch) event fetch ;;
    rev-parse)
      if [[ "$2" == origin/main ]]; then printf '%s\n' "$FLOW_TARGET";
      elif [[ "$2" == HEAD ]]; then cat "$FLOW_ROOT/checkout";
      else return 91; fi ;;
    switch)
      [[ "$2" == --detach && -n "$3" ]] || return 92
      event "checkout:$3"
      printf '%s\n' "$3" > "$FLOW_ROOT/checkout" ;;
    ls-remote) printf '%s\trefs/heads/main\n' "$FLOW_TARGET" ;;
    show)
      case "$2" in
        *:scripts/retirement_financial_evidence.py)
          printf '%s\n' 'print("{\"confirmed_infinitepay_count\":2,\"tables\":{\"fixture\":\"stable\"}}")' ;;
        *:scripts/retirement_pix_evidence.py)
          printf '%s\n' 'print("{\"tenant_count\":1,\"all_tenants_pix_available\":true,\"card_available_count\":0}")' ;;
        *) return 93 ;;
      esac ;;
    *) event "unexpected_git:$*"; return 94 ;;
  esac
}
docker() {
  local action service format identifier archive_input
  case "$1" in
    compose)
      shift
      while [[ $# -gt 0 ]]; do
        case "$1" in ps|config|build|stop|run|up|exec) action="$1"; shift; break ;; *) shift ;; esac
      done
      case "${action:-}" in
        ps)
          service="${!#}"
          if [[ -f "$FLOW_ROOT/published" ]]; then printf 'new-%s\n' "$service";
          else printf 'old-%s\n' "$service"; fi ;;
        config) event config ;;
        build)
          event build
          [[ "$FLOW_CASE" != build_failure ]] || return 55 ;;
        stop) service="${!#}"; event "stop:$service" ;;
        run)
          if [[ "$*" == *'alembic upgrade 20261022_0087'* ]]; then
            [[ "$(cat "$STATE_DIR/infinitepay-retirement-in-flight.sha")" == "$FLOW_TARGET" ]] || return 95
            event migration
            touch "$FLOW_ROOT/migrated"
          elif [[ "$*" == *'api python -' ]]; then
            event collector
            "$FLOW_PYTHON" -
          else event "unexpected_run:$*"; return 96; fi ;;
        up) event publish; touch "$FLOW_ROOT/published" ;;
        exec)
          case "$*" in
            *'SELECT pg_database_size'*) printf '1000000\n' ;;
            *'pg_dump -Fc'*) event dump; printf 'fixture-custom-archive\n' ;;
            *'pg_restore --list'*)
              event archive_validation
              archive_input="$(cat)"
              [[ "$archive_input" == fixture-custom-archive && "$FLOW_CASE" != backup_failure ]] || return 66 ;;
            *'alembic current'*)
              [[ -f "$FLOW_ROOT/migrated" ]] || return 97
              printf '20261022_0087 (head)\n' ;;
            *) event "unexpected_exec:$*"; return 98 ;;
          esac ;;
        *) event "unexpected_compose:$*"; return 99 ;;
      esac ;;
    inspect)
      format="$3"; identifier="$4"
      case "$format" in
        '{{.Image}}')
          case "$identifier" in
            old-api) printf 'sha256:%064d\n' 1 ;;
            old-web) printf 'sha256:%064d\n' 2 ;;
            old-worker) printf 'sha256:%064d\n' 3 ;;
            new-api) printf 'sha256:%064d\n' 4 ;;
            new-web) printf 'sha256:%064d\n' 5 ;;
            new-worker) printf 'sha256:%064d\n' 6 ;;
            *) return 100 ;;
          esac ;;
        '{{.State.Status}}:{{.State.ExitCode}}')
          if [[ "$FLOW_CASE" == worker_failure ]]; then printf 'exited:137\n'; else printf 'exited:0\n'; fi ;;
        '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}') printf 'healthy\n' ;;
        *) event "unexpected_inspect:$format"; return 101 ;;
      esac ;;
    image)
      if [[ "$2" == tag ]]; then event "tag:$3:$4";
      elif [[ "$2" == inspect ]]; then
        case "$5" in
          markina-gallery-api) printf 'sha256:%064d\n' 4 ;;
          markina-gallery-web) printf 'sha256:%064d\n' 5 ;;
          markina-gallery-worker) printf 'sha256:%064d\n' 6 ;;
          *) return 102 ;;
        esac
      else return 103; fi ;;
    start) shift; event "restart:$*" ;;
    *) event "unexpected_docker:$*"; return 104 ;;
  esac
}
release
'''


class RetirementReleaseFlowTests(unittest.TestCase):
    def run_flow(self, scenario: str):
        fixture = tempfile.TemporaryDirectory(prefix="retirement-release-")
        self.addCleanup(fixture.cleanup)
        directory = Path(fixture.name)
        state = directory / "state"
        backups = directory / "backups"
        state.mkdir(mode=0o700)
        backups.mkdir(mode=0o700)
        source = (ROOT / "scripts/deploy-prod-infinitepay-retirement.sh").read_text(encoding="utf-8")
        # Relocate only host filesystem boundaries; execute the actual functions.
        for original, replacement in (
            ('readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"',
             f'readonly STATE_DIR="{state.as_posix()}"'),
            ('readonly BACKUP_DIR="/var/lib/markina-gallery/backups"',
             f'readonly BACKUP_DIR="{backups.as_posix()}"'),
        ):
            self.assertEqual(source.count(original), 1, "host paths must be relocated before fixtures run")
            source = source.replace(original, replacement)
        script = directory / "executor.sh"
        script.write_text(source, encoding="utf-8", newline="\n")
        harness = directory / "harness.sh"
        harness.write_text(HARNESS, encoding="utf-8", newline="\n")
        (directory / "checkout").write_text(PREVIOUS + "\n", encoding="ascii")
        bash = shutil.which("bash")
        if sys.platform == "win32":
            git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
            if git_bash.exists():
                bash = str(git_bash)
        self.assertIsNotNone(bash, "bash is required for release flow fixtures")
        result = subprocess.run([bash, str(harness)], capture_output=True, text=True, timeout=30,
                                env=dict(os.environ, FLOW_SOURCE=script.as_posix(),
                                         FLOW_ROOT=directory.as_posix(), FLOW_PYTHON=Path(sys.executable).as_posix(),
                                         FLOW_TARGET=TARGET, FLOW_PREVIOUS=PREVIOUS,
                                         FLOW_FINGERPRINT=FINGERPRINT, FLOW_CASE=scenario,
                                         FLOW_INVENTORY=json.dumps(INVENTORY, sort_keys=True, separators=(",", ":"))))
        event_file = directory / "events"
        events = event_file.read_text().splitlines() if event_file.exists() else []
        return result, directory, events

    def test_release_preserves_images_validates_archive_and_compares_collectors(self):
        result, directory, events = self.run_flow("success")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected_tags = [f"tag:sha256:{number:064d}:markina-gallery-retirement-rollback-{service}-{number:064d}"
                         for number, service in enumerate(("api", "web", "worker"), 1)]
        self.assertEqual([event for event in events if event.startswith("tag:")], expected_tags)
        self.assertEqual(events.count("collector"), 4)
        for earlier, later in (("receipt", "build"), ("build", "stop:api"),
                               ("stop:worker", "dump"), ("dump", "archive_validation"),
                               ("archive_validation", "migration"), ("migration", "publish"),
                               ("publish", "remove_binding")):
            self.assertLess(events.index(earlier), events.index(later), events)
        archives = list((directory / "backups").glob("*.dump"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), ARCHIVE)
        manifest = archives[0].with_suffix(".manifest").read_text()
        self.assertIn(f"sha256={hashlib.sha256(ARCHIVE).hexdigest()}", manifest)
        self.assertFalse((directory / "state/infinitepay-retirement-in-flight.sha").exists())
        self.assertIn(f"release=saudavel sha={TARGET} schema=20261022_0087", result.stdout)

    def test_build_failure_restores_observed_checkout_before_stopping_services(self):
        result, directory, events = self.run_flow("build_failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("build", events, result.stderr)
        self.assertEqual((directory / "checkout").read_text().strip(), PREVIOUS, result.stderr)
        self.assertNotIn("stop:api", events)
        self.assertNotIn("migration", events)
        self.assertNotIn("remove_binding", events)

    def test_worker_failure_restarts_exact_containers_without_backup_or_migration(self):
        result, directory, events = self.run_flow("worker_failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stop:worker", events, result.stderr)
        self.assertEqual((directory / "checkout").read_text().strip(), PREVIOUS, result.stderr)
        self.assertIn("restart:old-api old-worker", events)
        self.assertNotIn("dump", events)
        self.assertNotIn("migration", events)
        self.assertNotIn("remove_binding", events)

    def test_invalid_archive_restores_runtime_and_does_not_migrate(self):
        result, directory, events = self.run_flow("backup_failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("archive_validation", events, result.stderr)
        self.assertEqual((directory / "checkout").read_text().strip(), PREVIOUS, result.stderr)
        self.assertIn("restart:old-api old-worker", events)
        self.assertNotIn("migration", events)
        self.assertNotIn("remove_binding", events)
        self.assertEqual(list((directory / "backups").iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
