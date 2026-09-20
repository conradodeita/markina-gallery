"use client";

import { useEffect, useId, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import styles from "./push-control.module.css";

import {
  cancelPushWork, clearDeviceNotifications, fetchPushState, PUSH_CHOICE_PREFIX, PUSH_LOGOUT_EVENT,
  pushSupportMessage, pushWorkIsCurrent, readPushChoice, reconcileDevicePush,
  registerDevicePush, rememberPushChoice, withPushDevice, type PushState,
} from "./push-device";
export { clearDeviceNotifications } from "./push-device";

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  async function logout() {
    setBusy(true); setError("");
    cancelPushWork();
    try {
      await withPushDevice(async () => {
        const response = await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
        if (!response.ok) throw new Error();
        await clearDeviceNotifications().catch(() => {}); // A revogação no servidor já terminou.
      });
      router.replace("/"); router.refresh();
    } catch { setError("Não foi possível sair. Tente novamente."); }
    finally { setBusy(false); }
  }
  return <span className={styles.control}><button className={styles.button} type="button" disabled={busy} onClick={logout}>{busy ? "Saindo…" : "Sair"}</button>{error && <span role="status">{error}</span>}</span>;
}

export function PushControl() {
  const pathname = usePathname();
  const [loaded, setLoaded] = useState<{ path: string; data: PushState } | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const version = useRef(0);
  const [message, setMessage] = useState("");
  const [dismissedIdentity, setDismissedIdentity] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    const refresh = () => {
      if (busyRef.current) return;
      const iteration = ++version.current;
      const deviceCurrent = pushWorkIsCurrent();
      const isCurrent = () => current && version.current === iteration && deviceCurrent();
      void withPushDevice(() => reconcileDevicePush(isCurrent)).then((data) => {
        if (!isCurrent()) return;
        setLoaded({ path: pathname, data });
        setMessage(!data.active && readPushChoice(data.identity) === "enabled"
          ? "Sua escolha está salva. Use Ativar notificações para concluir a conexão neste dispositivo." : "");
      }).catch(() => { if (isCurrent()) setLoaded(null); });
    };
    const stop = () => { version.current += 1; setLoaded(null); };
    const storage = (event: StorageEvent) => { if (event.key?.startsWith(PUSH_CHOICE_PREFIX)) refresh(); };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener("storage", storage);
    window.addEventListener(PUSH_LOGOUT_EVENT, stop);
    return () => { current = false; version.current += 1; window.removeEventListener("focus", refresh); window.removeEventListener("storage", storage); window.removeEventListener(PUSH_LOGOUT_EVENT, stop); };
  }, [pathname]);

  const state = loaded?.path === pathname ? loaded.data : null;
  async function toggle() {
    if (!state || busyRef.current) return;
    setMessage("");
    if (!state.active) {
      const unsupported = pushSupportMessage();
      if (unsupported) { setMessage(unsupported); return; }
    }
    busyRef.current = true; setBusy(true);
    const iteration = ++version.current;
    const deviceCurrent = pushWorkIsCurrent();
    const isCurrent = () => version.current === iteration && deviceCurrent();
    try {
      if (state.active) {
        await withPushDevice(async () => {
          const latest = await fetchPushState();
          if (!isCurrent() || latest.identity !== state.identity) throw new Error();
          const response = await fetch("/api/push/subscription", { method: "DELETE", credentials: "same-origin", headers: { "X-Push-Identity": state.identity } });
          if (!response.ok) throw new Error();
          rememberPushChoice(state.identity, "disabled");
          await clearDeviceNotifications().catch(() => {});
        });
        if (isCurrent()) {
          setLoaded({ path: pathname, data: { ...state, active: false } });
          setMessage("Notificações desativadas neste dispositivo.");
        }
      } else {
        if (readPushChoice(state.identity) !== "enabled") rememberPushChoice(state.identity, "dismissed");
        // Quando necessária, a permissão nativa é solicitada no gesto, antes da rede.
        const permission = Notification.permission === "granted" ? "granted" : Notification.permission === "denied" ? "denied" : await Notification.requestPermission();
        if (permission !== "granted") {
          rememberPushChoice(state.identity, "dismissed");
          setMessage(permission === "denied" ? "Notificações bloqueadas. Libere nas permissões do navegador." : "Você pode ativar as notificações quando quiser.");
          return;
        }
        const data = await withPushDevice(() => registerDevicePush(state, isCurrent));
        if (isCurrent()) {
          setLoaded({ path: pathname, data });
          setMessage("Notificações ativadas. Sua escolha está salva neste dispositivo.");
        }
      }
    } catch { if (isCurrent()) setMessage("Não foi possível atualizar as notificações. Tente novamente."); }
    finally { busyRef.current = false; setBusy(false); }
  }

  if (!state || (!state.available && !state.active)) return null;
  const invite = !busy && !state.active && state.identity !== dismissedIdentity && readPushChoice(state.identity) === null && !pushSupportMessage() && Notification.permission !== "denied";
  function dismissInvitation() {
    if (!state) return;
    rememberPushChoice(state.identity, "dismissed");
    setDismissedIdentity(state.identity);
  }
  return <div className={styles.control}>
    <button type="button" className={styles.button} disabled={busy} onClick={toggle} aria-label={state.active ? "Desativar notificações neste dispositivo" : "Ativar notificações"}>
      <span aria-hidden="true">{state.active ? "●" : "○"}</span> {busy ? "Aguarde…" : state.active ? "Notificações ativadas" : "Ativar notificações"}
    </button>
    {message && <span className={styles.message} role="status">{message}</span>}
    {invite && <PushInvitation onActivate={toggle} onDismiss={dismissInvitation} />}
  </div>;
}


function PushInvitation({ onActivate, onDismiss }: { onActivate: () => void; onDismiss: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    element.showModal();
    return () => { element.close(); };
  }, []);
  return <dialog ref={dialog} className={styles.invitation} aria-labelledby={`${id}-title`} aria-describedby={`${id}-detail`} onCancel={(event) => { event.preventDefault(); onDismiss(); }}>
    <p className={styles.eyebrow}>Avisos no seu dispositivo</p>
    <h2 id={`${id}-title`}>Quer receber notificações?</h2>
    <p id={`${id}-detail`}>Receba avisos sobre novidades nas galerias e atualizações de pedidos. Sua escolha fica salva para esta conta neste navegador ou aplicativo.</p>
    <p className={styles.hint}>Você pode desativar quando quiser. Em outro dispositivo ou após limpar os dados do navegador, será necessário ativar novamente.</p>
    <div className={styles.actions}>
      <button type="button" className={styles.button} onClick={onDismiss}>Agora não</button>
      <button type="button" className={`${styles.button} ${styles.activate}`} onClick={onActivate}>Ativar avisos</button>
    </div>
  </dialog>;
}
