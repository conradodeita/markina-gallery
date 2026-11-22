"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";

type WidgetOptions = {
  sitekey: string;
  action: "photographer_signup";
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": () => void;
};

declare global {
  interface Window {
    turnstile?: {
      render(container: HTMLElement, options: WidgetOptions): string;
      reset(widgetId: string): void;
      remove(widgetId: string): void;
    };
  }
}

type Props = {
  siteKey: string;
  resetSignal: number;
  onToken: (token: string) => void;
};

export function TurnstileWidget({ siteKey, resetSignal, onToken }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const onTokenRef = useRef(onToken);
  const [scriptReady, setScriptReady] = useState(false);
  const [rendered, setRendered] = useState(false);

  useEffect(() => { onTokenRef.current = onToken; }, [onToken]);

  useEffect(() => {
    if (!scriptReady || !container.current || !window.turnstile || widgetId.current) return;
    widgetId.current = window.turnstile.render(container.current, {
      sitekey: siteKey,
      action: "photographer_signup",
      callback: (token) => { onTokenRef.current(token); setRendered(true); },
      "expired-callback": () => { onTokenRef.current(""); setRendered(false); },
      "error-callback": () => { onTokenRef.current(""); setRendered(false); },
    });
    return () => {
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
    };
  }, [scriptReady, siteKey]);

  useEffect(() => {
    if (resetSignal > 0 && widgetId.current && window.turnstile) {
      window.turnstile.reset(widgetId.current);
      onTokenRef.current("");
      setRendered(false);
    }
  }, [resetSignal]);

  return <div>
    <Script
      src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
      strategy="afterInteractive"
      onReady={() => setScriptReady(true)}
    />
    <div ref={container} aria-label="Verificação de segurança" />
    <span className="sr-only" aria-live="polite">
      {rendered ? "Verificação concluída." : "Conclua a verificação de segurança."}
    </span>
  </div>;
}
