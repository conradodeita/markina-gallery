import { readFileSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, prefetch, ...props }: { children: React.ReactNode; href: string; prefetch?: boolean }) => <a href={href} data-prefetch={prefetch === true ? "true" : undefined} {...props}>{children}</a> }));

import LibraryPage from "./page";

afterEach(() => vi.restoreAllMocks());

function response(value: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

const publicGallery = {
  id: "public-1",
  name: "Festa escolar",
  event_name: "Formatura",
  access_mode: "standard",
  gallery_status: "active",
  browse_url: "/public-galleries/public-1",
};

const privateGallery = {
  id: "private-1",
  name: "Fotos da família",
  message: "Escolha com calma",
  selection_expires_at: null,
  gallery_status: "active",
  origin_removed: false,
  origin: { id: "public-1", name: "Festa escolar", available: true, browse_url: "/public-galleries/public-1" },
  folders: [{ id: "folder-1", name: "Apresentação" }],
};

describe("biblioteca privada da cliente", () => {
  it("agrupa carrinhos de galerias diferentes sem oferecer checkout global", async () => {
    const journey = (id: string, name: string, quantity: number, totalCents: number) => ({
      id,
      name,
      event_name: `Evento ${name}`,
      status: "active",
      primary_surface: "public",
      browse_url: `/public-galleries/${id}`,
      public_gallery: { ...publicGallery, id, name, browse_url: `/public-galleries/${id}` },
      private_gallery: { ...privateGallery, id: `private-${id}` },
      selection: { quantity, total_cents: totalCents, savings_cents: 0 },
      orders: [],
      has_prepared_photos: false,
      actions: { continue_url: `/public-galleries/${id}`, review_url: `/gallery/private-${id}`, orders_url: null, prepared_url: null, fallback_url: null },
    });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({ orders: [] })
      : response({ journeys: [journey("public-1", "Festa escolar", 2, 1400), journey("public-2", "Formatura", 1, 900)] })));

    render(<LibraryPage />);

    const cart = await screen.findByRole("region", { name: "Carrinho" });
    expect(within(cart).getAllByRole("article")).toHaveLength(2);
    expect(within(cart).getByLabelText("Total informativo do carrinho").textContent).toContain("3 fotos · R$ 23,00");
    const reviewLinks = within(cart).getAllByRole("link", { name: "Revisar carrinho" });
    expect(reviewLinks.map((link) => link.getAttribute("href"))).toEqual([
      "/gallery/private-public-1?mode=review",
      "/gallery/private-public-2?mode=review",
    ]);
    expect(screen.queryByRole("link", { name: /Finalizar todos/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Finalizar todos/i })).toBeNull();
  });

  it("contém erro de cotação no carrinho afetado e preserva os demais", async () => {
    const journey = (id: string, name: string, selection: object) => ({
      id, name, event_name: `Evento ${name}`, status: "active", primary_surface: "public",
      browse_url: `/public-galleries/${id}`, public_gallery: { ...publicGallery, id, name },
      private_gallery: { ...privateGallery, id: `private-${id}` }, selection, orders: [], has_prepared_photos: false,
      actions: { continue_url: `/public-galleries/${id}`, review_url: `/gallery/private-${id}`, orders_url: null, prepared_url: null, fallback_url: null },
    });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({}, 500)
      : response({ journeys: [
        journey("valid", "Galeria válida", { quantity: 2, total_cents: 1400 }),
        journey("invalid", "Galeria sem preço", { quantity: 1, pricing_error: "Cotação indisponível para esta galeria." }),
      ] })));

    render(<LibraryPage />);

    const cart = await screen.findByRole("region", { name: "Carrinho" });
    expect(within(cart).getByLabelText("Total informativo do carrinho").textContent).toContain("3 fotos");
    expect(within(cart).getByLabelText("Total informativo do carrinho").textContent).not.toContain("R$");
    const valid = within(cart).getByRole("article", { name: "Carrinho de Galeria válida" });
    const invalid = within(cart).getByRole("article", { name: "Carrinho de Galeria sem preço" });
    expect(valid.textContent).toContain("R$ 14,00");
    expect(within(valid).queryByText(/Cotação indisponível/)).toBeNull();
    expect(within(invalid).getByText("Cotação indisponível para esta galeria.")).toBeTruthy();
    expect(within(cart).getAllByRole("link", { name: "Revisar carrinho" })).toHaveLength(2);
    expect(await screen.findByText("Não foi possível carregar as compras")).toBeTruthy();
    expect(within(cart).getByText("Galeria válida")).toBeTruthy();
  });

  it("separa compras comunicadas do carrinho e não usa Ver pedido nem filtros", async () => {
    const purchase = {
      id: "reported-order",
      gallery_name: "Fotos da família",
      parent_gallery_name: "Festa escolar",
      gallery_status_label: "Galeria ativa",
      gallery_removed: false,
      communicated_at: "2026-09-12T12:00:00Z",
      confirmed_at: null,
      commercial_state: "payment_reported",
      total_cents: 1400,
      items: [{ photo_id: "photo-1", name: "Foto 1", preview_url: "/preview/photo-1", delivery_url: null, delivery_reference_available: false }],
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({ orders: [purchase] })
      : response({ journeys: [{
        id: "public-1", name: "Festa escolar", event_name: "Formatura", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery, private_gallery: privateGallery, selection: { quantity: 0 },
        orders: [{ order_id: "reported-order", commercial_state: "payment_reported", total_cents: 1400 }], has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-1", review_url: null, orders_url: "/gallery/private-1", prepared_url: null, fallback_url: null },
      }] })));

    render(<LibraryPage />);

    const purchases = await screen.findByRole("region", { name: "Compras" });
    expect(screen.getByRole("link", { name: "Ver compra" }).getAttribute("href")).toBe("/library#purchases");
    expect(screen.queryByText("Ver pedido")).toBeNull();
    expect(within(purchases).getByRole("article", { name: "Compra de Fotos da família" })).toBeTruthy();
    expect(within(purchases).getByText("Pagamento informado")).toBeTruthy();
    expect(within(purchases).getByText("Informada em 12/09/2026")).toBeTruthy();
    expect(within(purchases).queryByRole("button", { name: /Todas|Carrinho|Aguardando pagamento|Compradas/ })).toBeNull();
    expect(within(purchases).queryByRole("button", { name: /Selecionar|Desmarcar|Favoritar/ })).toBeNull();
  });

  it("mostra estado vazio de compras sem repetir o carrinho", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({ orders: [] })
      : response({ journeys: [{
        id: "public-1", name: "Festa escolar", event_name: "Formatura", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery, private_gallery: privateGallery, selection: { quantity: 1, total_cents: 700 }, orders: [], has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-1", review_url: "/gallery/private-1", orders_url: null, prepared_url: null, fallback_url: null },
      }] })));

    render(<LibraryPage />);

    const purchases = await screen.findByRole("region", { name: "Compras" });
    expect(within(purchases).getByText("Nenhuma compra")).toBeTruthy();
    expect(within(purchases).queryByText(/foto selecionada/i)).toBeNull();
  });

  it("libera as jornadas antes de o histórico comercial terminar", async () => {
    let resolvePurchases!: (value: Response) => void;
    const purchases = new Promise<Response>((resolve) => { resolvePurchases = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? purchases : response({
      journeys: [{
        id: "public-progressive",
        name: "Galeria já disponível",
        event_name: "Evento",
        status: "active",
        primary_surface: "public",
        browse_url: "/public-galleries/public-progressive",
        public_gallery: publicGallery,
        private_gallery: null,
        selection: { quantity: 0 },
        orders: [],
        has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-progressive", review_url: null, orders_url: null, prepared_url: null, fallback_url: null },
      }],
    })));

    render(<LibraryPage />);

    expect(await screen.findByText("Galeria já disponível")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver fotos" })).toBeTruthy();
    expect(screen.getByText("Carregando compras")).toBeTruthy();
    resolvePurchases(new Response(JSON.stringify({ orders: [] }), { status: 200 }));
    expect(await screen.findByText("Nenhuma compra")).toBeTruthy();
  });

  it("isola a falha do histórico e permite tentar novamente", async () => {
    let historyAttempts = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/purchases")) {
        historyAttempts += 1;
        return historyAttempts === 1 ? response({}, 500) : response({ orders: [] });
      }
      return response({ journeys: [{
        id: "public-retry", name: "Galeria preservada", event_name: "Evento", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-retry",
        public_gallery: publicGallery, private_gallery: null, selection: { quantity: 0 }, orders: [], has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-retry", review_url: null, orders_url: null, prepared_url: null, fallback_url: null },
      }] });
    }));

    render(<LibraryPage />);

    expect(await screen.findByText("Galeria preservada")).toBeTruthy();
    expect(await screen.findByText("Não foi possível carregar as compras")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma compra")).toBeTruthy();
    expect(screen.getByText("Galeria preservada")).toBeTruthy();
    expect(historyAttempts).toBe(2);
  });

  it("agrupa origem, seleção e conteúdo preparado em uma única jornada", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [{ id: "order-1", gallery_name: "Fotos da família", parent_gallery_name: "Festa escolar", gallery_status_label: "Galeria removida", gallery_removed: true, confirmed_at: "2026-08-31T12:00:00Z", total_cents: 2500, items: [{ photo_id: "photo-1", name: "Foto 1", preview_url: "/library/history/items/item-1/preview", delivery_url: null, delivery_reference_available: true }] }] }) : response({
      journeys: [{
        id: "public-1",
        name: "Festa escolar",
        event_name: "Formatura",
        status: "active",
        primary_surface: "public",
        browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery,
        private_gallery: privateGallery,
        selection: { quantity: 2, total_cents: 1400, savings_cents: 100 },
        orders: [{ order_id: "reported-1", commercial_state: "payment_reported", total_cents: 2500 }],
        has_prepared_photos: true,
        actions: { continue_url: "/public-galleries/public-1", review_url: "/gallery/private-1", orders_url: "/gallery/private-1", prepared_url: "/gallery/private-1", fallback_url: null },
      }],
    })));
    render(<LibraryPage />);

    expect(await screen.findByRole("heading", { name: "Minhas fotos", level: 1 })).toBeTruthy();
    expect(screen.queryByText("Sua área privada")).toBeNull();
    expect(screen.queryByText(/Cada evento aparece uma única vez/)).toBeNull();
    expect(screen.queryByText(/compras preservadas/i)).toBeNull();
    const section = await screen.findByRole("region", { name: "Galerias" });
    const cart = screen.getByRole("region", { name: "Carrinho" });
    expect(within(section).getAllByRole("article")).toHaveLength(1);
    expect(within(cart).getByRole("article", { name: "Carrinho de Festa escolar" }).textContent).toContain("2 fotos");
    expect(within(cart).getByRole("article", { name: "Carrinho de Festa escolar" }).textContent).toContain("R$ 14,00");
    expect(within(cart).getByRole("link", { name: "Revisar carrinho" }).getAttribute("href")).toBe("/gallery/private-1?mode=review");
    expect(within(section).getByRole("link", { name: "Carrinho (2)" }).getAttribute("href")).toBe("/library#cart");
    expect(within(section).getAllByRole("link")).toHaveLength(1);
    expect(within(section).getByText("Pagamento informado")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Galerias privadas" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Compras" })).toBeTruthy();
    expect(screen.getByText("Galeria removida", { exact: false })).toBeTruthy();
  });

  it("mantém a pública como retorno cotidiano sem duplicar a privada automática", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({
      journeys: [{
        id: "public-1",
        name: "Festa escolar",
        event_name: "Formatura",
        status: "active",
        primary_surface: "public",
        browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery,
        private_gallery: privateGallery,
        selection: { quantity: 1, total_cents: 700, savings_cents: 0 },
        has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-1", review_url: "/gallery/private-1", prepared_url: null, fallback_url: null },
      }],
    })));
    render(<LibraryPage />);

    const section = await screen.findByRole("region", { name: "Galerias" });
    const cart = screen.getByRole("region", { name: "Carrinho" });
    expect(within(section).getAllByRole("article")).toHaveLength(1);
    expect(within(section).getByRole("link", { name: "Carrinho (1)" }).getAttribute("href")).toBe("/library#cart");
    expect(within(section).getAllByRole("link")).toHaveLength(1);
    expect(within(cart).getByRole("link", { name: "Revisar carrinho" }).getAttribute("href")).toBe("/gallery/private-1?mode=review");
    expect(screen.queryByText("Abrir galeria privada")).toBeNull();
  });

  it.each([
    { state: "seleção editável", quantity: 1, orders: [], deadlineVisible: true },
    { state: "pagamento informado", quantity: 0, orders: [{ order_id: "reported-1", commercial_state: "payment_reported", total_cents: 700 }], deadlineVisible: false },
    { state: "sem seleção", quantity: 0, orders: [], deadlineVisible: false },
  ])("mostra o prazo contextual na biblioteca no estado $state", async ({ quantity, orders, deadlineVisible }) => {
    const datedPrivateGallery = { ...privateGallery, selection_expires_at: "2026-09-30T23:59:59Z" };
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({
      journeys: [{
        id: "public-deadline", name: "Galeria com prazo", event_name: "Formatura", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-deadline",
        public_gallery: publicGallery, private_gallery: datedPrivateGallery, selection: { quantity }, orders, has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-deadline", review_url: quantity > 0 ? "/gallery/private-1" : null, orders_url: orders.length ? "/gallery/private-1" : null, prepared_url: null, fallback_url: null },
      }],
    })));

    render(<LibraryPage />);
    expect((await screen.findAllByText("Galeria com prazo")).length).toBeGreaterThan(0);
    if (deadlineVisible) {
      expect(screen.getByText("Seleção até 30/09/2026")).toBeTruthy();
    } else {
      expect(screen.queryByText(/Seleção até/)).toBeNull();
    }
  });

  it("usa a privada como contingência quando a origem não está disponível", async () => {
    const preserved = { ...privateGallery, id: "private-removed", name: "Fotos preservadas", gallery_status: "origin_removed", origin_removed: true, origin: { id: "public-2", name: "Evento removido", available: false, browse_url: null } };
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({
      journeys: [{
        id: "public-2",
        name: "Evento removido",
        event_name: "",
        status: "origin_removed",
        primary_surface: "private",
        browse_url: "/gallery/private-removed",
        public_gallery: null,
        private_gallery: preserved,
        selection: { quantity: 0 },
        has_prepared_photos: false,
        actions: { continue_url: null, review_url: null, prepared_url: null, fallback_url: "/gallery/private-removed" },
      }],
    })));
    render(<LibraryPage />);

    expect(await screen.findByText("Origem indisponível")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver fotos" }).getAttribute("href")).toBe("/gallery/private-removed");
  });

  it("mostra estado vazio após desvinculação sem inventar acesso", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({ journeys: [], public_galleries: [], private_galleries: [], galleries: [] })));
    render(<LibraryPage />);
    expect(await screen.findByText("Nenhuma galeria disponível")).toBeTruthy();
    expect(screen.getByText("Nenhuma compra")).toBeTruthy();
  });

  it("não inventa galerias quando a consulta falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<LibraryPage />);
    expect(await screen.findByText("Biblioteca indisponível")).toBeTruthy();
  });

  it("mantém ação legível e expande as fotos dentro de cada pedido em grade", async () => {
    const order = (id: string, galleryName: string, names: string[]) => ({
      id,
      gallery_name: galleryName,
      parent_gallery_name: `Evento ${galleryName}`,
      gallery_status_label: "Galeria ativa",
      gallery_removed: false,
      confirmed_at: null,
      commercial_state: "payment_reported",
      total_cents: names.length * 700,
      items: names.map((name, index) => ({ photo_id: `${id}-${index}`, name, preview_url: `/preview/${id}-${index}`, delivery_url: null, delivery_reference_available: false })),
    });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({ orders: [order("order-1", "Primeira galeria", ["A.jpg", "B.jpg"]), order("order-2", "Segunda galeria", ["C.jpg"])] })
      : response({ journeys: [{
        id: "public-1", name: "Festa escolar", event_name: "Formatura", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery, private_gallery: null, selection: { quantity: 0 }, orders: [], has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-1", review_url: null, orders_url: null, prepared_url: null, fallback_url: null },
      }] })));

    render(<LibraryPage />);

    const action = await screen.findByRole("link", { name: "Ver fotos" });
    expect(action.className).toContain("mk-button--primary");
    expect(action.getAttribute("data-prefetch")).toBe("true");
    const firstOrder = screen.getByRole("article", { name: "Compra de Primeira galeria" });
    fireEvent.click(within(firstOrder).getByRole("button", { name: "Ver fotos (2)" }));
    const grid = within(firstOrder).getByRole("region", { name: "Fotos da compra de Primeira galeria" });
    expect(grid.className).toContain("library-order-photo-grid");
    expect(within(grid).getAllByRole("img")).toHaveLength(2);
    expect(within(grid).getByRole("img", { name: "Prévia protegida de A.jpg" })).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Prévia protegida de C.jpg" })).toBeNull();
    fireEvent.click(within(grid).getByRole("button", { name: "Ampliar prévia protegida de A.jpg" }));
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de A.jpg" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Anterior" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Próxima" })).toBeNull();

    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    expect(css).toMatch(/\.library-order-photo-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4,minmax\(0,1fr\)\)/);
    expect(css).toMatch(/@media\s*\(max-width:\s*700px\)[\s\S]*?\.library-order-photo-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,minmax\(0,1fr\)\)/);
  });
});
