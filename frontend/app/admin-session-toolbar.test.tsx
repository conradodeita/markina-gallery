import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const route = { pathname: "/admin/galleries" };

vi.mock("next/navigation", () => ({ usePathname: () => route.pathname }));
vi.mock("./push-control", () => ({
  PushControl: () => <button type="button">Ativar notificações</button>,
  LogoutButton: () => <button type="button">Sair</button>,
}));

import { AdminSessionToolbar } from "./admin-session-toolbar";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  route.pathname = "/admin/galleries";
});

it("mostra os controles do fotógrafo agrupados fora da navegação após validar a identidade", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ role: "admin", identity: "fotografo@example.com" }),
  }));

  render(<><AdminSessionToolbar /><nav aria-label="Navegação administrativa">Galerias</nav></>);

  const controls = await screen.findByRole("group", { name: "Controles da sessão do fotógrafo" });
  expect(screen.getByLabelText("Logado como: fotografo@example.com")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Ativar notificações" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Sair" })).toBeTruthy();
  expect(controls.contains(screen.getByRole("navigation", { name: "Navegação administrativa" }))).toBe(false);
});

it("não exibe controles administrativos em rotas de cliente ou de entrada", () => {
  route.pathname = "/library";
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  const { rerender } = render(<AdminSessionToolbar />);
  expect(screen.queryByRole("group")).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();

  route.pathname = "/admin/verify-email";
  rerender(<AdminSessionToolbar />);
  expect(screen.queryByRole("group")).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});

it("não exibe ações se a identidade validada não for de fotógrafo", async () => {
  route.pathname = "/admin";
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ role: "client", identity: "+5511999999999" }),
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<AdminSessionToolbar />);

  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(screen.queryByText("Logado como:")).toBeNull();
  expect(screen.queryByRole("button", { name: "Sair" })).toBeNull();
});
