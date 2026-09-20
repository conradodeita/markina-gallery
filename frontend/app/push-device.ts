export type PushState = { available: boolean; active: boolean; public_key: string; identity: string };
export type PushChoice = "enabled" | "disabled" | "dismissed";
export const PUSH_CHOICE_PREFIX = "pick-push-choice:v1:";
export const PUSH_LOGOUT_EVENT = "pick-push-logout";

const memory = new Map<string, PushChoice>();
let queue: Promise<unknown> = Promise.resolve();
let generation = 0;

export function readPushChoice(identity: string): PushChoice | null {
  try {
    const value = localStorage.getItem(PUSH_CHOICE_PREFIX + identity);
    return value === "enabled" || value === "disabled" || value === "dismissed" ? value : null;
  } catch { return memory.get(identity) ?? null; }
}

export function rememberPushChoice(identity: string, choice: PushChoice) {
  memory.set(identity, choice);
  try { localStorage.setItem(PUSH_CHOICE_PREFIX + identity, choice); } catch { /* Storage indisponível: mantém a escolha nesta página. */ }
}

export function pushSupportMessage() {
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
  const installed = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone;
  if (ios && !installed) return "Adicione o aplicativo à Tela de Início e abra por lá para ativar os avisos.";
  if (!window.isSecureContext || !("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return "Este navegador não oferece notificações push.";
  return "";
}

// Serializa inscrições e logout, inclusive entre abas quando Web Locks está disponível.
export function withPushDevice<T>(task: () => Promise<T>): Promise<T> {
  const run = () => navigator.locks?.request ? navigator.locks.request("pick-push-device", task) : task();
  const result = queue.then(run, run);
  queue = result.catch(() => {});
  return result;
}

export function cancelPushWork() {
  generation += 1;
  window.dispatchEvent(new Event(PUSH_LOGOUT_EVENT));
}

export function pushWorkIsCurrent() {
  const started = generation;
  return () => started === generation;
}

export async function fetchPushState(): Promise<PushState> {
  const response = await fetch("/api/push/subscription", { credentials: "same-origin", cache: "no-store" });
  if (!response.ok) throw new Error("Sessão indisponível.");
  return response.json();
}

export async function clearDeviceNotifications() {
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.getRegistration("/");
  registration?.active?.postMessage({ type: "CLEAR_PUSH_NOTIFICATIONS" });
  const subscription = await registration?.pushManager?.getSubscription();
  await subscription?.unsubscribe();
}

export async function registerDevicePush(state: PushState, isCurrent: () => boolean) {
  if (!isCurrent()) throw new Error("Operação substituída.");
  const before = await fetchPushState();
  if (!isCurrent() || before.identity !== state.identity || !before.available) throw new Error("A conta mudou.");
  await navigator.serviceWorker.register("/markina-sw.js", { scope: "/", updateViaCache: "none" });
  const registration = await navigator.serviceWorker.ready;
  if (!isCurrent()) throw new Error("Operação substituída.");
  const key = Uint8Array.from(atob(before.public_key.replace(/-/g, "+").replace(/_/g, "/")), (character) => character.charCodeAt(0));
  let subscription = await registration.pushManager.getSubscription();
  const previousKey = subscription?.options?.applicationServerKey;
  if (subscription && previousKey && (previousKey.byteLength !== key.length || new Uint8Array(previousKey).some((value, index) => value !== key[index]))) {
    await subscription.unsubscribe(); subscription = null;
  }
  subscription ??= await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key });
  try {
    const current = await fetchPushState();
    if (!isCurrent() || current.identity !== state.identity || !current.available) throw new Error("A conta mudou.");
    const response = await fetch("/api/push/subscription", {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: subscription.toJSON(), expected_identity: state.identity }),
    });
    if (!response.ok) throw new Error("Não foi possível registrar.");
  } catch (error) {
    await subscription.unsubscribe().catch(() => {});
    throw error;
  }
  rememberPushChoice(state.identity, "enabled");
  return { ...before, active: true };
}

export async function reconcileDevicePush(isCurrent: () => boolean): Promise<PushState> {
  const state = await fetchPushState();
  if (!isCurrent()) throw new Error("Operação substituída.");
  const choice = readPushChoice(state.identity);
  if (state.active && choice !== "disabled") rememberPushChoice(state.identity, "enabled");
  if (pushSupportMessage() || Notification.permission !== "granted") return { ...state, active: false };
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager?.getSubscription();
  if (state.active && subscription) return state;
  if (state.available && readPushChoice(state.identity) === "enabled" && isCurrent()) {
    try { return await registerDevicePush(state, isCurrent); }
    catch { return { ...state, active: false }; }
  }
  return { ...state, active: false };
}
