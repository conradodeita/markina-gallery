"""Executor contracts: immutable artifact before effects and receipts after HTTPS."""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'POSIX Bash required')
class HandoffShellContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pyp-handoff-shell-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        source = (ROOT / 'deploy-prod-app-services.sh').read_text()
        source = source.replace('readonly STATE_DIR="/var/lib/markina-gallery/deploy-state"',
                                'readonly STATE_DIR="' + str(self.state) + '"')
        self.script = self.root / 'executor.sh'
        self.script.write_text(source)
        self.log = self.root / 'calls'
        self.target, self.baseline = 'a' * 40, 'b' * 40
        self.api, self.web = 'sha256:' + 'c' * 64, 'sha256:' + 'd' * 64

    def run_shell(self, body, failure=''):
        harness = r'''
source "$EXECUTOR"
source "$STATE_HELPER"
eval "$(declare -f runtime_snapshot | sed '1s/runtime_snapshot/real_runtime_snapshot/')"
eval "$(declare -f handoff_https | sed '1s/handoff_https/real_handoff_https/')"
MODE=handoff-release
TARGET_SHA="$TEST_TARGET"
CHECKOUT_SHA="$TEST_BASELINE"
ACTIVE_SHA="$TEST_BASELINE"
COMPOSE_APP_VERSION="$TEST_BASELINE"
APPROVAL_FINGERPRINT="$(printf 'f%.0s' {1..64})"
ARTIFACT_SHA256="$(printf 'e%.0s' {1..64})"
API_BASE_IMAGE_ID="$TEST_API"
CANDIDATE_API_IMAGE_ID="$TEST_API"
CANDIDATE_WEB_IMAGE_ID="$TEST_WEB"
APP_WEB_IDENTITY="$TEST_BASELINE $TEST_WEB $(printf '1%.0s' {1..64}) $TEST_BASELINE"
log() { printf '%s\n' "$*" >> "$CALL_LOG"; }
verify_repository() { log repository; }
runtime_snapshot() { log runtime; }
verify_candidate_artifact() { log artifact; [[ "$FAILURE" != artifact ]]; }
cleanup_candidate_artifact() { log cleanup; }
load_candidate_artifact() { log load; }
compose() { printf 'synthetic-active\n'; }
release_image_id() { printf '%s\n' "$TEST_API"; }
docker() { if [[ "$1" == inspect ]]; then printf '%s\n' "$TEST_API"; else log "docker $*"; fi; }
git() {
  if [[ "$1" == switch ]]; then log "checkout $3"; else printf '%s\n' "$TEST_TARGET"; fi
}
handoff_bridge() {
  log "$1"
  if [[ "$1" == handoff-prepare ]]; then
    [[ "$FAILURE" != approval ]] || return 1
  elif [[ "$1" == handoff-apply ]]; then
    [[ "$FAILURE" != apply ]] || return 1
    printf 'handoff_status=healthy\ncheckout_sha=%s\napi_version=%s\nweb_version=%s\nweb_image_id=%s\nweb_semantic_hash=%s\n' \
      "$TEST_TARGET" "$TEST_TARGET" "$TEST_TARGET" "$TEST_WEB" "$(printf '2%.0s' {1..64})"
  fi
}
handoff_https() { log https; [[ "$FAILURE" != https ]]; }
curl() { log curl; }
'''
        env = dict(os.environ, EXECUTOR=str(self.script), STATE_HELPER=str(ROOT / 'deploy-prod-state.sh'),
                   TEST_TARGET=self.target, TEST_BASELINE=self.baseline, TEST_API=self.api,
                   TEST_WEB=self.web, CALL_LOG=str(self.log), FAILURE=failure)
        # Normalize the existing shared helper's line endings without editing it.
        helper = self.root / 'state-helper.sh'
        helper.write_text((ROOT / 'deploy-prod-state.sh').read_text())
        env['STATE_HELPER'] = str(helper)
        return subprocess.run(['bash', '-c', harness + '\n' + body], env=env,
                              capture_output=True, text=True, timeout=20, check=False)

    def test_success_records_health_only_after_https_and_preserves_historical_receipts(self):
        historical = self.state / 'web-previous.identity'
        historical.write_text('historical evidence')
        result = self.run_shell('handoff_release')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index('artifact'), calls.index('handoff-prepare'))
        self.assertLess(calls.index('handoff-prepare'), calls.index('handoff-apply'))
        self.assertLess(calls.index('handoff-apply'), calls.index('https'))
        self.assertEqual((self.state / 'app-last-healthy.sha').read_text().strip(), self.target)
        self.assertFalse((self.state / 'app-in-flight.sha').exists())
        self.assertEqual(historical.read_text(), 'historical evidence')

    def test_artifact_or_approval_failure_cannot_mark_or_replace_services(self):
        for failure in ('artifact', 'approval'):
            with self.subTest(failure=failure):
                self.log.unlink(missing_ok=True)
                result = self.run_shell('handoff_release', failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('handoff-apply', self.log.read_text())
                self.assertFalse((self.state / 'app-in-flight.sha').exists())

    def test_apply_or_https_failure_preserves_pending_marker_and_previous_identity(self):
        for failure in ('apply', 'https'):
            with self.subTest(failure=failure):
                result = self.run_shell('handoff_release', failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.state / 'app-in-flight.sha').read_text().strip(), self.target)
                self.assertEqual((self.state / 'app-web-rollback.identity').read_text().strip().split()[0], self.baseline)
                self.assertFalse((self.state / 'app-last-healthy.sha').exists())

    def test_marker_for_other_attempt_is_never_cleared(self):
        marker = self.state / 'app-in-flight.sha'
        marker.write_text(self.baseline)
        result = self.run_shell('handoff_clear_markers "$TEST_TARGET"')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), self.baseline)

    def test_legacy_snapshot_does_not_require_normal_repository_verification(self):
        body = r'''
MODE=handoff-legacy-recover
compose() { if [[ "$1" == ps ]]; then printf 'synthetic-%s\n' "$3"; fi; }
require_facial_processing_enabled_in_config() { :; }
resolved_hashes() { printf 'api %s\nweb %s\n' "$(printf '1%.0s' {1..64})" "$(printf '1%.0s' {1..64})"; }
bridge_call() {
  case "$1" in
    service-hash) printf '1%.0s' {1..64} ;;
    service-project) printf 'markina-gallery\n' ;;
    sources-fingerprint) printf '2%.0s' {1..64} ;;
    *) return 98 ;;
  esac
}
docker() {
  case "$3" in
    *com.docker.compose.project*) printf 'markina-gallery\n' ;;
    *com.docker.compose.service*) printf '%s\n' "${4#synthetic-}" ;;
    *State.Health*) printf 'healthy\n' ;;
    '{{.Image}}') printf '%s\n' "$TEST_API" ;;
    *NetworkSettings.Ports*) printf '%s\n' '{"80/tcp":[{"HostIp":"127.0.0.1","HostPort":"8080"}]}' ;;
    *) return 99 ;;
  esac
}
real_runtime_snapshot
'''
        result = self.run_shell(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('compose_sources=' + '2' * 64, result.stdout)

    def test_proxy_uses_approved_handoff_interface_and_tests_three_https_routes(self):
        for mode, expected in (('handoff-release', 'handoff-proxy'), ('handoff-recover', 'handoff-proxy'),
                               ('handoff-legacy-recover', 'handoff-legacy-recovery-proxy')):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                result = self.run_shell('MODE=' + mode + '; real_handoff_https')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.log.read_text().splitlines(), [expected, 'curl', 'curl', 'curl'])

    def test_candidate_ids_cannot_be_passed_to_recovery_or_be_equal(self):
        for arguments in (
            '--mode handoff-recovery-inventory --sha "$TEST_TARGET" --candidate-api-id "$TEST_API"',
            '--mode handoff-inventory --sha "$TEST_TARGET" --artifact-sha256 "$ARTIFACT_SHA256" --api-base-image-id "$TEST_API" --candidate-api-id "$TEST_API" --candidate-web-id "$TEST_API"',
        ):
            with self.subTest(arguments=arguments):
                # Reset globals normally initialized by parse_arguments in a fresh process.
                result = self.run_shell('CANDIDATE_DIGEST="$ARTIFACT_SHA256"; MODE=""; API_BASE_IMAGE_ID=""; CANDIDATE_API_IMAGE_ID=""; CANDIDATE_WEB_IMAGE_ID=""; ARTIFACT_SHA256=""; parse_arguments ' + arguments.replace('$ARTIFACT_SHA256', '$CANDIDATE_DIGEST'))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('IDs do artifact fora' if 'recovery' in arguments else 'identidade do artifact obrigatória', result.stderr)


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'POSIX Bash required')
class HandoffReadonlyWrapperContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pyp-handoff-wrapper-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        body = b'#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n'
        self.body = self.root / 'approved-body.sh'
        self.body.write_bytes(body)
        blob = hashlib.sha1(('blob ' + str(len(body)) + '\0').encode() + body).hexdigest()
        source = (ROOT / 'production-preflight-ssh-wrapper.sh').read_text()
        source = source.replace('readonly PROJECT_ROOT="/opt/markina-gallery"',
                                'readonly PROJECT_ROOT="' + str(self.root) + '"')
        source = re.sub(r'APP_SCRIPT_BLOB_SHA="[0-9a-f]{40}"', 'APP_SCRIPT_BLOB_SHA="' + blob + '"', source)
        self.wrapper = self.root / 'wrapper.sh'
        self.wrapper.write_text(source)
        self.log = self.root / 'fetch.log'
        curl = self.root / 'curl'
        curl.write_text('#!/usr/bin/env bash\nprintf fetched >> "$FETCH_LOG"\ncat "$APP_BODY"\n')
        curl.chmod(0o755)
        git = self.root / 'git'
        git.write_text("#!/usr/bin/env bash\n[[ \"$*\" == 'hash-object --stdin' ]] || exit 98\n"
                       "python3 -c 'import hashlib,sys; b=sys.stdin.buffer.read(); print(hashlib.sha1((\"blob \"+str(len(b))+chr(0)).encode()+b).hexdigest())'\n")
        git.chmod(0o755)

    def invoke(self, command):
        return subprocess.run(['bash', str(self.wrapper)],
                              env=dict(os.environ, PATH=str(self.root) + os.pathsep + os.environ['PATH'],
                                       SSH_ORIGINAL_COMMAND=command, APP_BODY=str(self.body), FETCH_LOG=str(self.log)),
                              capture_output=True, text=True, check=False, timeout=15)

    def test_readonly_commands_forward_only_the_fixed_inventory_arguments(self):
        sha, bundle = 'a' * 40, 'b' * 64
        base, api, web = ['sha256:' + char * 64 for char in ('c', 'd', 'e')]
        command = f'MARKINA_APP_HANDOFF_SHA={sha}_BUNDLE={bundle}_BASE={base}_API={api}_WEB={web}'
        result = self.invoke(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['--mode', 'handoff-inventory', '--sha', sha,
                         '--artifact-sha256', bundle, '--api-base-image-id', base,
                         '--candidate-api-id', api, '--candidate-web-id', web])
        for suffix, mode in (('WITNESSES', 'handoff-witness-inventory'),
                             ('LEGACY_RECOVERY', 'handoff-legacy-recovery-inventory'),
                             ('RECOVERY', 'handoff-recovery-inventory')):
            result = self.invoke(f'MARKINA_APP_HANDOFF_{suffix}_SHA={sha}')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['--mode', mode, '--sha', sha])

    def test_mutation_injection_and_extra_arguments_are_rejected_before_fetch(self):
        sha = 'a' * 40
        for command in (f'MARKINA_APP_HANDOFF_APPLY_SHA={sha}',
                        f'MARKINA_APP_HANDOFF_RECOVERY_SHA={sha};id',
                        f'MARKINA_APP_HANDOFF_WITNESSES_SHA={sha} --mode release',
                        f'MARKINA_APP_HANDOFF_LEGACY_RECOVERY_SHA={sha}\nid'):
            with self.subTest(command=command):
                result = self.invoke(command)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists())

    def test_modified_body_cannot_run_even_for_an_allowed_read_command(self):
        self.body.write_text('echo unreviewed-body-ran\n')
        result = self.invoke('MARKINA_APP_HANDOFF_WITNESSES_SHA=' + 'a' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('unreviewed-body-ran', result.stdout)


if __name__ == '__main__':
    unittest.main()
