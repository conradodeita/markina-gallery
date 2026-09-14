"use client";

import { useSyncExternalStore } from "react";
import { applyTheme, readTheme, THEME_EVENT, THEME_KEY, type ThemePreference } from "./theme";

function subscribe(onChange: () => void) {
  const system = matchMedia("(prefers-color-scheme: dark)");
  const update = () => { applyTheme(readTheme()); onChange(); };
  const storage = (event: StorageEvent) => {
    if (event.key !== THEME_KEY && event.key !== null) return;
    delete document.documentElement.dataset.themePreference;
    update();
  };
  update();
  system.addEventListener("change", update);
  window.addEventListener(THEME_EVENT, update);
  window.addEventListener("storage", storage);
  return () => {
    system.removeEventListener("change", update);
    window.removeEventListener(THEME_EVENT, update);
    window.removeEventListener("storage", storage);
  };
}

export function ThemeControl() {
  const preference = useSyncExternalStore(subscribe, readTheme, () => "system");
  function choose(value: ThemePreference) {
    applyTheme(value);
    try { localStorage.setItem(THEME_KEY, value); } catch { /* Preferência da página. */ }
    window.dispatchEvent(new Event(THEME_EVENT));
  }
  return <label className="theme-control"><span aria-hidden="true">◐</span><span>Aparência</span>
    <select aria-label="Aparência" value={preference} onChange={(event) => choose(event.target.value as ThemePreference)}>
      <option value="system">Sistema</option><option value="light">Claro</option><option value="dark">Escuro</option>
    </select>
  </label>;
}
