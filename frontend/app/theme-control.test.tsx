import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ThemeControl } from "./theme-control";
import { InstallApp } from "./install-app";
import { THEME_KEY, themeBootstrap } from "./theme";

let dark = false;
let listeners: Set<() => void>;
beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.themePreference;
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
  expect((screen.getByLabelText("Aparência") as HTMLSelectElement).value).toBe("dark");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"light" } });
  expect(localStorage.getItem(THEME_KEY)).toBe("light");
  unmount(); render(<ThemeControl />);
  expect(document.documentElement.dataset.theme).toBe("light");
});

it("acompanha o sistema somente quando Sistema está selecionado", () => {
  render(<ThemeControl />);
  act(() => { dark = true; listeners.forEach((listener) => listener()); });
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"light" } });
  act(() => listeners.forEach((listener) => listener()));
  expect(document.documentElement.dataset.theme).toBe("light");
  fireEvent.change(screen.getByLabelText("Aparência"), { target: { value:"system" } });
  expect(document.documentElement.dataset.theme).toBe("dark");
});

it("funciona sem armazenamento e com PWA instalado", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  window.eval(themeBootstrap);
  render(<><ThemeControl /><InstallApp /></>);
  fireEvent.change(screen.getByLabelText("Aparência"), { target:{ value:"dark" } });
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
