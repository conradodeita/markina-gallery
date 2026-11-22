"use client";

import { useEffect, useState } from "react";

type FolderDeadline = { access_expires_at?: string | null };
const MAX_TIMEOUT_MS = 2_147_483_647;

export function useFolderAccessClock(folders: readonly FolderDeadline[], enabled = true): number {
  const [observedAt, setObservedAt] = useState(() => Date.now());

  useEffect(() => {
    if (!enabled) return;

    const refresh = () => {
      const now = Date.now();
      setObservedAt((previous) => {
        const crossedDeadline = folders.some((folder) => {
          if (!folder.access_expires_at) return false;
          const deadline = Date.parse(folder.access_expires_at);
          return Number.isFinite(deadline) && previous < deadline && deadline <= now;
        });
        return crossedDeadline ? now : previous;
      });
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };

    refresh();
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [enabled, folders]);

  useEffect(() => {
    if (!enabled) return;

    const now = Date.now();
    const nextDeadline = folders.reduce<number | null>((nearest, folder) => {
      if (!folder.access_expires_at) return nearest;
      const deadline = Date.parse(folder.access_expires_at);
      if (!Number.isFinite(deadline) || deadline <= now) return nearest;
      return nearest === null || deadline < nearest ? deadline : nearest;
    }, null);

    if (nextDeadline === null) return;
    const delay = Math.min(Math.max(0, nextDeadline - now) + 1, MAX_TIMEOUT_MS);
    const timeout = window.setTimeout(() => setObservedAt(Date.now()), delay);
    return () => window.clearTimeout(timeout);
  }, [enabled, folders, observedAt]);

  return observedAt;
}
