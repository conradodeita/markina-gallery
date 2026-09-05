import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));

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
        has_prepared_photos: true,
        actions: { continue_url: "/public-galleries/public-1", review_url: "/gallery/private-1", prepared_url: "/gallery/private-1", fallback_url: null },
      }],
    })));
    render(<LibraryPage />);

    const section = await screen.findByRole("region", { name: "Galerias e seleções" });
    expect(within(section).getAllByRole("article")).toHaveLength(1);
    expect(within(section).getByRole("link", { name: "Ver fotos e continuar" }).getAttribute("href")).toBe("/public-galleries/public-1");
    expect(within(section).getByRole("link", { name: "Revisar seleção e fotos preparadas" }).getAttribute("href")).toBe("/gallery/private-1");
    expect(within(section).getByLabelText("Resumo da seleção").textContent).toContain("2 foto(s) selecionada(s)");
    expect(within(section).getByLabelText("Resumo da seleção").textContent).toContain("R$ 14,00");
    expect(within(section).getByText("Apresentação")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Galerias privadas" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Histórico de compras" })).toBeTruthy();
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

    const section = await screen.findByRole("region", { name: "Galerias e seleções" });
    expect(within(section).getAllByRole("article")).toHaveLength(1);
    expect(within(section).getByRole("link", { name: "Ver fotos e continuar" }).getAttribute("href")).toBe("/public-galleries/public-1");
    expect(within(section).getByRole("link", { name: "Revisar seleção" }).getAttribute("href")).toBe("/gallery/private-1");
    expect(screen.queryByText("Abrir galeria privada")).toBeNull();
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
    expect(screen.getByText(/Galeria pública de origem foi removida/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Abrir fotos preservadas" }).getAttribute("href")).toBe("/gallery/private-removed");
  });

  it("mostra estado vazio após desvinculação sem inventar acesso", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({ journeys: [], public_galleries: [], private_galleries: [], galleries: [] })));
    render(<LibraryPage />);
    expect(await screen.findByText("Nenhuma galeria disponível")).toBeTruthy();
    expect(screen.getByText("Nenhuma compra confirmada")).toBeTruthy();
  });

  it("não inventa galerias quando a consulta falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<LibraryPage />);
    expect(await screen.findByText("Biblioteca indisponível")).toBeTruthy();
  });
});
