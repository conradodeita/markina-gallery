"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { protectedContext } from "./session-recovery";
import { PUSH_LOGOUT_EVENT } from "./push-device";

export function MonitorActivity() {
  const pathname = usePathname();
  useEffect(() => {
    if (!protectedContext(pathname)) return;
    const controller = new AbortController();
    let enabled = false;
    let lastSent = -Infinity;
    let stopped = false;
    let pending = false;
    void fetch("/api/auth/activity-policy", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (response) => { if (response.ok) enabled = (await response.json()).enabled === true; })
      .catch(() => undefined);
    function interact() {
      if (!enabled || stopped || pending || document.visibilityState !== "visible" || Date.now() - lastSent < 60_000) return;
      lastSent = Date.now();
      pending = true;
      void fetch("/api/auth/activity", {
        method: "POST", credentials: "same-origin", cache: "no-store", signal: controller.signal,
        headers: { "X-Monitor-Activity": "1" },
      }).then((response) => { if (response.status === 401 || response.status === 403) stopped = true; })
        .catch(() => undefined).finally(() => { pending = false; });
    }
    const stop = () => { stopped = true; controller.abort(); };
    window.addEventListener("pointerdown", interact, { passive: true });
    window.addEventListener("keydown", interact);
    window.addEventListener(PUSH_LOGOUT_EVENT, stop);
    return () => {
      stop();
      window.removeEventListener("pointerdown", interact);
      window.removeEventListener("keydown", interact);
      window.removeEventListener(PUSH_LOGOUT_EVENT, stop);
    };
  }, [pathname]);
  return null;
}
