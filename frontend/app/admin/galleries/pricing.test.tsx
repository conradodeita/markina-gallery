import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery-1" }) }));

import GalleryPricingPage from "./[galleryId]/pricing/page";
import { appendContiguousTier, hasDownwardJump, removeContiguousTier } from "./pricing-rules";

afterEach(() => vi.restoreAllMocks());

describe("configuração comercial da galeria", () => {
  it("remove a edição legada e encaminha para a etapa Vendas da Galeria pública", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      inherited_from_parent_gallery_id: "source-1",
      editable: false,
      tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }],
      pix: { copy_paste: "snapshot-nao-editavel", qr_code_payload: null, instructions: null },
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPricingPage />);

    expect(await screen.findByRole("heading", { name: /Preço e PIX pertencem à Galeria pública/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Abrir etapa Vendas/i }).getAttribute("href")).toBe("/admin/galleries/sources/source-1/edit/vendas");
    expect(screen.queryByRole("button", { name: /salvar/i })).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it("mantém faixas contíguas ao acrescentar e remover", () => {
    const appended = appendContiguousTier([{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }]);
    expect(appended).toEqual([
      { minimum_quantity: 1, maximum_quantity: 1, unit_price_cents: 700 },
      { minimum_quantity: 2, maximum_quantity: null, unit_price_cents: 700 },
    ]);
    expect(removeContiguousTier(appended, 0)).toEqual([
      { minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 },
    ]);
  });

  it("detecta o salto comercial usando valores inteiros em centavos", () => {
    expect(hasDownwardJump([
      { minimum_quantity: 1, maximum_quantity: 10, unit_price_cents: 700 },
      { minimum_quantity: 11, maximum_quantity: null, unit_price_cents: 500 },
    ])).toBe(true);
    expect(hasDownwardJump([
      { minimum_quantity: 1, maximum_quantity: 10, unit_price_cents: 700 },
      { minimum_quantity: 11, maximum_quantity: null, unit_price_cents: 700 },
    ])).toBe(false);
  });
});
