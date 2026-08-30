import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminSettingsPage from "./page";

const branding = {
  login_title: "Sua galeria, do seu jeito.",
  login_intro: "Entre para acessar fotos.",
  login_helper: "Escolha seu acesso.",
  logo_url: null,
  app_icon_url: null,
  favicon_url: null,
  watermark_text: "MARKINA • PRÉVIA",
  watermark_font: "sans-serif",
  watermark_color: "#FFFFFF",
  watermark_size: 24,
  watermark_direction: "diagonal",
};

afterEach(() => vi.restoreAllMocks());

describe("configurações administrativas de marca", () => {
  it("apresenta fallback e envia cada ativo ao endpoint autorizado", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        const asset = path.split("/").at(-1);
        return Promise.resolve(new Response(JSON.stringify({ ...branding, [`${asset?.replace("-", "_")}_url`]: `/branding/${asset}` }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);

    expect((await screen.findAllByText("Usando fallback Markina")).length).toBe(3);
    const logo = new File(["logo"], "logo.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Enviar Logo principal"), { target: { files: [logo] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/logo", expect.objectContaining({ method: "PUT", body: logo })));
    expect(await screen.findByText("Logo principal atualizado.")).toBeTruthy();
  });

  it("informa indisponibilidade quando a configuração não carrega", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    render(<AdminSettingsPage />);
    expect(await screen.findByText("Configurações indisponíveis")).toBeTruthy();
  });

  it("salva a proteção visual global no endpoint administrativo", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(branding), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);
    fireEvent.change(await screen.findByLabelText("Texto da marca-d’água"), { target: { value: "MARCA GLOBAL" } });
    expect(await screen.findByText("MARCA GLOBAL")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção global" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/protection", expect.objectContaining({ method: "PATCH" })));
    expect(await screen.findByText(/Proteção visual global salva/)).toBeTruthy();
  });

  it("salva templates de pagamento com variáveis controladas", async () => {
    const templates = { confirmed: "Olá {{cliente}}, pedido {{pedido}} confirmado.", refused: "Olá {{cliente}}, revise o pedido {{pedido}}." };
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      if (path.endsWith("/payment-message-templates")) return Promise.resolve(new Response(JSON.stringify({ templates }), { status: 200 }));
      if (path.includes("/payment-message-templates/") && options?.method === "PUT") {
        return Promise.resolve(new Response(JSON.stringify({ kind: "confirmed", body: templates.confirmed }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);
    const confirmation = await screen.findByLabelText("Confirmação");
    fireEvent.change(confirmation, { target: { value: "Olá {{cliente}}, pedido {{pedido}} confirmado." } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar confirmação" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/payment-message-templates/confirmed",
      expect.objectContaining({ method: "PUT" }),
    ));
    expect(await screen.findByText("Mensagem transacional salva.")).toBeTruthy();
  });
});
