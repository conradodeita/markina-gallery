import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminAccountAction } from "./account-action";

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("ações públicas da conta administrativa", () => {
  it("retira o token de redefinição do fragmento e o envia somente no POST", async () => {
    window.history.replaceState({}, "", "/admin/reset-password#token=segredo-opaco");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Senha redefinida. Entre novamente." }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="password" />);

    await screen.findByLabelText("Nova senha");
    expect(window.location.hash).toBe("");
    expect(window.location.href).not.toContain("segredo-opaco");
    fireEvent.change(screen.getByLabelText("Nova senha"), { target: { value: "Senha-muito-forte-2026!" } });
    fireEvent.change(screen.getByLabelText("Confirme a nova senha"), { target: { value: "Senha-muito-forte-2026!" } });
    fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/admin/recovery/reset",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ token: "segredo-opaco", new_password: "Senha-muito-forte-2026!" }) }),
    ));
    expect(await screen.findByRole("link", { name: "Ir para o login" })).toBeTruthy();
  });

  it("não executa confirmação de e-mail por GET e exige ação explícita", async () => {
    window.history.replaceState({}, "", "/admin/verify-email#token=confirmacao-opaca");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "E-mail confirmado. Entre novamente." }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="email" />);

    const button = await screen.findByRole("button", { name: "Confirmar novo e-mail" });
    expect(window.location.hash).toBe("");
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(button);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/admin/email/confirm",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ token: "confirmacao-opaca" }) }),
    ));
  });

  it("informa link inválido sem realizar requisição", async () => {
    window.history.replaceState({}, "", "/admin/reset-password");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="password" />);

    expect(await screen.findByText(/link está incompleto/i)).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
