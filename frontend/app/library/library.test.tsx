import { readFileSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, prefetch, ...props }: { children: React.ReactNode; href: string; prefetch?: boolean }) => <a href={href} data-prefetch={prefetch === true ? "true" : undefined} {...props}>{children}</a> }));

import LibraryPage from "./page";
import PurchasesPage from "./purchases/page";

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

describe("biblioteca e compras da cliente", () => {
  it("preserva itens e contagem quando a prévia está ausente ou falha", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [{
      id: "order-missing", gallery_name: "Evento", parent_gallery_name: "Evento", confirmed_at: null, total_cents: 1400,
      items: [{ photo_id: "missing", name: "Ausente.jpg", preview_url: null }, { photo_id: "failed", name: "Falha.jpg", preview_url: "/library/history/items/failed/preview" }],
    }] }) : response({ journeys: [] })));
    render(<PurchasesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Ver fotos (2)" }));
    expect(screen.getByText("Ausente.jpg")).toBeTruthy();
    fireEvent.error(screen.getByRole("img", { name: "Prévia protegida de Falha.jpg" }));
    expect(screen.getAllByText("Prévia indisponível")).toHaveLength(2);
    expect(screen.getByText(/2 foto\(s\)/)).toBeTruthy();
  });

  it("mostra um único card por galeria, mesmo quando há seleção e compra", async () => {
    const fetcher = vi.fn((path: string) => response({ journeys: [1, 2].map((id) => ({
      id: String(id), name: `Galeria ${id}`, event_name: "Evento", status: "active",
      browse_url: `/public-galleries/${id}`, private_gallery: privateGallery,
      selection: { quantity: 2, total_cents: 1400 }, orders: [{ commercial_state: "purchased" }],
      actions: { continue_url: `/public-galleries/${id}` },
    })) }));
    vi.stubGlobal("fetch", fetcher);
    render(<LibraryPage />);
    const galleries = await screen.findByRole("region", { name: "Galerias" });
    expect(within(galleries).getAllByRole("article")).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Ver fotos" }).map((item) => item.getAttribute("href"))).toEqual(["/public-galleries/1", "/public-galleries/2"]);
    expect(screen.queryByText("Revisar carrinho")).toBeNull();
    expect(screen.queryByRole("region", { name: "Carrinho" })).toBeNull();
    expect(fetcher.mock.calls.every(([path]) => path === "/api/library")).toBe(true);
  });

  it("mantém falha do histórico independente e permite repetir", async () => {
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? (++attempts === 1 ? response({}, 500) : response({ orders: [], payment_groups: [] }))
      : response({ journeys: [] })));
    render(<><LibraryPage /><PurchasesPage /></>);
    expect(await screen.findByText("Não foi possível carregar as compras")).toBeTruthy();
    expect(screen.getByText("Nenhuma galeria disponível")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Nenhuma compra.")).toBeTruthy();
  });

  it("mostra um PIX com suas duas galerias e mantém pedido legado separado", async () => {
    const order = (id: string) => ({ id, gallery_name: `Galeria ${id}`, parent_gallery_name: `Evento ${id}`,
      commercial_state: "payment_reported", confirmed_at: null, total_cents: 700, items: [] });
    vi.stubGlobal("fetch", vi.fn(() => response({ orders: [order("antiga")], payment_groups: [{
      id: "grupo-1", total_cents: 1400, orders: [order("1"), order("2")],
    }] })));
    render(<PurchasesPage />);
    expect(await screen.findByRole("region", { name: "Compra grupo-1" })).toBeTruthy();
    expect(screen.getByText(/PIX único/).textContent).toContain("14,00");
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(screen.getAllByText("Pagamento informado")).toHaveLength(3);
  });
  it.each([
    { state: "seleção editável", quantity: 1, orders: [], deadlineVisible: true },
    { state: "pagamento informado", quantity: 0, orders: [{ order_id: "reported-1", commercial_state: "payment_reported", total_cents: 700 }], deadlineVisible: true },
    { state: "sem seleção", quantity: 0, orders: [], deadlineVisible: true },
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
      expect(screen.getAllByLabelText("Prazo para novas seleções").length).toBeGreaterThan(0);
      expect(within(screen.getByRole("region", { name: "Galerias" })).getByLabelText("Prazo para novas seleções").textContent).toContain("30/09/2026");
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
      items: names.map((name, index) => ({ photo_id: `${id}-${index}`, name, preview_url: `/gallery/gallery-1/photos/${id}-${index}/preview`, delivery_url: null, delivery_reference_available: false })),
    });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases")
      ? response({ orders: [order("order-1", "Primeira galeria", ["A.jpg", "B.jpg"]), order("order-2", "Segunda galeria", ["C.jpg"])] })
      : response({ journeys: [{
        id: "public-1", name: "Festa escolar", event_name: "Formatura", status: "active", primary_surface: "public", browse_url: "/public-galleries/public-1",
        public_gallery: publicGallery, private_gallery: null, selection: { quantity: 0 }, orders: [], has_prepared_photos: false,
        actions: { continue_url: "/public-galleries/public-1", review_url: null, orders_url: null, prepared_url: null, fallback_url: null },
      }] })));

    render(<><LibraryPage /><PurchasesPage /></>);

    const action = await screen.findByRole("link", { name: "Ver fotos" });
    expect(action.className).toContain("mk-button--primary");
    expect(action.getAttribute("data-prefetch")).toBe("true");
    const firstOrder = screen.getByRole("article", { name: "Compra de Primeira galeria" });
    fireEvent.click(within(firstOrder).getByRole("button", { name: "Ver fotos (2)" }));
    const grid = within(firstOrder).getByRole("region", { name: "Fotos da compra de Primeira galeria" });
    expect(grid.className).toContain("library-order-photo-grid");
    expect(within(grid).getAllByRole("img")).toHaveLength(2);
    expect(within(grid).getByRole("img", { name: "Prévia protegida de A.jpg" })).toBeTruthy();
    expect(within(grid).getByRole("img", { name: "Prévia protegida de A.jpg" }).getAttribute("src")).toBe("/api/gallery/gallery-1/photos/order-1-0/preview");
    expect(screen.queryByRole("img", { name: "Prévia protegida de C.jpg" })).toBeNull();
    fireEvent.click(within(grid).getByRole("button", { name: "Ampliar prévia protegida de A.jpg" }));
    expect(screen.getByRole("dialog", { name: "Prévia ampliada de A.jpg" })).toBeTruthy();
    expect(screen.getByRole("img", { name: "Prévia protegida ampliada de A.jpg" }).getAttribute("src")).toBe("/api/gallery/gallery-1/photos/order-1-0/preview");
    expect(screen.queryByRole("button", { name: "Anterior" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Próxima" })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Fechar" }));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Fechar" }));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(within(grid).getByRole("button", { name: "Ampliar prévia protegida de A.jpg" }));

    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");
    expect(css).toMatch(/\.library-order-photo-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4,minmax\(0,1fr\)\)/);
    expect(css).toMatch(/@media\s*\(max-width:\s*700px\)[\s\S]*?\.library-order-photo-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,minmax\(0,1fr\)\)/);
  });
});
