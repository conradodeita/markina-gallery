import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ children, href }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href}>{children}</a>
  ),
}));

import StatisticsPage from "./page";

afterEach(() => vi.restoreAllMocks());

function reportData(overrides: Record<string, unknown> = {}) {
  return {
    revenue_cents: 0,
    confirmed_order_count: 0,
    sold_photo_count: 0,
    average_order_cents: null,
    eligible_selection_count: 0,
    converted_selection_count: 0,
    conversion_rate_percent: null,
    selection_metrics_available: true,
    orders_total: 0,
    orders: [],
    purchased_total: 0,
    purchased_photos: [],
    selected_not_purchased_total: 0,
    selected_not_purchased_photos: [],
    revenue_by_day: [],
    reconciliations: [],
    abandoned: [],
    selected_not_purchased: [],
    by_gallery: [],
    by_folder: [],
    ...overrides,
  };
}

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
      if (path.includes("/statistics/report")) {
        return Promise.resolve(new Response(JSON.stringify(reportData()), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }));
    render(<StatisticsPage />);
    expect(await screen.findByLabelText("Galeria pública")).toBeTruthy();
    expect(screen.queryByText(/^Acervo$/i)).toBeNull();
    expect(screen.queryByRole("link", { name: "Baixar CSV" })).toBeNull();
  });

  it("combina galeria, pasta e pagamento na consulta e nos relatórios", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      calls.push(path);
      if (path.endsWith("/filters")) {
        return Promise.resolve(new Response(JSON.stringify({
          clients: [{ id: "client-1", name: "Ana" }],
          parent_galleries: [{ id: "gallery-1", name: "Evento" }],
          derived_galleries: [], folders: [{ id: "folder-1", name: "Pasta" }],
        }), { status: 200 }));
      }
      if (path.endsWith("/csv-access")) return Promise.resolve(new Response(JSON.stringify({ allowed: true }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(reportData()), { status: 200 }));
    }));
    render(<StatisticsPage />);
    fireEvent.change(await screen.findByLabelText("Galeria pública"), { target: { value: "gallery-1" } });
    fireEvent.change(screen.getByLabelText("Pasta"), { target: { value: "folder-1" } });
    fireEvent.change(screen.getByLabelText("Pagamento"), { target: { value: "pix" } });
    fireEvent.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    expect(await screen.findByText("Nenhum pedido corresponde aos filtros.")).toBeTruthy();
    expect(calls.some((path) => path.includes("parent_gallery_id=gallery-1") && path.includes("folder_id=folder-1") && path.includes("payment_method=pix"))).toBe(true);
    const csv = await screen.findByRole("link", { name: "Baixar CSV" });
    expect(csv.getAttribute("href")).toContain("parent_gallery_id=gallery-1");
    expect(csv.getAttribute("href")).toContain("folder_id=folder-1");
    expect(csv.getAttribute("href")).toContain("payment_method=pix");
  });

  it("preserva paginação separada para pedidos e listas longas de fotos", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      calls.push(path);
      if (path.endsWith("/filters")) {
        return Promise.resolve(new Response(JSON.stringify({
          clients: [], parent_galleries: [], derived_galleries: [],
        }), { status: 200 }));
      }
      if (path.includes("/statistics/report")) {
        const next = path.includes("purchased_offset=50");
        return Promise.resolve(new Response(JSON.stringify(reportData({
          purchased_total: 51,
          purchased_photos: [{ item_id: next ? "item-51" : "item-1", fotografia_id: next ? "photo-51" : "photo-1",
            fotografia_nome: "foto.jpg", pasta_nome: "Pasta", galeria_nome: "Galeria", total_item: 100, pedido_id: "order" }],
        })), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }));
    render(<StatisticsPage />);
    const pagination = await screen.findByRole("navigation", { name: "Paginação de fotos compradas" });
    fireEvent.click(within(pagination).getByRole("button", { name: "Próxima" }));
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
      if (path.includes("/statistics/report")) {
        statisticsAttempts += 1;
        if (statisticsAttempts === 1) return Promise.resolve(new Response("", { status: 503 }));
        return Promise.resolve(new Response(JSON.stringify(reportData({
          confirmed_order_count: 2,
          revenue_cents: 1250,
        })), { status: 200 }));
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
