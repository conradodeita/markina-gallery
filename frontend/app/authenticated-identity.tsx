"use client";

import { useEffect, useState } from "react";
import styles from "./push-control.module.css";

type Identity = { role: "admin" | "client"; identity: string };

export function AuthenticatedIdentity() {
  const [identity, setIdentity] = useState<Identity | null>(null);

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
        if (
          typeof result.identity !== "string" ||
          !result.identity ||
          (result.role !== "admin" && result.role !== "client")
        ) throw new Error("Identidade inválida");
        if (active) setIdentity(result as Identity);
      })
      .catch(() => {
        if (active) setIdentity(null);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  if (!identity) return null;
  return (
    <span className={styles.identity} aria-label={`Logado como: ${identity.identity}`}>
      <span aria-hidden="true">Logado como:</span> {identity.identity}
    </span>
  );
}
