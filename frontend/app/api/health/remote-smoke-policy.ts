export const REMOTE_SMOKE_ORIGIN = 'https://markina-homolog.duckdns.org';

export type RemoteSmokeConfiguration = {
  origin: string;
  environment: string | undefined;
  authorized: boolean;
  authorizationReference: string;
  abTestClosed: boolean;
  maxRequests: number;
};

export function validateRemoteSmokeConfiguration(
  configuration: RemoteSmokeConfiguration,
): string {
  const referenceIsPresent = typeof configuration.authorizationReference === 'string'
    && configuration.authorizationReference.trim().length > 0;
  if (
    configuration.origin !== REMOTE_SMOKE_ORIGIN
    || configuration.environment !== 'homolog'
    || configuration.authorized !== true
    || !referenceIsPresent
    || configuration.abTestClosed !== true
    || configuration.maxRequests !== 3
  ) {
    throw new Error('remote_smoke_preflight_failed');
  }
  return REMOTE_SMOKE_ORIGIN;
}
