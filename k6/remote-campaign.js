import http from 'k6/http';
import { check, fail } from 'k6';
import { buildRemoteSummary } from './remote-report.js';

const ALLOWED_ORIGIN = 'https://markina-homolog.duckdns.org';
const HIGH_IMPACT = new Set(['stress', 'soak']);

function required(name) {
  const value = __ENV[name];
  if (!value || !value.trim()) fail(`missing_required_gate:${name}`);
  return value.trim();
}

function positiveInteger(name) {
  const value = Number(required(name));
  if (!Number.isSafeInteger(value) || value < 1) fail(`invalid_positive_integer:${name}`);
  return value;
}

function positiveRate(name) {
  const value = Number(required(name));
  if (!Number.isFinite(value) || value <= 0) fail(`invalid_positive_rate:${name}`);
  return value;
}

function parseThresholds() {
  let thresholds;
  try {
    thresholds = JSON.parse(required('PYP_THRESHOLDS_JSON'));
  } catch (_) {
    fail('invalid_thresholds_json');
  }
  if (!thresholds || Array.isArray(thresholds) || Object.keys(thresholds).length === 0) {
    fail('thresholds_missing');
  }
  for (const [name, expressions] of Object.entries(thresholds)) {
    if (!name.trim() || !Array.isArray(expressions) || expressions.length === 0 ||
        expressions.some((expression) => typeof expression !== 'string' || !expression.trim())) {
      fail('thresholds_invalid');
    }
  }
  return thresholds;
}

const origin = required('PYP_REMOTE_TARGET_URL');
if (origin !== ALLOWED_ORIGIN) fail('target_not_allowlisted');
if (required('PYP_REMOTE_ENVIRONMENT') !== 'homolog') fail('environment_not_allowed');
if (required('PYP_OWNER_APPROVED') !== '1' || !required('PYP_AUTHORIZATION_REFERENCE')) {
  fail('profile_not_approved');
}
if (required('PYP_AB_TEST_CLOSED') !== '1') fail('ab_exercise_still_active');

const profile = required('PYP_PROFILE');
if (!['expected', 'peak', 'stress', 'soak'].includes(profile)) fail('profile_unknown');
if (HIGH_IMPACT.has(profile) && required('PYP_HIGH_IMPACT_AUTHORIZED') !== '1') {
  fail('high_impact_profile_not_approved');
}
const maxVUs = positiveInteger('PYP_MAX_VUS');
const maxRps = positiveInteger('PYP_MAX_RPS');
const targetRps = positiveRate('PYP_TARGET_RPS');
if (targetRps > maxRps) fail('target_rate_exceeds_approved_maximum');
const rateTimeUnitSeconds = Math.max(1, Math.round(1 / targetRps));
const arrivalRatePerTimeUnit = Math.round(targetRps * rateTimeUnitSeconds);
if (Math.abs(arrivalRatePerTimeUnit / rateTimeUnitSeconds - targetRps) > 1e-9) {
  fail('target_rate_not_representable');
}
const durationSeconds = positiveInteger('PYP_DURATION_SECONDS');
const sourceRevision = required('PYP_SOURCE_REVISION');
const sourceWorktreeDirtyFlag = required('PYP_SOURCE_WORKTREE_DIRTY');
if (!['0', '1'].includes(sourceWorktreeDirtyFlag)) fail('invalid_source_worktree_state');
const sourceWorktreeDirty = sourceWorktreeDirtyFlag === '1';
const rampUpSeconds = Number(required('PYP_RAMP_UP_SECONDS'));
const rampDownSeconds = Number(required('PYP_RAMP_DOWN_SECONDS'));
if (!Number.isSafeInteger(rampUpSeconds) || rampUpSeconds < 0 ||
    !Number.isSafeInteger(rampDownSeconds) || rampDownSeconds < 0) {
  fail('ramp_invalid');
}
if (durationSeconds + rampUpSeconds + rampDownSeconds > 1200) {
  fail('campaign_duration_exceeds_runner_limit');
}
const thresholds = {};
for (const [name, expressions] of Object.entries(parseThresholds())) {
    thresholds[name] = expressions.map((threshold) => ({
      threshold,
      abortOnFail: true,
      delayAbortEval: '1s',
  }));
}
const plannedRequestsMax = Math.ceil(
  targetRps * rampUpSeconds +
  targetRps * durationSeconds +
  (targetRps / 2) * rampDownSeconds,
);

export const options = {
  scenarios: {
    approved_read_only_health: {
      executor: 'ramping-arrival-rate',
      startRate: arrivalRatePerTimeUnit,
      timeUnit: `${rateTimeUnitSeconds}s`,
      stages: [
        ...(rampUpSeconds ? [{ target: arrivalRatePerTimeUnit, duration: `${rampUpSeconds}s` }] : []),
        { target: arrivalRatePerTimeUnit, duration: `${durationSeconds}s` },
        ...(rampDownSeconds ? [{ target: 0, duration: `${rampDownSeconds}s` }] : []),
      ],
      preAllocatedVUs: Math.min(maxVUs, Math.max(1, maxRps)),
      maxVUs,
      exec: 'healthCheck',
      gracefulStop: '5s',
    },
  },
  thresholds,
  discardResponseBodies: true,
  noConnectionReuse: false,
  userAgent: 'pyp-remote-test-campaign/k6',
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
};

const HEALTH_PATHS = ['/healthz', '/api/health'];

export function healthCheck() {
  const path = HEALTH_PATHS[(__ITER + __VU) % HEALTH_PATHS.length];
  const response = http.get(`${ALLOWED_ORIGIN}${path}`, {
    redirects: 0,
    tags: { name: 'read_only_health', path },
    timeout: '10s',
  });
  const passed = check(response, {
    'health endpoint returns 200': (res) => res.status === 200,
    'health endpoint does not redirect': (res) => res.status !== 301 && res.status !== 302 && res.status !== 307 && res.status !== 308,
  });
  if (!passed) fail('healthcheck_failed');
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(buildRemoteSummary(data, {
      sourceRevision,
      sourceWorktreeDirty,
      profile,
      maxVUs,
      maxRps,
      targetRps,
      plannedRequestsMax,
      durationSeconds,
      rampUpSeconds,
      rampDownSeconds,
    }), null, 2),
  };
}
