"use client";

import { useEffect, useState } from "react";

import { PUSH_LOGOUT_EVENT } from "../push-device";
import { CapacityDiagnostics } from "./capacity-diagnostics";

export function InstallationDiagnostics() {
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    let current = true;
    let version = 0;
    let request: AbortController | null = null;
    const stop = () => {
      version += 1;
      request?.abort();
      request = null;
      setAuthorized(false);
    };
    const refresh = () => {
      stop();
      const iteration = version;
      const controller = new AbortController();
      request = controller;
      void fetch("/api/admin/installation-capabilities", {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
      }).then(async (response) => {
        if (!response.ok) return;
        const data = await response.json() as { capacity_diagnostics?: unknown };
        if (current && iteration === version) setAuthorized(data.capacity_diagnostics === true);
      }).catch(() => {
        if (current && iteration === version) setAuthorized(false);
      });
    };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener(PUSH_LOGOUT_EVENT, stop);
    return () => {
      current = false;
      version += 1;
      request?.abort();
      window.removeEventListener("focus", refresh);
      window.removeEventListener(PUSH_LOGOUT_EVENT, stop);
    };
  }, []);

  if (!authorized) return null;
  return <section className="capacity-diagnostics-section">
    <CapacityDiagnostics onAccessDenied={() => setAuthorized(false)} />
  </section>;
}
