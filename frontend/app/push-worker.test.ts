import { readFileSync } from "node:fs";
import vm from "node:vm";
import { expect, it, vi } from "vitest";

function worker() {
  const handlers: Record<string, (event: Record<string, unknown>) => void> = {};
  const showNotification = vi.fn().mockResolvedValue(undefined);
  const clients = { matchAll: vi.fn().mockResolvedValue([]), openWindow: vi.fn() };
  const close = vi.fn();
  vm.runInNewContext(readFileSync("public/markina-sw.js", "utf8"), {
    URL, self: { location: { origin: "https://example.test" }, clients,
      registration: { showNotification, getNotifications: async () => [{ close }] },
      addEventListener: (name: string, handler: typeof handlers[string]) => { handlers[name] = handler; } },
  });
  return { handlers, showNotification, clients, close };
}
const payload = { id: "11111111-1111-4111-8111-111111111111", title: "Novas fotos", body: "Sua galeria está pronta.", path: "/library" };

it("recebe somente texto curto e usa a mesma tag para o mesmo evento", async () => {
  const { handlers, showNotification } = worker();
  const waitUntil = vi.fn();
  handlers.push({ data: { json: () => payload }, waitUntil });
  handlers.push({ data: { json: () => payload }, waitUntil });
  await Promise.all(waitUntil.mock.calls.map(([promise]) => promise));
  expect(showNotification).toHaveBeenCalledTimes(2);
  expect(showNotification.mock.calls[0]).toEqual(showNotification.mock.calls[1]);
  expect(showNotification.mock.calls[0][1]).toMatchObject({ tag: `pick-event-${payload.id}`, renotify: false, data: { path: "/library" } });
});

it("rejeita payload inválido e destinos externos, arbitrários ou com token", () => {
  const { handlers, showNotification } = worker();
  for (const path of ["https://evil.test", "//evil.test", "/library?token=secret", "/api/private", "/admin/settings"]) {
    handlers.push({ data: { json: () => ({ ...payload, path }) }, waitUntil: vi.fn() });
  }
  handlers.push({ data: { json: () => { throw new Error(); } }, waitUntil: vi.fn() });
  handlers.push({ data: { json: () => ({ ...payload, body: "x".repeat(141) }) }, waitUntil: vi.fn() });
  expect(showNotification).not.toHaveBeenCalled();
});

it("foca aba interna ou abre destino protegido, nunca aba de terceiro", async () => {
  const { handlers, clients } = worker();
  const tab = { url: "https://example.test/", navigate: vi.fn(), focus: vi.fn() };
  clients.matchAll.mockResolvedValue([{ url: "https://evil.test" }, tab]);
  const waitUntil = vi.fn();
  const close = vi.fn();
  handlers.notificationclick({ notification: { data: { path: "/library" }, close }, waitUntil });
  await waitUntil.mock.calls[0][0];
  expect(tab.navigate).toHaveBeenCalledWith("https://example.test/library");
  expect(tab.focus).toHaveBeenCalledOnce();
  clients.matchAll.mockResolvedValue([]);
  handlers.notificationclick({ notification: { data: { path: "/library" }, close }, waitUntil });
  await waitUntil.mock.calls[1][0];
  expect(clients.openWindow).toHaveBeenCalledWith("https://example.test/library");
  handlers.notificationclick({ notification: { data: { path: "//evil.test" }, close }, waitUntil });
  expect(waitUntil).toHaveBeenCalledTimes(2);
});

it("limpa avisos no logout somente por mensagem da própria origem", async () => {
  const { handlers, close } = worker();
  const waitUntil = vi.fn();
  handlers.message({ data: { type: "CLEAR_PUSH_NOTIFICATIONS" }, source: { url: "https://evil.test" }, waitUntil });
  expect(waitUntil).not.toHaveBeenCalled();
  handlers.message({ data: { type: "CLEAR_PUSH_NOTIFICATIONS" }, source: { url: "https://example.test/library" }, waitUntil });
  await waitUntil.mock.calls[0][0];
  expect(close).toHaveBeenCalledOnce();
});
