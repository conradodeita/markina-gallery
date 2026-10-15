// Coordinate this browser context with the bounded monitor reads on the API.
// Failure advances the queue; cancelled requests never start a network call.
let pending: Promise<void> = Promise.resolve();

export function monitorFetch(path: string, options: RequestInit): Promise<Response> {
  const request = pending.then(() => {
    options.signal?.throwIfAborted();
    return fetch(path, options);
  });
  pending = request.then(() => undefined, () => undefined);
  return request;
}
