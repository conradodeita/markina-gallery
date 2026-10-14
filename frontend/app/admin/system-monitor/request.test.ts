import { afterEach, expect, it, vi } from "vitest";
import { monitorFetch } from "./request";

afterEach(() => vi.unstubAllGlobals());

it("ordena consultas e mantém opções privadas sem ampliar leituras simultâneas", async () => {
  let finish!: (value: Response) => void;
  const fetcher = vi.fn((path: string) => path.endsWith("/tree")
    ? new Promise<Response>((resolve) => { finish = resolve; })
    : Promise.resolve(new Response("{}")));
  vi.stubGlobal("fetch", fetcher);
  const options = { credentials: "same-origin", cache: "no-store" } as const;
  const first = monitorFetch("/api/admin/system-monitor/tree", options);
  const second = monitorFetch("/api/admin/system-monitor", options);
  await Promise.resolve();
  expect(fetcher).toHaveBeenCalledTimes(1);
  finish(new Response("{}"));
  await Promise.all([first, second]);
  expect(fetcher.mock.calls).toEqual([
    ["/api/admin/system-monitor/tree", options],
    ["/api/admin/system-monitor", options],
  ]);
});

it("cancelamento na fila não inicia consulta e não bloqueia a próxima", async () => {
  let finish!: (value: Response) => void;
  const fetcher = vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; }));
  vi.stubGlobal("fetch", fetcher);
  const first = monitorFetch("/api/admin/system-monitor", {});
  const controller = new AbortController();
  const cancelled = monitorFetch("/api/admin/system-monitor/tree", { signal: controller.signal });
  const rejected = expect(cancelled).rejects.toMatchObject({ name: "AbortError" });
  controller.abort();
  await Promise.resolve();
  finish(new Response("{}"));
  await first;
  await rejected;
  expect(fetcher).toHaveBeenCalledTimes(1);
  fetcher.mockImplementation(() => Promise.resolve(new Response("{}")));
  await monitorFetch("/api/admin/system-monitor/incidents", {});
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("falha de rede libera a fila sem repetir a consulta", async () => {
  const fetcher = vi.fn().mockRejectedValueOnce(new TypeError("network"))
    .mockResolvedValueOnce(new Response("{}"));
  vi.stubGlobal("fetch", fetcher);
  const first = monitorFetch("/api/admin/system-monitor", {});
  const rejected = expect(first).rejects.toThrow("network");
  const second = monitorFetch("/api/admin/system-monitor/tree", {});
  await rejected;
  expect((await second).status).toBe(200);
  expect(fetcher).toHaveBeenCalledTimes(2);
});
