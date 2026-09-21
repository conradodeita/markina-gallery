import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CartPage from "./page";
import { ClientNavigation } from "../../client-navigation";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const response = (data: object, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status }));
const group = (id: string) => ({ gallery_id: id, parent_gallery_id: id, name: `Galeria ${id}`, quantity: 1,
  total_cents: 700, error: null, browse_url: `/gallery/${id}`, selection_expires_at: null,
  items: [{ id: `photo-${id}`, name: `Foto ${id}`, folder_name: `Pasta ${id}`, preview_url: `/gallery/${id}/photos/photo-${id}/preview` }] });
const cart = { groups: [group("1"), group("2")], quantity: 2, can_prepare: true, total_cents: 1400 };
const payment = { id: "group-1", revision: "a".repeat(64), total_cents: 1400, pix_copy_paste: "PIX",
  pix_qr_code: "data:image/png;base64,AA", receiver_name: "Fotógrafo", pix_instructions: "Confira o valor" };

describe("revisão global da cliente", () => {
  it("abre fotos de duas galerias e pastas com um único PIX e registra uma compra", async () => {
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...cart, payment }
      : path.endsWith("/report") ? { status: "pending_review" } : cart));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Revise suas fotos e faça o PIX" })).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Fotos de Galeria 1" })).getByText("Pasta 1")).toBeTruthy();
    expect(screen.getAllByRole("img", { name: /QR Code/ })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: /Total/ }).textContent).toContain("14,00");
    fireEvent.click(screen.getByRole("button", { name: "Informar pagamento" }));
    expect(await screen.findByRole("heading", { name: "Pagamento informado" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver compra" }).getAttribute("href")).toBe("/library/purchases#payment-group-1");
    expect(fetcher.mock.calls.filter(([path]) => path.endsWith("/report"))).toHaveLength(1);
  });

  it("restaura a seleção após remontar sem registrar compra por visitar o PIX", async () => {
    const fetcher = vi.fn((path: string) => response(path.endsWith("/prepare") ? { ...cart, payment } : cart));
    vi.stubGlobal("fetch", fetcher);
    const first = render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    first.unmount();
    render(<CartPage />);
    await screen.findByRole("button", { name: "Informar pagamento" });
    expect(screen.getByText("Foto 2")).toBeTruthy();
    expect(fetcher.mock.calls.some(([path]) => path.endsWith("/report"))).toBe(false);
  });

  it("retira o PIX quando a revisão muda e exige conferência novamente", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/report")
      ? response({ detail: "O carrinho mudou. Confira o total." }, 409)
      : response(path.endsWith("/prepare") ? { ...cart, payment } : cart)));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Informar pagamento" }));
    expect(await screen.findByText("O carrinho mudou. Confira o total.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
    expect(screen.getByRole("button", { name: "Atualizar revisão" })).toBeTruthy();
  });

  it("bloqueia total parcial e permite remover explicitamente o grupo impedido", async () => {
    let removed = false;
    const fetcher = vi.fn((path: string, options?: RequestInit) => {
      if (options?.method === "DELETE") removed = true;
      return response(removed ? { ...cart, groups: [group("2")], quantity: 1, total_cents: 700, payment }
        : { ...cart, can_prepare: false, total_cents: null, groups: [{ ...group("1"), error: "Prazo expirado" }, group("2")] });
    });
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByText("Prazo expirado")).toBeTruthy();
    expect(screen.queryByRole("img", { name: /QR Code/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Remover seleção de Galeria 1" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Fotos de Galeria 1" })).toBeNull());
    expect(fetcher.mock.calls.some(([path, options]) => path === "/api/library/cart/1" && options?.method === "DELETE")).toBe(true);
  });

  it("sinaliza falha ao salvar sem apagar fotos da revisão", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string, options?: RequestInit) => options?.method === "DELETE"
      ? response({}, 500) : response(path.endsWith("/prepare") ? { ...cart, payment } : cart)));
    render(<CartPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Remover Foto 1 de Galeria 1" }));
    expect(await screen.findByText(/Não foi possível salvar a remoção/)).toBeTruthy();
    expect(screen.getByText("Foto 1")).toBeTruthy();
  });

  it("não prepara PIX para carrinho vazio", async () => {
    const fetcher = vi.fn(() => response({ groups: [], quantity: 0, total_cents: null, can_prepare: false }));
    vi.stubGlobal("fetch", fetcher);
    render(<CartPage />);
    expect(await screen.findByText("Seu carrinho está vazio.")).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("oculta fotos e PIX quando a sessão deixa de ter acesso", async () => {
    let authorized = true;
    vi.stubGlobal("fetch", vi.fn((path: string) => authorized
      ? response(path.endsWith("/prepare") ? { ...cart, payment } : cart) : response({}, 403)));
    render(<CartPage />);
    expect(await screen.findByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    authorized = false;
    fireEvent.focus(window);
    expect(await screen.findByText("Não foi possível consultar o carrinho.")).toBeTruthy();
    expect(screen.queryByText("Foto 1")).toBeNull();
    expect(screen.queryByRole("button", { name: "Informar pagamento" })).toBeNull();
  });

  it("mantém os três destinos acessíveis e limpa contador após acesso negado", async () => {
    let authorized = true;
    vi.stubGlobal("fetch", vi.fn(() => authorized ? response({ quantity: 6 }) : response({}, 403)));
    render(<ClientNavigation />);
    expect((await screen.findByRole("link", { name: "Carrinho (6)" })).getAttribute("href")).toBe("/library/cart");
    expect(screen.getByRole("link", { name: "Galerias" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Compras" })).toBeTruthy();
    authorized = false; fireEvent.focus(window);
    expect(await screen.findByRole("link", { name: "Carrinho" })).toBeTruthy();
    expect(screen.queryByText("Carrinho (6)")).toBeNull();
  });
});
