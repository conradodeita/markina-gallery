"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { clearFacialSearchStorage } from "./facial-search-storage";
import { protectedContext, recoveryLocation } from "./session-recovery";

type Notice = "temporary" | "temporary-action" | "forbidden" | "uncertain" | "recovered" | null;
const defaultNavigate = (destination: string) => window.location.replace(destination);

function ProtectedSession({ pathname, children, navigate }: {
  pathname: string;
  children: React.ReactNode;
  navigate: (destination: string) => void;
}) {
  const [authorized, setAuthorized] = useState(false);
  const [expired, setExpired] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const verifiedOnce = useRef(false);
  const uncertainMutation = useRef(false);

  useEffect(() => {
    let active = true;
    let blocked = false;
    let verified = verifiedOnce.current;
    let pending: Promise<void> | null = null;
    let followUp = false;
    let controller: AbortController | null = null;
    let retryTimer: number | null = null;
    let retryDelay = 1_000;
    const originalFetch = window.fetch;
    const context = protectedContext(pathname);

    function clearRetry() {
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
        retryTimer = null;
      }
    }

    function scheduleRetry() {
      if (!active || blocked || retryTimer !== null || document.visibilityState !== "visible") return;
      const delay = retryDelay;
      retryDelay = Math.min(retryDelay * 2, 30_000);
      retryTimer = window.setTimeout(() => {
        retryTimer = null;
        if (active && !blocked && document.visibilityState === "visible") void check();
      }, delay);
    }

    function temporary() {
      if (active && !blocked) {
        setNotice(uncertainMutation.current ? "temporary-action" : "temporary");
        scheduleRetry();
      }
    }

    function checkAfterFailure(mutation: boolean) {
      if (!active || blocked) return;
      if (mutation) {
        uncertainMutation.current = true;
        setNotice("uncertain");
      }
      if (retryTimer === null) void check();
    }

    function check(cause?: "forbidden") {
      if (!active || blocked || document.visibilityState !== "visible") return pending;
      if (pending) {
        if (cause === "forbidden") followUp = true;
        return pending;
      }
      controller = new AbortController();
      const signal = controller.signal;
      const timeout = window.setTimeout(() => controller?.abort(), 10_000);
      pending = (async () => {
        try {
          const response = await originalFetch("/api/auth/destination", { credentials: "same-origin", cache: "no-store", signal });
          if (!active) return;
          if (response.status === 401) {
            blocked = true;
            clearRetry();
            clearFacialSearchStorage();
            setAuthorized(false);
            setExpired(true);
            navigate(recoveryLocation(pathname, window.location.hash));
            return;
          }
          if (response.status === 403) {
            blocked = true;
            clearRetry();
            clearFacialSearchStorage();
            setAuthorized(false);
            setNotice("forbidden");
            return;
          }
          if (!response.ok) {
            temporary();
            return;
          }
          const result = await response.json();
          if (!active) return;
          if (typeof result.destination !== "string") {
            temporary();
            return;
          }
          if ((result.destination === "/admin") !== (context === "admin")) {
            blocked = true;
            clearRetry();
            clearFacialSearchStorage();
            setAuthorized(false);
            setNotice("forbidden");
            return;
          }
          verified = true;
          verifiedOnce.current = true;
          retryDelay = 1_000;
          clearRetry();
          setAuthorized(true);
          setNotice((previous) => cause === "forbidden" ? "forbidden" : uncertainMutation.current ? "recovered" : (previous === "temporary" || previous === "temporary-action") ? null : previous);
        } catch {
          temporary();
        } finally {
          window.clearTimeout(timeout);
          pending = null;
          if (followUp) {
            followUp = false;
            void check("forbidden");
          }
        }
      })();
      return pending;
    }

    const observedFetch: typeof fetch = async (input, options) => {
      let ownApi = false;
      let activitySignal = false;
      try {
        const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin);
        ownApi = url.origin === window.location.origin && url.pathname.startsWith("/api/");
        activitySignal = url.pathname === "/api/auth/activity";
      } catch {
        ownApi = false;
      }
      const method = (options?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
      const mutation = !activitySignal && !["GET", "HEAD", "OPTIONS"].includes(method);
      if (ownApi && blocked) throw new DOMException("Sessão indisponível", "AbortError");
      try {
        const response = await originalFetch(input, options);
        if (ownApi && active && verified && !blocked) {
          if (response.status === 401 || response.status === 403) void check("forbidden");
          else if (response.status === 408 || response.status >= 500) checkAfterFailure(mutation);
        }
        return response;
      } catch (error) {
        const signal = options?.signal ?? (input instanceof Request ? input.signal : undefined);
        if (ownApi && !signal?.aborted) checkAfterFailure(mutation);
        throw error;
      }
    };

    window.fetch = observedFetch;
    const resume = () => { if (document.visibilityState === "visible") void check(); };
    window.addEventListener("focus", resume);
    window.addEventListener("pageshow", resume);
    document.addEventListener("visibilitychange", resume);
    const interval = window.setInterval(() => {
      if (retryTimer === null) resume();
    }, 60_000);
    void check();
    return () => {
      active = false;
      controller?.abort();
      clearRetry();
      window.clearInterval(interval);
      window.removeEventListener("focus", resume);
      window.removeEventListener("pageshow", resume);
      document.removeEventListener("visibilitychange", resume);
      if (window.fetch === observedFetch) window.fetch = originalFetch;
    };
  }, [pathname, navigate]);

  return <>
    {expired ? <p role="status">Sua sessão terminou. Redirecionando para entrar novamente…</p> : null}
    {!expired && notice ? <section className="section-card" aria-label="Estado da sessão">
      <p role={notice === "recovered" || notice === "uncertain" ? "status" : "alert"}>{notice === "temporary" || notice === "temporary-action"
        ? notice === "temporary-action"
          ? "A conexão está temporariamente indisponível. Não repita envios ou compras sem conferir se foram concluídos."
          : "A conexão está temporariamente indisponível para esta leitura. A confirmação será tentada novamente automaticamente."
        : notice === "uncertain"
          ? "Não foi possível confirmar o resultado da ação anterior. Confira antes de repetir envios ou compras."
          : notice === "recovered"
          ? "Conexão confirmada. Confira o resultado da ação anterior antes de tentar novamente."
          : "Acesso negado para esta operação ou área. Confira suas permissões ou os dados informados."}</p>
      {notice === "recovered" ? <button type="button" className="mk-button mk-button--secondary" onClick={() => { uncertainMutation.current = false; setNotice(null); }}>Fechar aviso</button> : null}
      {notice === "forbidden" && !authorized ? <a href={recoveryLocation(pathname, window.location.hash)}>Voltar à entrada</a> : null}
    </section> : null}
    {!authorized && !expired && !notice ? <p role="status">Verificando sua sessão…</p> : null}
    {authorized && !expired ? children : null}
  </>;
}

export function SessionBoundary({ children, navigate = defaultNavigate }: {
  children: React.ReactNode;
  navigate?: (destination: string) => void;
}) {
  const pathname = usePathname();
  if (!protectedContext(pathname)) return children;
  return <ProtectedSession key={protectedContext(pathname)} pathname={pathname} navigate={navigate}>{children}</ProtectedSession>;
}
