import { describe, expect, it } from 'vitest';
import {
  REMOTE_SMOKE_ORIGIN,
  validateRemoteSmokeConfiguration,
  type RemoteSmokeConfiguration,
} from './remote-smoke-policy';

const approvedConfiguration: RemoteSmokeConfiguration = {
  origin: REMOTE_SMOKE_ORIGIN,
  environment: 'homolog',
  authorized: true,
  authorizationReference: 'non-secret-approval-reference',
  abTestClosed: true,
  maxRequests: 3,
};

describe('preflight remoto do Vitest', () => {
  it('aceita somente o conjunto exato de gates do smoke', () => {
    expect(validateRemoteSmokeConfiguration(approvedConfiguration)).toBe(REMOTE_SMOKE_ORIGIN);
  });

  it.each([
    ['target arbitrário', { origin: 'https://outside.invalid?token=do-not-print' }],
    ['ambiente incorreto', { environment: 'production' }],
    ['sem autorização', { authorized: false }],
    ['sem referência', { authorizationReference: '' }],
    ['A+B ativo', { abTestClosed: false }],
    ['teto incorreto', { maxRequests: 4 }],
  ])('falha fechado: %s sem expor os valores recebidos', (_reason, override) => {
    let message = '';
    try {
      validateRemoteSmokeConfiguration({ ...approvedConfiguration, ...override });
    } catch (error) {
      message = error instanceof Error ? error.message : '';
    }
    expect(message).toBe('remote_smoke_preflight_failed');
    expect(message).not.toContain('do-not-print');
  });
});
