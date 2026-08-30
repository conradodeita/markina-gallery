import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import WhatsAppPanel from "./whatsapp-panel";

const channel = {
  provider: "evolution",
  environment: "homolog",
  expected_phone: "+55••••••••99",
  connected_phone: null,
  status: "pending_pairing",
  last_error: null,
  last_checked_at: "2026-08-30T02:00:00Z",
  deliveries: { queued: 2, delivered: 5 },
};

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("configuração administrativa do WhatsApp", () => {
  it.each([
    ["sandbox", "Modo seguro"],
    ["pending_pairing", "Aguardando pareamento"],
    ["connecting", "Conectando"],
    ["ready", "Canal pronto"],
    ["mismatch", "Número divergente"],
    ["disconnected", "Canal desconectado"],
    ["error", "Verificação indisponível"],
  ])("explica o estado %s sem prometer prontidão indevida", async (status, label) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...channel, status }), { status: 200 })));
    const { unmount } = render(<WhatsAppPanel />);

    expect((await screen.findAllByText(label)).length).toBeGreaterThan(0);
    if (status !== "ready") expect(screen.queryByText("Conexão e identidade confirmadas.")).toBeNull();
    unmount();
  });

  it("salva E.164, mascara identidades e só então permite parear", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "PATCH") {
        return Promise.resolve(new Response(JSON.stringify(channel), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ ...channel, expected_phone: null }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<WhatsAppPanel />);

    const pairingButton = await screen.findByRole("button", { name: "Parear aparelho" });
    expect((pairingButton as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Número próprio de homologação"), { target: { value: "+5511999999999" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar número" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/whatsapp/channel",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ expected_phone_e164: "+5511999999999" }) }),
    ));
    expect(await screen.findByText("+55••••••••99")).toBeTruthy();
    expect((pairingButton as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByText("+5511999999999")).toBeNull();
  });

  it("mantém QR e código somente na memória visível e os expira", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/pairing") && options?.method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({
          ...channel,
          status: "connecting",
          pairing: { state: "connecting", pairing_code: "ABCD-1234", qr_base64: "cXI=" },
        }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify(channel), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<WhatsAppPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Parear aparelho" }));
    const pairingCode = await screen.findByText("ABCD-1234");
    const pairingQr = screen.getByAltText(/QR code efêmero/);
    expect(pairingCode.closest(".whatsapp-pairing-controls")).toBeTruthy();
    expect(pairingQr.closest(".whatsapp-pairing-visual")).toBeTruthy();
    expect(pairingQr.closest(".whatsapp-pairing-controls")).toBeNull();

    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(screen.queryByText("ABCD-1234")).toBeNull();
    expect(screen.queryByAltText(/QR code efêmero/)).toBeNull();
    expect(screen.getByText(/QR code\/código expirou/)).toBeTruthy();
  });

  it("mantém o canal bloqueado quando a atualização falha", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...channel, status: "disconnected" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<WhatsAppPanel />);

    const refreshButton = await screen.findByRole("button", { name: "Atualizar conexão" });
    await waitFor(() => expect((refreshButton as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(refreshButton);
    expect(await screen.findByText("Não foi possível atualizar a conexão. Os envios continuam bloqueados.")).toBeTruthy();
    expect(screen.getAllByText("Canal desconectado").length).toBeGreaterThan(0);
  });
});
