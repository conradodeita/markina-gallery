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
  function choosePreset(value: string) {
    const [nextPreference, nextFinish] = value.split(":") as [ThemePreference, AppearanceFinish];
    applyTheme(nextPreference);
    applyAppearanceFinish(nextFinish);
    try {
      localStorage.setItem(THEME_KEY, nextPreference);
      localStorage.setItem(APPEARANCE_FINISH_KEY, nextFinish);
    } catch { /* O preset continua aplicado durante a página. */ }
    window.dispatchEvent(new Event(THEME_EVENT));
  }
  const finishes: { value: AppearanceFinish; label: string }[] = [
    { value: "neutral", label: "Neutro" },
    { value: "silver", label: "Cinza metálico" },
    { value: "blue", label: "Azul metálico" },
    { value: "wine", label: "Vinho metálico" },
  ];
  const modes: { value: ThemePreference; label: string }[] = [
    { value: "system", label: "Sistema" },
    { value: "light", label: "Claro" },
    { value: "dark", label: "Escuro" },
  ];
  return <label className="theme-control"><span aria-hidden="true">◐</span><span>Aparência</span>
    <select aria-label="Aparência" value={`${preference}:${finish}`} onChange={(event) => choosePreset(event.target.value)}>
      {finishes.flatMap((appearanceFinish) => modes.map((mode) => (
        <option key={`${mode.value}:${appearanceFinish.value}`} value={`${mode.value}:${appearanceFinish.value}`}>
          {`${mode.label} · ${appearanceFinish.label}`}
        </option>
      )))}
    </select>
  </label>;
}
