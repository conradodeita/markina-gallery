"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function browserMode() {
  if (window.matchMedia("(display-mode: standalone)").matches
    || (navigator as Navigator & { standalone?: boolean }).standalone) return "standalone";
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
  if (/Safari/.test(ua) && !/Chrome|Chromium|Edg|Android/.test(ua)) return "safari";
  if (/Android/.test(ua) && /Firefox/.test(ua)) return "android";
  return "browser";
}

function subscribeMode(onChange: () => void) {
  const mode = window.matchMedia("(display-mode: standalone)");
  mode.addEventListener("change", onChange);
  return () => mode.removeEventListener("change", onChange);
}

export function InstallApp() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const mode = useSyncExternalStore(subscribeMode, browserMode, () => "browser");
  const manual = ["ios", "safari", "android"].includes(mode) ? mode : null;
  const [installed, setInstalled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const beforeInstall = (event: Event) => {
      event.preventDefault();
      setPrompt(event as InstallPrompt);
    };
    const didInstall = () => { setInstalled(true); setPrompt(null); };
    window.addEventListener("beforeinstallprompt", beforeInstall);
    window.addEventListener("appinstalled", didInstall);
    if ("serviceWorker" in navigator && window.isSecureContext) {
      // O worker não armazena páginas, API, fotos ou credenciais.
      void navigator.serviceWorker.register("/markina-sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {});
    }
    return () => {
      window.removeEventListener("beforeinstallprompt", beforeInstall);
      window.removeEventListener("appinstalled", didInstall);
    };
  }, []);

  async function install() {
    setError("");
    if (!prompt) { dialog.current?.showModal(); return; }
    setBusy(true);
    setPrompt(null); // Evento nativo é consumível uma única vez.
    try {
      await prompt.prompt();
      const result = await prompt.userChoice;
      if (result.outcome === "accepted") setInstalled(true);
    } catch { setError("Use o menu do navegador para instalar o aplicativo."); }
    finally { setBusy(false); }
  }

  if (installed || mode === "standalone" || (!prompt && !manual && !busy && !error)) return null;
  return <div className="pwa-install-bar">
    {error ? <span role="status">{error}</span> : null}
    <button type="button" className="pwa-install-button" onClick={install} disabled={busy}>
      <span aria-hidden="true">↓</span>{busy ? "Abrindo…" : "Instalar aplicativo"}
    </button>
    <dialog ref={dialog} className="pwa-install-dialog" aria-labelledby="pwa-install-title">
      <h2 id="pwa-install-title">Instalar aplicativo</h2>
      <p>{manual === "ios"
        ? "No menu de compartilhamento do navegador, escolha Adicionar à Tela de Início e confirme Adicionar. Se a opção não aparecer, abra este site no Safari."
        : manual === "safari"
          ? "No Safari, abra Arquivo e escolha Adicionar ao Dock. Se essa opção não estiver disponível, use um navegador compatível, como Chrome ou Edge."
          : "No menu do navegador, escolha Instalar ou Adicionar à tela inicial e confirme."}</p>
      <p>O aplicativo precisa de internet para acessar suas fotos.</p>
      <form method="dialog"><button className="pwa-install-button">Entendi</button></form>
    </dialog>
  </div>;
}
