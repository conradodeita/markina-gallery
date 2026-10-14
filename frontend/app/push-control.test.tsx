import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LogoutButton, PushControl } from "./push-control";
import { PUSH_CHOICE_PREFIX } from "./push-device";

const route = vi.hoisted(() => ({ pathname: "/library", replace: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ usePathname: () => route.pathname, useRouter: () => route }));
const subscription = { unsubscribe: vi.fn().mockResolvedValue(true), toJSON: () => ({ endpoint: "https://fcm.googleapis.com/test", keys: {} }) };
const registration = { active: { postMessage: vi.fn() }, pushManager: { getSubscription: vi.fn().mockResolvedValue(null), subscribe: vi.fn().mockResolvedValue(subscription) } };
const permission = vi.fn().mockResolvedValue("granted");
const state = { available: true, active: false, public_key: "BAAA", identity: "client:test" };
let currentState = { ...state };
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, value: function (this: HTMLDialogElement) { this.open = true; } });
  Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, value: function (this: HTMLDialogElement) { this.open = false; } });
  route.pathname = "/library";
  currentState = { ...state };
  permission.mockClear(); subscription.unsubscribe.mockClear(); registration.active.postMessage.mockClear();
  registration.pushManager.getSubscription.mockResolvedValue(null);
  registration.pushManager.subscribe.mockClear();
  registration.pushManager.subscribe.mockImplementation(async () => { registration.pushManager.getSubscription.mockResolvedValue(subscription); return subscription; });
  subscription.unsubscribe.mockImplementation(async () => { registration.pushManager.getSubscription.mockResolvedValue(null); return true; });
  permission.mockImplementation(async () => { Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" }); return "granted"; });
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("PushManager", function () {});
  vi.stubGlobal("Notification", { permission: "default", requestPermission: permission });
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
  expect(fetchMock).toHaveBeenCalledWith("/api/push/subscription", expect.objectContaining({ method: "POST", body: JSON.stringify({ subscription: subscription.toJSON(), expected_identity: state.identity }) }));
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
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  registration.pushManager.getSubscription.mockResolvedValue(subscription);
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


it.each(["client:test", "admin:test"])("restaura escolha de %s após logout e novo acesso sem repetir permissão", async (identity) => {
  currentState.identity = identity;
  const page = render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(localStorage.getItem(PUSH_CHOICE_PREFIX + identity)).toBe("enabled");
  page.unmount();
  const logout = render(<LogoutButton />);
  fireEvent.click(screen.getByRole("button", { name: "Sair" }));
  await waitFor(() => expect(subscription.unsubscribe).toHaveBeenCalled());
  await waitFor(() => expect(screen.queryByText("Saindo…")).toBeNull());
  logout.unmount();
  permission.mockClear();
  render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(permission).not.toHaveBeenCalled();
  expect(registration.pushManager.subscribe).toHaveBeenCalledTimes(2);
});

it("lembra desativação e não restaura após reload mesmo com permissão concedida", async () => {
  localStorage.setItem(PUSH_CHOICE_PREFIX + state.identity, "enabled");
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  const page = render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" }));
  await screen.findByText("Notificações desativadas neste dispositivo.");
  page.unmount();
  fetchMock.mockClear();
  render(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(localStorage.getItem(PUSH_CHOICE_PREFIX + state.identity)).toBe("disabled");
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
});

it("não herda a escolha de outra conta e não confunde permissão nativa com adesão", async () => {
  localStorage.setItem(PUSH_CHOICE_PREFIX + "admin:previous", "enabled");
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  render(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
  expect(permission).not.toHaveBeenCalled();
});

it("mantém inscrição existente e repara inscrição perdida sem mostrar estado ativo incorreto", async () => {
  currentState.active = true;
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  registration.pushManager.getSubscription.mockResolvedValue(subscription);
  const page = render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(registration.pushManager.subscribe).not.toHaveBeenCalled();
  page.unmount();
  registration.pushManager.getSubscription.mockResolvedValue(null);
  render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(registration.pushManager.subscribe).toHaveBeenCalledOnce();
  expect(permission).not.toHaveBeenCalled();
});

it("não repete prompts quando a permissão foi revogada", async () => {
  localStorage.setItem(PUSH_CHOICE_PREFIX + state.identity, "enabled");
  Object.defineProperty(Notification, "permission", { configurable: true, value: "denied" });
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  expect(await screen.findByText(/Libere nas permissões/)).toBeTruthy();
  expect(permission).not.toHaveBeenCalled();
  expect(registration.pushManager.subscribe).not.toHaveBeenCalled();
});

it("falha na restauração preserva escolha e oferece nova tentativa sem loop", async () => {
  localStorage.setItem(PUSH_CHOICE_PREFIX + state.identity, "enabled");
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  fetchMock.mockImplementation((_url: string, options?: RequestInit) => Promise.resolve(new Response(JSON.stringify(state), { status: options?.method ? 503 : 200 })));
  render(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(await screen.findByText(/Sua escolha está salva/)).toBeTruthy();
  expect(localStorage.getItem(PUSH_CHOICE_PREFIX + state.identity)).toBe("enabled");
  expect(registration.pushManager.subscribe).toHaveBeenCalledOnce();
});

it("descarta ativação quando a conta muda durante a inscrição", async () => {
  registration.pushManager.subscribe.mockImplementation(async () => { currentState = { ...state, identity: "admin:other" }; return subscription; });
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar notificações" }));
  await screen.findByText(/Não foi possível atualizar/);
  expect(subscription.unsubscribe).toHaveBeenCalledOnce();
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
  expect(localStorage.getItem(PUSH_CHOICE_PREFIX + "admin:other")).toBeNull();
});


it("oferece convite inicial e memoriza dispensa sem pedir permissão", async () => {
  const page = render(<PushControl />);
  expect(await screen.findByRole("dialog", { name: "Quer receber notificações?" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Agora não" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(localStorage.getItem(PUSH_CHOICE_PREFIX + state.identity)).toBe("dismissed");
  page.unmount();
  render(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(permission).not.toHaveBeenCalled();
});

it("ativa pelo convite e não o repete após recarregar", async () => {
  const page = render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar avisos" }));
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(screen.queryByRole("dialog")).toBeNull();
  page.unmount();
  render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(permission).toHaveBeenCalledOnce();
});

it("dispensa convite por Escape e não oferece convite em navegador incompatível", async () => {
  const page = render(<PushControl />);
  fireEvent(await screen.findByRole("dialog"), new Event("cancel", { bubbles: true, cancelable: true }));
  expect(screen.queryByRole("dialog")).toBeNull();
  page.unmount();
  localStorage.clear();
  vi.stubGlobal("isSecureContext", false);
  render(<PushControl />);
  await screen.findByRole("button", { name: "Ativar notificações" });
  expect(screen.queryByRole("dialog")).toBeNull();
});


it("logout durante inscrição cancela o POST e preserva a revogação", async () => {
  let finishSubscribe!: (value: typeof subscription) => void;
  registration.pushManager.subscribe.mockImplementation(() => new Promise((resolve) => { finishSubscribe = resolve; }));
  render(<><PushControl /><LogoutButton /></>);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar avisos" }));
  await waitFor(() => expect(finishSubscribe).toBeTypeOf("function"));
  fireEvent.click(screen.getByRole("button", { name: "Sair" }));
  finishSubscribe(subscription);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", expect.objectContaining({ method: "POST" })));
  await waitFor(() => expect(screen.queryByText("Saindo…")).toBeNull());
  expect(fetchMock.mock.calls.some(([url, options]) => url === "/api/push/subscription" && options?.method === "POST")).toBe(false);
  expect(subscription.unsubscribe).toHaveBeenCalled();
});

it("ativa mesmo com armazenamento local indisponível sem insistir no convite", async () => {
  currentState.identity = "client:no-storage";
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("indisponível"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("indisponível"); });
  render(<PushControl />);
  fireEvent.click(await screen.findByRole("button", { name: "Ativar avisos" }));
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("revalida no refoco e respeita a escolha desativada em outra aba", async () => {
  localStorage.setItem(PUSH_CHOICE_PREFIX + state.identity, "enabled");
  Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
  render(<PushControl />);
  await screen.findByRole("button", { name: "Desativar notificações neste dispositivo" });
  fetchMock.mockClear();
  localStorage.setItem(PUSH_CHOICE_PREFIX + state.identity, "disabled");
  registration.pushManager.getSubscription.mockResolvedValue(null);
  fireEvent(window, new StorageEvent("storage", { key: PUSH_CHOICE_PREFIX + state.identity }));
  await screen.findByRole("button", { name: "Ativar notificações" });
  fireEvent.focus(window);
  await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(1));
  expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
  expect(screen.queryByRole("dialog")).toBeNull();
});
