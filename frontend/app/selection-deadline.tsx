"use client";

import { useEffect, useRef, useState } from "react";

export function selectionTimeRemaining(expiresAt: string, currentTime: number): string {
  const remaining = new Date(expiresAt).getTime() - currentTime;
  if (remaining <= 0) return "Prazo de seleção expirado";
  const minutes = Math.floor(remaining / 60000);
  if (!minutes) return "Menos de 1 minuto para selecionar";
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h para selecionar`;
  if (hours) return `${hours}h ${minutes % 60}min para selecionar`;
  return `${minutes}min para selecionar`;
}

export function SelectionDeadline({ expiresAt, onRevalidate }: { expiresAt?: string | null; onRevalidate?: () => void }) {
  const [currentTime, setCurrentTime] = useState<number | null>(null);
  const callback = useRef(onRevalidate);
  useEffect(() => { callback.current = onRevalidate; }, [onRevalidate]);
  useEffect(() => {
    if (!expiresAt || !Number.isFinite(Date.parse(expiresAt))) return;
    let active = true;
    let expired = Date.now() >= Date.parse(expiresAt);
    const update = () => {
      if (!active) return false;
      const now = Date.now();
      setCurrentTime(now);
      const nextExpired = now >= Date.parse(expiresAt);
      const crossedDeadline = nextExpired && !expired;
      if (crossedDeadline) callback.current?.();
      expired = nextExpired;
      return crossedDeadline;
    };
    queueMicrotask(update);
    const timer = window.setInterval(update, 60000);
    const focus = () => { if (!update()) callback.current?.(); };
    const visible = () => { if (document.visibilityState === "visible") focus(); };
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", visible);
    return () => { active = false; window.clearInterval(timer); window.removeEventListener("focus", focus); document.removeEventListener("visibilitychange", visible); };
  }, [expiresAt]);
  if (!expiresAt || !Number.isFinite(Date.parse(expiresAt))) return null;
  const expired = currentTime !== null && currentTime >= Date.parse(expiresAt);
  return <div className={`selection-deadline${expired ? " selection-deadline--expired" : ""}`} aria-label="Prazo para novas seleções">
    <strong>{currentTime === null ? "Prazo de seleção" : selectionTimeRemaining(expiresAt, currentTime)}</strong>
    <time dateTime={expiresAt}>{new Date(expiresAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</time>
  </div>;
}
