function metric(summary, name, field) {
  const value = summary.metrics?.[name]?.values?.[field];
  return Number.isFinite(value) ? value : null;
}

export function buildRemoteSummary(data, configuration) {
  // `http_req_failed` is a Rate whose true samples mean failures, so k6 stores
  // those in `passes`; `fails` counts successful requests.
  const failedRequests = metric(data, 'http_req_failed', 'passes');
  const successfulRequests = metric(data, 'http_req_failed', 'fails');
  const checksFailed = metric(data, 'checks', 'fails');
  const droppedIterations = metric(data, 'dropped_iterations', 'count');
  const medianLatency = metric(data, 'http_req_duration', 'med');
  const hasLatencySample = Number.isFinite(medianLatency) && medianLatency > 0;
  const hasFailures = (failedRequests || 0) + (checksFailed || 0) + (droppedIterations || 0) > 0;

  return {
    schema: 'pyp-remote-test-report/v1',
    source_revision: configuration.sourceRevision,
    source_worktree_dirty: configuration.sourceWorktreeDirty,
    k6_version: 'v0.54.0',
    environment: 'homolog',
    target: 'https://markina-homolog.duckdns.org',
    profile: configuration.profile,
    max_vus: configuration.maxVUs,
    observed_vus_peak: metric(data, 'vus', 'max'),
    max_operations_per_second: configuration.maxRps,
    target_operations_per_second: configuration.targetRps,
    planned_requests_max: configuration.plannedRequestsMax,
    duration_seconds: configuration.durationSeconds,
    observed_duration_ms: Number.isFinite(data.state?.testRunDurationMs)
      ? data.state.testRunDurationMs
      : null,
    ramp_up_seconds: configuration.rampUpSeconds,
    ramp_down_seconds: configuration.rampDownSeconds,
    requests: metric(data, 'http_reqs', 'count'),
    operations_per_second: metric(data, 'http_reqs', 'rate'),
    successful_requests: successfulRequests,
    failed_requests: failedRequests,
    latency_ms: {
      p50: hasLatencySample ? medianLatency : null,
      p95: hasLatencySample ? metric(data, 'http_req_duration', 'p(95)') : null,
      p99: hasLatencySample ? metric(data, 'http_req_duration', 'p(99)') : null,
    },
    failed_request_rate: metric(data, 'http_req_failed', 'rate'),
    dropped_iterations: droppedIterations,
    checks_passed: metric(data, 'checks', 'passes'),
    checks_failed: checksFailed,
    errors: {
      failed_requests: failedRequests,
      failed_checks: checksFailed,
      dropped_iterations: droppedIterations,
    },
    server_metrics: {
      api_pool: 'unavailable_not_collected',
      postgres_connections: 'unavailable_not_collected',
      queues: 'unavailable_not_collected',
      host_cpu_memory_disk: 'unavailable_not_collected',
    },
    functional_checks: ['read_only_health_endpoints'],
    limitations: ['This profile measures health endpoints only; it does not establish multi-tenant capacity.'],
    recommendation: hasFailures
      ? 'Diagnose failed requests, checks, or dropped iterations; do not increase the approved profile limits.'
      : 'Health profile completed only; review server metrics and approve the next profile before advancing.',
  };
}
