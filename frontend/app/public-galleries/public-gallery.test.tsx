import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => <a href={href} {...props}>{children}</a> }));
const navigation = vi.hoisted(() => ({ galleryId: "public-1" }));
vi.mock("next/navigation", () => ({ useParams: () => navigation }));
vi.mock("../push-control", () => ({ PushControl: () => null, LogoutButton: () => null }));

import PublicGalleryPage from "./[galleryId]/page";

afterEach(() => {
  navigation.galleryId = "public-1";
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

function response(value: object, status = 200) { return Promise.resolve(new Response(JSON.stringify(value), { status })); }

describe("Galeria pública da cliente", () => {
  function mockRegionJourney(admit: () => Promise<Response>) {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(360);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(240);
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", minor_search_available: true, consent_version: "v1" });
      if (path.endsWith("/latest")) return response({}, 404);
      if (path.endsWith("/face-regions")) return response({ auto_threshold: 4, regions: [{ id: "region-1", x: .2, y: .2, width: .2, height: .2 }] });
      if (path.endsWith("/face-region-searches")) return admit();
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview", width: 360, height: 240 }] });
      return response({ id: navigation.galleryId, name: "Galeria", favorites_enabled: false });
    }));
  }

  it.each(["failed", "no_candidates"])("mantém a foto e seleção manual sem salto quando a busca termina em %s", async (status) => {
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    mockRegionJourney(() => response({ id: "direct-empty", status, progress: { index: { ready: 1, total: 1 }, comparison: { done: 1, total: 1 } }, candidates: [] }));
    render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de Foto 1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" }));
    await waitFor(() => expect(screen.getAllByText(status === "failed" ? "A busca não foi concluída. Toque no rosto para tentar novamente." : "Nenhuma possibilidade foi encontrada.").length).toBeGreaterThan(0));
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: "Selecionar foto" })).toBeTruthy();
    expect(scroll).not.toHaveBeenCalled();
  });

  it("respeita Retry-After e permite nova tentativa consciente", async () => {
    const clock = vi.spyOn(Date, "now").mockReturnValue(1000);
    const admit = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "Busca temporariamente ocupada." }), { status: 503, headers: { "Retry-After": "3" } })));
    mockRegionJourney(admit);
    render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de Foto 1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" }));
    await screen.findAllByText(/Tente novamente em 3 segundos/);
    fireEvent.click(screen.getByRole("button", { name: "Procurar pessoa no rosto 1" }));
    expect(admit).toHaveBeenCalledTimes(1);
    clock.mockReturnValue(4001);
    fireEvent.click(screen.getByRole("button", { name: "Procurar pessoa no rosto 1" }));
    await waitFor(() => expect(admit).toHaveBeenCalledTimes(2));
  });

  it("ignora resposta pendente ao trocar de galeria", async () => {
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    let complete!: (value: Response) => void;
    mockRegionJourney(() => new Promise<Response>((resolve) => { complete = resolve; }));
    const { rerender } = render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de Foto 1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" }));
    navigation.galleryId = "public-2";
    rerender(<PublicGalleryPage />);
    await screen.findByRole("button", { name: "Ampliar prévia protegida de Foto 1" });
    await act(async () => complete(new Response(JSON.stringify({ id: "stale-direct", status: "ready" }))));
    expect(window.sessionStorage.getItem("markina:facial-search:public-1")).toBeNull();
    expect(window.sessionStorage.getItem("markina:facial-search:public-2")).toBeNull();
    expect(scroll).not.toHaveBeenCalled();
  });

  it("busca por toque sem consentimento, evita duplicação e volta ao topo uma vez", async () => {
    vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(360);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(240);
    const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    let complete!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => { complete = resolve; });
    const fetchMock = vi.fn((path: string, _init?: RequestInit) => {
      void _init;
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", minor_search_available: true, consent_version: "v1" });
      if (path.endsWith("/latest")) return response({}, 404);
      if (path.endsWith("/face-regions")) return response({ auto_threshold: 4, regions: [{ id: "region-1", x: .2, y: .2, width: .2, height: .2 }] });
      if (path.endsWith("/face-region-searches")) return pending;
      if (path.endsWith("/selection")) return response({ private_gallery_id: "private-1", cart: { quantity: 1 } });
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview", width: 360, height: 240 }], cart: { quantity: 0 } });
      return response({ id: "public-1", name: "Galeria", favorites_enabled: false });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ampliar prévia protegida de Foto 1" }));
    const face = await screen.findByRole("button", { name: "Procurar pessoa no rosto 1" });
    fireEvent.click(face);
    fireEvent.click(face);
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.getAllByText("Aguarde, procurando fotos…").length).toBeGreaterThan(0);
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/face-region-searches"))).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/public-galleries/public-1/face-region-searches", expect.objectContaining({ body: JSON.stringify({ face_region_id: "region-1" }) }));
    await act(async () => complete(new Response(JSON.stringify({ id: "direct-1", status: "ready", reference_deleted: true, progress: { index: { total: 1, ready: 1 }, comparison: { total: 1, done: 1 } }, candidates: [{ photo_id: "photo-1", rank: 1, match_class: "matched" }] }), { status: 202 })));
    expect(await screen.findByRole("region", { name: "Possibilidades encontradas" })).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(scroll).toHaveBeenCalledTimes(1);
    expect(scroll).toHaveBeenCalledWith({ top: 0, behavior: "instant" });
    fireEvent.click(screen.getByRole("button", { name: "Selecionar foto" }));
    await waitFor(() => expect(screen.getByLabelText("Resumo da seleção")).toBeTruthy());
    expect(scroll).toHaveBeenCalledTimes(1);
  });

  it("usa a largura útil do desktop e amplia a foto sem limitar as demais páginas", () => {
    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    expect(css).toContain(".public-gallery-shell { display:grid; width:min(calc(100% - 32px),1760px);");
    expect(css).toContain(".gallery-presentation { width:100%;");
    expect(css).toContain(".gallery-presentation-dialog { width:min(100%,1600px);");
    expect(css).toContain(".gallery-presentation-grid { grid-template-columns:repeat(4,minmax(0,1fr));");
    expect(css).toContain("@media (max-width: 560px)");
  });

  it("carrega somente após autorização e mantém a primeira seleção na jornada pública", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/photos/photo-1/selection") && init?.method === "POST") return response({ status: "selected", private_gallery_id: "private-1", gallery_created: true, reference_created: true, selection_created: true, selection_expires_at: "2026-09-30T23:59:59Z", cart: { quantity: 1, total_cents: 700, savings_cents: 0 } }, 201);
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/public-galleries/public-1/photos/photo-1/preview", selected: false }], private_gallery_id: null, cart: { quantity: 0, items: [] } });
      return response({ id: "public-1", name: "Festa escolar", event_name: "Formatura", description: "Escolha suas fotos", access_mode: "standard", photos_url: "/public-galleries/public-1/photos" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);
    expect(screen.getByText("Abrindo Galeria pública")).toBeTruthy();
    fireEvent.click(await screen.findByRole("button", { name: "Selecionar foto" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/photos/photo-1/selection",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    ));
    expect(await screen.findByText("Sua seleção foi iniciada e ficará salva nesta galeria.")).toBeTruthy();
    expect(screen.getByLabelText("Prazo para novas seleções").textContent).toContain("30/09/2026");
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/public-galleries/public-1/photos"))).toHaveLength(1);
    expect((screen.getByRole("button", { name: /Desmarcar/ }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByLabelText("Resumo da seleção").textContent).toContain("1 foto");
    expect(screen.getByLabelText("Resumo da seleção").textContent).toContain("7,00");
    expect(within(screen.getByLabelText("Resumo da seleção")).getByRole("link", { name: /^Carrinho/ }).getAttribute("href")).toBe("/library/cart");
    expect(within(screen.getByLabelText("Resumo da seleção")).getByRole("link", { name: /^Carrinho/ }).className).toContain("selection-summary__proceed");
  });

  it("mantém acesso à galeria privada quando o carrinho está vazio", async () => {
    let finishPhotos!: (value: Response) => void;
    const photosResponse = new Promise<Response>((resolve) => { finishPhotos = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/photos")) return photosResponse;
      if (path.endsWith("/facial-search")) return response({ state: "unavailable", manual_selection_available: true });
      if (path.endsWith("/facial-searches/latest")) return response({ detail: "Consulta indisponível" }, 404);
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos", private_gallery_id: "private-1" });
    }));

    render(<PublicGalleryPage />);

    const privateGalleryLink = await screen.findByRole("link", { name: "Minha galeria" });
    expect(privateGalleryLink.getAttribute("href")).toBe("/gallery/private-1");
    expect(screen.getByText("Carregando fotos")).toBeTruthy();

    await act(async () => {
      finishPhotos(new Response(JSON.stringify({
          photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview", selected: false, commercial_state: "payment_reported" }],
          private_gallery_id: "private-1",
          cart: { quantity: 0, items: [] },
        }), { status: 200 }));
    });
    expect(await screen.findByRole("img", { name: "Prévia protegida de Foto 1" })).toBeTruthy();
    expect(screen.queryByLabelText("Resumo da seleção")).toBeNull();
  });

  it("não mostra grade coletiva ou não autorizada quando o backend nega", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Acesso não autorizado." }), { status: 403 })));
    render(<PublicGalleryPage />);
    expect(await screen.findByText("Galeria indisponível")).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("button", { name: "Selecionar foto" })).toBeNull();
  });

  it("mantém a grade e informa erro sem simular seleção", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "POST") return response({ detail: "Prazo de seleção expirado." }, 409);
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview" }] });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "invite_only", photos_url: "/photos" });
    }));
    render(<PublicGalleryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Selecionar foto" }));
    expect(await screen.findByText("Prazo de seleção expirado.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Selecionar foto" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("restaura seleção persistida e permite desmarcar pelo backend", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/photos/photo-1/selection") && init?.method === "DELETE") return response({ status: "unselected", private_gallery_id: null, gallery_closed: true, cart: { quantity: 0, items: [] } });
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview", selected: true }], private_gallery_id: "private-1", cart: { quantity: 1, total_cents: 700, items: [{ id: "photo-1", name: "Foto 1" }] } });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Desmarcar/ }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/photos/photo-1/selection",
      expect.objectContaining({ method: "DELETE", credentials: "same-origin" }),
    ));
    expect(await screen.findByText("A foto foi removida da sua seleção.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Selecionar foto" })).toBeTruthy();
    expect(screen.queryByLabelText("Resumo da seleção")).toBeNull();
  });

  it("consente, filtra em dois blocos e seleciona candidata pela mesma jornada comercial", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/facial-search") && !init?.method) return response({ state: "consent_required", manual_selection_available: true, minor_search_available: true, minor_representation_reference: "representation-opaque-1", consent_version: "consent-v1", legal_notice_version: "notice-v1", reference_retention_seconds: 900, candidate_retention_seconds: 86400 });
      if (path.endsWith("/facial-searches") && init?.method === "POST") return response({ id: "request-1", gallery_id: "public-1", status: "ready", progress: { index: { ready: 3, total: 3 }, comparison: { done: 3, total: 3 } }, reference_deleted: true, expires_at: new Date(Date.now() + 60_000).toISOString(), candidates: [{ photo_id: "photo-1", rank: 3, quality_band: "other", match_class: "ambiguous" }, { photo_id: "photo-2", rank: 1, quality_band: "best", match_class: "matched" }, { photo_id: "photo-3", rank: 2, quality_band: "best", match_class: "matched" }, { photo_id: "photo-2", rank: 8, quality_band: "other", match_class: "ambiguous" }] }, 202);
      if (path.includes("/candidates/photo-2/selection") && init?.method === "POST") return response({ status: "selected", private_gallery_id: "private-1", gallery_created: true, reference_created: true, selection_created: true, cart: { quantity: 1, total_cents: 700 } }, 201);
      if (path.endsWith("/gallery/private-1/photos/photo-2/favorite") && init?.method === "POST") return response({ status: "favorited" }, 201);
      if (path.includes("/candidates/photo-1") && init?.method === "DELETE") return response({ rejected: true });
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview-1", selected: false, favorited: false }, { id: "photo-2", name: "Foto 2", preview_url: "/preview-2", selected: false, favorited: false }, { id: "photo-3", name: "Foto 3", preview_url: "/preview-3", selected: false, favorited: false }], cart: { quantity: 0, items: [] } });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos", favorites_enabled: true });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Enviar foto para procurar" }));
    expect(screen.getByText(/Autorizo, de forma livre, informada e específica/)).toBeTruthy();
    expect(screen.getByText(/Não há cadastro biométrico permanente/)).toBeTruthy();
    const file = new File(["jpeg"], "referencia.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Escolher foto JPEG da galeria do celular"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("radio", { name: "Criança ou adolescente" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Sou pai, mãe ou responsável legal/ }));
    fireEvent.submit(screen.getByRole("button", { name: "Autorizar e procurar fotos" }).closest("form")!);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/facial-searches",
      expect.objectContaining({
        headers: expect.objectContaining({
          "x-facial-subject-declaration": "minor",
          "x-facial-consent-accepted": "true",
        }),
      }),
    ));

    expect(await screen.findByText("Correspondências")).toBeTruthy();
    expect(screen.getByText("Possíveis correspondências")).toBeTruthy();
    expect(screen.getByText("Sem imagem temporária nesta busca")).toBeTruthy();
    const featured = screen.getByRole("region", { name: "Possibilidades encontradas" });
    const fullCollection = screen.getByRole("heading", { name: "Fotos disponíveis" });
    expect(featured.compareDocumentPosition(fullCollection) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect([...featured.querySelectorAll("img")].map((image) => image.getAttribute("alt"))).toEqual([
      "Prévia protegida de Foto 2",
      "Prévia protegida de Foto 3",
      "Prévia protegida de Foto 1",
    ]);
    fireEvent.click(featured.querySelectorAll<HTMLButtonElement>("button[aria-pressed='false']")[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/facial-searches/request-1/candidates/photo-2/selection",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(screen.getByLabelText("Resumo da seleção").textContent).toContain("1 foto");
    expect(within(screen.getByLabelText("Resumo da seleção")).getByRole("link", { name: /^Carrinho/ })).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Favoritar" })[0]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/gallery/private-1/photos/photo-2/favorite",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    ));
    expect(screen.getAllByRole("button", { name: "Remover dos favoritos" }).length).toBeGreaterThan(0);
    expect(screen.queryByText("Favoritar")).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: "Não é esta pessoa" })[2]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/facial-searches/request-1/candidates/photo-1",
      expect.objectContaining({ method: "DELETE" }),
    ));
    expect(screen.getAllByText("Foto 1")).toHaveLength(1);
  });

  it("retoma pelo request opaco após refresh sem guardar a imagem", async () => {
    window.sessionStorage.setItem("markina:facial-search:public-1", "request-restored");
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", manual_selection_available: true, minor_search_available: false, consent_version: "consent-v1" });
      if (path.endsWith("/facial-searches/request-restored")) return response({ id: "request-restored", gallery_id: "public-1", status: "searching", progress: { index: { ready: 1, total: 1 }, comparison: { done: 0, total: 1 } }, reference_deleted: false, expires_at: new Date(Date.now() + 60_000).toISOString(), candidates: [] });
      if (path.endsWith("/photos")) return response({ photos: [] });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);
    expect(await screen.findByText("Procurando possibilidades")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/facial-searches/request-restored",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(window.sessionStorage.getItem("markina:facial-search:public-1")).toBe("request-restored");
    expect(document.querySelector("img[src*='referencia']")).toBeNull();
  });

  it("recupera a consulta mais recente após fechar a aba e mantém melhores resultados no topo", async () => {
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) return response({ state: "unavailable", manual_selection_available: true, minor_search_available: false });
      if (path.endsWith("/facial-searches/latest")) return response({ id: "latest-request", gallery_id: "public-1", status: "ready", progress: { index: { ready: 2, total: 2 }, comparison: { done: 2, total: 2 } }, reference_deleted: true, expires_at: new Date(Date.now() + 60_000).toISOString(), candidates: [{ photo_id: "photo-2", rank: 1, quality_band: "best", match_class: "matched" }, { photo_id: "photo-1", rank: 2, quality_band: "other", match_class: "ambiguous" }] });
      if (path.endsWith("/photos")) return response({ photos: [{ id: "photo-1", name: "Foto 1", preview_url: "/preview-1" }, { id: "photo-2", name: "Foto 2", preview_url: "/preview-2" }] });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos" });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<PublicGalleryPage />);

    expect(await screen.findByText("Correspondências")).toBeTruthy();
    expect(screen.getByText("Possíveis correspondências")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/public-galleries/public-1/facial-searches/latest",
      { credentials: "same-origin" },
    );
    expect(window.sessionStorage.getItem("markina:facial-search:public-1")).toBe("latest-request");
  });

  it("leva o foco ao consentimento e permite cancelar por teclado", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/facial-search")) return response({ state: "consent_required", manual_selection_available: true, minor_search_available: false, consent_version: "consent-v1", legal_notice_version: "notice-v1" });
      if (path.endsWith("/photos")) return response({ photos: [] });
      return response({ id: "public-1", name: "Festa", event_name: null, description: null, access_mode: "standard", photos_url: "/photos" });
    }));
    render(<PublicGalleryPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Enviar foto para procurar" }));
    const dialog = screen.getByRole("dialog", { name: "Busca facial nesta galeria" });
    expect(document.activeElement).toBe(dialog);
    expect(dialog.getAttribute("aria-describedby")).toContain("facial-consent-purpose");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Busca facial nesta galeria" })).toBeNull();
  });
});
