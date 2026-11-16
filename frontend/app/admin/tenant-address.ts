import { useEffect, useState } from "react";

export type TenantAddress = {
  base_domain: "pickyourpic.com.br";
  hostname: string | null;
  state: "unselected" | "reserved" | "ready";
  choice_complete: boolean;
  suggested_prefix: string | null;
  public_url: string | null;
};

export const ADDRESS_ENDPOINT = "/api/admin/onboarding/address";
export const ADDRESS_CHANGED = "pyp:tenant-address-changed";

export function parseTenantAddress(value: unknown): TenantAddress {
  if (!value || typeof value !== "object") throw new Error("Endereço indisponível.");
  const data = value as Record<string, unknown>;
  const validHostname = typeof data.hostname === "string" &&
    /^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/.test(data.hostname);
  if (data.base_domain !== "pickyourpic.com.br" ||
      !["unselected", "reserved", "ready"].includes(String(data.state)) ||
      (data.state === "unselected" ? data.hostname !== null || data.choice_complete !== false
        : !validHostname || data.choice_complete !== true) ||
      (data.state === "ready" ? data.public_url !== `https://${data.hostname}` : data.public_url !== null) ||
      (data.suggested_prefix !== null && typeof data.suggested_prefix !== "string")) {
    throw new Error("Endereço indisponível.");
  }
  return data as TenantAddress;
}

export function useTenantAddress(enabled = true, context = "") {
  const [address, setAddress] = useState<TenantAddress | null>(null);
  const [phase, setPhase] = useState<"loading" | "ready" | "hidden" | "error">("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    fetch(ADDRESS_ENDPOINT, { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (response.status === 403 || response.status === 404) return null;
        if (!response.ok) throw new Error("Endereço indisponível.");
        return parseTenantAddress(await response.json());
      })
      .then((data) => {
        if (!cancelled) { setAddress(data); setPhase(data ? "ready" : "hidden"); }
      })
      .catch(() => { if (!cancelled) setPhase("error"); });
    return () => { cancelled = true; };
  }, [enabled, context, attempt]);

  useEffect(() => {
    function changed() { setAttempt((current) => current + 1); }
    window.addEventListener(ADDRESS_CHANGED, changed);
    return () => window.removeEventListener(ADDRESS_CHANGED, changed);
  }, []);

  function retry() { setPhase("loading"); setAttempt((current) => current + 1); }
  return { address, phase, retry, setAddress };
}
