import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

import LibraryPage from "./page";

afterEach(() => vi.restoreAllMocks());

describe("biblioteca privada da cliente", () => {
  it("separa rodadas liberadas do histórico de compras", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(path.endsWith("/purchases") ? { orders: [] } : { galleries: [{ id: "gallery-1", name: "Festa escolar", message: "Escolha com calma", selection_expires_at: null, folders: [{ id: "folder-1", name: "Apresentação" }] }] }), { status: 200 }))));
    render(<LibraryPage />);
    expect(await screen.findByText("Festa escolar")).toBeTruthy();
    expect(screen.getByText("Apresentação")).toBeTruthy();
    expect(screen.getByText("Nenhuma compra confirmada")).toBeTruthy();
    expect(screen.queryByText("Clientes e operação")).toBeNull();
  });

  it("não inventa galerias quando a consulta falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    render(<LibraryPage />);
    expect(await screen.findByText("Biblioteca indisponível")).toBeTruthy();
  });
});
