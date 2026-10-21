import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import InfinitePayPanel from "./infinitepay-panel";

const empty = { status: "unconfigured", handle: null, version: 0, card_enabled: false,
  api_key_configured: false, checkout_available: false, credential_status: "absent",
  credential_validation: "unavailable", credential_storage_available: true };
const active = { ...empty, status: "active", handle: "synthetic_tag", version: 1,
  card_enabled: true, api_key_configured: true, checkout_available: true, credential_status: "stored" };
const challenge = { challenge_id: "synthetic", expires_at: new Date(Date.now() + 600000).toISOString(),
  proposal: { handle: "synthetic_tag", version: 0, checkout_ready: true, card_enabled: true } };
const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
beforeEach(() => { vi.spyOn(window, "confirm").mockReturnValue(true); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function fillInitial() {
  fireEvent.click(await screen.findByRole("button", { name: "Preparar InfinitePay" }));
  fireEvent.change(screen.getByLabelText("InfiniteTag"), { target: { value: "synthetic_tag" } });
  fireEvent.change(screen.getByLabelText("API Key InfinitePay"), { target: { value: "synthetic-private-key" } });
  fireEvent.click(screen.getByLabelText(/Conferi que esta InfiniteTag/));
  fireEvent.click(screen.getByLabelText(/Habilitar pagamento por cartão/));
  fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
}

describe("Credenciais InfinitePay no card existente", () => {
  it("envia o segredo apenas no cadastro e mantém somente status após confirmação", async () => {
    const storage = vi.spyOn(Storage.prototype, "setItem");
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body))).toEqual({ current_password: "synthetic-password", expected_version: 0,
          configuration: { handle: "synthetic_tag" }, api_key: "synthetic-private-key", checkout_ready: true, card_enabled: true });
        return response(challenge);
      }
      if (path.endsWith("/confirm")) {
        expect(JSON.parse(String(init?.body))).toEqual({ challenge_id: "synthetic", code: "123456" });
        return response(active);
      }
      return response(empty);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await fillInitial();
    const secret = screen.getByLabelText("API Key InfinitePay");
    expect(secret).toHaveProperty("type", "password");
    expect(secret.getAttribute("data-private")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    const otp = await screen.findByLabelText("Código de confirmação InfinitePay");
    expect(document.activeElement).toBe(otp);
    expect(screen.queryByLabelText("API Key InfinitePay")).toBeNull();
    fireEvent.change(otp, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar configuração InfinitePay" }));
    expect(await screen.findByText("API Key cadastrada. Seu valor não é exibido.")).toBeTruthy();
    expect(screen.getByText(/Validação remota indisponível/)).toBeTruthy();
    expect(screen.getAllByRole("heading", { name: "Cartão de crédito · InfinitePay" })).toHaveLength(1);
    expect(screen.queryByDisplayValue("synthetic-private-key")).toBeNull();
    expect(storage).not.toHaveBeenCalled();
    expect(document.cookie + window.location.href).not.toContain("synthetic-private-key");
    expect(fetchMock.mock.calls.filter(([, init]) => String(init?.body).includes("synthetic-private-key"))).toHaveLength(1);
  });

  it("permite ocultar e revelar somente o valor digitado durante a edição", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(empty)));
    render(<InfinitePayPanel />);
    await fillInitial();
    const field = screen.getByLabelText("API Key InfinitePay");
    fireEvent.click(screen.getByRole("button", { name: "Mostrar API Key" }));
    expect(field).toHaveProperty("type", "text");
    fireEvent.click(screen.getByRole("button", { name: "Ocultar API Key" }));
    expect(field).toHaveProperty("type", "password");
  });

  it("abre substituição com campo vazio e foco no segredo sem recuperar a chave antiga", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(active)));
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Substituir API Key" }));
    const field = screen.getByLabelText("Nova API Key InfinitePay");
    expect(field).toHaveProperty("value", "");
    expect(field).toHaveProperty("required", true);
    await waitFor(() => expect(document.activeElement).toBe(field));
    expect(screen.getByText(/Antes de revogar uma chave antiga/)).toBeTruthy();
  });

  it("permite manter a chave ao desabilitar novos cartões", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        const body = JSON.parse(String(init?.body));
        expect(body.card_enabled).toBe(false);
        expect(body).not.toHaveProperty("api_key");
        return response({ ...challenge, proposal: { ...challenge.proposal, card_enabled: false } });
      }
      return response(active);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Alterar InfiniteTag ou disponibilidade do cartão" }));
    expect(screen.getByLabelText("Nova API Key InfinitePay")).toHaveProperty("required", false);
    fireEvent.click(screen.getByLabelText(/Habilitar pagamento por cartão/));
    fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    expect(await screen.findByText(/Esta alteração manterá cartão desabilitado/)).toBeTruthy();
  });

  it("impede abandono acidental e descarta o segredo somente após confirmação", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(empty)));
    render(<InfinitePayPanel />);
    await fillInitial();
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    vi.mocked(window.confirm).mockReturnValue(false);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar alteração InfinitePay" }));
    expect(screen.getByLabelText("API Key InfinitePay")).toHaveProperty("value", "synthetic-private-key");
    vi.mocked(window.confirm).mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar alteração InfinitePay" }));
    expect(screen.queryByDisplayValue("synthetic-private-key")).toBeNull();
    expect(await screen.findByText(/Alteração cancelada/)).toBeTruthy();
  });

  it("limpa senha e chave após falha e recarrega versão em conflito sem reaplicar", async () => {
    let reads = 0;
    const fetchMock = vi.fn((path: string) => path.endsWith("/challenge")
      ? response({ detail: "A configuração mudou em outra sessão." }, 409)
      : response(reads++ ? { ...active, version: 2 } : empty));
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await fillInitial();
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "A configuração mudou em outra sessão.");
    expect(screen.getByLabelText("Senha atual do Pick-your-Pic")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Nova API Key InfinitePay")).toHaveProperty("value", "");
    expect(fetchMock.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(false);
  });

  it("explica desconexão e mantém a conta diante de compras pendentes", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body)).configuration).toBeNull();
        expect(JSON.parse(String(init?.body))).not.toHaveProperty("api_key");
        return response({ detail: "Existem compras de cartão pendentes. Concilie-as antes de desconectar." }, 409);
      }
      return response(active);
    }));
    render(<InfinitePayPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Desconectar InfinitePay" }));
    expect(screen.getByText(/O PIX manual permanece disponível/)).toBeTruthy();
    expect(screen.queryByLabelText(/API Key InfinitePay/)).toBeNull();
    fireEvent.change(screen.getByLabelText("Senha atual do Pick-your-Pic"), { target: { value: "synthetic-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("compras de cartão pendentes"));
  });

  it("não apresenta cadastro como validação e informa cofre indisponível", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...active, api_key_configured: false,
      checkout_available: false, credential_status: "unavailable", credential_storage_available: false })));
    render(<InfinitePayPanel />);
    expect(await screen.findByText(/API Key exige atenção/)).toBeTruthy();
    expect(screen.getByText(/Cadastro seguro temporariamente indisponível/)).toBeTruthy();
    expect(screen.queryByText("Credencial validada pela InfinitePay.")).toBeNull();
  });

  it.each(["validated", "rejected"])("distingue evidência de validação %s quando fornecida pelo backend", async (validation) => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...active, credential_validation: validation })));
    render(<InfinitePayPanel />);
    expect(await screen.findByText(validation === "validated" ? "Credencial validada pela InfinitePay." : /Credencial rejeitada pela InfinitePay/)).toBeTruthy();
  });

  it("recusa código expirado sem enviar confirmação", async () => {
    const fetchMock = vi.fn((path: string) => path.endsWith("/challenge")
      ? response({ ...challenge, expires_at: new Date(Date.now() - 1000).toISOString() }) : response(empty));
    vi.stubGlobal("fetch", fetchMock);
    render(<InfinitePayPanel />);
    await fillInitial();
    fireEvent.click(screen.getByRole("button", { name: "Enviar código InfinitePay" }));
    fireEvent.change(await screen.findByLabelText("Código de confirmação InfinitePay"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar configuração InfinitePay" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("expirou"));
    expect(fetchMock.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(false);
  });
});
