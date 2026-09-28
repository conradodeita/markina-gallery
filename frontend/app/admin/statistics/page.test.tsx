import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ children, href }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href}>{children}</a>
  ),
}));

import StatisticsPage from "./page";

afterEach(() => vi.restoreAllMocks());

describe("estatísticas administrativas", () => {
  it("usa Galeria pública nos filtros visíveis e acessíveis", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/filters")) {
        return Promise.resolve(new Response(JSON.stringify({
          clients: [],
          parent_galleries: [{ id: "public-1", name: "Formatura" }],
          derived_galleries: [],
        }), { status: 200 }));
      }
      if (path.includes("/statistics")) {
        return Promise.resolve(new Response(JSON.stringify({
          purchased_count: 0,
          selected_not_purchased_count: 0,
          purchased_total: 0,
          selected_not_purchased_total: 0,
          revenue_cents: 0,
          revenue_by_day: [],
          purchased_photos: [],
          selected_not_purchased_photos: [],
        }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }));
    render(<StatisticsPage />);
    expect(await screen.findByLabelText("Galeria pública")).toBeTruthy();
    expect(screen.queryByText(/^Acervo$/i)).toBeNull();
  });

  it("mostra paginação independente para listas longas", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      calls.push(path);
      if (path.endsWith("/filters")) {
        return Promise.resolve(new Response(JSON.stringify({
          clients: [], parent_galleries: [], derived_galleries: [],
        }), { status: 200 }));
      }
      if (path.includes("/statistics")) {
        const next = path.includes("purchased_offset=50");
        return Promise.resolve(new Response(JSON.stringify({
          purchased_count: 51,
          selected_not_purchased_count: 0,
          purchased_total: 51,
          selected_not_purchased_total: 0,
          revenue_cents: 100,
          revenue_by_day: [],
          purchased_photos: [{ id: next ? "photo-51" : "photo-1", filename: "foto.jpg" }],
          selected_not_purchased_photos: [],
        }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }));
    render(<StatisticsPage />);
    expect(await screen.findByRole("button", { name: "Próxima" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    expect(await screen.findByText("photo-51")).toBeTruthy();
    expect(calls.some((path) => path.includes("purchased_offset=50"))).toBe(true);
  });

  it("mostra erro de consulta e permite tentar novamente sem zerar indicadores", async () => {
    let statisticsAttempts = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/filters")) {
        return Promise.resolve(new Response(JSON.stringify({
          clients: [], parent_galleries: [], derived_galleries: [],
        }), { status: 200 }));
      }
      if (path.includes("/statistics")) {
        statisticsAttempts += 1;
        if (statisticsAttempts === 1) return Promise.resolve(new Response("", { status: 503 }));
        return Promise.resolve(new Response(JSON.stringify({
          purchased_count: 2,
          selected_not_purchased_count: 0,
          purchased_total: 2,
          selected_not_purchased_total: 0,
          revenue_cents: 1250,
          revenue_by_day: [],
          purchased_photos: [],
          selected_not_purchased_photos: [],
        }), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }));
    render(<StatisticsPage />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText("R$ 0,00")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("2")).toBeTruthy();
    expect(statisticsAttempts).toBe(2);
  });
});
