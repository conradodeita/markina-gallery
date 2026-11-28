import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState({}, "", "/");
});

function renderBrandSettings() {
  window.history.replaceState({}, "", "/admin/settings#settings-brand");
  return render(<AdminSettingsPage />);
}

function stubBrandingFetch(fetcher: (path: string, init?: RequestInit) => Promise<Response>) {
  vi.stubGlobal("fetch", (path: string, init?: RequestInit) =>
    path === "/api/admin/closure"
      ? Promise.resolve(new Response(JSON.stringify({
        lifecycle: "open", credits_remaining: 0,
        terms: { available: false, accepted: false, version: null, sha256: null },
        request: null, blockers: [],
      }), { status: 200 }))
      : path === "/api/admin/facial-engine-experiment"
      ? Promise.resolve(new Response(null, { status: 403 }))
      : fetcher(path, init));
}

describe("configurações administrativas de marca", () => {
  it("recolhe grupos sem perder o formulário e abre os destinos da navegação", async () => {
    stubBrandingFetch(async () => new Response(JSON.stringify(branding)));
    render(<AdminSettingsPage />);
    await screen.findByRole("heading", { name: "Configurações" });
    const groups = Array.from(document.querySelectorAll<HTMLDetailsElement>("[data-settings-page] > details"));
    expect(groups).toHaveLength(7);
    expect(groups[0].open).toBe(true);
    expect(groups.slice(1).every((group) => !group.open)).toBe(true);
    const nav = screen.getByRole("navigation", { name: "Seções de configurações" });
    fireEvent.click(within(nav).getByRole("link", { name: "Marca e aparência" }));
    const brand = document.getElementById("settings-brand") as HTMLDetailsElement;
    expect(brand.open).toBe(true);
    const title = screen.getByLabelText("Título da entrada") as HTMLInputElement;
    fireEvent.change(title, { target: { value: "Minha entrada personalizada" } });
    fireEvent.click(brand.querySelector("summary")!);
    expect(brand.open).toBe(false);
    fireEvent.click(brand.querySelector("summary")!);
    expect(brand.open).toBe(true);
    expect(screen.getByLabelText("Título da entrada")).toBe(title);
    expect(title.value).toBe("Minha entrada personalizada");
    fireEvent.click(within(nav).getByRole("link", { name: "Termos de uso" }));
    const terms = document.getElementById("settings-terms") as HTMLDetailsElement;
    expect(terms.open).toBe(true);
    expect(groups.at(-1)).toBe(terms);
    expect(within(terms).getByText("Aceite e histórico dos Termos")).toBeTruthy();
  });

  it("abre os ancestrais de links diretos para PIX e WhatsApp", async () => {
    window.history.replaceState({}, "", "/admin/settings#pix");
    stubBrandingFetch(async () => new Response(JSON.stringify(branding)));
    render(<AdminSettingsPage />);
    await screen.findByRole("heading", { name: "Configurações" });
    const payments = document.getElementById("settings-payments") as HTMLDetailsElement;
    await waitFor(() => expect(payments.open).toBe(true));
    const whatsapp = document.getElementById("settings-whatsapp") as HTMLDetailsElement;
    expect(whatsapp.open).toBe(false);
    window.history.replaceState({}, "", "/admin/settings#whatsapp");
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(whatsapp.open).toBe(true);
    expect(payments.open).toBe(true);
  });

  it("apresenta fallback e envia cada ativo ao endpoint autorizado", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        const asset = path.split("/").at(-1);
        return Promise.resolve(new Response(JSON.stringify({ ...branding, [`${asset?.replace("-", "_")}_url`]: `/branding/${asset}` }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    stubBrandingFetch(fetchMock);
    renderBrandSettings();

    expect((await screen.findAllByText("Ainda não configurado")).length).toBe(3);
    const logo = new File(["logo"], "logo.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Enviar Logo principal"), { target: { files: [logo] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/logo", expect.objectContaining({ method: "PUT", body: logo })));
    expect(await screen.findByText("Logo principal atualizado.")).toBeTruthy();
  });

  it.each([["Ícone do aplicativo", "app-icon"], ["Favicon", "favicon"]])("envia e mostra a arte de %s", async (label, asset) => {
    const fetchMock = vi.fn(async (_path: string, init?: RequestInit) => new Response(JSON.stringify(
      init?.method === "PUT" ? { ...branding, [`${asset.replace("-", "_")}_url`]: `/branding/${asset}` } : branding,
    ), { status: 200 }));
    stubBrandingFetch(fetchMock);
    renderBrandSettings();
    const input = await screen.findByLabelText(`Enviar ${label}`);
    const file = new File(["arte oficial"], "icone.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });
    await screen.findByText(`${label} atualizado.`);
    expect(fetchMock).toHaveBeenCalledWith(`/api/admin/branding/${asset}`, expect.objectContaining({ method: "PUT", body: file }));
    expect(screen.getByAltText(`${label} configurado`).getAttribute("src")).toMatch(new RegExp(`/api/branding/${asset}\\?v=\\d+`));
  });

  it("informa falha de rede do upload e permite tentar novamente", async () => {
    stubBrandingFetch(vi.fn(async (_path: string, init?: RequestInit) => {
      if (init?.method === "PUT") throw new Error("offline");
      return new Response(JSON.stringify(branding), { status: 200 });
    }));
    renderBrandSettings();
    const input = await screen.findByLabelText("Enviar Favicon");
    fireEvent.change(input, { target: { files: [new File(["arte"], "icon.png", { type: "image/png" })] } });
    await screen.findByText("Não foi possível enviar favicon.");
    expect((input as HTMLInputElement).disabled).toBe(false);
  });

  it("informa indisponibilidade quando a configuração não carrega", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
    renderBrandSettings();
    expect(await screen.findByText("Configurações indisponíveis")).toBeTruthy();
  });

  it("salva a proteção visual global no endpoint administrativo", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      void path;
      void options;
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    stubBrandingFetch(fetchMock);
    renderBrandSettings();
    fireEvent.change(await screen.findByLabelText("Texto da marca-d’água"), { target: { value: "MARCA GLOBAL" } });
    expect((await screen.findAllByText("MARCA GLOBAL")).length).toBe(2);
    expect(screen.getByRole("group", { name: "Conteúdo" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Aparência" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Transparência/), { target: { value: "60" } });
    fireEvent.click(screen.getByLabelText("Usar linhas transversais de segurança"));
    fireEvent.click(screen.getByLabelText("Inferior centro"));
    expect(screen.getByRole("complementary", { name: "Como a identificação se comporta" }).textContent).toContain("não simulam uma fotografia");
    expect(screen.getByText(/não promete bloquear capturas de tela/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção da sua conta" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/admin/branding/protection", expect.objectContaining({ method: "PATCH" })));
    const request = fetchMock.mock.calls.find(([path, options]) => path === "/api/admin/branding/protection" && options?.method === "PATCH")?.[1];
    expect(JSON.parse(String(request?.body))).toEqual(expect.objectContaining({ watermark_opacity: 60, watermark_position: "bottom-center", watermark_shadow: true, watermark_security_lines: true }));
    expect(await screen.findByText(/Proteção visual da sua conta salva/)).toBeTruthy();
  });

  it("representa na prova a cobertura percentual aceita pelo servidor", async () => {
    const fetchMock = vi.fn((path: string, options?: RequestInit) => {
      void path;
      void options;
      return Promise.resolve(new Response(JSON.stringify(branding), { status: 200 }));
    });
    stubBrandingFetch(fetchMock);
    const { container } = renderBrandSettings();
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
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção da sua conta" }));
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
    stubBrandingFetch(fetchMock);
    renderBrandSettings();
    await screen.findByLabelText("Direção");
    fireEvent.click(screen.getByRole("button", { name: "Salvar proteção da sua conta" }));
    expect(await screen.findByText("Não foi possível salvar a proteção visual.")).toBeTruthy();
  });

  it("não duplica o editor de mensagens nem consulta os templates antigos", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(branding))));
    stubBrandingFetch(fetchMock);
    renderBrandSettings();
    await screen.findByLabelText("Direção");
    expect(screen.queryByText("Mensagens de pagamento")).toBeNull();
    expect(fetchMock.mock.calls.some(([path]) => String(path).includes("payment-message-templates"))).toBe(false);
  });
});
