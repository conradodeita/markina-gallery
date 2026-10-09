import { describe, expect, it } from 'vitest';
import { buildRemoteSummary } from '../../../../k6/remote-report.js';

const configuration = {
  sourceRevision: 'a'.repeat(40),
  sourceWorktreeDirty: false,
  profile: 'expected',
  maxVUs: 4,
  maxRps: 8,
  targetRps: 8,
  plannedRequestsMax: 800,
  durationSeconds: 90,
  rampUpSeconds: 5,
  rampDownSeconds: 5,
};

describe('resumo remoto k6', () => {
  it('serializa métricas, limites aprovados e lacunas do servidor', () => {
    const summary = buildRemoteSummary({
      state: { testRunDurationMs: 100_000 },
      metrics: {
        vus: { values: { max: 4 } },
        http_reqs: { values: { count: 800, rate: 8 } },
        http_req_failed: { values: { passes: 4, fails: 796, rate: 0.005 } },
        http_req_duration: { values: { med: 35, 'p(95)': 90, 'p(99)': 140 } },
        checks: { values: { passes: 1596, fails: 4 } },
      },
    }, configuration);

    expect(summary).toMatchObject({
      source_revision: 'a'.repeat(40),
      source_worktree_dirty: false,
      k6_version: 'v0.54.0',
      max_vus: 4,
      max_operations_per_second: 8,
      target_operations_per_second: 8,
      planned_requests_max: 800,
      requests: 800,
      latency_ms: { p50: 35, p95: 90, p99: 140 },
      errors: { failed_requests: 4, failed_checks: 4 },
      recommendation: expect.stringContaining('do not increase'),
    });
    expect(Object.values(summary.server_metrics)).toEqual([
      'unavailable_not_collected',
      'unavailable_not_collected',
      'unavailable_not_collected',
      'unavailable_not_collected',
    ]);
  });

  it('marca métricas ausentes como null e não recomenda progressão sem observabilidade', () => {
    const summary = buildRemoteSummary({ metrics: {} }, configuration);

    expect(summary.observed_vus_peak).toBeNull();
    expect(summary.requests).toBeNull();
    expect(summary.latency_ms).toEqual({ p50: null, p95: null, p99: null });
    expect(summary.recommendation).toContain('review server metrics');
  });

  it('conta falhas pelo lado verdadeiro da Rate e não inventa latência sem amostra', () => {
    const summary = buildRemoteSummary({
      metrics: {
        http_reqs: { values: { count: 1, rate: 0.08 } },
        http_req_failed: { values: { passes: 1, fails: 0, rate: 1 } },
        http_req_duration: { values: { count: 0, med: 0, 'p(95)': 0, 'p(99)': 0 } },
        checks: { values: { passes: 1, fails: 1 } },
      },
    }, configuration);

    expect(summary).toMatchObject({
      successful_requests: 0,
      failed_requests: 1,
      failed_request_rate: 1,
      latency_ms: { p50: null, p95: null, p99: null },
      recommendation: expect.stringContaining('Diagnose failed requests'),
    });
  });
});
