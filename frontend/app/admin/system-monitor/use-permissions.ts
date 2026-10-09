"use client";

import { useCallback, useEffect, useState } from "react";
import { PUSH_LOGOUT_EVENT } from "../../push-device";

export type Permissions = { metrics: boolean; tree: boolean; incidents: boolean; export: boolean };

export function useMonitorPermissions() {
  const [permissions, setPermissions] = useState<Permissions | null>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const revoke = useCallback(() => { setPermissions(null); setLoading(false); }, []);
  useEffect(() => {
    let version = 0;
    let controller: AbortController | null = null;
    function refresh() {
      const current = ++version;
      controller?.abort();
      controller = new AbortController();
      setPermissions(null);
      setLoading(true);
      void fetch("/api/admin/system-monitor/capabilities", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
        .then(async (response) => {
          if (!response.ok) return;
          const data = await response.json();
          if (version === current) {
            setPermissions({ metrics: data.metrics === true, tree: data.tree === true, incidents: data.incidents === true, export: data.export === true });
            setRevision((value) => value + 1);
          }
        }).catch(() => undefined).finally(() => { if (version === current) setLoading(false); });
    }
    const stop = () => { version++; controller?.abort(); revoke(); };
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener(PUSH_LOGOUT_EVENT, stop);
    return () => { stop(); window.removeEventListener("focus", refresh); window.removeEventListener(PUSH_LOGOUT_EVENT, stop); };
  }, [revoke]);
  return { permissions, loading, revoke, revision };
}
