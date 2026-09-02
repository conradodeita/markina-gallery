import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { formatBrazilianCurrency, maskBrazilianCurrencyInput, parseBrazilianCurrency } from "../galleries/pricing-rules";
import PricingPresetsPage from "./page";

afterEach(() => vi.restoreAllMocks());

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("tabelas globais de preço progressivo", () => {
  it("formata e valida valores em moeda brasileira", () => {
    expect(formatBrazilianCurrency(123456)).toMatch(/R\$\s*1\.234,56/);
    expect(parseBrazilianCurrency("R$ 7,00")).toBe(700);
    expect(parseBrazilianCurrency("1.234,56")).toBe(123456);
    expect(parseBrazilianCurrency("7.00")).toBeNull();
    expect(parseBrazilianCurrency("R$ -1,00")).toBeNull();
    expect(maskBrazilianCurrencyInput("700")).toMatch(/R\$\s*7,00/);
    expect(maskBrazilianCurrencyInput("700000")).toMatch(/R\$\s*7\.000,00/);
  });

  it("lista versões e faixas cadastradas", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      presets: [{
        id: "preset-1",
        code: "01",
        name: "Escolar",
        label: "01 — Escolar",
        version: 2,
        active: true,
        tiers: [
          { minimum_quantity: 1, maximum_quantity: 30, unit_price_cents: 700 },
          { minimum_quantity: 31, maximum_quantity: null, unit_price_cents: 600 },
        ],
      }],
    })));

    render(<PricingPresetsPage />);

    expect(await screen.findByText("01 — Escolar")).toBeTruthy();
    expect(screen.getByText("Versão 2")).toBeTruthy();
    expect(screen.getByText("31–∞ fotos")).toBeTruthy();
    expect(screen.getAllByText(/R\$\s*6,00/).length).toBeGreaterThan(0);
  });

  it("cria uma tabela com faixas contíguas e preços em centavos", async () => {
    const createdPreset = {
      id: "preset-1",
      code: "01",
      name: "Escolar",
      label: "01 — Escolar",
      version: 1,
      active: true,
      tiers: [
        { minimum_quantity: 1, maximum_quantity: 30, unit_price_cents: 700 },
        { minimum_quantity: 31, maximum_quantity: null, unit_price_cents: 600 },
      ],
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ presets: [] }))
      .mockResolvedValueOnce(jsonResponse(createdPreset, 201))
      .mockResolvedValueOnce(jsonResponse({ presets: [createdPreset] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<PricingPresetsPage />);

    await screen.findByText("Nenhuma tabela cadastrada");
    fireEvent.change(screen.getByLabelText("Código"), { target: { value: "01" } });
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Escolar" } });
    fireEvent.change(screen.getByLabelText("Valor unitário"), { target: { value: "700" } });
    expect(screen.getByLabelText("Valor unitário")).toHaveProperty("value", expect.stringMatching(/R\$\s*7,00/));
    fireEvent.click(screen.getByRole("button", { name: "Adicionar faixa" }));
    const upperLimit = screen.getByLabelText("Até");
    fireEvent.change(upperLimit, { target: { value: "30" } });
    const priceInputs = screen.getAllByLabelText("Valor unitário");
    fireEvent.change(priceInputs[1], { target: { value: "600" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar tabela" }));

    await screen.findByText("Tabela criada.");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const request = fetchMock.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(request.body))).toEqual({
      code: "01",
      name: "Escolar",
      tiers: [
        { minimum_quantity: 1, maximum_quantity: 30, unit_price_cents: 700 },
        { minimum_quantity: 31, maximum_quantity: null, unit_price_cents: 600 },
      ],
    });
  });
});
