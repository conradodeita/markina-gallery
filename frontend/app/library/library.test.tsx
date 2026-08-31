import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));

import LibraryPage from "./page";

afterEach(() => vi.restoreAllMocks());

function response(value: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

describe("biblioteca privada da cliente", () => {
  it("separa Galerias públicas, privadas e histórico preservado", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [{ id: "order-1", gallery_name: "Fotos da família", parent_gallery_name: "Festa escolar", gallery_status_label: "Galeria removida", gallery_removed: true, confirmed_at: "2026-08-31T12:00:00Z", total_cents: 2500, items: [{ photo_id: "photo-1", name: "Foto 1", preview_url: "/library/history/items/item-1/preview", delivery_url: null, delivery_reference_available: true }] }] }) : response({
      public_galleries: [{ id: "public-1", name: "Festa escolar", event_name: "Formatura", access_mode: "standard", gallery_status: "active", browse_url: "/public-galleries/public-1" }],
      private_galleries: [{ id: "private-1", name: "Fotos da família", message: "Escolha com calma", selection_expires_at: null, gallery_status: "active", origin_removed: false, origin: { id: "public-1", name: "Festa escolar", available: true, browse_url: "/public-galleries/public-1" }, folders: [{ id: "folder-1", name: "Apresentação" }] }],
    })));
    render(<LibraryPage />);
    const publicSection = await screen.findByRole("region", { name: "Galerias públicas abertas" });
    expect(within(publicSection).getByRole("link", { name: /Festa escolar/ }).getAttribute("href")).toBe("/public-galleries/public-1");
    const privateSection = screen.getByRole("region", { name: "Galerias privadas" });
    expect(within(privateSection).getByText("Apresentação")).toBeTruthy();
    expect(within(privateSection).getByRole("link", { name: "Voltar à Galeria pública" }).getAttribute("href")).toBe("/public-galleries/public-1");
    expect(screen.getByRole("heading", { name: "Histórico de compras" })).toBeTruthy();
    expect(screen.getByText("Galeria removida", { exact: false })).toBeTruthy();
  });

  it("explica galeria expirada e origem removida sem perder as privadas", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({
      public_galleries: [],
      private_galleries: [
        { id: "private-expired", name: "Seleção antiga", message: "", selection_expires_at: "2026-08-01T00:00:00Z", gallery_status: "expired", origin_removed: false, origin: { id: "public-1", name: "Festa", available: false, browse_url: null }, folders: [] },
        { id: "private-removed", name: "Fotos preservadas", message: "", selection_expires_at: null, gallery_status: "origin_removed", origin_removed: true, origin: { id: "public-2", name: "Evento removido", available: false, browse_url: null }, folders: [{ id: "folder-1", name: "Lote preservado" }] },
      ],
    })));
    render(<LibraryPage />);
    expect(await screen.findByText("Prazo expirado")).toBeTruthy();
    expect(screen.getByText("Origem removida")).toBeTruthy();
    expect(screen.getByText(/Galeria pública de origem foi removida/)).toBeTruthy();
    expect(screen.getAllByRole("link", { name: "Abrir galeria privada" })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: "Voltar à Galeria pública" })).toBeNull();
  });

  it("mostra estado vazio após desvinculação sem inventar acesso", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/purchases") ? response({ orders: [] }) : response({ public_galleries: [], private_galleries: [], galleries: [] })));
    render(<LibraryPage />);
    expect(await screen.findByText("Nenhuma Galeria pública aberta")).toBeTruthy();
    expect(screen.getByText("Nenhuma galeria privada ativa")).toBeTruthy();
    expect(screen.getByText("Nenhuma compra confirmada")).toBeTruthy();
  });

  it("não inventa galerias quando a consulta falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<LibraryPage />);
    expect(await screen.findByText("Biblioteca indisponível")).toBeTruthy();
  });
});
