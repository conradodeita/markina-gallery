import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminSettingsPage, { calculateWatermarkPreviewFontSize } from "./page";

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
  watermark_opacity: 42,
  watermark_position: "middle-center",
  watermark_shadow: true,
  watermark_security_lines: false,
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
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      void path;
      void options;
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);
    fireEvent.change(await screen.findByLabelText("Texto da marca-d’água"), { target: { value: "MARCA GLOBAL" } });
    expect((await screen.findAllByText("MARCA GLOBAL")).length).toBe(2);
    expect(screen.getByRole("group", { name: "Conteúdo" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Aparência" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Transparência/), { target: { value: "60" } });
    fireEvent.click(screen.getByLabelText("Usar linhas transversais de segurança"));
    fireEvent.click(screen.getByLabelText("Inferior centro"));
    expect(screen.getByRole("complementary", { name: "Como a identificação se comporta" }).textContent).toContain("não simulam uma fotografia");
    expect(screen.getByText(/não promete bloquear capturas de tela/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção global" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/protection", expect.objectContaining({ method: "PATCH" })));
    const request = fetchMock.mock.calls.find(([path, options]) => path === "/api/admin/branding/protection" && options?.method === "PATCH")?.[1];
    expect(JSON.parse(String(request?.body))).toEqual(expect.objectContaining({ watermark_opacity: 60, watermark_position: "bottom-center", watermark_shadow: true, watermark_security_lines: true }));
    expect(await screen.findByText(/Proteção visual global salva/)).toBeTruthy();
  });

  it("representa na prova a cobertura percentual aceita pelo servidor", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      void path;
      void options;
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<AdminSettingsPage />);
    const size = await screen.findByLabelText("Cobertura da marca-d’água (%)");
    expect(size.getAttribute("min")).toBe("10");
    expect(size.getAttribute("max")).toBe("96");
    expect(screen.getByText(/Percentual aproximado do eixo da foto/i)).toBeTruthy();

    fireEvent.change(size, { target: { value: "10" } });
    await waitFor(() => expect(Array.from(container.querySelectorAll<HTMLElement>(".protection-preview-surface")).every((surface) => surface.dataset.watermarkCoverage === "10")).toBe(true));

    fireEvent.change(size, { target: { value: "74" } });
    await waitFor(() => expect(Array.from(container.querySelectorAll<HTMLElement>(".protection-preview-surface")).every((surface) => surface.dataset.watermarkCoverage === "74")).toBe(true));

    fireEvent.change(size, { target: { value: "96" } });
    await waitFor(() => expect(Array.from(container.querySelectorAll<HTMLElement>(".protection-preview-surface")).every((surface) => surface.dataset.watermarkCoverage === "96")).toBe(true));

    fireEvent.change(size, { target: { value: "74" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção global" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/protection", expect.objectContaining({ method: "PATCH" })));
    const request = fetchMock.mock.calls.find(([path, options]) => path === "/api/admin/branding/protection" && options?.method === "PATCH")?.[1];
    expect(JSON.parse(String(request?.body)).watermark_size).toBe(74);
  });

  it.each(["horizontal", "vertical", "diagonal"])("dimensiona %s por cobertura e redimensionamento sem tratar o valor como pixels", (direction) => {
    const base = {
      width: 400,
      height: 260,
      textWidthAt100: 620,
      textHeightAt100: 100,
      direction,
      shadow: true,
    };
    const small = calculateWatermarkPreviewFontSize({ ...base, coverage: 10 });
    const configured = calculateWatermarkPreviewFontSize({ ...base, coverage: 74 });
    const maximum = calculateWatermarkPreviewFontSize({ ...base, coverage: 96 });
    const resized = calculateWatermarkPreviewFontSize({ ...base, width: 800, height: 520, coverage: 74 });

    expect(configured).toBeGreaterThan(small);
    expect(maximum).toBeGreaterThanOrEqual(configured);
    expect(resized).toBeGreaterThan(configured * 1.8);
  });

  it("mantém os controles disponíveis e informa falha de salvamento", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => Promise.resolve(
      new Response(JSON.stringify(branding), { status: path.endsWith("/protection") && options?.method === "PATCH" ? 500 : 200 }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<AdminSettingsPage />);
    await screen.findByLabelText("Direção");
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção global" }));
    expect(await screen.findByText("Não foi possível salvar a proteção visual.")).toBeTruthy();
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
