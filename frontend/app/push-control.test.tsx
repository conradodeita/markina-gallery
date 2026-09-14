import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LogoutButton, PushControl } from "./push-control";

const route = vi.hoisted(() => ({ pathname: "/library", replace: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => route.pathname, useRouter: () => route }));
const subscription = { unsubscribe: vi.fn().mockResolvedValue(true), toJSON: () => ({ endpoint: "https://fcm.googleapis.com/test", keys: {} }) };
const registration = { active: { postMessage: vi.fn() }, pushManager: { getSubscription: vi.fn().mockResolvedValue(null), subscribe: vi.fn().mockResolvedValue(subscription) } };
const permission = vi.fn().mockResolvedValue("granted");
const state = { available: true, active: false, public_key: "BAAA", identity: "client:test" };
let currentState = { ...state };
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  route.pathname = "/library";
  currentState = { ...state };
  permission.mockClear(); subscription.unsubscribe.mockClear(); registration.active.postMessage.mockClear();
  registration.pushManager.getSubscription.mockResolvedValue(null);
  permission.mockResolvedValue("granted");
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("PushManager", function () {});
  vi.stubGlobal("Notification", { requestPermission: permission });
  vi.stubGlobal("matchMedia", () => ({ matches: false }));
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Chrome");
  Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: { register: vi.fn().mockResolvedValue(registration), ready: Promise.resolve(registration), getRegistration: vi.fn().mockResolvedValue(registration) } });
  fetchMock = vi.fn((_url: string, options?: RequestInit) => Promise.resolve(options?.method ? new Response(null, { status: 204 }) : new Response(JSON.stringify(currentState))));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("ativa só após clique, salva a inscrição e desativa somente este dispositivo", async () => {
  render(<PushControl />);
  const activate = await screen.findByRole("button", { name: "Ativar notificações" });
  expect(permission).not.toHaveBeenCalled();
  fireEvent.click(activate);
  fireEvent.click(await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" }));
  expect(await screen.findByText("Notificações desativadas neste dispositivo.")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/push/subscription", expect.objectContaining({ method: "POST", body: JSON.stringify({ subscription: subscription.toJSON() }) }));
  expect(fetchMock).toHaveBeenCalledWith("/api/push/subscription", expect.objectContaining({ method: "DELETE" }));
});

it("explica permissão negada e não envia inscrição", async () => {
  permission.mockResolvedValue("denied");
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  expect(await screen.findByText(/Libere nas permissões/)).toBeTruthy();
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
});

it("informa instalação iOS e navegador incompatível sem abrir prompt", async () => {
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("iPhone Safari");
  const { unmount } = render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  expect(await screen.findByText(/Tela de Início/)).toBeTruthy();
  expect(permission).not.toHaveBeenCalled();
  unmount();
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Chrome");
  vi.stubGlobal("isSecureContext", false);
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  expect(await screen.findByText(/não oferece notificações/)).toBeTruthy();
});

it("reload e troca de conta consultam o estado sem repetir prompts", async () => {
  currentState.active = true;
  const { rerender } = render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  currentState = { ...state, identity: "admin:other" };
  route.pathname = "/admin";
  rerender(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(permission).not.toHaveBeenCalled();
});

it("falha de cadastro desfaz inscrição do navegador e permite tentar novamente", async () => {
  fetchMock.mockImplementation((_url: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(state), { status: options?.method ? 503 : 200 })));
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  expect(await screen.findByText(/Não foi possível atualizar/)).toBeTruthy();
  expect(subscription.unsubscribe).toHaveBeenCalledOnce();
});

it("logout revoga no servidor antes de limpar o dispositivo e voltar à entrada", async () => {
  registration.pushManager.getSubscription.mockResolvedValue(subscription);
  render(<LogoutButton />);
  fireEvent.click(screen.getByRole("button", { name: "Sair" }));
  await waitFor(() => expect(route.replace).toHaveBeenCalledWith("/"));
  expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" }));
  expect(subscription.unsubscribe).toHaveBeenCalledOnce();
  expect(registration.active.postMessage).toHaveBeenCalledWith({ type: "CLEAR_PUSH_NOTIFICATIONS" });
});
