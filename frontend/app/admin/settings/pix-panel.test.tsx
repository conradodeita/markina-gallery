import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import PixPanel from "./pix-panel";

const empty = { status: "unconfigured", version: 0, checkout_available: false };
const active = { status: "active", version: 1, copy_paste: "foto@example.test", receiver_name: "MARKINA", receiver_city: "SAO PAULO", instructions: "Confirmação manual", qr_png_data_url: "data:image/png;base64,AAAA", checkout_available: true };
const response = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));
afterEach(() => vi.restoreAllMocks());

describe("PIX global em Configurações", () => {
  it("confirma com senha e OTP antes de mostrar a nova configuração", async () => {
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/challenge")) return response({ challenge_id: "challenge-1", expires_at: new Date(Date.now() + 600000).toISOString(), proposal: { ...active, receiver_name: "RECEBEDOR CANONICO" } });
      if (path.endsWith("/confirm")) return response(active);
      return response(empty);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PixPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Configurar PIX" }));
    fireEvent.change(screen.getByLabelText("Chave PIX ou copia e cola"), { target: { value: "foto@example.test" } });
    fireEvent.change(screen.getByLabelText("Nome do recebedor"), { target: { value: "MARKINA" } });
    fireEvent.change(screen.getByLabelText("Cidade do recebedor"), { target: { value: "SAO PAULO" } });
    fireEvent.change(screen.getByLabelText("Senha atual"), { target: { value: "senha-atual" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código de confirmação" }));
    const code = await screen.findByLabelText("Código de confirmação");
    expect(document.activeElement).toBe(code);
    expect(screen.getByText("RECEBEDOR CANONICO")).toBeTruthy();
    expect(screen.getByText("PIX não configurado")).toBeTruthy();
    expect(screen.queryByLabelText("Senha atual")).toBeNull();
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar PIX" }));
    expect(await screen.findByText(/PIX global salvo/)).toBeTruthy();
    expect(screen.getByAltText("QR Code PIX global")).toBeTruthy();
    const confirm = fetchMock.mock.calls.find(([path]) => path.endsWith("/confirm"));
    expect(confirm).toBeTruthy();
  });

  it("mantém a configuração atual quando o WhatsApp falha e permite cancelar", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/challenge") ? response({ detail: "Canal WhatsApp indisponível para confirmação." }, 409) : response(active)));
    render(<PixPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Alterar PIX" }));
    fireEvent.change(screen.getByLabelText("Senha atual"), { target: { value: "senha" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código de confirmação" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Canal WhatsApp indisponível para confirmação.");
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByText(/Alteração cancelada/)).toBeTruthy();
    expect(screen.getByText("PIX configurado")).toBeTruthy();
  });

  it("remove somente após confirmação e trata código expirado sem perder os dados", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/challenge")) {
        expect(JSON.parse(String(init?.body)).configuration).toBeNull();
        return response({ challenge_id: "expired", expires_at: new Date(Date.now() - 1).toISOString() });
      }
      return response(active);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PixPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover PIX" }));
    fireEvent.change(screen.getByLabelText("Senha atual"), { target: { value: "senha" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar código de confirmação" }));
    fireEvent.change(await screen.findByLabelText("Código de confirmação"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirmar remoção" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("O código expirou"));
    expect(fetchMock.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(false);
    expect(screen.getByText("PIX configurado")).toBeTruthy();
  });
});
