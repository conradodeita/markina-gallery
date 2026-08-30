import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useParams: () => ({ galleryId: "gallery-1" }) }));

import GalleryPricingPage from "./[galleryId]/pricing/page";

afterEach(() => vi.restoreAllMocks());

describe("configuração comercial da galeria", () => {
  it("alerta sobre salto comercial antes de enviar as faixas", async () => {
    const fetchMock = vi.fn((_: string, options?: RequestInit) => {
      if (options?.method === "PUT") return Promise.resolve(new Response(JSON.stringify({ tiers: [], pix: {} }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({
        tiers: [
          { minimum_quantity: 1, maximum_quantity: 10, unit_price_cents: 700 },
          { minimum_quantity: 11, maximum_quantity: null, unit_price_cents: 500 },
        ],
        pix: { copy_paste: null, qr_code_payload: null, instructions: null },
      }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<GalleryPricingPage />);

    expect((await screen.findByRole("alert")).textContent).toMatch(/reduz o total/i);
    fireEvent.click(screen.getByRole("button", { name: /salvar regras comerciais/i }));
    expect(confirm).toHaveBeenCalled();
    await waitFor(() => expect(fetchMock).not.toHaveBeenCalledWith(
      expect.anything(), expect.objectContaining({ method: "PUT" }),
    ));
  });

  it("permite acrescentar uma faixa contígua e salva instruções PIX", async () => {
    const fetchMock = vi.fn((_: string, options?: RequestInit) => {
      if (options?.method === "PUT") return Promise.resolve(new Response(JSON.stringify({
        tiers: [{ minimum_quantity: 1, maximum_quantity: 1, unit_price_cents: 700 }, { minimum_quantity: 2, maximum_quantity: null, unit_price_cents: 600 }],
        pix: { copy_paste: "pix-controlado", qr_code_payload: null, instructions: "Aguarde confirmação." },
      }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ tiers: [{ minimum_quantity: 1, maximum_quantity: null, unit_price_cents: 700 }], pix: { copy_paste: null, qr_code_payload: null, instructions: null } }), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<GalleryPricingPage />);

    await screen.findByRole("heading", { name: /preço e pix manual/i });
    fireEvent.click(screen.getByRole("button", { name: /adicionar faixa/i }));
    expect((screen.getByLabelText("Início da faixa 2") as HTMLInputElement).value).toBe("2");
    fireEvent.change(screen.getByLabelText("Copia e cola"), { target: { value: "pix-controlado" } });
    fireEvent.click(screen.getByRole("button", { name: /salvar regras comerciais/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/derived-galleries/gallery-1/pricing",
      expect.objectContaining({ method: "PUT" }),
    ));
    expect(await screen.findByText(/nenhum pagamento foi confirmado/i)).toBeTruthy();
  });
});
