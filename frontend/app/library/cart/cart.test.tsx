import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import CartPage from "./page";

vi.mock("next/link", () => ({ default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => <a href={href} {...props}>{children}</a> }));
vi.mock("../../purchase-preview", () => ({ PurchasePreview: ({ name }: { name: string }) => <img alt={name} /> }));
vi.mock("../../selection-deadline", () => ({ SelectionDeadline: () => null }));

const cart = {
  groups: [{ gallery_id: "gallery-1", parent_gallery_id: "parent-1", name: "Evento", quantity: 1,
    total_cents: 100, error: null, browse_url: "/gallery/gallery-1", selection_expires_at: null,
    items: [{ id: "photo-1", name: "Foto 1", folder_name: null, preview_url: "/preview" }] }],
  quantity: 1, can_prepare: true, pix_available: true, total_cents: 100,
};
const prepared = { ...cart, payment: { id: "payment-1", revision: "revision-1", total_cents: 100,
  pix_copy_paste: "PIX-SINTETICO", pix_qr_code: "data:image/png;base64,cGl4", pix_instructions: null, receiver_name: "SINTETICO" } };

describe("carrinho após aposentadoria da InfinitePay", () => {
  it("mantém o PIX manual e não oferece checkout de cartão", async () => {
    const fetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify(init?.method === "POST" ? prepared : cart), { status: 200 },
    ));
    vi.stubGlobal("fetch", fetch);
    render(<CartPage />);

    expect(await screen.findByLabelText("PIX copia e cola")).toHaveProperty("value", "PIX-SINTETICO");
    expect(screen.getByRole("button", { name: "Informar pagamento" })).toBeTruthy();
    expect(screen.queryByText(/InfinitePay/)).toBeNull();
    expect(screen.queryByRole("button", { name: /cartão|InfinitePay/i })).toBeNull();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/library/cart/prepare", expect.objectContaining({ method: "POST" })));
  });

  it("explica o mínimo Mercado Pago e mantém o PIX manual abaixo de R$ 1,00", async () => {
    const lowCart = { ...cart, total_cents: 99, mercadopago_available: true,
      cart_revision: "a".repeat(64) };
    const fetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => new Response(
      JSON.stringify(init?.method === "POST" ? { ...prepared, ...lowCart } : lowCart), { status: 200 },
    ));
    vi.stubGlobal("fetch", fetch);
    render(<CartPage />);

    expect(await screen.findByText(/disponível a partir de R\$ 1,00/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Pagar com PIX do sistema" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Pagar com Mercado Pago" })).toBeNull();
  });

  it("mostra separadamente as compras Mercado Pago em processamento", async () => {
    const active = [
      { id: "11111111-1111-4111-8111-111111111111", provider: "mercadopago",
        method: "credit_card", state: "processing", active: true, total_cents: 100,
        cart_revision: "a".repeat(64), can_cancel: false, items: [] },
      { id: "22222222-2222-4222-8222-222222222222", provider: "mercadopago",
        method: "credit_card", state: "pending", active: true, total_cents: 10500,
        cart_revision: "b".repeat(64), can_cancel: true, items: [] },
    ];
    const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      return new Response(JSON.stringify(url.endsWith("/mercadopago/active")
        ? { payments: active } : init?.method === "POST" ? prepared : cart), { status: 200 });
    });
    vi.stubGlobal("fetch", fetch);
    render(<CartPage />);

    await waitFor(() => expect(screen.getAllByRole("link", { name: "Acompanhar pagamento" })).toHaveLength(2));
    expect(screen.getAllByRole("link", { name: "Acompanhar pagamento" }).map((link) => link.getAttribute("href"))).toEqual([
      "/library/checkout?payment=11111111-1111-4111-8111-111111111111",
      "/library/checkout?payment=22222222-2222-4222-8222-222222222222",
    ]);
    expect(screen.getByText(/Pagamento em processamento · R\$ 1,00/)).toBeTruthy();
    expect(screen.getByText(/Aguardando pagamento · R\$ 105,00/)).toBeTruthy();
  });
});
