import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SecurityPanel from "./security-panel";

afterEach(() => vi.restoreAllMocks());

const summary = {
  email_masked: "ad***@example.test",
  whatsapp_status: "ready",
  email_channel: { status: "ready", mode: "smtp" },
  recovery_codes_available: 0,
};

describe("segurança da conta administrativa", () => {
  it("troca senha com reautenticação e OTP e informa o encerramento das sessões", async () => {
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(new Response(JSON.stringify(summary), { status: 200 }));
      if (path.endsWith("/password/challenge")) return Promise.resolve(new Response(JSON.stringify({ challenge_id: "challenge-password", message: "Código enviado." }), { status: 202 }));
      if (path.endsWith("/password/confirm")) return Promise.resolve(new Response(JSON.stringify({ message: "Senha alterada. Entre novamente." }), { status: 200 }));
      return Promise.resolve(new Response(null, { status: 500 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SecurityPanel />);

    expect(await screen.findByText("ad***@example.test")).toBeTruthy();
    const section = screen.getByRole("region", { name: "Trocar senha" });
    fireEvent.change(within(section).getByLabelText("Senha atual"), { target: { value: "senha-atual" } });
    fireEvent.change(within(section).getByLabelText("Nova senha"), { target: { value: "Nova-senha-segura-2026!" } });
    fireEvent.change(within(section).getByLabelText("Confirme a nova senha"), { target: { value: "Nova-senha-segura-2026!" } });
    fireEvent.click(within(section).getByRole("button", { name: "Enviar código de confirmação" }));

    const code = await within(section).findByLabelText("Código enviado ao WhatsApp");
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.click(within(section).getByRole("button", { name: "Confirmar nova senha" }));

    expect(await screen.findByText("Todas as sessões foram encerradas por segurança.")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/admin/security/password/confirm", expect.objectContaining({ body: JSON.stringify({ challenge_id: "challenge-password", code: "123456", new_password: "Nova-senha-segura-2026!" }) }));
  });

  it("mantém o e-mail atual até a confirmação do link e permite cancelar", async () => {
    const unavailable = { ...summary, whatsapp_status: "disconnected", email_channel: { status: "sandbox", mode: "sandbox" } };
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(new Response(JSON.stringify(unavailable), { status: 200 }));
      if (path.endsWith("/email/challenge")) return Promise.resolve(new Response(JSON.stringify({ challenge_id: "challenge-email", message: "Código enviado." }), { status: 202 }));
      if (path.endsWith("/email/verify-otp")) return Promise.resolve(new Response(JSON.stringify({ message: "Enviamos a confirmação para o novo endereço." }), { status: 202 }));
      return Promise.resolve(new Response(null, { status: 500 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SecurityPanel />);

    expect(await screen.findByText(/WhatsApp administrativo antes/i)).toBeTruthy();
    expect(screen.getByText(/e-mail transacional ainda não está pronto/i)).toBeTruthy();
    const section = screen.getByRole("region", { name: "Trocar e-mail" });
    fireEvent.change(within(section).getByLabelText("Novo e-mail"), { target: { value: "novo@example.test" } });
    fireEvent.change(within(section).getByLabelText("Senha atual"), { target: { value: "senha-atual" } });
    fireEvent.click(within(section).getByRole("button", { name: "Validar alteração pelo WhatsApp" }));
    const code = await within(section).findByLabelText("Código enviado ao WhatsApp");
    fireEvent.change(code, { target: { value: "654321" } });
    fireEvent.click(within(section).getByRole("button", { name: "Enviar confirmação por e-mail" }));

    expect(await screen.findByText(/e-mail atual continuará válido/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Fechar" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Trocar e-mail" })).toBeTruthy());
  });

  it("mostra códigos de recuperação uma vez e não os recupera do storage", async () => {
    const codes = ["ABCD_1234-efgh_5678-IJKL", "MNOP_1234-qrst_5678-UVWX"];
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(new Response(JSON.stringify(summary), { status: 200 }));
      if (path.endsWith("/totp/recovery-codes")) return Promise.resolve(new Response(JSON.stringify({ codes, message: "Guarde agora." }), { status: 200 }));
      return Promise.resolve(new Response(null, { status: 500 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:recovery-codes");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const downloadClick = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<SecurityPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Gerar ou regenerar códigos" }));
    const recovery = screen.getByRole("region", { name: "Recuperação do autenticador" });
    fireEvent.change(within(recovery).getByLabelText("Senha atual"), { target: { value: "senha-atual" } });
    fireEvent.change(within(recovery).getByLabelText("Código TOTP atual"), { target: { value: "123456" } });
    fireEvent.click(within(recovery).getByRole("button", { name: "Gerar 10 códigos" }));

    expect(await screen.findByText(codes[0])).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/admin/security/totp/recovery-codes", expect.objectContaining({
      body: JSON.stringify({ current_password: "senha-atual", second_factor_code: "123456" }),
    }));
    fireEvent.click(screen.getByRole("button", { name: "Baixar lote uma vez" }));
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(downloadClick).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:recovery-codes");
    expect(screen.getByRole("button", { name: "Lote baixado" }).hasAttribute("disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Fechar e limpar da tela" }));
    expect(screen.queryByText(codes[0])).toBeNull();
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);
  });

  it("libera o formulário se a rede falhar ao emitir códigos", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(new Response(JSON.stringify(summary), { status: 200 }));
      return Promise.reject(new Error("synthetic network failure"));
    }));
    render(<SecurityPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Gerar ou regenerar códigos" }));
    const recovery = screen.getByRole("region", { name: "Recuperação do autenticador" });
    fireEvent.change(within(recovery).getByLabelText("Senha atual"), { target: { value: "senha-atual" } });
    fireEvent.change(within(recovery).getByLabelText("Código TOTP atual"), { target: { value: "123456" } });
    fireEvent.click(within(recovery).getByRole("button", { name: "Gerar 10 códigos" }));

    expect(await screen.findByText("Não foi possível gerar os códigos de recuperação.")).toBeTruthy();
    expect(within(recovery).getByRole("button", { name: "Gerar 10 códigos" }).hasAttribute("disabled")).toBe(false);
  });
});
