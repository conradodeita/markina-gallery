"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import styles from "./push-control.module.css";

type SubscriptionState = { available: boolean; active: boolean; public_key: string; identity: string };

export async function clearDeviceNotifications() {
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.getRegistration("/");
  registration?.active?.postMessage({ type: "CLEAR_PUSH_NOTIFICATIONS" });
  const subscription = await registration?.pushManager?.getSubscription();
  await subscription?.unsubscribe();
}

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  async function logout() {
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
      if (!response.ok) throw new Error();
      await clearDeviceNotifications().catch(() => {}); // A revogação no servidor já terminou.
      router.replace("/"); router.refresh();
    } catch { setError("Não foi possível sair. Tente novamente."); }
    finally { setBusy(false); }
  }
  return <span className={styles.control}><button className={styles.button} type="button" disabled={busy} onClick={logout}>{busy ? "Saindo…" : "Sair"}</button>{error && <span role="status">{error}</span>}</span>;
}

export function PushControl() {
  const pathname = usePathname();
  const [loaded, setLoaded] = useState<{ path: string; data: SubscriptionState } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    let current = true;
    fetch("/api/push/subscription", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (current) { setLoaded({ path: pathname, data }); setMessage(""); }
      }).catch(() => { if (current) setLoaded(null); });
    return () => { current = false; };
  }, [pathname]);

  const state = loaded?.path === pathname ? loaded.data : null;
  async function toggle() {
    if (!state || busy) return;
    setMessage("");
    if (!state.active) {
      const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
      const installed = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone;
      if (ios && !installed) { setMessage("Adicione o aplicativo à Tela de Início e abra por lá para ativar os avisos."); return; }
      if (!window.isSecureContext || !("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
        setMessage("Este navegador não oferece notificações push."); return;
      }
    }
    setBusy(true);
    try {
      if (state.active) {
        const response = await fetch("/api/push/subscription", { method: "DELETE", credentials: "same-origin" });
        if (!response.ok) throw new Error();
        await clearDeviceNotifications().catch(() => {});
        setLoaded({ path: pathname, data: { ...state, active: false } });
        setMessage("Notificações desativadas neste dispositivo.");
      } else {
        // Solicitação nativa no gesto explícito, antes de qualquer chamada de rede.
        const permission = await Notification.requestPermission();
        if (permission !== "granted") { setMessage(permission === "denied" ? "Notificações bloqueadas. Libere nas permissões do navegador." : "Você pode ativar as notificações quando quiser."); return; }
        await navigator.serviceWorker.register("/markina-sw.js", { scope: "/", updateViaCache: "none" });
        const registration = await navigator.serviceWorker.ready;
        const previous = await registration.pushManager.getSubscription();
        if (previous) await previous.unsubscribe();
        const publicKey = Uint8Array.from(atob(state.public_key.replace(/-/g, "+").replace(/_/g, "/")), (character) => character.charCodeAt(0));
        const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: publicKey });
        const identity = await fetch("/api/push/subscription", { credentials: "same-origin", cache: "no-store" });
        if (!identity.ok || (await identity.json()).identity !== state.identity) {
          await subscription.unsubscribe(); throw new Error();
        }
        const response = await fetch("/api/push/subscription", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subscription: subscription.toJSON() }),
        }).catch(async () => { await subscription.unsubscribe().catch(() => {}); throw new Error(); });
        if (!response.ok) { await subscription.unsubscribe().catch(() => {}); throw new Error(); }
        setLoaded({ path: pathname, data: { ...state, active: true } });
        setMessage("Notificações ativadas neste dispositivo.");
      }
    } catch { setMessage("Não foi possível atualizar as notificações. Tente novamente."); }
    finally { setBusy(false); }
  }

  if (!state || (!state.available && !state.active)) return null;
  return <div className={styles.control}>
    <button type="button" className={styles.button} disabled={busy} onClick={toggle} aria-label={state.active ? "Desativar notificações neste dispositivo" : "Ativar notificações"}>
      <span aria-hidden="true">{state.active ? "●" : "○"}</span> {busy ? "Aguarde…" : state.active ? "Notificações ativadas" : "Ativar notificações"}
    </button>
    {message && <span className={styles.message} role="status">{message}</span>}
  </div>;
}
