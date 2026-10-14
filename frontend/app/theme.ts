export type ThemePreference = "light" | "dark" | "system";
export type AppearanceFinish = "neutral" | "silver" | "blue" | "wine";
export const THEME_KEY = "pick-your-pic-theme";
export const APPEARANCE_FINISH_KEY = "pick-your-pic-appearance-finish";
export const THEME_EVENT = "pick-theme-change";

export function readTheme(): ThemePreference {
  const active = document.documentElement.dataset.themePreference;
  if (active === "light" || active === "dark" || active === "system") return active;
  try {
    const value = localStorage.getItem(THEME_KEY);
    if (value === "light" || value === "dark") return value;
  } catch { /* A escolha continua funcionando nesta página sem armazenamento. */ }
  return "system";
}

export function applyTheme(preference: ThemePreference) {
  const dark = preference === "dark" || (preference === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.dataset.themePreference = preference;
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

export function readAppearanceFinish(): AppearanceFinish {
  const active = document.documentElement.dataset.appearanceFinish;
  if (active === "neutral" || active === "silver" || active === "blue" || active === "wine") return active;
  try {
    const value = localStorage.getItem(APPEARANCE_FINISH_KEY);
    if (value === "silver" || value === "blue" || value === "wine") return value;
  } catch { /* O acabamento continua selecionável nesta página sem armazenamento. */ }
  return "neutral";
}

export function applyAppearanceFinish(finish: AppearanceFinish) {
  document.documentElement.dataset.appearanceFinish = finish;
}

// Executado antes da pintura; não lê conta, sessão ou dados pessoais.
export const themeBootstrap = `(function(){var p='system';var a='neutral';try{var v=localStorage.getItem('${THEME_KEY}');if(v==='light'||v==='dark')p=v;var f=localStorage.getItem('${APPEARANCE_FINISH_KEY}');if(f==='silver'||f==='blue'||f==='wine')a=f}catch(e){}var d=p==='dark'||(p==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);var r=document.documentElement;r.dataset.theme=d?'dark':'light';r.dataset.themePreference=p;r.dataset.appearanceFinish=a;r.style.colorScheme=d?'dark':'light'})()`;
