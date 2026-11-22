import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";

import { AdminAccountAction } from "./account-action";

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("ações públicas da conta administrativa", () => {
  it("prepara recuperação assistida sem exigir o fator perdido ou anunciar acesso liberado", async () => {
    window.history.replaceState({}, "", "/photographer-access-recovery#token=synthetic-link");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "E-mail confirmado. Aguarde o proprietário concluir o atendimento." })));
    vi.stubGlobal("fetch", fetchMock);
    render(<StrictMode><AdminAccountAction kind="assisted" /></StrictMode>);
    fireEvent.change(await screen.findByLabelText("Nova senha"), { target: { value: "SyntheticReplacement!20261110" } });
    fireEvent.change(screen.getByLabelText("Confirme a nova senha"), { target: { value: "SyntheticReplacement!20261110" } });
    expect(screen.queryByLabelText("Código do autenticador ou de recuperação")).toBeNull();
    expect(window.location.hash).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Confirmar e aguardar proprietário" }));
    await screen.findByText(/só entrarão em vigor quando o proprietário/);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/photographer-access-recovery/confirm", expect.objectContaining({
      method: "POST", body: JSON.stringify({ token: "synthetic-link", new_password: "SyntheticReplacement!20261110" }),
    }));
    expect(screen.queryByText(/Suas sessões anteriores foram encerradas/)).toBeNull();
  });

  it("permite tentar novamente após falha de conexão sem perder o contexto", async () => {
    window.history.replaceState({}, "", "/photographer-access-recovery#token=synthetic-link");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<AdminAccountAction kind="assisted" />);
    fireEvent.change(await screen.findByLabelText("Nova senha"), { target: { value: "SyntheticReplacement!20261110" } });
    fireEvent.change(screen.getByLabelText("Confirme a nova senha"), { target: { value: "SyntheticReplacement!20261110" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar e aguardar proprietário" }));
    await screen.findByText(/Verifique sua conexão/);
    expect(screen.getByRole("button", { name: "Confirmar e aguardar proprietário" }).hasAttribute("disabled")).toBe(false);
  });
  it("retira o token de redefinição do fragmento e o envia somente no POST", async () => {
    window.history.replaceState({}, "", "/admin/reset-password#token=segredo-opaco");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Senha redefinida. Entre novamente." }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="password" />);

    await screen.findByLabelText("Nova senha");
    expect(screen.getByText(/após validar o código do WhatsApp, deixe o campo vazio/)).toBeTruthy();
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

  it("envia o segundo fator junto ao link para conta criada pelo website", async () => {
    window.history.replaceState({}, "", "/admin/reset-password#token=link-de-uso-unico");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "Senha redefinida." }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="password" />);
    fireEvent.change(await screen.findByLabelText("Nova senha"), { target: { value: "Senha-muito-forte-2026!" } });
    fireEvent.change(screen.getByLabelText("Confirme a nova senha"), { target: { value: "Senha-muito-forte-2026!" } });
    fireEvent.change(screen.getByLabelText("Código do autenticador ou de recuperação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Redefinir senha" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/admin/recovery/reset",
      expect.objectContaining({ body: JSON.stringify({ token: "link-de-uso-unico", new_password: "Senha-muito-forte-2026!", second_factor_code: "123456" }) }),
    ));
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

  it.each(["network", "http"])("preserva a confirmação de e-mail após falha %s e só repete por ação explícita", async (failure) => {
    window.history.replaceState({}, "", "/admin/verify-email#token=synthetic-email-token");
    const fetchMock = vi.fn();
    if (failure === "network") fetchMock.mockRejectedValueOnce(new Error("offline"));
    else fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Serviço temporariamente indisponível." }), { status: 503 }));
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ message: "E-mail confirmado. Entre novamente." })));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminAccountAction kind="email" />);
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar novo e-mail" }));
    await screen.findByText(failure === "network" ? /Verifique sua conexão/ : "Serviço temporariamente indisponível.");
    const retry = screen.getByRole("button", { name: "Confirmar novo e-mail" });
    expect(retry.hasAttribute("disabled")).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe("");
    fireEvent.click(retry);
    await screen.findByRole("link", { name: "Ir para o login" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    for (const call of fetchMock.mock.calls) {
      expect(call[0]).toBe("/api/auth/admin/email/confirm");
      expect(JSON.parse(String(call[1]?.body))).toEqual({ token: "synthetic-email-token" });
    }
  });
});
