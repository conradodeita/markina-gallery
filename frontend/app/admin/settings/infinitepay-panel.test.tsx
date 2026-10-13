import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import InfinitePayPanel from "./infinitepay-panel";

const empty = { status: "unconfigured", handle: null, version: 0, card_enabled: false, checkout_available: false };
const pending = { status: "pending", handle: "synthetic_a", version: 1, card_enabled: false, checkout_available: false };
const active = { status: "active", handle: "synthetic_a", version: 1, card_enabled: true, checkout_available: true };
const challenge = { challenge_id: "synthetic", expires_at: new Date(Date.now() + 600000).toISOString(), proposal: { handle: "synthetic_a", version: 0, checkout_ready: true, card_enabled: true } };
const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function begin() {
  fireEvent.click(await screen.findByRole("button", { name: "Preparar InfinitePay" }));
  fireEvent.change(screen.getByLabelText("InfiniteTag"), { target: { value: "$synthetic_a" } });
  fireEvent.click(screen.getByLabelText(/Conferi que esta InfiniteTag/));
  fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
}

describe("Preparação InfinitePay individual", () => {
  it("usa teclado, vincula a autodeclaração ao desafio e não pede API Key", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body))).toEqual({ current_password: "synthetic-password", expected_version: 0, configuration: { handle: "$synthetic_a" }, checkout_ready: true, card_enabled: true });
        return response(challenge);
      }
      if (path.endsWith("/confirm")) {
        expect(JSON.parse(String(init?.body))).toEqual({ challenge_id: "synthetic", code: "123456" });
        return response({ ...pending, status: "active", card_enabled: true, checkout_available: true });
      }
      return response(empty);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    expect(await screen.findByText(/deixe cartão de crédito ligado e PIX desligado/)).toBeTruthy();
    expect(screen.getByText(/crie um link de teste sem concluir a compra/)).toBeTruthy();
    expect(screen.getByText(/Essa preferência também se aplica aos links de checkout criados pela API/)).toBeTruthy();
    const user = userEvent.setup();
    (await screen.findByRole("button", { name: "Preparar InfinitePay" })).focus();
    await user.keyboard("{Enter}");
    expect(document.activeElement).toBe(screen.getByLabelText("InfiniteTag"));
    await user.type(screen.getByLabelText("InfiniteTag"), "$synthetic_a");
    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/Conferi que esta InfiniteTag/));
    await user.keyboard(" ");
    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/Habilitar pagamento por cartão de crédito/));
    await user.keyboard(" ");
    await user.tab();
    expect(document.activeElement).toBe(screen.getByLabelText("Senha atual do Pick-your-Pic"));
    await user.keyboard("synthetic-password{Enter}");
    const otp = await screen.findByLabelText("Código de confirmação InfinitePay");
    expect(document.activeElement).toBe(otp);
    expect(screen.getByText("synthetic_a")).toBeTruthy();
    expect(screen.queryByLabelText(/API Key/i)).toBeNull();
    await user.keyboard("123456{Enter}");
    expect(await screen.findByText(/Cartão habilitado para novas compras/)).toBeTruthy();
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("button", { name: "Alterar InfiniteTag ou disponibilidade do cartão" })));
    expect(fetchMock.mock.calls.every(([path]) => path.startsWith("/api/admin/settings/infinitepay"))).toBe(true);
  });

  it("mantém o cartão indisponível se o fotógrafo não atestou link somente-cartão", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body)).checkout_ready).toBe(false);
        return response({ ...challenge, proposal: { ...challenge.proposal, checkout_ready: false } });
      }
      return response(empty);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Preparar InfinitePay" }));
    fireEvent.change(screen.getByLabelText("InfiniteTag"), { target: { value: "$synthetic_a" } });
    fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    await screen.findByText("Use o código enviado ao WhatsApp administrativo do Pick-your-Pic. Ele confirma somente esta alteração e é válido por 10 minutos.");
    expect(screen.getByText("Cartão indisponível")).toBeTruthy();
  });

  it("desabilita apenas novos checkouts de cartão após a confirmação sensível", async () => {
    const disablingChallenge = { ...challenge, proposal: { handle: "synthetic_a", version: 1,
      checkout_ready: true, card_enabled: false } };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body))).toEqual({ current_password: "synthetic-password",
          expected_version: 1, configuration: { handle: "synthetic_a" }, checkout_ready: true, card_enabled: false });
        return response(disablingChallenge);
      }
      if (path.endsWith("/confirm")) return response({ ...active, card_enabled: false, checkout_available: false });
      return response(active);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Alterar InfiniteTag ou disponibilidade do cartão" }));
    const cardToggle = screen.getByLabelText(/Habilitar pagamento por cartão de crédito/);
    expect(cardToggle).toHaveProperty("checked", true);
    fireEvent.click(cardToggle);
    fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    await screen.findByText(/Esta alteração manterá cartão desabilitado para novos pedidos/);
    fireEvent.change(screen.getByLabelText("Código de confirmação InfinitePay"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar configuração InfinitePay" }));
    expect(await screen.findByText(/InfinitePay está configurada, mas cartão está desabilitado/)).toBeTruthy();
    expect(screen.getByText("Cartão desabilitado para novos pedidos")).toBeTruthy();
  });

  it("trata concorrência recarregando versão, sem reaplicar proposta", async () => {
    let reads = 0;
    const fetchMock = vi.fn((path: string) => path.endsWith("/challenge")
      ? response({ detail: "A configuração mudou em outra sessão." }, 409)
      : response(reads++ ? pending : empty));
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await begin();
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "A configuração mudou em outra sessão.");
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => !path.endsWith("/challenge"))).toHaveLength(2));
    expect(fetchMock.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(false);
    expect(screen.getByLabelText("Senha atual do Pick-your-Pic")).toHaveProperty("value", "");
  });

  it("recusa expiração local, permite cancelar sem mudar recebedor", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/challenge")
      ? response({ ...challenge, expires_at: new Date(0).toISOString() }) : response(empty));
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await begin();
    fireEvent.change(await screen.findByLabelText("Código de confirmação InfinitePay"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar configuração InfinitePay" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "O código expirou. Solicite outro usando sua senha do Pick-your-Pic.");
    expect(fetchMock.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar alteração InfinitePay" }));
    expect(screen.getByText(/Alteração cancelada/)).toBeTruthy();
  });

  it("reenvia somente o desafio e mantém a proposta", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) return response(challenge);
      if (path.endsWith("/resend")) {
        expect(JSON.parse(String(init?.body))).toEqual({ challenge_id: "synthetic" });
        return response({ challenge_id: "synthetic", expires_at: challenge.expires_at });
      }
      return response(empty);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await begin();
    fireEvent.click(await screen.findByRole("button", { name: "Reenviar código InfinitePay" }));
    expect(await screen.findByText(/Novo código enviado/)).toBeTruthy();
    expect(screen.getByText("synthetic_a")).toBeTruthy();
  });

  it("remoção envia configuração nula e exige confirmação", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body)).configuration).toBeNull();
        return response({ ...challenge, proposal: { handle: null, version: 1 } });
      }
      if (path.endsWith("/confirm")) return response({ ...empty, status: "inactive", version: 2 });
      return response(pending);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover configuração InfinitePay" }));
    fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    fireEvent.change(await screen.findByLabelText("Código de confirmação InfinitePay"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar configuração InfinitePay" }));
    expect(await screen.findByText("Configuração InfinitePay removida.")).toBeTruthy();
  });
});
