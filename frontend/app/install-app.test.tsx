import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InstallApp } from "./install-app";

beforeEach(() => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches:false, addEventListener:vi.fn(), removeEventListener:vi.fn() })));
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("Chrome Desktop");
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("aguarda evento de instalação e consome prompt apenas uma vez", async () => {
  render(<InstallApp />);
  expect(screen.queryByRole("button")).toBeNull();
  const prompt = vi.fn().mockResolvedValue(undefined);
  const event = Object.assign(new Event("beforeinstallprompt", { cancelable:true }), {
    prompt, userChoice:Promise.resolve({ outcome:"dismissed" }),
  });
  act(() => { window.dispatchEvent(event); });
  expect(event.defaultPrevented).toBe(true);
  fireEvent.click(screen.getByRole("button", { name:"Instalar aplicativo" }));
  await waitFor(() => expect(screen.queryByRole("button")).toBeNull());
  expect(prompt).toHaveBeenCalledTimes(1);
});

it("oculta a instalação no modo standalone e ao receber appinstalled", () => {
  const { unmount } = render(<InstallApp />);
  act(() => { window.dispatchEvent(Object.assign(new Event("beforeinstallprompt"), { prompt:vi.fn() })); });
  expect(screen.getByRole("button", { name:"Instalar aplicativo" })).toBeTruthy();
  act(() => { window.dispatchEvent(new Event("appinstalled")); });
  expect(screen.queryByRole("button")).toBeNull();
  unmount();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches:true, addEventListener:vi.fn(), removeEventListener:vi.fn() })));
  render(<InstallApp />);
  expect(screen.queryByRole("button")).toBeNull();
});

it("oferece instruções manuais no iPhone sem abrir popup automaticamente", () => {
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue("iPhone Safari");
  const show = vi.fn();
  vi.stubGlobal("HTMLDialogElement", window.HTMLDialogElement);
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", { value:show, configurable:true });
  render(<InstallApp />);
  expect(show).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name:"Instalar aplicativo" }));
  expect(show).toHaveBeenCalledOnce();
  expect(screen.getByText(/Adicionar à Tela de Início/)).toBeTruthy();
});
