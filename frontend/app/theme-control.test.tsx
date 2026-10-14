import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ThemeControl } from "./theme-control";
import { InstallApp } from "./install-app";
import { APPEARANCE_FINISH_KEY, THEME_KEY, themeBootstrap } from "./theme";

let dark = false;
let listeners: Set<() => void>;
beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.themePreference;
  delete document.documentElement.dataset.appearanceFinish;
  dark = false;
  listeners = new Set();
  vi.stubGlobal("matchMedia", (query: string) => ({
    get matches() { return query.includes("color-scheme") ? dark : false; },
    addEventListener: (_: string, listener: () => void) => listeners.add(listener),
    removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
  }));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("aplica preferência salva antes da pintura e após remontagem", () => {
  localStorage.setItem(THEME_KEY, "dark");
  window.eval(themeBootstrap);
  expect(document.documentElement.dataset.theme).toBe("dark");
  const { unmount } = render(<ThemeControl />);
  expect((screen.getByLabelText("Aparência") as HTMLSelectElement).value).toBe("dark:neutral");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"light:neutral" } });
  expect(localStorage.getItem(THEME_KEY)).toBe("light");
  unmount(); render(<ThemeControl />);
  expect(document.documentElement.dataset.theme).toBe("light");
});

it("acompanha o sistema somente quando Sistema está selecionado", () => {
  render(<ThemeControl />);
  act(() => { dark = true; listeners.forEach((listener) => listener()); });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"light:neutral" } });
  act(() => listeners.forEach((listener) => listener()));
  expect(document.documentElement.dataset.theme).toBe("light");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"system:neutral" } });
  expect(document.documentElement.dataset.theme).toBe("dark");
});

it("funciona sem armazenamento e com PWA instalado", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  window.eval(themeBootstrap);
  render(<><ThemeControl /><InstallApp /></>);
  fireEvent.change(screen.getByLabelText("Aparência"), { target:{ value:"dark:neutral" } });
  expect(document.documentElement.dataset.theme).toBe("dark");
  act(() => window.dispatchEvent(new Event("appinstalled")));
  expect(screen.getByLabelText("Aparência")).toBeTruthy();
});

it("sincroniza remoção e mudança da preferência em outra aba", () => {
  render(<ThemeControl />);
  act(() => { localStorage.setItem(THEME_KEY, "dark"); window.dispatchEvent(new StorageEvent("storage", {key:THEME_KEY})); });
  expect(document.documentElement.dataset.theme).toBe("dark");
  act(() => { localStorage.removeItem(THEME_KEY); window.dispatchEvent(new StorageEvent("storage", {key:THEME_KEY})); });
  expect(document.documentElement.dataset.theme).toBe("light");
});

it("oferece somente Aparência com presets combinados e persiste modo e acabamento", () => {
  localStorage.setItem(THEME_KEY, "dark");
  localStorage.setItem(APPEARANCE_FINISH_KEY, "blue");
  window.eval(themeBootstrap);
  render(<ThemeControl />);
  const appearance = screen.getByLabelText("Aparência") as HTMLSelectElement;
  expect(screen.queryByLabelText("Acabamento")).toBeNull();
  expect(appearance.value).toBe("dark:blue");
  expect(appearance.options).toHaveLength(12);
  expect(appearance.selectedOptions[0].textContent).toBe("Escuro · Azul metálico");
  fireEvent.change(appearance, { target: { value: "dark:wine" } });
  expect(localStorage.getItem(APPEARANCE_FINISH_KEY)).toBe("wine");
  expect(localStorage.getItem(THEME_KEY)).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(document.documentElement.dataset.appearanceFinish).toBe("wine");
});

it("usa acabamento neutro para valores inválidos e tolera armazenamento indisponível", () => {
  localStorage.setItem(APPEARANCE_FINISH_KEY, "invalid");
  window.eval(themeBootstrap);
  expect(document.documentElement.dataset.appearanceFinish).toBe("neutral");
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  render(<ThemeControl />);
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value: "light:silver" } });
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(document.documentElement.dataset.appearanceFinish).toBe("silver");
});

it("sincroniza acabamento entre abas", () => {
  render(<ThemeControl />);
  act(() => { localStorage.setItem(APPEARANCE_FINISH_KEY, "wine"); window.dispatchEvent(new StorageEvent("storage", { key: APPEARANCE_FINISH_KEY })); });
  expect((screen.getByLabelText("Aparência") as HTMLSelectElement).value).toBe("system:wine");
  expect(document.documentElement.dataset.appearanceFinish).toBe("wine");
});
