"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { LogoutButton, PushControl } from "./push-control";
import styles from "./push-control.module.css";

type AdminIdentity = { role: "admin"; identity: string };

function AdminSessionActions() {
  const [identity, setIdentity] = useState<AdminIdentity | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    fetch("/api/auth/identity", {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Identidade indisponível");
        const result = await response.json();
        if (result.role !== "admin" || typeof result.identity !== "string" || !result.identity) {
          throw new Error("Identidade inválida");
        }
        if (active) setIdentity({ role: "admin", identity: result.identity });
      })
      .catch(() => { if (active) setIdentity(null); });
    return () => { active = false; controller.abort(); };
  }, []);

  if (!identity) return null;
  return <div className={`${styles.actions} admin-session-toolbar`} role="group" aria-label="Controles da sessão do fotógrafo">
    <span className={styles.identity} aria-label={`Logado como: ${identity.identity}`}>
      <span aria-hidden="true">Logado como:</span> {identity.identity}
    </span>
    <PushControl />
    <LogoutButton />
  </div>;
}

export function AdminSessionToolbar() {
  const pathname = usePathname();
  const isAdminRoute = pathname === "/admin" || pathname.startsWith("/admin/");
  const isPublicAuthRoute = ["/admin/reset-password", "/admin/verify-email"].includes(pathname);
  if (!isAdminRoute || isPublicAuthRoute) return null;
  return <AdminSessionActions />;
}
