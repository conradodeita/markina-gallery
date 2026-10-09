import { open, realpath } from 'node:fs/promises';
import { dirname, relative, resolve, sep } from 'node:path';
import { describe, expect, it } from 'vitest';
import { validateRemoteSmokeConfiguration } from './remote-smoke-policy';

const enabled = process.env.PYP_REMOTE_CAMPAIGN === '1';

async function writeSanitizedRecord(record: {
  outcome: 'passed' | 'failed';
  duration_ms: number;
  request_duration_ms: number | null;
  request_count: 0 | 1;
  http_status: number | null;
}): Promise<void> {
  const runnerTemp = process.env.RUNNER_TEMP;
  const reportDir = process.env.PYP_SMOKE_REPORT_DIR;
  if (!runnerTemp || !reportDir) throw new Error('smoke_report_directory_missing');
  const base = await realpath(runnerTemp);
  const directory = await realpath(reportDir);
  const pathFromBase = relative(base, directory);
  if (!pathFromBase || pathFromBase === '..' || pathFromBase.startsWith(`..${sep}`) || resolve(base, pathFromBase) !== directory) {
    throw new Error('smoke_report_directory_not_confined');
  }
  const destination = resolve(directory, 'vitest_api_health.json');
  if (dirname(destination) !== directory) throw new Error('smoke_report_path_invalid');
  const handle = await open(destination, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify({
      check: 'vitest_api_health',
      ...record,
      target: 'https://markina-homolog.duckdns.org',
    })}\n`, 'utf8');
  } finally {
    await handle.close();
  }
}

describe.skipIf(!enabled)('GET /api/health remoto', () => {
  it('consulta apenas o endpoint de saúde homologado após validar os gates', async () => {
    const started = performance.now();
    let outcome: 'passed' | 'failed' = 'failed';
    let requestCount: 0 | 1 = 0;
    let status: number | null = null;
    let requestDuration: number | null = null;
    try {
      const origin = validateRemoteSmokeConfiguration({
        origin: process.env.PYP_REMOTE_TARGET_URL ?? '',
        environment: process.env.PYP_REMOTE_ENVIRONMENT,
        authorized: process.env.PYP_SMOKE_AUTHORIZED === '1',
        authorizationReference: process.env.PYP_SMOKE_AUTHORIZATION_REFERENCE ?? '',
        abTestClosed: process.env.PYP_AB_TEST_CLOSED === '1',
        maxRequests: Number(process.env.PYP_SMOKE_MAX_REQUESTS ?? '0'),
      });
      const endpoint = new URL('/api/health', origin);
      requestCount = 1;
      const requestStarted = performance.now();
      const response = await fetch(endpoint, { redirect: 'manual', signal: AbortSignal.timeout(10_000) });
      requestDuration = performance.now() - requestStarted;
      status = response.status;
      expect(response.status).toBe(200);
      expect(response.redirected).toBe(false);
      expect(response.url).toBe(endpoint.href);
      outcome = 'passed';
    } finally {
      await writeSanitizedRecord({
        outcome,
        duration_ms: performance.now() - started,
        request_duration_ms: requestDuration,
        request_count: requestCount,
        http_status: status,
      });
    }
  });
});
