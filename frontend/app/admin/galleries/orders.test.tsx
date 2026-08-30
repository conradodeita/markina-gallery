import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery-1" }) }));

import GalleryOrdersPage from "./[galleryId]/orders/page";

afterEach(() => vi.restoreAllMocks());

describe("pedidos da galeria", () => {
  it("mostra snapshots pendentes sem oferecer confirmação financeira", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ orders: [{
      id: "order-1", payment_status: "pending", total_cents: 1200, client_name: "Ana", created_at: "2026-08-29T10:00:00Z",
      price_rule: { minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 1200 }, sales_message: "Obrigada.",
      pix: { copy_paste: "pix-controlado", qr_code_payload: null, instructions: "Aguarde." },
      items: [{ photo_id: "photo-1", name: "IMG_001.jpg", unit_price_cents: 1200 }],
    }] }), { status: 200 }))));
    render(<GalleryOrdersPage />);
    expect(await screen.findByText(/pendente de confirmação/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Ana · R\$ 12,00/ })).toBeTruthy();
    expect(screen.getByText("IMG_001.jpg · R$ 12,00")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /confirmar/i })).toBeNull();
  });
});
