"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { clearFacialSearchStorage } from "./facial-search-storage";
import { protectedContext, recoveryLocation } from "./session-recovery";

type Notice = "temporary" | "forbidden" | "recovered" | null;
const defaultNavigate = (destination: string) => window.location.replace(destination);

function ProtectedSession({ pathname, children, navigate }: {
  pathname: string;
  children: React.ReactNode;
  navigate: (destination: string) => void;
}) {
  const [authorized, setAuthorized] = useState(false);
  const [expired, setExpired] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const retry = useRef<() => void>(() => undefined);

  useEffect(() => {
    let active = true;
    let blocked = false;
    let verified = false;
    let pending: Promise<void> | null = null;
    let followUp = false;
    let controller: AbortController | null = null;
    const originalFetch = window.fetch;
    const context = protectedContext(pathname);

    function temporary() {
      if (active && !blocked) setNotice("temporary");
    }

    function check(cause?: "forbidden" | "retry") {
      if (!active || blocked) return pending;
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
            clearFacialSearchStorage();
            setAuthorized(false);
            setExpired(true);
            navigate(recoveryLocation(pathname));
            return;
          }
          if (response.status === 403) {
            blocked = true;
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
            clearFacialSearchStorage();
            setAuthorized(false);
            setNotice("forbidden");
            return;
          }
          verified = true;
          setAuthorized(true);
          setNotice((previous) => cause === "forbidden" ? "forbidden" : cause === "retry" ? "recovered" : previous);
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
      try {
        const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin);
        ownApi = url.origin === window.location.origin && url.pathname.startsWith("/api/");
      } catch {
        ownApi = false;
      }
      if (ownApi && blocked) throw new DOMException("Sessão indisponível", "AbortError");
      try {
        const response = await originalFetch(input, options);
        if (ownApi && active && verified && !blocked) {
          if (response.status === 401 || response.status === 403) void check("forbidden");
          else if (response.status === 408 || response.status >= 500) temporary();
        }
        return response;
      } catch (error) {
        const signal = options?.signal ?? (input instanceof Request ? input.signal : undefined);
        if (ownApi && !signal?.aborted) temporary();
        throw error;
      }
    };

    window.fetch = observedFetch;
    retry.current = () => { void check("retry"); };
    const resume = () => { if (document.visibilityState === "visible") void check(); };
    window.addEventListener("focus", resume);
    window.addEventListener("pageshow", resume);
    document.addEventListener("visibilitychange", resume);
    const interval = window.setInterval(resume, 60_000);
    void check();
    return () => {
      active = false;
      controller?.abort();
      window.clearInterval(interval);
      window.removeEventListener("focus", resume);
      window.removeEventListener("pageshow", resume);
      document.removeEventListener("visibilitychange", resume);
      if (window.fetch === observedFetch) window.fetch = originalFetch;
      retry.current = () => undefined;
    };
  }, [pathname, navigate]);

  return <>
    {expired ? <p role="status">Sua sessão terminou. Redirecionando para entrar novamente…</p> : null}
    {!expired && notice ? <section className="section-card" aria-label="Estado da sessão">
      <p role="alert">{notice === "temporary"
        ? "A conexão está temporariamente indisponível. Não repita envios ou compras sem conferir se foram concluídos."
        : notice === "forbidden" ? "Acesso negado para esta operação ou área. Confira suas permissões ou os dados informados."
          : "Conexão confirmada. Confira o resultado da ação anterior antes de tentar novamente."}</p>
      {notice === "temporary" ? <button type="button" onClick={() => retry.current()}>Verificar conexão novamente</button> : null}
      {notice === "forbidden" && !authorized ? <a href={recoveryLocation(pathname)}>Voltar à entrada</a> : null}
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
  return <ProtectedSession key={pathname} pathname={pathname} navigate={navigate}>{children}</ProtectedSession>;
}
