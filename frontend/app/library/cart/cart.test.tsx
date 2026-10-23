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
});
