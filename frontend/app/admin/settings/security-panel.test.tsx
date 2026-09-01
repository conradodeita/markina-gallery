import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SecurityPanel from "./security-panel";

afterEach(() => vi.restoreAllMocks());

const summary = {
  email_masked: "ad***@example.test",
  whatsapp_status: "ready",
  email_channel: { status: "ready", mode: "smtp" },
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
});
