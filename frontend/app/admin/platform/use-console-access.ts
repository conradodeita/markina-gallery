"use client";

import { useEffect, useState } from "react";
import { PUSH_LOGOUT_EVENT } from "../../push-device";

export function useConsoleAccess() {
  const [access, setAccess] = useState<boolean | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let version = 0;
    let controller: AbortController | null = null;
    const refresh = () => {
      const current = ++version;
      controller?.abort();
      controller = new AbortController();
      setAccess(null);
      setRevision((value) => value + 1);
      void fetch("/api/admin/platform/console/capabilities", {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
      }).then(async (response) => {
        const payload = response.ok ? await response.json() : null;
        if (version === current) setAccess(payload?.read_console === true);
      }).catch(() => { if (version === current) setAccess(false); });
    };
    const stop = () => { version++; controller?.abort(); setAccess(false); setRevision((value) => value + 1); };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener(PUSH_LOGOUT_EVENT, stop);
    return () => {
      version++; controller?.abort();
      window.removeEventListener("focus", refresh);
      window.removeEventListener(PUSH_LOGOUT_EVENT, stop);
    };
  }, []);
  return { access, revision };
}
