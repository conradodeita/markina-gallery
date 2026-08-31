import { render, screen } from "@testing-library/react";
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
});
