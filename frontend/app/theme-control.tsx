"use client";

import { useSyncExternalStore } from "react";
import { applyAppearanceFinish, applyTheme, readAppearanceFinish, readTheme, APPEARANCE_FINISH_KEY, THEME_EVENT, THEME_KEY, type AppearanceFinish, type ThemePreference } from "./theme";

function subscribe(onChange: () => void) {
  const system = matchMedia("(prefers-color-scheme: dark)");
  const update = () => { applyTheme(readTheme()); applyAppearanceFinish(readAppearanceFinish()); onChange(); };
  const storage = (event: StorageEvent) => {
    if (event.key !== THEME_KEY && event.key !== APPEARANCE_FINISH_KEY && event.key !== null) return;
    if (event.key === THEME_KEY || event.key === null) delete document.documentElement.dataset.themePreference;
    if (event.key === APPEARANCE_FINISH_KEY || event.key === null) delete document.documentElement.dataset.appearanceFinish;
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
  const finish = useSyncExternalStore(subscribe, readAppearanceFinish, () => "neutral");
  function choose(value: ThemePreference) {
    applyTheme(value);
    try { localStorage.setItem(THEME_KEY, value); } catch { /* Preferência da página. */ }
    window.dispatchEvent(new Event(THEME_EVENT));
  }
  function chooseFinish(value: AppearanceFinish) {
    applyAppearanceFinish(value);
    try { localStorage.setItem(APPEARANCE_FINISH_KEY, value); } catch { /* Acabamento disponível durante a página. */ }
    window.dispatchEvent(new Event(THEME_EVENT));
  }
  return <>
    <label className="theme-control"><span aria-hidden="true">◐</span><span>Aparência</span>
      <select aria-label="Aparência" value={preference} onChange={(event) => choose(event.target.value as ThemePreference)}>
        <option value="system">Sistema</option><option value="light">Claro</option><option value="dark">Escuro</option>
      </select>
    </label>
    <label className="theme-control"><span>Acabamento</span>
      <select aria-label="Acabamento" value={finish} onChange={(event) => chooseFinish(event.target.value as AppearanceFinish)}>
        <option value="neutral">Neutro</option><option value="silver">Cinza metálico</option><option value="blue">Azul metálico</option><option value="wine">Vinho metálico</option>
      </select>
    </label>
  </>;
}
